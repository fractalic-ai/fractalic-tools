#!/usr/bin/env python3
"""LS Tool - Fractalic Compatible Implementation

Lists files and directories in a given path with optional ignore patterns.
Provides detailed file information including sizes, permissions, and modification times.
"""

import json
import sys
import os
import stat
import time
import fnmatch
from pathlib import Path
from datetime import datetime

def process_data(data):
    """Main processing function for directory listing."""
    try:
        # Extract and validate parameters
        path = data.get("path")
        ignore = data.get("ignore", [])
        
        if not path:
            return {"status": "error", "error": "path parameter is required"}
        
        # Validate path is absolute
        if not os.path.isabs(path):
            return {"status": "error", "error": "path must be an absolute path, not a relative path"}
        
        # Validate ignore patterns
        if not isinstance(ignore, list):
            return {"status": "error", "error": "ignore parameter must be an array of glob patterns"}
        
        # List directory contents
        result = _list_directory(path, ignore)
        
        if "error" in result:
            return {"status": "error", "error": result["error"]}
        
        return {
            "status": "success",
            "data": result
        }
        
    except Exception as e:
        return {"status": "error", "error": str(e)}

def _list_directory(path, ignore_patterns):
    """List directory contents with detailed information."""
    try:
        # Check if path exists
        if not os.path.exists(path):
            return {"error": f"Path does not exist: {path}"}
        
        # Check if path is a directory
        if not os.path.isdir(path):
            return {"error": f"Path is not a directory: {path}"}
        
        # Check if directory is readable
        if not os.access(path, os.R_OK):
            return {"error": f"Permission denied accessing directory: {path}"}
        
        entries = []
        total_size = 0
        file_count = 0
        dir_count = 0
        
        try:
            # Get directory listing
            for entry_name in os.listdir(path):
                entry_path = os.path.join(path, entry_name)
                
                # Check ignore patterns
                if _should_ignore(entry_name, ignore_patterns):
                    continue
                
                try:
                    # Get file stats
                    entry_stat = os.lstat(entry_path)  # Use lstat to not follow symlinks
                    
                    # Determine entry type
                    if stat.S_ISDIR(entry_stat.st_mode):
                        entry_type = "directory"
                        dir_count += 1
                    elif stat.S_ISLNK(entry_stat.st_mode):
                        entry_type = "symlink"
                    elif stat.S_ISREG(entry_stat.st_mode):
                        entry_type = "file"
                        file_count += 1
                        total_size += entry_stat.st_size
                    else:
                        entry_type = "other"
                    
                    # Format permissions
                    permissions = _format_permissions(entry_stat.st_mode)
                    
                    # Format modification time
                    mod_time = datetime.fromtimestamp(entry_stat.st_mtime)
                    
                    entry_info = {
                        "name": entry_name,
                        "type": entry_type,
                        "size": entry_stat.st_size if entry_type in ["file", "symlink"] else None,
                        "sizeFormatted": _format_size(entry_stat.st_size) if entry_type in ["file", "symlink"] else None,
                        "permissions": permissions,
                        "owner": _get_owner_name(entry_stat.st_uid),
                        "group": _get_group_name(entry_stat.st_gid),
                        "modified": mod_time.isoformat(),
                        "modifiedFormatted": mod_time.strftime("%Y-%m-%d %H:%M:%S"),
                        "path": entry_path
                    }
                    
                    # Add symlink target if applicable
                    if entry_type == "symlink":
                        try:
                            target = os.readlink(entry_path)
                            entry_info["symlinkTarget"] = target
                            # Check if target exists
                            target_path = target if os.path.isabs(target) else os.path.join(path, target)
                            entry_info["symlinkValid"] = os.path.exists(target_path)
                        except OSError:
                            entry_info["symlinkTarget"] = "unknown"
                            entry_info["symlinkValid"] = False
                    
                    entries.append(entry_info)
                    
                except (OSError, PermissionError) as e:
                    # Add entry with error info
                    entries.append({
                        "name": entry_name,
                        "type": "error",
                        "error": str(e),
                        "path": entry_path
                    })
                    
        except PermissionError:
            return {"error": f"Permission denied reading directory contents: {path}"}
        
        # Sort entries by name (directories first, then files)
        entries.sort(key=lambda x: (x["type"] != "directory", x["name"].lower()))
        
        return {
            "path": path,
            "entries": entries,
            "summary": {
                "totalEntries": len(entries),
                "fileCount": file_count,
                "directoryCount": dir_count,
                "totalSize": total_size,
                "totalSizeFormatted": _format_size(total_size),
                "ignorePatterns": ignore_patterns
            },
            "scannedAt": int(time.time())
        }
        
    except Exception as e:
        return {"error": f"Failed to list directory: {str(e)}"}

def _should_ignore(name, ignore_patterns):
    """Check if entry should be ignored based on patterns."""
    for pattern in ignore_patterns:
        if fnmatch.fnmatch(name, pattern):
            return True
    return False

def _format_permissions(mode):
    """Format file permissions as rwx string."""
    perms = []
    
    # Owner permissions
    perms.append('r' if mode & stat.S_IRUSR else '-')
    perms.append('w' if mode & stat.S_IWUSR else '-')
    perms.append('x' if mode & stat.S_IXUSR else '-')
    
    # Group permissions
    perms.append('r' if mode & stat.S_IRGRP else '-')
    perms.append('w' if mode & stat.S_IWGRP else '-')
    perms.append('x' if mode & stat.S_IXGRP else '-')
    
    # Other permissions
    perms.append('r' if mode & stat.S_IROTH else '-')
    perms.append('w' if mode & stat.S_IWOTH else '-')
    perms.append('x' if mode & stat.S_IXOTH else '-')
    
    return ''.join(perms)

def _format_size(size_bytes):
    """Format file size in human-readable format."""
    if size_bytes == 0:
        return "0 B"
    
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    unit_index = 0
    size = float(size_bytes)
    
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1
    
    if unit_index == 0:
        return f"{int(size)} {units[unit_index]}"
    else:
        return f"{size:.1f} {units[unit_index]}"

def _get_owner_name(uid):
    """Get owner name from UID."""
    try:
        import pwd
        return pwd.getpwuid(uid).pw_name
    except (ImportError, KeyError):
        return str(uid)

def _get_group_name(gid):
    """Get group name from GID."""
    try:
        import grp
        return grp.getgrgid(gid).gr_name
    except (ImportError, KeyError):
        return str(gid)

def get_schema():
    """Return Fractalic-compatible JSON schema."""
    return {
        "name": "_ls",
        "description": "Lists files and directories in a given path. The path parameter must be an absolute path, not a relative path. You can optionally provide an array of glob patterns to ignore with the ignore parameter. You should generally prefer the Glob and Grep tools, if you know which directories to search.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The absolute path to the directory to list (must be absolute, not relative)"
                },
                "ignore": {
                    "type": "array",
                    "description": "List of glob patterns to ignore",
                    "items": {"type": "string"}
                }
            },
            "required": ["path"],
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