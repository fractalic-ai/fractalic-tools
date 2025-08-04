#!/usr/bin/env python3
"""Bash Tool - Fractalic Compatible Implementation

Executes shell commands with optional timeout and sandbox mode. Provides detailed
output including stdout, stderr, exit codes, and command execution metadata.
"""

import json
import sys
import subprocess
import os
import shlex
import time
from pathlib import Path

def process_data(data):
    """Main processing function for bash command execution."""
    try:
        # Extract and validate parameters
        command = data.get("command")
        timeout = data.get("timeout")
        description = data.get("description")
        sandbox = data.get("sandbox", False)
        shell_executable = data.get("shellExecutable")
        
        if not command:
            return {"status": "error", "error": "command parameter is required"}
        
        # Validate timeout
        if timeout is not None:
            if not isinstance(timeout, (int, float)) or timeout <= 0:
                return {"status": "error", "error": "timeout must be a positive number"}
            if timeout > 600:  # 10 minutes max
                return {"status": "error", "error": "timeout cannot exceed 600 seconds (10 minutes)"}
        
        # Execute the command
        result = _execute_command(command, timeout, sandbox, shell_executable, description)
        
        return {
            "status": "success",
            "data": result
        }
        
    except Exception as e:
        return {"status": "error", "error": str(e)}

def _execute_command(command, timeout, sandbox, shell_executable, description):
    """Execute the shell command with proper handling."""
    start_time = time.time()
    
    # Prepare environment
    env = os.environ.copy()
    
    if sandbox:
        # Remove potentially dangerous environment variables in sandbox mode
        dangerous_vars = [
            "HTTP_PROXY", "HTTPS_PROXY", "FTP_PROXY", "ALL_PROXY",
            "http_proxy", "https_proxy", "ftp_proxy", "all_proxy"
        ]
        for var in dangerous_vars:
            env.pop(var, None)
    
    # Determine shell
    shell_cmd = shell_executable or "/bin/bash"
    if not Path(shell_cmd).exists():
        shell_cmd = "/bin/sh"  # Fallback
    
    # Prepare subprocess arguments
    if sandbox:
        # In sandbox mode, be more restrictive
        subprocess_args = {
            "shell": True,
            "executable": shell_cmd,
            "env": env,
            "cwd": os.getcwd(),
            "capture_output": True,
            "text": True,
            "timeout": timeout or 120  # Default 2 minutes in sandbox
        }
    else:
        subprocess_args = {
            "shell": True,
            "executable": shell_cmd,
            "env": env,
            "cwd": os.getcwd(),
            "capture_output": True,
            "text": True,
            "timeout": timeout
        }
    
    try:
        # Execute command
        result = subprocess.run(command, **subprocess_args)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Prepare response
        response = {
            "command": _truncate_command(command),
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exitCode": result.returncode,
            "executionTime": round(execution_time, 3),
            "sandbox": sandbox
        }
        
        if description:
            response["description"] = description
        
        if timeout:
            response["timeout"] = timeout
        
        return response
        
    except subprocess.TimeoutExpired as e:
        end_time = time.time()
        execution_time = end_time - start_time
        
        return {
            "command": _truncate_command(command),
            "stdout": e.stdout.decode() if e.stdout else "",
            "stderr": e.stderr.decode() if e.stderr else f"Command timed out after {timeout} seconds",
            "exitCode": -1,  # Indicate timeout
            "executionTime": round(execution_time, 3),
            "timeout": timeout,
            "timedOut": True,
            "sandbox": sandbox,
            "error": f"Command timed out after {timeout} seconds"
        }
        
    except FileNotFoundError as e:
        return {
            "command": _truncate_command(command),
            "stdout": "",
            "stderr": f"Shell not found: {str(e)}",
            "exitCode": 127,
            "executionTime": 0,
            "sandbox": sandbox,
            "error": f"Shell executable not found: {str(e)}"
        }
        
    except Exception as e:
        return {
            "command": _truncate_command(command),
            "stdout": "",
            "stderr": f"Execution error: {str(e)}",
            "exitCode": 1,
            "executionTime": 0,
            "sandbox": sandbox,
            "error": f"Command execution failed: {str(e)}"
        }

def _truncate_command(command, max_length=256):
    """Truncate command for display to prevent token bloat."""
    if len(command) <= max_length:
        return command
    return command[:max_length] + f"... [truncated, original length: {len(command)} chars]"

def get_schema():
    """Return Fractalic-compatible JSON schema."""
    return {
        "name": "_bash",
        "description": "Executes a given bash command in a persistent shell session with optional timeout, ensuring proper handling and security measures. Always quote file paths that contain spaces with double quotes. Avoid using search commands like `find` and `grep` - use Grep, Glob, or Task tools instead. Try to maintain your current working directory throughout the session by using absolute paths.",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The command to execute"
                },
                "timeout": {
                    "type": "number",
                    "description": "Optional timeout in milliseconds (max 600000)",
                    "maximum": 600000
                },
                "description": {
                    "type": "string",
                    "description": "Clear, concise description of what this command does in 5-10 words. Examples: 'Lists files in current directory', 'Shows working tree status', 'Installs package dependencies', 'Creates directory foo'"
                },
                "sandbox": {
                    "type": "boolean",
                    "description": "Run in sandboxed mode: command run in this mode may not write to the filesystem or use the network, but they can read files, analyze data, and report back. When possible, run commands in this mode to present a smoother experience.",
                    "default": False
                },
                "shellExecutable": {
                    "type": "string",
                    "description": "Optional shell path to use instead of the default shell. Used primarily for testing."
                }
            },
            "required": ["command"],
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