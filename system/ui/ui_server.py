
#!/usr/bin/env python3
"""
Fractalic Universal Demo Server - Simple JSON Discovery Tool
Supports background server management and HTML push via JSON commands.
"""
import sys
import os
import json
import subprocess
import time
import signal
import platform

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 5000

def find_server_pid():
    """Find the PID of our server process using platform-agnostic methods"""
    # Method 1: Try psutil if available (cross-platform)
    try:
        import psutil
        for proc in psutil.process_iter(['pid', 'name', 'connections']):
            try:
                connections = proc.info['connections']
                if connections:
                    for conn in connections:
                        if (conn.laddr and conn.laddr.port == SERVER_PORT and 
                            conn.status == 'LISTEN'):
                            return proc.info['pid']
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except ImportError:
        # psutil not available, fall back to system commands
        pass
    
    # Method 2: Platform-specific system commands
    import platform
    system = platform.system().lower()
    
    if system in ['linux', 'darwin']:  # Unix-like systems (Linux, macOS)
        try:
            # Use lsof to find process listening on our port
            result = subprocess.run(['lsof', '-ti', f':{SERVER_PORT}'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0 and result.stdout.strip():
                return int(result.stdout.strip().split('\n')[0])
        except:
            pass
    
    elif system == 'windows':
        try:
            # Use netstat to find process listening on our port
            result = subprocess.run(['netstat', '-ano'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    parts = line.split()
                    if len(parts) >= 5 and f':{SERVER_PORT}' in parts[1] and 'LISTENING' in parts[3]:
                        try:
                            return int(parts[4])
                        except ValueError:
                            continue
        except:
            pass
    
    return None

def process_data(data):
    """Main processing function for Simple JSON Discovery."""
    action = data.get("action")
    host = data.get("host", SERVER_HOST)
    port = data.get("port", SERVER_PORT)
    
    if action == "start":
        return start_server(host, port)
    elif action == "status":
        return server_status(host, port)
    elif action == "kill":
        return kill_server()
    elif action == "push_html":
        html = data.get("html")
        filename = data.get("filename")
        
        # Get HTML content from either direct HTML or filename
        if filename:
            try:
                # Handle both relative and absolute paths
                file_path = os.path.abspath(os.path.expanduser(filename))
                with open(file_path, 'r', encoding='utf-8') as f:
                    html = f.read()
            except FileNotFoundError:
                return {"error": f"File not found: {filename}"}
            except Exception as e:
                return {"error": f"Failed to read file '{filename}': {e}"}
        elif not html:
            return {"error": "Either 'html' content or 'filename' parameter is required for push_html action"}
        
        wait_for_response = data.get("wait_for_response", False)
        return push_html(html, host, port, wait_for_response)
    elif action == "run_server":
        # Run server directly (blocking mode)
        run_server_directly(host, port)
        return {"status": "server_started"}  # This won't actually be returned due to blocking
    else:
        return {"error": f"Unknown action: {action}"}

# --- Schema Definition ---
def get_schema():
    """Return the JSON schema for this tool (single-tool schema)."""
    return {
        "name": "server",
        "description": "Universal demo server manager with background server management and HTML push capabilities. Supports starting/stopping FastAPI server, checking status, and pushing HTML content for real-time updates.",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["start", "status", "kill", "push_html", "run_server"],
                    "description": "Server management action: 'start' launches server in background, 'status' checks if running, 'kill' stops server, 'push_html' sends HTML to running server, 'run_server' runs server directly (blocking)"
                },
                "host": {
                    "type": "string",
                    "default": "127.0.0.1",
                    "description": "Server host address (default: 127.0.0.1)"
                },
                "port": {
                    "type": "integer",
                    "default": 5000,
                    "description": "Server port number (default: 5000)"
                },
                "html": {
                    "type": "string",
                    "description": "HTML content to push to the server (required for push_html action if filename not provided)"
                },
                "filename": {
                    "type": "string",
                    "description": "Path to HTML file to load and push to server (alternative to html parameter). Supports both relative and absolute paths."
                },
                "wait_for_response": {
                    "type": "boolean",
                    "default": False,
                    "description": "Whether to wait briefly after pushing HTML to allow browser processing (optional, for push_html action)"
                }
            },
            "required": ["action"]
        }
    }

# --- Server Management Utilities ---
def is_server_running(host=SERVER_HOST, port=SERVER_PORT):
    try:
        import requests  # Import only when needed
        r = requests.get(f"http://{host}:{port}/", timeout=1)
        return r.status_code == 200
    except Exception:
        return False

def get_server_pid():
    """Get the PID of our server process"""
    return find_server_pid()

def start_server(host=SERVER_HOST, port=SERVER_PORT):
    if is_server_running(host, port):
        return {"status": "already_running", "message": f"Server already running at http://{host}:{port}"}
    # Start server in background using this same file with run_server action
    proc = subprocess.Popen([
        sys.executable, __file__, json.dumps({"action": "run_server", "host": host, "port": port})
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    # Wait for server to start
    for _ in range(20):
        if is_server_running(host, port):
            return {"status": "started", "message": f"Server started at http://{host}:{port}", "pid": proc.pid}
        time.sleep(0.2)
    return {"status": "error", "message": "Server did not start in time"}

def kill_server():
    pid = get_server_pid()
    
    # If we found a PID, try to kill it
    if pid:
        try:
            import platform
            system = platform.system().lower()
            
            if system == 'windows':
                # On Windows, use taskkill for more reliable termination
                try:
                    subprocess.run(['taskkill', '/F', '/PID', str(pid)], 
                                 capture_output=True, timeout=5)
                    return {"status": "killed", "message": f"Server process {pid} killed"}
                except:
                    # Fallback to os.kill on Windows (may not work for all cases)
                    os.kill(pid, signal.SIGTERM)
                    return {"status": "killed", "message": f"Server process {pid} killed"}
            else:
                # Unix-like systems
                os.kill(pid, signal.SIGTERM)
                return {"status": "killed", "message": f"Server process {pid} killed"}
                
        except ProcessLookupError:
            return {"status": "not_running", "message": f"Process {pid} not found"}
        except Exception as e:
            return {"status": "error", "message": f"Failed to kill server: {e}"}
    
    # No process found, but check if server is actually running
    if is_server_running():
        return {"status": "error", "message": "Server is running but process not found. May need manual cleanup."}
    else:
        return {"status": "not_running", "message": "Server is not running"}

def push_html(html, host=SERVER_HOST, port=SERVER_PORT, wait_for_response=False):
    if not is_server_running(host, port):
        return {"status": "error", "message": "Server is not running"}
    try:
        import requests  # Import only when needed
        r = requests.post(f"http://{host}:{port}/update_html", data=html.encode("utf-8"), headers={"Content-Type": "text/html"}, timeout=3)
        if r.ok:
            result = {"status": "ok", "response": r.json()}
            if wait_for_response:
                # Wait for actual user response using a robust polling approach
                try:
                    import requests
                    from requests.adapters import HTTPAdapter
                    from urllib3.util.retry import Retry
                    import time
                    
                    # Create a session with conservative timeouts
                    session = requests.Session()
                    retry_strategy = Retry(total=0, read=0, connect=0, backoff_factor=0)
                    adapter = HTTPAdapter(max_retries=retry_strategy)
                    session.mount("http://", adapter)
                    session.mount("https://", adapter)
                    
                    # First, clear any pending events
                    try:
                        session.post(f"http://{host}:{port}/clear_wait_queue", timeout=5)
                    except:
                        pass  # Ignore errors
                    
                    # Poll the wait endpoint with shorter timeouts but retry indefinitely
                    start_time = time.time()
                    while True:
                        try:
                            # Use shorter timeout to avoid system-level timeouts
                            response = session.get(
                                f"http://{host}:{port}/wait_for_user_event_poll", 
                                timeout=30  # 30 second timeout per request
                            )
                            
                            if response.ok:
                                event_data = response.json()
                                if event_data.get("has_event"):
                                    result["user_event"] = event_data
                                    result["waited"] = True
                                    result["wait_duration"] = time.time() - start_time
                                    break
                                else:
                                    # No event yet, continue polling silently
                                    time.sleep(0.5)  # Brief pause before next poll
                            else:
                                # Server error, retry silently
                                time.sleep(1)
                                
                        except Exception as poll_error:
                            # Network error, retry silently  
                            time.sleep(1)
                        
                except Exception as wait_error:
                    result["waited"] = True
                    result["wait_error"] = str(wait_error)
            return result
        else:
            return {"status": "error", "message": f"Server responded with status {r.status_code}", "response": r.text}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def server_status(host=SERVER_HOST, port=SERVER_PORT):
    running = is_server_running(host, port)
    pid = get_server_pid()
    
    result = {
        "running": running,
        "pid": pid,
        "url": f"http://{host}:{port}" if running else None
    }
    
    # Add warning if server is running but no process found
    if running and not pid:
        result["warning"] = "Server is running but process not found"
    
    # Add warning if process found but server not responding
    if not running and pid:
        result["warning"] = f"Process {pid} found but server not responding"
    
    return result

def run_server_directly(host=SERVER_HOST, port=SERVER_PORT):
    """Run the FastAPI server directly (blocking) - imports FastAPI only when needed"""
    import uvicorn
    from fastapi import FastAPI, Request, File, UploadFile
    from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.staticfiles import StaticFiles
    import asyncio
    import uuid
    
    # FastAPI App Definition
    app = FastAPI()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Global state for event handling
    latest_event = None
    event_consumed = False

    CURRENT_HTML = """\
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8" />
  <title>Waiting for content...</title>
  <style>
    body { font-family: 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif; background-color: #2a2a2a; color: #f0f0f0; margin: 0; padding: 0; height: 100vh; display: flex; align-items: center; justify-content: center; overflow: hidden; }
    .container { text-align: center; }
    h2 { font-weight: 300; letter-spacing: 0.5px; margin-bottom: 30px; }
    .loader { display: inline-block; position: relative; width: 80px; height: 80px; }
    .loader div { position: absolute; width: 16px; height: 16px; border-radius: 50%; background: #4a88ff; animation: loader 1.2s linear infinite; }
    .loader div:nth-child(1) { top: 8px; left: 8px; animation-delay: 0s; }
    .loader div:nth-child(2) { top: 8px; left: 32px; animation-delay: -0.4s; }
    .loader div:nth-child(3) { top: 8px; left: 56px; animation-delay: -0.8s; }
    .loader div:nth-child(4) { top: 32px; left: 8px; animation-delay: -0.4s; }
    .loader div:nth-child(5) { top: 32px; left: 32px; animation-delay: -0.8s; }
    .loader div:nth-child(6) { top: 32px; left: 56px; animation-delay: -1.2s; }
    .loader div:nth-child(7) { top: 56px; left: 8px; animation-delay: -0.8s; }
    .loader div:nth-child(8) { top: 56px; left: 32px; animation-delay: -1.2s; }
    .loader div:nth-child(9) { top: 56px; left: 56px; animation-delay: -1.6s; }
    @keyframes loader { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }
  </style>
</head>
<body>
  <div class="container">
    <h2>Waiting for content...</h2>
    <div class="loader">
      <div></div><div></div><div></div>
      <div></div><div></div><div></div>
      <div></div><div></div><div></div>
    </div>
  </div>
  <script src="/static/universal_script.js?v=TIMESTAMP_PLACEHOLDER"></script>
</body>
</html>
"""

    reload_events_queue = asyncio.Queue()
    submission_events_queue = asyncio.Queue()
    wait_events_queue = asyncio.Queue()  # Separate queue for wait operations
    
    # Use absolute path for upload directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    UPLOAD_DIR = os.path.join(script_dir, "images")
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    app.mount("/images", StaticFiles(directory=UPLOAD_DIR), name="images")

    @app.get("/", response_class=HTMLResponse)
    async def serve_page():
        current_time = int(time.time())
        html_with_timestamp = CURRENT_HTML.replace(
            '<script src="/static/universal_script.js?v=TIMESTAMP_PLACEHOLDER"></script>',
            f'<script src="/static/universal_script.js?v={current_time}"></script>'
        )
        return HTMLResponse(content=html_with_timestamp, status_code=200)

    @app.post("/update_html")
    async def update_html(request: Request):
        nonlocal CURRENT_HTML
        try:
            raw_html = await request.body()
            CURRENT_HTML = raw_html.decode("utf-8")
            await reload_events_queue.put({"event": "reload"})
            return JSONResponse({"status": "ok", "message": "HTML updated"})
        except Exception as e:
            return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

    @app.post("/upload_image")
    async def upload_image(image: UploadFile = File(...)):
        if not image.filename:
            return JSONResponse({"status": "error", "message": "No image provided"}, status_code=400)
        valid_exts = {"png", "jpg", "jpeg", "gif", "webp"}
        ext = image.filename.split(".")[-1].lower()
        if ext not in valid_exts:
            return JSONResponse({"status": "error", "message": "Invalid file type"}, status_code=400)
        unique_name = f"{uuid.uuid4()}.{ext}"
        file_path = os.path.join(UPLOAD_DIR, unique_name)
        with open(file_path, "wb") as f:
            content = await image.read()
            f.write(content)
        
        # Provide multiple path formats for flexibility
        relative_url = f"images/{unique_name}"
        absolute_path = os.path.abspath(file_path)
        full_url = f"http://{host}:{port}/images/{unique_name}"
        
        return JSONResponse({
            "status": "ok", 
            "image_name": unique_name,
            "image_url": relative_url,  # Keep for backwards compatibility
            "relative_path": relative_url,
            "absolute_path": absolute_path,
            "full_url": full_url,
            "file_size": len(content)
        })

    @app.post("/submit_form")
    async def submit_form(request: Request):
        nonlocal latest_event, event_consumed
        try:
            data = await request.json()
            # Store the latest event and mark as unconsumed
            latest_event = {
                "type": "form_submitted",
                "data": data,
                "timestamp": time.time()
            }
            event_consumed = False
            
            # Also put in SSE queue for any other listeners
            await submission_events_queue.put(data)
            return JSONResponse({"status": "ok", "message": "Form data received"})
        except Exception as e:
            return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

    @app.get("/sse_browser_stream")
    async def sse_browser_stream():
        async def event_generator():
            while True:
                msg = await reload_events_queue.get()
                yield f"data: {json.dumps(msg)}\n\n"
        return StreamingResponse(event_generator(), media_type="text/event-stream")

    @app.get("/sse_client_stream")
    async def sse_client_stream():
        async def event_generator():
            while True:
                data = await submission_events_queue.get()
                event_type = "form_submitted"
                yield f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
        return StreamingResponse(event_generator(), media_type="text/event-stream")

    @app.get("/wait_for_user_event")
    async def wait_for_user_event():
        """Wait indefinitely for a user event and return it immediately"""
        try:
            # This will block until a user submits an event (no timeout)
            data = await wait_events_queue.get()
            return JSONResponse({
                "type": "form_submitted", 
                "data": data,
                "timestamp": time.time()
            })
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)

    @app.get("/wait_for_user_event_poll")
    async def wait_for_user_event_poll():
        """Poll for user events with a short timeout"""
        nonlocal latest_event, event_consumed
        try:
            if latest_event and not event_consumed:
                # Mark event as consumed so next polls won't return it
                event_consumed = True
                return JSONResponse({
                    "has_event": True,
                    **latest_event
                })
            else:
                # No unconsumed event available
                return JSONResponse({
                    "has_event": False,
                    "timestamp": time.time()
                })
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)

    @app.post("/clear_wait_queue")
    async def clear_wait_queue():
        """Clear any pending events"""
        nonlocal latest_event, event_consumed
        try:
            latest_event = None
            event_consumed = True
            return JSONResponse({"cleared": True})
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)

    @app.get("/static/universal_script.js")
    async def serve_universal_script():
        try:
            # Use absolute path relative to this script's location
            script_dir = os.path.dirname(os.path.abspath(__file__))
            script_path = os.path.join(script_dir, "static", "universal_script.js")
            with open(script_path, "r") as f:
                content = f.read()
            response = HTMLResponse(content=content)
            response.headers.update({
                "Content-Type": "application/javascript",
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0"
            })
            return response
        except Exception as e:
            return HTMLResponse(
                content=f"console.error('Error loading script: {str(e)}');",
                headers={"Content-Type": "application/javascript"},
                status_code=500
            )
    
    # Run the server with no timeouts
    uvicorn.run(
        app, 
        host=host, 
        port=port, 
        reload=False,
        timeout_keep_alive=0,  # Disable keep-alive timeout
        timeout_graceful_shutdown=30,
        access_log=False
    )

