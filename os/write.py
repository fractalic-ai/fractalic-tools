#!/usr/bin/env python3
"""Write Tool - Fractalic Compatible Implementation

Writes a file to the local filesystem with automatic directory creation and diff reporting.
Supports both creating new files and updating existing files.
"""

import json
import sys
import os
from pathlib import Path

def process_data(data):
    """Main processing function for file writing."""
    try:
        # Extract and validate parameters
        file_path = data.get("file_path")
        content = data.get("content")
        
        if not file_path:
            return {"status": "error", "error": "file_path parameter is required"}
        
        if content is None:
            return {"status": "error", "error": "content parameter is required"}
        
        # Resolve path
        path = Path(file_path).resolve()
        
        # Check if file exists
        file_exists = path.exists()
        original_content = None
        
        if file_exists:
            if not path.is_file():
                return {"status": "error", "error": f"Path exists but is not a file: {file_path}"}
            
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    original_content = f.read()
            except UnicodeDecodeError:
                # Existing file is binary, but we're writing text
                return {"status": "error", "error": "Cannot overwrite binary file with text content"}
            except Exception as e:
                return {"status": "error", "error": f"Failed to read existing file: {str(e)}"}
        
        # Create directory if needed
        dir_path = path.parent
        if not dir_path.exists():
            try:
                dir_path.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                return {"status": "error", "error": f"Failed to create directory {dir_path}: {str(e)}"}
        
        # Write the file
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
        except Exception as e:
            return {"status": "error", "error": f"Failed to write file: {str(e)}"}
        
        # Generate response
        result = {
            "status": "success",
            "data": {
                "type": "update" if file_exists else "create",
                "filePath": str(path),
                "contentLength": len(content),
                "bytesWritten": len(content.encode('utf-8'))
            }
        }
        
        # Add diff info if updating existing file
        if file_exists and original_content != content:
            result["data"]["structuredPatch"] = _generate_diff_info(original_content, content)
            result["data"]["originalContentLength"] = len(original_content)
        
        return result
        
    except Exception as e:
        return {"status": "error", "error": str(e)}

def _generate_diff_info(original_content, new_content):
    """Generate basic diff information."""
    original_lines = original_content.split('\n')
    new_lines = new_content.split('\n')
    
    return [{
        "type": "replace",
        "oldStart": 1,
        "oldLines": len(original_lines),
        "newStart": 1,
        "newLines": len(new_lines),
        "linesAdded": max(0, len(new_lines) - len(original_lines)),
        "linesRemoved": max(0, len(original_lines) - len(new_lines)),
        "linesModified": min(len(original_lines), len(new_lines))
    }]

def get_schema():
    """Return Fractalic-compatible JSON schema."""
    return {
        "name": "_write",
        "description": "Writes a file to the local filesystem. This tool will overwrite the existing file if there is one at the provided path. Always prefer editing existing files in the codebase. Never write new files unless explicitly required.",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "The absolute path to the file to write (must be absolute, not relative)"
                },
                "content": {
                    "type": "string",
                    "description": "The content to write to the file"
                }
            },
            "required": ["file_path", "content"],
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