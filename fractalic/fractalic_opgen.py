#!/usr/bin/env python3
"""
fractalic_opgen.py – Generate Fractalic operation blocks
─────────────────────────────────────────────────────────

Simple JSON Discovery Tool for generating Fractalic operation YAML blocks.

This tool provides a unified interface for creating all types of Fractalic operations
through JSON input, returning structured responses with ready-to-insert YAML blocks.

Usage modes:
 • Called with '{"__test__": true}'     → {"success": true, "_simple": true}
 • Called with JSON operation data      → generates YAML block and returns structured result
 • Called with --fractalic-dump-schema  → prints tool schema for autodiscovery

JSON Operations supported:
 • {"op": "llm", "prompt": "...", ...}     → LLM operation: Call Large Language Models
 • {"op": "shell", "prompt": "...", ...}   → Shell operation: Execute OS commands  
 • {"op": "import", "file": "...", ...}    → Import operation: Include content from files
 • {"op": "goto", "block": "...", ...}     → Goto operation: Jump to workflow blocks
 • {"op": "run", "file": "...", ...}       → Run operation: Execute sub-workflows
 • {"op": "return", "prompt": "...", ...}  → Return operation: Emit final results

Features:
 • Rich parameter validation with detailed error messages
 • Structured JSON responses with success/error status  
 • No line-wrapping in generated YAML output
 • Support for all Fractalic operation types and parameters
 • Auto-generated schema for tool discovery systems

Drop this file in your tools/ directory for automatic discovery by Fractalic.
"""
from __future__ import annotations
import json, sys, yaml
from enum import Enum
from typing import Any, Dict, Type, Literal
from pydantic import BaseModel, Field, ValidationError

# ───────────── shared enum
class Mode(str, Enum):
    """How the generated content is written into its target block."""
    append  = "append"   # add after existing content
    prepend = "prepend"  # add before existing content
    replace = "replace"  # overwrite the target block completely

# ───────────── Pydantic models (one per operation)

class LLM(BaseModel):
    """
    Invoke a Large-Language-Model (OpenAI, Anthropic, etc.) and insert
    its response into the active Fractalic context.

    • `prompt` / `block` construct the request messages.  
    • The response is written into the block identified by `to`
      (default: the same one the @llm lives in).  
    • If `tools` is set to "all" Fractalic exposes every registered
      MCP tool to the model so it can emit subsequent tool-calls.
    """
    op: Literal["llm"] = Field("llm", description="Operation tag")
    prompt: str | None = Field(
        None,
        description="Prompt text sent to the language model. Use \\n for explicit newlines."
    )
    block: str | list[str] | None = Field(
        None,
        description="Block label(s) whose *contents* are prepended to the prompt as additional context."
    )
    model: str | None = Field(
        None,
        description="Specific model override (e.g. gpt-4o, claude-3-sonnet). If omitted the project default is used."
    )
    tools: str | list[str] | None = Field(
        "none",
        description='Which tools the model may call within this @llm run. Allowed values: "none" (default), "all", or a list of explicit tool names.'
    )
    temperature: float | None = Field(
        None,
        description="Sampling temperature (0..2). 0 = deterministic; higher values → more creative / random."
    )
    stop: list[str] | None = Field(
        None,
        alias="stop-sequences",
        description="Array of hard stop sequences: generation truncates when any is seen in the output."
    )
    save_to_file: str | None = Field(
        None,
        alias="save-to-file",
        description="Path to file where response will be saved, overwrites existing file."
    )
    use_header: str | None = Field(
        None,
        alias="use-header",
        description="Header for the block that will contain LLM response."
    )
    mode: str | None = Field(
        None,
        description="How to insert LLM response into target block (append, prepend, replace)."
    )
    to: str | None = Field(
        None,
        description="Target block where LLM response will be placed."
    )
    provider: str | None = Field(
        None,
        description="Optional LLM provider to override the default setting."
    )
    media: list[str] | None = Field(
        None,
        description="Paths to media files to add with context or prompt."
    )

