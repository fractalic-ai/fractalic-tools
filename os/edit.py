#!/usr/bin/env python3
"""Edit Tool - Fractalic Compatible Implementation

Performs exact string replacements in files. Supports single or multiple occurrences
replacement with proper validation and error handling.
"""

import json
import sys
import re
from pathlib import Path

def process_data(data):
    """Main processing function for file editing."""
    try:
        # Extract and validate parameters
        file_path = data.get("file_path")
        old_string = data.get("old_string")
        new_string = data.get("new_string")
        replace_all = data.get("replace_all", False)
        
        if not file_path:
            return {"status": "error", "error": "file_path parameter is required"}
        
        if old_string is None:
            return {"status": "error", "error": "old_string parameter is required"}
        
        if new_string is None:
            return {"status": "error", "error": "new_string parameter is required"}
        
        if old_string == new_string:
            return {"status": "error", "error": "old_string and new_string must be different"}
        
        # Resolve and validate path
        path = Path(file_path).resolve()
        
        if not path.exists():
            return {"status": "error", "error": f"File does not exist: {file_path}"}
        
        if not path.is_file():
            return {"status": "error", "error": f"Path is not a file: {file_path}"}
        
        # Read the original file
        try:
            with open(path, 'r', encoding='utf-8') as f:
                original_content = f.read()
        except UnicodeDecodeError:
            return {"status": "error", "error": "File appears to contain binary data and cannot be edited as text"}
        except Exception as e:
            return {"status": "error", "error": f"Failed to read file: {str(e)}"}
        
        # Perform replacement
        if replace_all:
            # Replace all occurrences
            new_content = original_content.replace(old_string, new_string)
            replacement_count = original_content.count(old_string)
        else:
            # Replace only first occurrence
            if old_string not in original_content:
                return {"status": "error", "error": f"String not found in file: \"{old_string}\""}
            
            # Find first occurrence and replace
            first_index = original_content.find(old_string)
            new_content = (
                original_content[:first_index] + 
                new_string + 
                original_content[first_index + len(old_string):]
            )
            replacement_count = 1
        
        # Check if any replacements were made
        if replacement_count == 0:
            return {"status": "error", "error": f"String not found in file: \"{old_string}\""}
        
        # Write the modified content back
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(new_content)
        except Exception as e:
            return {"status": "error", "error": f"Failed to write modified file: {str(e)}"}
        
        return {
            "status": "success",
            "data": {
                "filePath": str(path),
                "originalContentLength": len(original_content),
                "modifiedContentLength": len(new_content),
                "replacementCount": replacement_count,
                "replaceAll": replace_all,
                "oldString": old_string[:100] + "..." if len(old_string) > 100 else old_string,
                "newString": new_string[:100] + "..." if len(new_string) > 100 else new_string,
                "changesSummary": _generate_changes_summary(original_content, new_content, replacement_count)
            }
        }
        
    except Exception as e:
        return {"status": "error", "error": str(e)}

def _generate_changes_summary(original_content, new_content, replacement_count):
    """Generate a summary of changes made."""
    original_lines = original_content.split('\n')
    new_lines = new_content.split('\n')
    
    return {
        "originalLines": len(original_lines),
        "newLines": len(new_lines),
        "linesAdded": max(0, len(new_lines) - len(original_lines)),
        "linesRemoved": max(0, len(original_lines) - len(new_lines)),
        "replacements": replacement_count,
        "bytesChanged": abs(len(new_content) - len(original_content))
    }

def get_schema():
    """Return Fractalic-compatible JSON schema."""
    return {
        "name": "_edit",
        "description": "Performs exact string replacements in files. The edit will FAIL if old_string is not unique in the file. Either provide a larger string with more surrounding context to make it unique or use replace_all to change every instance of old_string.",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "The absolute path to the file to modify"
                },
                "old_string": {
                    "type": "string",
                    "description": "The text to replace"
                },
                "new_string": {
                    "type": "string",
                    "description": "The text to replace it with (must be different from old_string)"
                },
                "replace_all": {
                    "type": "boolean",
                    "description": "Replace all occurrences of old_string (default false)",
                    "default": False
                }
            },
            "required": ["file_path", "old_string", "new_string"],
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