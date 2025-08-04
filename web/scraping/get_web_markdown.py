#!/usr/bin/env python3
"""
Web to Markdown Converter Tool - Simple JSON Convention
Downloads web pages and converts their content to clean Markdown format
"""

import json
import sys
import os
from typing import Dict, Any, Optional

# Test mode for autodiscovery
if len(sys.argv) > 1 and sys.argv[1] == '{"__test__": true}':
    print('{"success": true, "_simple": true}')
    sys.exit(0)

# Schema dump for fractalic introspection
if len(sys.argv) > 1 and sys.argv[1] in ["--fractalic-dump-schema", "--fractalic-dump-multi-schema"]:
    schema = {
        "name": "get_web_markdown",
        "description": "Download web pages and convert their content to clean Markdown format. Perfect for extracting readable text from articles, blogs, documentation, and other web content for analysis or processing.",
        "command": "simple-json",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "Full HTTP/HTTPS URL of the web page to download and convert to Markdown. Should include the protocol (http:// or https://)"
                },
                "timeout": {
                    "type": "integer",
                    "description": "Request timeout in seconds (default: 10)",
                    "default": 10,
                    "minimum": 1,
                    "maximum": 60
                },
                "user_agent": {
                    "type": "string",
                    "description": "Custom User-Agent header to use for the request (default: Fractalic-Markdown-Tool/2.0)"
                },
                "include_links": {
                    "type": "boolean",
                    "description": "Whether to preserve hyperlinks in the Markdown output (default: true)"
                },
                "strip_html": {
                    "type": "boolean",
                    "description": "Whether to strip HTML tags more aggressively for cleaner text (default: false)"
                }
            },
            "required": ["url"]
        }
    }
    print(json.dumps(schema, indent=2, ensure_ascii=False))
    sys.exit(0)

def get_html_converter():
    """Get the best available HTML to Markdown converter"""
    try:
        from markdownify import markdownify
        return markdownify
    except ImportError:
        try:
            from markitdown import convert
            return convert
        except ImportError:
            return None

def fetch_webpage(url: str, timeout: int = 10, user_agent: str = None) -> Dict[str, Any]:
    """Fetch a webpage and return its content"""
    try:
        import requests
    except ImportError:
        return {"error": "Missing dependency: pip install requests"}
    
    if not user_agent:
        user_agent = "Fractalic-Markdown-Tool/2.0"
    
    try:
        headers = {"User-Agent": user_agent}
        resp = requests.get(url, timeout=timeout, headers=headers)
        resp.raise_for_status()
        
        # Ensure proper encoding detection
        if resp.encoding is None or resp.encoding == 'ISO-8859-1':
            resp.encoding = resp.apparent_encoding
        
        return {
            "success": True,
            "content": resp.text,
            "status_code": resp.status_code,
            "content_type": resp.headers.get("content-type", ""),
            "final_url": resp.url
        }
        
    except requests.exceptions.Timeout:
        return {"error": f"Request timeout after {timeout} seconds"}
    except requests.exceptions.ConnectionError:
        return {"error": "Failed to connect to the URL"}
    except requests.exceptions.HTTPError as e:
        return {"error": f"HTTP error {e.response.status_code}: {e.response.reason}"}
    except requests.exceptions.RequestException as e:
        return {"error": f"Request failed: {str(e)}"}
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}

