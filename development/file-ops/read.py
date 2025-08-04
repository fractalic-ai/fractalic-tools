#!/usr/bin/env python3
"""Read Tool - Fractalic Compatible Implementation

Reads files from the local filesystem with support for text files, images, and binary detection.
Supports line offsets and limits for large files, with automatic image base64 encoding.
"""

import json
import sys
import base64
import mimetypes
from pathlib import Path

# File type detection
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tiff", ".ico"}
BINARY_EXTENSIONS = {
    ".mp3", ".wav", ".flac", ".ogg", ".aac", ".m4a", ".wma", ".aiff", ".opus",
    ".mp4", ".avi", ".mov", ".wmv", ".flv", ".mkv", ".webm", ".m4v", ".mpeg", ".mpg",
    ".zip", ".rar", ".tar", ".gz", ".bz2", ".7z", ".xz", ".z", ".tgz", ".iso",
    ".exe", ".dll", ".so", ".dylib", ".app", ".msi", ".deb", ".rpm", ".bin", ".dat",
    ".db", ".sqlite", ".sqlite3", ".mdb", ".idx", ".doc", ".docx", ".xls", ".xlsx",
    ".ppt", ".pptx", ".odt", ".ods", ".odp", ".ttf", ".otf", ".woff", ".woff2", ".eot",
    ".psd", ".ai", ".eps", ".sketch", ".fig", ".xd", ".blend", ".obj", ".3ds", ".max",
    ".class", ".jar", ".war", ".pyc", ".pyo", ".rlib", ".swf", ".fla"
}

# Limits
MAX_FILE_SIZE_BYTES = 262144  # 256KB for text files
MAX_LINES_DEFAULT = 2000

def process_data(data):
    """Main processing function for file reading."""
    try:
        # Extract and validate parameters
        file_path = data.get("file_path")
        offset = data.get("offset", 1)  # 1-based line numbering
        limit = data.get("limit")
        
        if not file_path:
            return {"status": "error", "error": "file_path parameter is required"}
        
        # Resolve and validate path
        path = Path(file_path).resolve()
        
        if not path.exists():
            return {"status": "error", "error": f"File does not exist: {file_path}"}
        
        if not path.is_file():
            return {"status": "error", "error": f"Path is not a file: {file_path}"}
        
        # Get file info
        file_size = path.stat().st_size
        file_extension = path.suffix.lower()
        
        # Handle different file types
        if file_extension in IMAGE_EXTENSIONS:
            return _read_image_file(path, file_size)
        elif file_extension in BINARY_EXTENSIONS:
            return {"status": "error", "error": f"Cannot read binary files. The file appears to be a binary {file_extension[1:]} file."}
        else:
            return _read_text_file(path, file_size, offset, limit)
            
    except Exception as e:
        return {"status": "error", "error": str(e)}

def _read_image_file(path, file_size):
    """Read and encode image file as base64."""
    try:
        with open(path, 'rb') as f:
            image_data = f.read()
        
        base64_data = base64.b64encode(image_data).decode('utf-8')
        
        # Determine MIME type
        mime_type, _ = mimetypes.guess_type(str(path))
        if not mime_type or not mime_type.startswith('image/'):
            # Fallback based on extension
            ext = path.suffix.lower()
            if ext == '.jpg' or ext == '.jpeg':
                mime_type = 'image/jpeg'
            elif ext == '.png':
                mime_type = 'image/png'
            elif ext == '.gif':
                mime_type = 'image/gif'
            elif ext == '.bmp':
                mime_type = 'image/bmp'
            elif ext == '.webp':
                mime_type = 'image/webp'
            else:
                mime_type = 'image/png'  # Default fallback
        
        return {
            "status": "success",
            "data": {
                "type": "image",
                "file": {
                    "base64": base64_data,
                    "type": mime_type,
                    "originalSize": file_size,
                    "filePath": str(path)
                }
            }
        }
        
    except Exception as e:
        return {"status": "error", "error": f"Failed to read image file: {str(e)}"}

def _read_text_file(path, file_size, offset, limit):
    """Read text file with optional offset and limit."""
    try:
        # Check size limit for full file reads
        if limit is None and file_size > MAX_FILE_SIZE_BYTES:
            return {
                "status": "error", 
                "error": f"File content ({file_size} bytes) exceeds maximum allowed size ({MAX_FILE_SIZE_BYTES} bytes). Please use offset and limit parameters to read specific portions of the file."
            }
        
        with open(path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        total_lines = len(lines)
        
        # Apply offset and limit
        start_index = max(0, offset - 1)  # Convert to 0-based
        
        if limit is not None:
            end_index = start_index + limit
            selected_lines = lines[start_index:end_index]
        else:
            selected_lines = lines[start_index:]
            # Apply default limit if no explicit limit
            if len(selected_lines) > MAX_LINES_DEFAULT:
                selected_lines = selected_lines[:MAX_LINES_DEFAULT]
                limit = MAX_LINES_DEFAULT
        
        content = ''.join(selected_lines)
        
        # Remove final newline if present to match original behavior
        if content.endswith('\n'):
            content = content[:-1]
        
        return {
            "status": "success", 
            "data": {
                "type": "text",
                "file": {
                    "filePath": str(path),
                    "content": _format_with_line_numbers(content, offset),
                    "numLines": len(selected_lines),
                    "startLine": offset,
                    "totalLines": total_lines,
                    "rawContent": content  # Also provide raw content
                }
            }
        }
        
    except UnicodeDecodeError:
        # File might be binary despite extension
        return {"status": "error", "error": "File appears to contain binary data and cannot be read as text"}
    except Exception as e:
        return {"status": "error", "error": f"Failed to read text file: {str(e)}"}

def _format_with_line_numbers(content, start_line):
    """Format content with line numbers like Claude Code's original format."""
    lines = content.split('\n')
    formatted_lines = []
    
    for i, line in enumerate(lines):
        line_num = start_line + i
        # Use the same format as original: spaces + line number + arrow + content
        formatted_lines.append(f"{line_num:6d}→{line}")
    
    return '\n'.join(formatted_lines)

def get_schema():
    """Return Fractalic-compatible JSON schema."""
    return {
        "name": "_read",
        "description": "Reads a file from the local filesystem. You can access any file directly by using this tool. Supports reading text files with line numbers, images (returned as base64), and handles binary file detection. For large files, use offset and limit parameters.",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "The absolute path to the file to read"
                },
                "offset": {
                    "type": "number",
                    "description": "The line number to start reading from (1-based). Only provide if the file is too large to read at once",
                    "minimum": 1
                },
                "limit": {
                    "type": "number", 
                    "description": "The number of lines to read. Only provide if the file is too large to read at once",
                    "minimum": 1
                }
            },
            "required": ["file_path"],
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