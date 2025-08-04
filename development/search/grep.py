#!/usr/bin/env python3
"""Grep Tool - Fractalic Compatible Implementation

A powerful search tool built on regular expressions. Supports full regex syntax,
file filtering, and multiple output modes. Uses ripgrep if available for performance.
"""

import json
import sys
import re
import os
import subprocess
import fnmatch
from pathlib import Path

def process_data(data):
    """Main processing function for grep search."""
    try:
        # Extract and validate parameters
        pattern = data.get("pattern")
        search_path = data.get("path")
        glob_pattern = data.get("glob")
        output_mode = data.get("output_mode", "files_with_matches")
        context_before = data.get("-B", 0)
        context_after = data.get("-A", 0)
        context_both = data.get("-C")
        show_line_numbers = data.get("-n", False)
        case_insensitive = data.get("-i", False)
        file_type = data.get("type")
        head_limit = data.get("head_limit")
        multiline = data.get("multiline", False)
        
        if not pattern:
            return {"status": "error", "error": "pattern parameter is required"}
        
        # Use current working directory if path not specified
        if search_path is None:
            search_path = os.getcwd()
        
        # Resolve search path
        path_obj = Path(search_path).resolve()
        
        if not path_obj.exists():
            return {"status": "error", "error": f"Search path does not exist: {search_path}"}
        
        # Handle context parameters
        if context_both is not None:
            context_before = context_both
            context_after = context_both
        
        # Try to use ripgrep if available, fallback to Python implementation
        if _has_ripgrep():
            result = _ripgrep_search(
                pattern, path_obj, glob_pattern, output_mode, 
                context_before, context_after, show_line_numbers,
                case_insensitive, file_type, head_limit, multiline
            )
        else:
            result = _python_search(
                pattern, path_obj, glob_pattern, output_mode,
                context_before, context_after, show_line_numbers, 
                case_insensitive, file_type, head_limit, multiline
            )
        
        return {
            "status": "success",
            "data": result
        }
        
    except Exception as e:
        return {"status": "error", "error": str(e)}