def convert_to_markdown(html_content: str, include_links: bool = True, strip_html: bool = False) -> Dict[str, Any]:
    """Convert HTML content to Markdown"""
    converter = get_html_converter()
    if not converter:
        return {"error": "Missing dependency: pip install markdownify"}
    
    try:
        # Configure conversion options based on the converter
        if converter.__name__ == 'markdownify':
            if strip_html:
                # Only use 'strip' (not 'convert')
                options = {
                    'strip': ['script', 'style']
                }
            else:
                # Only use 'convert' (not 'strip')
                options = {
                    'convert': ['a', 'b', 'blockquote', 'br', 'div', 'em', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'i', 'li', 'ol', 'p', 'pre', 'strong', 'ul', 'code']
                }
                if not include_links:
                    options['convert'] = [tag for tag in options['convert'] if tag != 'a']
            markdown_text = converter(html_content, **options)
        else:
            # Fallback converter
            markdown_text = converter(html_content)
        
        # Clean up the markdown
        lines = markdown_text.split('\n')
        cleaned_lines = []
        prev_line_empty = False
        
        for line in lines:
            line = line.strip()
            
            # Skip multiple consecutive empty lines
            if not line:
                if not prev_line_empty:
                    cleaned_lines.append('')
                prev_line_empty = True
                continue
            
            prev_line_empty = False
            cleaned_lines.append(line)
        
        # Remove leading/trailing empty lines
        while cleaned_lines and not cleaned_lines[0]:
            cleaned_lines.pop(0)
        while cleaned_lines and not cleaned_lines[-1]:
            cleaned_lines.pop()
        
        return {
            "success": True,
            "markdown": '\n'.join(cleaned_lines),
            "length": len(cleaned_lines),
            "word_count": len(' '.join(cleaned_lines).split())
        }
        
    except Exception as e:
        return {"error": f"Markdown conversion failed: {str(e)}"}

def execute_web_to_markdown(url: str, **kwargs) -> Dict[str, Any]:
    """Main function to fetch and convert web page to markdown"""
    
    # Validate URL
    if not url or not isinstance(url, str):
        return {"error": "URL is required and must be a string"}
    
    if not (url.startswith('http://') or url.startswith('https://')):
        return {"error": "URL must start with http:// or https://"}
    
    # Extract parameters
    timeout = kwargs.get('timeout', 10)
    user_agent = kwargs.get('user_agent')
    include_links = kwargs.get('include_links', True)
    strip_html = kwargs.get('strip_html', False)
    
    # Validate parameters
    if not isinstance(timeout, int) or timeout < 1 or timeout > 60:
        return {"error": "Timeout must be an integer between 1 and 60 seconds"}
    
    # Fetch the webpage
    fetch_result = fetch_webpage(url, timeout, user_agent)
    if not fetch_result.get('success'):
        return fetch_result
    
    # Convert to markdown
    convert_result = convert_to_markdown(
        fetch_result['content'], 
        include_links=include_links,
        strip_html=strip_html
    )
    if not convert_result.get('success'):
        return convert_result
    
    # Return combined result
    return {
        "success": True,
        "url": url,
        "final_url": fetch_result.get('final_url', url),
        "content_type": fetch_result.get('content_type', ''),
        "markdown": convert_result['markdown'],
        "length": convert_result['length'],
        "word_count": convert_result['word_count'],
        "status_code": fetch_result.get('status_code')
    }

def main():
    """Main entry point for simple JSON contract"""
    if len(sys.argv) == 1:
        print(json.dumps({
            "error": "No URL specified",
            "usage": "python3 get_web_markdown.py '{\"url\": \"https://example.com\"}'"
        }, ensure_ascii=False))
        sys.exit(1)
    elif len(sys.argv) != 2:
        print(json.dumps({"error": "Usage: python3 get_web_markdown.py '{\"url\": \"https://example.com\", ...}'"}, ensure_ascii=False))
        sys.exit(1)
    
    try:
        # Parse JSON input
        input_data = json.loads(sys.argv[1])
        
        # Extract URL
        url = input_data.get('url')
        if not url:
            print(json.dumps({"error": "Missing 'url' field in input JSON"}, ensure_ascii=False))
            sys.exit(1)
        
        # Remove url from kwargs
        kwargs = {k: v for k, v in input_data.items() if k != 'url'}
        
        # Execute the conversion
        result = execute_web_to_markdown(url, **kwargs)
        
        # Output result as JSON
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"Invalid JSON input: {str(e)}"}, ensure_ascii=False))
        sys.exit(1)
    except KeyboardInterrupt:
        print(json.dumps({"error": "Operation cancelled by user"}, ensure_ascii=False))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"error": f"Execution failed: {str(e)}"}, ensure_ascii=False))
        sys.exit(1)

if __name__ == "__main__":
    main()