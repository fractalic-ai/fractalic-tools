#!/usr/bin/env python3
"""MultiEdit Tool - Fractalic Compatible Implementation

Performs multiple edits to a single file in one operation. All edits are applied
sequentially and either all succeed or none are applied (atomic operation).
"""

import json
import sys
from pathlib import Path

def process_data(data):
    """Main processing function for multiple file edits."""
    try:
        # Extract and validate parameters
        file_path = data.get("file_path")
        edits = data.get("edits")
        
        if not file_path:
            return {"status": "error", "error": "file_path parameter is required"}
        
        if not edits:
            return {"status": "error", "error": "edits parameter is required"}
        
        if not isinstance(edits, list) or len(edits) == 0:
            return {"status": "error", "error": "edits must be a non-empty array"}
        
        # Validate edit operations
        for i, edit in enumerate(edits):
            if not isinstance(edit, dict):
                return {"status": "error", "error": f"Edit {i+1} must be an object"}
            
            if "old_string" not in edit:
                return {"status": "error", "error": f"Edit {i+1} missing required field: old_string"}
            
            if "new_string" not in edit:
                return {"status": "error", "error": f"Edit {i+1} missing required field: new_string"}
            
            if edit["old_string"] == edit["new_string"]:
                return {"status": "error", "error": f"Edit {i+1}: old_string and new_string must be different"}
        
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
        
        # Apply edits sequentially
        current_content = original_content
        applied_edits = []
        total_replacements = 0
        
        for i, edit in enumerate(edits):
            old_string = edit["old_string"]
            new_string = edit["new_string"]
            replace_all = edit.get("replace_all", False)
            
            # Check if old_string exists
            if old_string not in current_content:
                return {
                    "status": "error", 
                    "error": f"Edit {i+1}: String not found in file: \"{old_string}\""
                }
            
            # Apply the edit
            if replace_all:
                replacement_count = current_content.count(old_string)
                current_content = current_content.replace(old_string, new_string)
            else:
                # Replace only first occurrence
                first_index = current_content.find(old_string)
                current_content = (
                    current_content[:first_index] + 
                    new_string + 
                    current_content[first_index + len(old_string):]
                )
                replacement_count = 1
            
            applied_edits.append({
                "editNumber": i + 1,
                "oldString": old_string[:50] + "..." if len(old_string) > 50 else old_string,
                "newString": new_string[:50] + "..." if len(new_string) > 50 else new_string,
                "replaceAll": replace_all,
                "replacementCount": replacement_count
            })
            
            total_replacements += replacement_count
        
        # Write the modified content back
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(current_content)
        except Exception as e:
            return {"status": "error", "error": f"Failed to write modified file: {str(e)}"}
        
        return {
            "status": "success",
            "data": {
                "filePath": str(path),
                "editsApplied": len(edits),
                "totalReplacements": total_replacements,
                "originalContentLength": len(original_content),
                "modifiedContentLength": len(current_content),
                "appliedEdits": applied_edits,
                "changesSummary": _generate_changes_summary(original_content, current_content, total_replacements)
            }
        }
        
    except Exception as e:
        return {"status": "error", "error": str(e)}

def _generate_changes_summary(original_content, new_content, total_replacements):
    """Generate a summary of all changes made."""
    original_lines = original_content.split('\n')
    new_lines = new_content.split('\n')
    
    return {
        "originalLines": len(original_lines),
        "newLines": len(new_lines),
        "linesAdded": max(0, len(new_lines) - len(original_lines)),
        "linesRemoved": max(0, len(original_lines) - len(new_lines)),
        "totalReplacements": total_replacements,
        "bytesChanged": abs(len(new_content) - len(original_content))
    }

def get_schema():
    """Return Fractalic-compatible JSON schema."""
    return {
        "name": "_multiedit",
        "description": "Performs multiple edits to a single file in one operation. All edits are applied in sequence, in the order they are provided. Each edit operates on the result of the previous edit. All edits must be valid for the operation to succeed - if any edit fails, none will be applied.",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "The absolute path to the file to modify"
                },
                "edits": {
                    "type": "array",
                    "description": "Array of edit operations to perform sequentially on the file",
                    "minItems": 1,
                    "items": {
                        "type": "object",
                        "properties": {
                            "old_string": {
                                "type": "string",
                                "description": "The text to replace"
                            },
                            "new_string": {
                                "type": "string",
                                "description": "The text to replace it with"
                            },
                            "replace_all": {
                                "type": "boolean",
                                "description": "Replace all occurrences of old_string (default false)",
                                "default": False
                            }
                        },
                        "required": ["old_string", "new_string"],
                        "additionalProperties": False
                    }
                }
            },
            "required": ["file_path", "edits"],
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