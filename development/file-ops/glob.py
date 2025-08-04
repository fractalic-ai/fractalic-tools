#!/usr/bin/env python3
"""Glob Tool - Fractalic Compatible Implementation

Fast file pattern matching tool that works with any codebase size.
Supports glob patterns and returns matching file paths sorted by modification time.
"""

import json
import sys
import fnmatch
import os
from pathlib import Path

def process_data(data):
    """Main processing function for glob pattern matching."""
    try:
        # Extract and validate parameters
        pattern = data.get("pattern")
        search_path = data.get("path")
        
        if not pattern:
            return {"status": "error", "error": "pattern parameter is required"}
        
        # Use current working directory if path not specified
        if search_path is None:
            search_path = os.getcwd()
        
        # Resolve and validate search path
        path_obj = Path(search_path).resolve()
        
        if not path_obj.exists():
            return {"status": "error", "error": f"Search path does not exist: {search_path}"}
        
        if not path_obj.is_dir():
            return {"status": "error", "error": f"Search path is not a directory: {search_path}"}
        
        # Perform glob search
        matches = _perform_glob_search(path_obj, pattern)
        
        return {
            "status": "success",
            "data": {
                "pattern": pattern,
                "searchPath": str(path_obj),
                "matches": matches,
                "totalMatches": len(matches)
            }
        }
        
    except Exception as e:
        return {"status": "error", "error": str(e)}

def _perform_glob_search(search_path, pattern):
    """Perform the actual glob search with proper pattern handling."""
    matches = []
    
    # Handle different pattern types
    if "**" in pattern:
        # Recursive pattern
        matches = _recursive_glob(search_path, pattern)
    else:
        # Non-recursive pattern
        matches = _simple_glob(search_path, pattern)
    
    # Sort by modification time (most recent first)
    try:
        matches.sort(key=lambda x: Path(x).stat().st_mtime, reverse=True)
    except (OSError, FileNotFoundError):
        # If there's an issue with file stats, just return unsorted
        pass
    
    return matches

def _recursive_glob(search_path, pattern):
    """Handle recursive glob patterns with **."""
    matches = []
    
    # Split pattern on **
    if "**" in pattern:
        parts = pattern.split("**")
        if len(parts) == 2:
            prefix = parts[0].rstrip("/")
            suffix = parts[1].lstrip("/")
            
            # Walk the directory tree
            for root, dirs, files in os.walk(search_path):
                root_path = Path(root)
                
                # Check if prefix matches
                if prefix:
                    rel_path = root_path.relative_to(search_path)
                    if not fnmatch.fnmatch(str(rel_path), prefix + "*"):
                        continue
                
                # Check files against suffix pattern
                for file in files:
                    if not suffix or fnmatch.fnmatch(file, suffix):
                        matches.append(str(root_path / file))
                
                # Check directories against suffix pattern if no file extension in suffix
                if suffix and "." not in suffix:
                    for dir_name in dirs:
                        if fnmatch.fnmatch(dir_name, suffix):
                            matches.append(str(root_path / dir_name))
        else:
            # Complex ** pattern, fallback to simple recursive
            for root, dirs, files in os.walk(search_path):
                for file in files:
                    file_path = Path(root) / file
                    rel_path = file_path.relative_to(search_path)
                    if fnmatch.fnmatch(str(rel_path), pattern):
                        matches.append(str(file_path))
    
    return matches

def _simple_glob(search_path, pattern):
    """Handle simple (non-recursive) glob patterns."""
    matches = []
    
    try:
        # Handle patterns with directory separators
        if "/" in pattern:
            # Pattern includes path components
            pattern_path = Path(pattern)
            if pattern_path.is_absolute():
                # Absolute pattern
                start_path = Path(pattern).parent
                file_pattern = pattern_path.name
            else:
                # Relative pattern
                start_path = search_path / pattern_path.parent
                file_pattern = pattern_path.name
            
            if start_path.exists() and start_path.is_dir():
                for item in start_path.iterdir():
                    if fnmatch.fnmatch(item.name, file_pattern):
                        matches.append(str(item))
        else:
            # Simple filename pattern
            for item in search_path.iterdir():
                if fnmatch.fnmatch(item.name, pattern):
                    matches.append(str(item))
    
    except (OSError, PermissionError):
        # Handle permission errors gracefully
        pass
    
    return matches

def get_schema():
    """Return Fractalic-compatible JSON schema."""
    return {
        "name": "_glob",
        "description": "Fast file pattern matching tool that works with any codebase size. Supports glob patterns like \"**/*.js\" or \"src/**/*.ts\". Returns matching file paths sorted by modification time. Use this tool when you need to find files by name patterns.",
        "parameters": {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "The glob pattern to match files against"
                },
                "path": {
                    "type": "string",
                    "description": "The directory to search in. If not specified, the current working directory will be used. IMPORTANT: Omit this field to use the default directory. DO NOT enter \"undefined\" or \"null\" - simply omit it for the default behavior. Must be a valid directory path if provided."
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