class Shell(BaseModel):
    """
    Execute an **OS shell command** (`bash`, PowerShell on Windows, etc.),
    capture *stdout*/*stderr*, and write the result back into the context.

    Typical use-cases: git status, unit-test runs, CLI data scrapers.
    """
    op: Literal["shell"] = Field("shell", description="Operation tag")
    prompt: str = Field(
        None,
        description="The exact shell command to run."
    )
    use_header: str | None = Field(
        "# OS Shell Tool response block",
        alias="use-header",
        description="A comment-style header inserted *before* the captured "
                    "command output so humans can spot it easily."
    )
    mode: Mode = Field(
        Mode.append,
        description="How to merge the captured output into the destination "
                    "block (append / prepend / replace)."
    )
    to: str | None = Field(
        None,
        description="Label of the *destination* block to write into. "
                    "If omitted the operation's own block is used."
    )
    run_once: bool = Field(
        False,
        alias="run-once",
        description="If true, Fractalic caches the result on first run and "
                    "skips execution in subsequent passes (idempotent)."
    )

class Import(BaseModel):
    """
    Copy a fragment from another **Markdown file** into the current context.

    Handy for re-using templates, spec snippets, or any boiler-plate.
    """
    op: Literal["import"] = Field("import", description="Operation tag")
    file: str = Field(
        None,
        description="Path of the *source* markdown file (relative or absolute)."
    )
    block: str | list[str] | None = Field(
        None,
        description="Optional block label(s) *inside* the file to import. If omitted the entire file is imported."
    )
    mode: Mode = Field(
        Mode.append,
        description="append / prepend / replace when writing into the target."
    )
    to: str | None = Field(
        None,
        description="Name of the *destination* block inside the current file."
    )
    run_once: bool = Field(
        False,
        alias="run-once",
        description="Import only once per session even if the flow loops back."
    )

class Goto(BaseModel):
    """
    Jump execution to another **block** within the *same* markdown file.
    Essentially a labelled `goto` for branching workflows.
    """
    op: Literal["goto"] = Field("goto", description="Operation tag")
    block: str | list[str] | None = Field(
        None,
        description="Destination block label(s). Must exist in the current file."
    )
    run_once: bool = Field(
        False,
        alias="run-once",
        description="If true this jump is ignored after the first pass."
    )

class Run(BaseModel):
    """
    Execute an **entire sub-flow** (another Fractalic markdown file) in the
    current session and then return to the caller.

    Great for reusable routines like `unit_test.md` or `deploy.md`.
    """
    op: Literal["run"] = Field("run", description="Operation tag")
    file: str = Field(
        None,
        description="Path to the markdown workflow file to execute."
    )
    prompt: str | None = Field(
        None,
        description="Optional text displayed in logs *before* the sub-flow "
                    "starts (acts like a title)."
    )
    block: str | list[str] | None = Field(
        None,
        description="Block label(s) injected into the sub-flow context so it "
                    "can read from the parent workflow."
    )
    use_header: str | None = Field(
        None,
        alias="use-header",
        description="Header inserted before the *returned* output."
    )
    mode: Mode = Field(
        Mode.append,
        description="append / prepend / replace when writing the sub-flow "
                    "result into the destination block."
    )
    to: str | None = Field(
        None,
        description="Target block label for the sub-flow output."
    )
    run_once: bool = Field(
        False,
        alias="run-once",
        description="Execute only the first time—subsequent calls are skipped."
    )

class Return(BaseModel):
    """
    Emit a **final result** back to the user or to the *caller* flow.
    Often used at the end of a long chain to expose the outcome.
    """
    op: Literal["return"] = Field("return", description="Operation tag")
    prompt: str | None = Field(
        None,
        description="Text returned to the user (or parent flow) verbatim."
    )
    block: str | list[str] | None = Field(
        None,
        description="Block content returned upward instead of plain text."
    )
    use_header: str | None = Field(
        None,
        alias="use-header",
        description="Header inserted before the returned text / block."
    )

# ───────────── map CLI sub-command → (tag, model)
OP_MAP: dict[str, tuple[str, Type[BaseModel]]] = {
    "llm":    ("@llm",     LLM),
    "shell":  ("@shell",   Shell),
    "import": ("@import",  Import),
    "goto":   ("@goto",    Goto),
    "run":    ("@run",     Run),
    "return": ("@return",  Return),
}

