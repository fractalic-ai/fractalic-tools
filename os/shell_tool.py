#!/usr/bin/env python3
"""
Shell Tool - Simple JSON Discovery Tool
Execute shell commands with persistent working directory state.
"""
import sys
import os
import json
import subprocess
import re
from pathlib import Path

# ─────────────────────────── Configuration ──────────────────────────
STATE_FILE = Path.home() / ".shell_tool_cwd"

def process_data(data):
    """Main processing function for Simple JSON Discovery."""
    cmd = data.get("cmd")
    cd = data.get("cd")
    reset = data.get("reset", False)
    timeout = data.get("timeout", False)  # Default to no timeout
    
    # Determine starting directory
    # cwd = Path.cwd() if reset else load_last_cwd()  # Commented out persistent state
    cwd = Path.cwd()  # Always use current working directory
    
    # Apply directory change if provided
    if cd:
        try:
            new_dir = Path(cd).expanduser()
            if not new_dir.is_absolute():
                new_dir = (cwd / new_dir).resolve()
            else:
                new_dir = new_dir.resolve()
            
            if not new_dir.is_dir():
                return {"error": f"Directory does not exist: '{cd}' -> '{new_dir}'"}
            cwd = new_dir
        except Exception as e:
            return {"error": f"Failed to change directory to '{cd}': {e}"}
    
    # Build result
    result = {"cwd": str(cwd)}
    
    # Execute command if provided
    if cmd:
        try:
            exec_result = run_shell(cmd, cwd, timeout)
            
            # Truncate command field to prevent token bloat from large heredocs/file writes
            command_display = cmd
            if len(cmd) > 256:
                command_display = cmd[:256] + f"... [truncated, original length: {len(cmd)} chars]"
            
            result.update({
                "command": command_display,
                "stdout": exec_result["stdout"],
                "stderr": exec_result["stderr"],
                "returncode": exec_result["returncode"],
                "success": exec_result["returncode"] == 0
            })
        except Exception as e:
            return {"error": f"Failed to execute command: {e}", "cwd": str(cwd)}
    else:
        result["message"] = f"Working directory set to {cwd}"
    
    # Save directory state
    # save_cwd(cwd)  # Commented out persistent state saving
    return result

# ─────────────────────────── Schema Definition ──────────────────────
def get_schema():
    """Return the JSON schema for this tool (single-tool schema)."""
    return {
        "name": "shell",
        "description": "Execute shell commands with configurable timeout. Uses current working directory as base. Command field in response is truncated to 256 chars for token efficiency when writing large files. IMPORTANT: For file reading, use efficient strategies - check file size first with 'wc -l filename' before using 'cat'. For large files (>100 lines), use targeted extraction like 'head -30', 'grep pattern', or 'sed -n \"10,30p\"' instead of full 'cat' to prevent massive token usage.",
        "parameters": {
            "type": "object",
            "properties": {
                "cmd": {
                    "type": "string",
                    "description": "Shell command to execute (e.g., 'ls -la', 'git status'). Optional if only changing directory."
                },
                "cd": {
                    "type": "string",
                    "description": "Directory to change into before executing command. Can be absolute or relative to current working directory."
                },
                "reset": {
                    "type": "boolean",
                    "default": False,
                    "description": "If true, reset to the original directory instead of using saved state. Default: false."
                },
                "timeout": {
                    "type": ["number", "boolean"],
                    "default": False,
                    "description": "Command timeout in seconds. Set to false (default) for no timeout, or a positive number for timeout in seconds."
                }
            },
            "required": []
        }
    }

# ─────────────────────────── Helper Functions ───────────────────────
def strip_ansi_codes(text):
    """Remove ANSI escape sequences from text."""
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)

def load_last_cwd():
    """Return the directory stored in STATE_FILE, or the current dir if absent."""
    # Commented out persistent state loading - always use current directory
    # try:
    #     saved = STATE_FILE.read_text().strip()
    #     if saved and Path(saved).is_dir():
    #         return Path(saved)
    # except FileNotFoundError:
    #     pass
    return Path.cwd()

def save_cwd(path):
    """Persist the given path for next launch."""
    # Commented out persistent state saving
    # try:
    #     STATE_FILE.write_text(str(path))
    # except Exception as e:
    #     # Don't fail on state file errors, just warn
    #     pass
    pass

def run_shell(cmd, cwd, timeout=False):
    """Execute cmd in cwd; return a dict with stdout/err/returncode."""
    # Convert timeout parameter - False means no timeout, number means timeout in seconds
    timeout_value = None if timeout is False else timeout
    
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            cwd=str(cwd),
            executable="/bin/bash",  # use bash for common built-ins
            timeout=timeout_value
        )
        return {
            "stdout": strip_ansi_codes(result.stdout),
            "stderr": strip_ansi_codes(result.stderr),
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired as e:
        return {
            "stdout": e.stdout.decode() if e.stdout else "",
            "stderr": e.stderr.decode() if e.stderr else f"Command timed out after {timeout} seconds",
            "returncode": -1,  # Use -1 to indicate timeout
        }

# ─────────────────────────── Main Entrypoint ────────────────────────
def main():
    # Simple JSON Discovery: respond to test input
    if len(sys.argv) == 2 and sys.argv[1] == '{"__test__": true}':
        print(json.dumps({"success": True, "_simple": True}))
        return

    # Schema dump for autodiscovery
    if len(sys.argv) == 2 and sys.argv[1] == "--fractalic-dump-schema":
        print(json.dumps(get_schema(), indent=2))
        return

    # Main: expect a single JSON argument
    if len(sys.argv) != 2:
        print(json.dumps({"error": "Expected exactly one JSON argument"}))
        sys.exit(1)

    try:
        params = json.loads(sys.argv[1])
        if not isinstance(params, dict):
            raise ValueError("Input must be a JSON object")

        result = process_data(params)
        print(json.dumps(result, ensure_ascii=False))
        
        # Exit with command return code if command was executed
        if "returncode" in result:
            sys.exit(result["returncode"])
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)

if __name__ == "__main__":
    main()