def _has_ripgrep():
    """Check if ripgrep is available."""
    try:
        subprocess.run(["rg", "--version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def _ripgrep_search(pattern, search_path, glob_pattern, output_mode, 
                   context_before, context_after, show_line_numbers,
                   case_insensitive, file_type, head_limit, multiline):
    """Use ripgrep for search if available."""
    cmd = ["rg"]
    
    # Add flags
    if case_insensitive:
        cmd.append("-i")
    
    if multiline:
        cmd.extend(["-U", "--multiline-dotall"])
    
    # Add context
    if context_before > 0:
        cmd.extend(["-B", str(context_before)])
    if context_after > 0:
        cmd.extend(["-A", str(context_after)])
    
    # Add output mode
    if output_mode == "files_with_matches":
        cmd.append("-l")
    elif output_mode == "count":
        cmd.append("-c")
    elif output_mode == "content":
        if show_line_numbers:
            cmd.append("-n")
    
    # Add file filtering
    if glob_pattern:
        cmd.extend(["--glob", glob_pattern])
    
    if file_type:
        cmd.extend(["--type", file_type])
    
    # Add pattern and path
    cmd.extend([pattern, str(search_path)])
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0 and result.returncode != 1:
            # ripgrep error (code 1 is no matches, which is OK)
            return {"error": f"ripgrep error: {result.stderr}"}
        
        output = result.stdout.strip()
        
        # Process output based on mode
        return _process_ripgrep_output(output, output_mode, head_limit, pattern, str(search_path))
        
    except subprocess.TimeoutExpired:
        return {"error": "Search timed out after 30 seconds"}
    except Exception as e:
        # Fallback to Python implementation
        return _python_search(
            pattern, search_path, glob_pattern, output_mode,
            context_before, context_after, show_line_numbers,
            case_insensitive, file_type, head_limit, multiline
        )

def _process_ripgrep_output(output, output_mode, head_limit, pattern, search_path):
    """Process ripgrep output into structured format."""
    if not output:
        if output_mode == "files_with_matches":
            return {"files": [], "totalFiles": 0}
        elif output_mode == "count":
            return {"counts": {}, "totalMatches": 0}
        else:
            return {"content": "", "totalMatches": 0}
    
    lines = output.split('\n')
    
    if head_limit and len(lines) > head_limit:
        lines = lines[:head_limit]
    
    if output_mode == "files_with_matches":
        return {"files": lines, "totalFiles": len(lines)}
    elif output_mode == "count":
        counts = {}
        total = 0
        for line in lines:
            if ':' in line:
                file_path, count_str = line.rsplit(':', 1)
                try:
                    count = int(count_str)
                    counts[file_path] = count
                    total += count
                except ValueError:
                    pass
        return {"counts": counts, "totalMatches": total}
    else:  # content mode
        return {"content": '\n'.join(lines), "totalMatches": len(lines)}

def _python_search(pattern, search_path, glob_pattern, output_mode,
                  context_before, context_after, show_line_numbers,
                  case_insensitive, file_type, head_limit, multiline):
    """Python-based search implementation as fallback."""
    try:
        # Compile regex
        flags = re.IGNORECASE if case_insensitive else 0
        if multiline:
            flags |= re.MULTILINE | re.DOTALL
        
        regex = re.compile(pattern, flags)
        
        matches = []
        file_counts = {}
        
        # Search files
        if search_path.is_file():
            files_to_search = [search_path]
        else:
            files_to_search = _get_files_to_search(search_path, glob_pattern, file_type)
        
        for file_path in files_to_search:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                file_matches = list(regex.finditer(content))
                
                if file_matches:
                    if output_mode == "files_with_matches":
                        matches.append(str(file_path))
                    elif output_mode == "count":
                        file_counts[str(file_path)] = len(file_matches)
                    else:  # content mode
                        lines = content.split('\n')
                        for match in file_matches:
                            line_num = content[:match.start()].count('\n') + 1
                            line_content = lines[line_num - 1]
                            
                            match_info = {
                                "file": str(file_path),
                                "line": line_num,
                                "content": line_content.strip(),
                                "match": match.group()
                            }
                            matches.append(match_info)
                            
            except (UnicodeDecodeError, PermissionError, IsADirectoryError):
                continue
        
        # Apply head limit
        if head_limit:
            if output_mode == "content":
                matches = matches[:head_limit]
            elif output_mode == "files_with_matches":
                matches = matches[:head_limit]
        
        # Format output
        if output_mode == "files_with_matches":
            return {"files": matches, "totalFiles": len(matches)}
        elif output_mode == "count":
            total_matches = sum(file_counts.values())
            return {"counts": file_counts, "totalMatches": total_matches}
        else:  # content mode
            if show_line_numbers:
                content_lines = [f"{m['file']}:{m['line']}: {m['content']}" for m in matches]
            else:
                content_lines = [f"{m['file']}: {m['content']}" for m in matches]
            
            return {"content": '\n'.join(content_lines), "totalMatches": len(matches)}
            
    except re.error as e:
        return {"error": f"Invalid regular expression: {str(e)}"}

def _get_files_to_search(search_path, glob_pattern, file_type):
    """Get list of files to search based on filters."""
    files = []
    
    # File type extensions mapping
    type_extensions = {
        "py": [".py"],
        "js": [".js", ".jsx"],
        "ts": [".ts", ".tsx"],
        "go": [".go"],
        "rust": [".rs"],
        "java": [".java"],
        "cpp": [".cpp", ".cc", ".cxx", ".c++"],
        "c": [".c", ".h"],
        "php": [".php"],
        "rb": [".rb"],
        "swift": [".swift"],
        "kt": [".kt"],
        "cs": [".cs"],
        "scala": [".scala"],
        "clj": [".clj", ".cljs"],
        "hs": [".hs"],
        "elm": [".elm"],
        "dart": [".dart"],
        "lua": [".lua"],
        "perl": [".pl", ".pm"],
        "sh": [".sh", ".bash"],
        "sql": [".sql"],
        "xml": [".xml"],
        "html": [".html", ".htm"],
        "css": [".css"],
        "json": [".json"],
        "yaml": [".yaml", ".yml"],
        "toml": [".toml"],
        "md": [".md", ".markdown"],
        "txt": [".txt"],
        "log": [".log"]
    }
    
    for root, dirs, filenames in os.walk(search_path):
        for filename in filenames:
            file_path = Path(root) / filename
            
            # Apply file type filter
            if file_type:
                extensions = type_extensions.get(file_type, [])
                if not any(filename.lower().endswith(ext) for ext in extensions):
                    continue
            
            # Apply glob filter
            if glob_pattern:
                if not fnmatch.fnmatch(filename, glob_pattern):
                    continue
            
            files.append(file_path)
    
    return files

def get_schema():
    """Return Fractalic-compatible JSON schema."""
    return {
        "name": "_grep",
        "description": "A powerful search tool built on ripgrep. Supports full regex syntax (e.g., \"log.*Error\", \"function\\\\s+\\\\w+\"). Filter files with glob parameter (e.g., \"*.js\", \"**/*.tsx\") or type parameter (e.g., \"js\", \"py\", \"rust\"). Output modes: \"content\" shows matching lines, \"files_with_matches\" shows only file paths (default), \"count\" shows match counts.",
        "parameters": {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "The regular expression pattern to search for in file contents"
                },
                "path": {
                    "type": "string",
                    "description": "File or directory to search in (rg PATH). Defaults to current working directory."
                },
                "glob": {
                    "type": "string",
                    "description": "Glob pattern to filter files (e.g. \"*.js\", \"*.{ts,tsx}\") - maps to rg --glob"
                },
                "output_mode": {
                    "type": "string",
                    "enum": ["content", "files_with_matches", "count"],
                    "description": "Output mode: \"content\" shows matching lines, \"files_with_matches\" shows file paths, \"count\" shows match counts. Defaults to \"files_with_matches\".",
                    "default": "files_with_matches"
                },
                "-B": {
                    "type": "number",
                    "description": "Number of lines to show before each match (rg -B). Requires output_mode: \"content\", ignored otherwise."
                },
                "-A": {
                    "type": "number", 
                    "description": "Number of lines to show after each match (rg -A). Requires output_mode: \"content\", ignored otherwise."
                },
                "-C": {
                    "type": "number",
                    "description": "Number of lines to show before and after each match (rg -C). Requires output_mode: \"content\", ignored otherwise."
                },
                "-n": {
                    "type": "boolean",
                    "description": "Show line numbers in output (rg -n). Requires output_mode: \"content\", ignored otherwise.",
                    "default": False
                },
                "-i": {
                    "type": "boolean",
                    "description": "Case insensitive search (rg -i)",
                    "default": False
                },
                "type": {
                    "type": "string",
                    "description": "File type to search (rg --type). Common types: js, py, rust, go, java, etc. More efficient than include for standard file types."
                },
                "head_limit": {
                    "type": "number",
                    "description": "Limit output to first N lines/entries, equivalent to \"| head -N\". Works across all output modes."
                },
                "multiline": {
                    "type": "boolean",
                    "description": "Enable multiline mode where . matches newlines and patterns can span lines (rg -U --multiline-dotall). Default: false.",
                    "default": False
                }
            },
            "required": ["pattern"],
            "additionalProperties": False
        }
    }

def main():
    """Main entry point for the tool."""
    # Discovery test (REQUIRED)
    if len(sys.argv) == 2 and sys.argv[1] == '{"__test__": true}':
        print(json.dumps({"success": True, "_simple": True}))
        return
    
    # Schema dump (REQUIRED)
    if len(sys.argv) == 2 and sys.argv[1] == "--fractalic-dump-schema":
        print(json.dumps(get_schema(), indent=2))
        return
    
    # Main execution
    if len(sys.argv) != 2:
        print(json.dumps({"status": "error", "error": "Expected exactly one JSON argument"}))
        sys.exit(1)
    
    try:
        params = json.loads(sys.argv[1])
        if not isinstance(params, dict):
            raise ValueError("Input must be a JSON object")
        
        result = process_data(params)
        print(json.dumps(result, ensure_ascii=False))
        
        # Exit with appropriate code
        if result.get("status") == "error":
            sys.exit(1)
        
    except json.JSONDecodeError as e:
        print(json.dumps({"status": "error", "error": f"Invalid JSON input: {str(e)}"}))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"status": "error", "error": str(e)}))
        sys.exit(1)

if __name__ == "__main__":
    main()