# ───────────── utilities
def enum_to_str(obj):
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, dict):
        return {k: enum_to_str(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [enum_to_str(v) for v in obj]
    return obj

def emit_yaml_block(tag: str, params: Dict[str, Any]) -> None:
    # Remove 'op' field from params
    params = {k: v for k, v in params.items() if k != 'op'}
    params = enum_to_str(params)
    # Custom YAML dumper to use '|' for multiline strings
    class LiteralStr(str): pass
    def literal_str_representer(dumper, data):
        return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
    yaml.add_representer(LiteralStr, literal_str_representer)
    def to_literal_str(val):
        if isinstance(val, str) and '\n' in val:
            return LiteralStr(val)
        return val
    params = {k: to_literal_str(v) if not isinstance(v, list) else [to_literal_str(i) for i in v] for k, v in params.items()}
    print(tag)
    # Dump YAML with no indent for top-level fields, indent for arrays, and no line wrapping
    yaml_str = yaml.dump(params, sort_keys=False, allow_unicode=True, default_flow_style=False, width=float('inf'))
    # Remove the first line '---' if present
    if yaml_str.startswith('---'):
        yaml_str = '\n'.join(yaml_str.splitlines()[1:])
    print(yaml_str.rstrip())

def merged_schema() -> dict:
    """
    Output a single OpenAI-compatible schema with 'op' as enum and all possible fields at the top level.
    This is used for Simple JSON Discovery single-tool schema.
    """
    # Collect all fields from all models
    all_fields = {}
    op_values = []
    descriptions = {}
    for op_name, (_, Model) in OP_MAP.items():
        op_values.append(op_name)
        sch = Model.model_json_schema()
        for fname, fdef in sch.get("properties", {}).items():
            if fname == "op":
                continue
            # If field already exists, skip or merge description
            if fname not in all_fields:
                all_fields[fname] = fdef
                descriptions[fname] = fdef.get("description", "")
            else:
                # Merge descriptions if different
                if fdef.get("description") and fdef.get("description") not in descriptions[fname]:
                    descriptions[fname] += f" / {fdef.get('description')}"
    
    # Add op field
    all_fields["op"] = {
        "type": "string",
        "enum": op_values,
        "description": "Operation type: one of " + ", ".join(op_values)
    }
    
    # Add merged descriptions back
    for fname, desc in descriptions.items():
        if desc:
            all_fields[fname]["description"] = desc
    
    # Return Simple JSON Discovery compatible schema
    return {
        "name": "fractalic_opgen",
        "description": (
            "Generate a single Fractalic operation block in YAML syntax.\n"
            "Supported operations (set the 'op' parameter):\n"
            "  - llm:    Call a Large Language Model and insert its response.\n"
            "  - shell:  Execute a shell command and capture output.\n"
            "  - import: Import content from another markdown file.\n"
            "  - goto:   Jump execution to another block in the same file.\n"
            "  - run:    Execute a sub-workflow (another markdown file).\n"
            "  - return: Return content and terminate execution.\n"
            "Select the operation and provide the appropriate parameters. "
            "The tool returns ready-to-insert YAML text within a structured JSON response."
        ),
        "parameters": {
            "type": "object",
            "properties": all_fields,
            "required": ["op"],
            "additionalProperties": False
        },
        "examples": [
            {
                "description": "Execute a shell command and capture output",
                "input": {
                    "op": "shell",
                    "prompt": "ls -la",
                    "mode": "prepend",
                    "to": "setup"
                }
            },
            {
                "description": "Call LLM with specific model and temperature",
                "input": {
                    "op": "llm",
                    "prompt": "Summarise today's changelog",
                    "model": "gpt-4o",
                    "temperature": 0.3
                }
            },
            {
                "description": "Execute a sub-workflow and capture result",
                "input": {
                    "op": "run",
                    "file": "deploy.md",
                    "prompt": "Deploy to staging",
                    "mode": "replace",
                    "to": "deployment-log"
                }
            },
            {
                "description": "Import content from another markdown file",
                "input": {
                    "op": "import",
                    "file": "templates/header.md",
                    "block": "title",
                    "mode": "prepend",
                    "to": "document-start"
                }
            },
            {
                "description": "Return final result to user",
                "input": {
                    "op": "return",
                    "prompt": "Processing completed successfully!",
                    "use-header": "# Final Result"
                }
            }
        ]
    }

# ───────────── Simple JSON Discovery schema functions only

def detailed_operations_info() -> dict:
    """
    Provides detailed documentation for each operation type.
    This gives the same rich information as the original tool_descriptor but in JSON Discovery format.
    """
    return {
        "operations": [
            {
                "op": "llm",
                "description": "Call a Large Language Model and insert its response.",
                "use_cases": ["Generate content", "Analyze text", "Code completion", "Translation"],
                "parameters": [
                    {"name": "prompt", "type": "string", "required": False, "description": "Prompt text sent to the language model. Use \\n for explicit newlines."},
                    {"name": "block", "type": "string | array", "required": False, "description": "Block label(s) whose *contents* are prepended to the prompt as additional context."},
                    {"name": "model", "type": "string", "required": False, "description": "Specific model override (e.g. gpt-4o, claude-3-sonnet). If omitted the project default is used."},
                    {"name": "tools", "type": "string | array", "required": False, "description": "Which tools the model may call within this @llm run. Allowed values: 'none' (default), 'all', or a list of explicit tool names."},
                    {"name": "temperature", "type": "float", "required": False, "description": "Sampling temperature (0..2). 0 = deterministic; higher values → more creative / random."},
                    {"name": "stop-sequences", "type": "array", "required": False, "description": "Array of hard stop sequences: generation truncates when any is seen in the output."},
                    {"name": "save-to-file", "type": "string", "required": False, "description": "Path to file where response will be saved, overwrites existing file."},
                    {"name": "use-header", "type": "string", "required": False, "description": "Header for the block that will contain LLM response."},
                    {"name": "mode", "type": "string", "required": False, "description": "How to insert LLM response into target block (append, prepend, replace)."},
                    {"name": "to", "type": "string", "required": False, "description": "Target block where LLM response will be placed."},
                    {"name": "provider", "type": "string", "required": False, "description": "Optional LLM provider to override the default setting."},
                    {"name": "media", "type": "array", "required": False, "description": "Paths to media files to add with context or prompt."}
                ]
            },
            {
                "op": "shell",
                "description": "Execute a shell command and capture output.",
                "use_cases": ["Run tests", "Git operations", "File system commands", "Build scripts"],
                "parameters": [
                    {"name": "prompt", "type": "string", "required": True, "description": "The exact shell command to run."},
                    {"name": "use-header", "type": "string", "required": False, "description": "A comment-style header inserted before the captured command output so humans can spot it easily."},
                    {"name": "mode", "type": "string", "required": False, "description": "How to merge the captured output into the destination block (append / prepend / replace)."},
                    {"name": "to", "type": "string", "required": False, "description": "Label of the destination block to write into. If omitted the operation's own block is used."},
                    {"name": "run-once", "type": "boolean", "required": False, "description": "If true, Fractalic caches the result on first run and skips execution in subsequent passes (idempotent)."}
                ]
            },
            {
                "op": "import",
                "description": "Import content from another markdown file.",
                "use_cases": ["Reuse templates", "Include boilerplate", "Share content blocks", "Modular workflows"],
                "parameters": [
                    {"name": "file", "type": "string", "required": True, "description": "Path of the source markdown file (relative or absolute)."},
                    {"name": "block", "type": "string | array", "required": False, "description": "Optional block label(s) inside the file to import. If omitted the entire file is imported."},
                    {"name": "mode", "type": "string", "required": False, "description": "append / prepend / replace when writing into the target."},
                    {"name": "to", "type": "string", "required": False, "description": "Name of the destination block inside the current file."},
                    {"name": "run-once", "type": "boolean", "required": False, "description": "Import only once per session even if the flow loops back."}
                ]
            },
            {
                "op": "goto",
                "description": "Jump execution to another block in the same file.",
                "use_cases": ["Conditional branching", "Loop workflows", "Skip sections", "Dynamic flow control"],
                "parameters": [
                    {"name": "block", "type": "string | array", "required": True, "description": "Destination block label(s). Must exist in the current file."},
                    {"name": "run-once", "type": "boolean", "required": False, "description": "If true this jump is ignored after the first pass."}
                ]
            },
            {
                "op": "run",
                "description": "Execute a sub-workflow (another markdown file).",
                "use_cases": ["Reusable workflows", "Testing suites", "Deployment scripts", "Modular processes"],
                "parameters": [
                    {"name": "file", "type": "string", "required": True, "description": "Path to the markdown workflow file to execute."},
                    {"name": "prompt", "type": "string", "required": False, "description": "Optional text displayed in logs before the sub-flow starts (acts like a title)."},
                    {"name": "block", "type": "string | array", "required": False, "description": "Block label(s) injected into the sub-flow context so it can read from the parent workflow."},
                    {"name": "use-header", "type": "string", "required": False, "description": "Header inserted before the returned output."},
                    {"name": "mode", "type": "string", "required": False, "description": "append / prepend / replace when writing the sub-flow result into the destination block."},
                    {"name": "to", "type": "string", "required": False, "description": "Target block label for the sub-flow output."},
                    {"name": "run-once", "type": "boolean", "required": False, "description": "Execute only the first time—subsequent calls are skipped."}
                ]
            },
            {
                "op": "return",
                "description": "Return content and terminate execution.",
                "use_cases": ["Final results", "Early termination", "Status reporting", "Output generation"],
                "parameters": [
                    {"name": "prompt", "type": "string", "required": False, "description": "Text returned to the user (or parent flow) verbatim."},
                    {"name": "block", "type": "string | array", "required": False, "description": "Block content returned upward instead of plain text."},
                    {"name": "use-header", "type": "string", "required": False, "description": "Header inserted before the returned text / block."}
                ]
            }
        ]
    }

# ───────────── main
def process_json_data(data: dict) -> dict:
    """Process JSON input data and generate fractalic operation block."""
    try:
        # Validate that 'op' is provided
        op = data.get("op")
        if not op:
            return {"error": "Missing required field 'op'"}
        
        if op not in OP_MAP:
            return {"error": f"Unknown operation: {op}. Valid operations: {list(OP_MAP.keys())}"}

        # Manual required checks for each operation
        required_fields = {
            "shell": ["prompt"],
            "import": ["file"],
            "goto": ["block"],
            "run": ["file"],
        }
        
        if op in required_fields:
            for field in required_fields[op]:
                if field not in data or data[field] is None:
                    return {"error": f"Missing required field '{field}' for operation '{op}'"}

        # Get the model for this operation
        tag, Model = OP_MAP[op]
        
        # Validate and create the model instance
        try:
            model_instance = Model(**data)
            params = model_instance.model_dump(by_alias=True, exclude_none=True)
        except ValidationError as e:
            return {"error": f"Validation error: {str(e)}"}
        
        # Generate YAML block
        import io
        import contextlib
        
        # Capture the YAML output
        yaml_output = io.StringIO()
        with contextlib.redirect_stdout(yaml_output):
            emit_yaml_block(tag, params)
        
        yaml_content = yaml_output.getvalue()
        
        return {
            "success": True,
            "operation": op,
            "yaml": yaml_content,
            "parameters": {k: v for k, v in params.items() if k != 'op'}
        }
        
    except Exception as e:
        return {"error": f"Processing error: {str(e)}"}

def main() -> None:
    # Simple JSON Discovery: respond to test input
    if len(sys.argv) == 2 and sys.argv[1] == '{"__test__": true}':
        print(json.dumps({"success": True, "_simple": True}))
        return

    # Schema dump for autodiscovery
    if len(sys.argv) == 2 and sys.argv[1] == "--fractalic-dump-schema":
        print(json.dumps(merged_schema(), ensure_ascii=False, indent=2))
        return

    # Simple JSON mode: accept JSON input
    if len(sys.argv) == 2:
        try:
            params = json.loads(sys.argv[1])
            if not isinstance(params, dict):
                print(json.dumps({"error": "Input must be a JSON object"}))
                sys.exit(1)
            
            result = process_json_data(params)
            print(json.dumps(result, ensure_ascii=False))
            
            # Exit with error code if there was an error
            if "error" in result:
                sys.exit(1)
                
        except json.JSONDecodeError as e:
            print(json.dumps({"error": f"Invalid JSON: {str(e)}"}))
            sys.exit(1)
        except Exception as e:
            print(json.dumps({"error": f"Unexpected error: {str(e)}"}))
            sys.exit(1)
        return

    # If no valid argument provided, show usage
    print(json.dumps({
        "error": "Usage: fractalic_opgen.py <JSON_OPERATION> or --fractalic-dump-schema",
        "example": '{"op": "shell", "prompt": "ls -la"}'
    }))
    sys.exit(1)

if __name__ == "__main__":
    main()