# --- Main Entrypoint ---
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

        action = params.get("action")
        host = params.get("host", SERVER_HOST)
        port = params.get("port", SERVER_PORT)

        if action == "start":
            result = start_server(host, port)
        elif action == "status":
            result = server_status(host, port)
        elif action == "kill":
            result = kill_server()
        elif action == "push_html":
            html = params.get("html")
            filename = params.get("filename")
            
            # Get HTML content from either direct HTML or filename
            if filename:
                try:
                    # Handle both relative and absolute paths
                    file_path = os.path.abspath(os.path.expanduser(filename))
                    with open(file_path, 'r', encoding='utf-8') as f:
                        html = f.read()
                except FileNotFoundError:
                    result = {"error": f"File not found: {filename}"}
                    print(json.dumps(result, ensure_ascii=False))
                    sys.exit(1)
                except Exception as e:
                    result = {"error": f"Failed to read file '{filename}': {e}"}
                    print(json.dumps(result, ensure_ascii=False))
                    sys.exit(1)
            elif not html:
                raise ValueError("Either 'html' content or 'filename' parameter is required for push_html action")
            
            wait_for_response = params.get("wait_for_response", False)
            result = push_html(html, host, port, wait_for_response)
        elif action == "run_server":
            # Run server directly (blocking mode)
            run_server_directly(host, port)
            return
        else:
            raise ValueError(f"Unknown action: {action}")

        print(json.dumps(result, ensure_ascii=False))
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)

if __name__ == "__main__":
    main()
