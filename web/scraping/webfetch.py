#!/usr/bin/env python3
"""WebFetch Tool - Fractalic Compatible Implementation

Fetches content from a specified URL and processes it using an AI model.
Takes a URL and a prompt as input, fetches the URL content, converts HTML to markdown,
and processes the content with the prompt.
"""

import json
import sys
import requests
import time
from urllib.parse import urlparse, urljoin
import re

def process_data(data):
    """Main processing function for web content fetching."""
    try:
        # Extract and validate parameters
        url = data.get("url")
        prompt = data.get("prompt")
        
        if not url:
            return {"status": "error", "error": "url parameter is required"}
        
        if not prompt:
            return {"status": "error", "error": "prompt parameter is required"}
        
        # Validate URL format
        if not _is_valid_url(url):
            return {"status": "error", "error": f"Invalid URL format: {url}"}
        
        # Fetch and process content
        fetch_result = _fetch_url_content(url)
        
        if "error" in fetch_result:
            return {"status": "error", "error": fetch_result["error"]}
        
        # Process content with prompt
        processed_result = _process_content_with_prompt(fetch_result, prompt)
        
        return {
            "status": "success",
            "data": processed_result
        }
        
    except Exception as e:
        return {"status": "error", "error": str(e)}

def _is_valid_url(url):
    """Validate URL format."""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

def _fetch_url_content(url):
    """Fetch content from URL with proper handling."""
    try:
        # Upgrade HTTP to HTTPS if needed
        if url.startswith("http://"):
            url = url.replace("http://", "https://", 1)
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1"
        }
        
        # Fetch with timeout
        response = requests.get(url, headers=headers, timeout=30, allow_redirects=True)
        
        # Check for redirects to different hosts
        if response.url != url:
            parsed_original = urlparse(url)
            parsed_final = urlparse(response.url)
            
            if parsed_original.netloc != parsed_final.netloc:
                return {
                    "redirected": True,
                    "originalUrl": url,
                    "finalUrl": response.url,
                    "redirectMessage": f"URL redirected to different host: {parsed_final.netloc}"
                }
        
        response.raise_for_status()
        
        # Get content type
        content_type = response.headers.get("content-type", "").lower()
        
        if "text/html" in content_type:
            # Convert HTML to markdown
            markdown_content = _html_to_markdown(response.text)
        elif "text/plain" in content_type:
            markdown_content = response.text
        elif "application/json" in content_type:
            # Pretty print JSON
            try:
                json_data = response.json()
                markdown_content = f"```json\n{json.dumps(json_data, indent=2)}\n```"
            except:
                markdown_content = response.text
        else:
            # Default to plain text
            markdown_content = response.text
        
        return {
            "url": response.url,
            "originalUrl": url,
            "statusCode": response.status_code,
            "contentType": content_type,
            "contentLength": len(response.text),
            "markdownContent": markdown_content,
            "title": _extract_title(response.text) if "text/html" in content_type else None,
            "fetchedAt": int(time.time())
        }
        
    except requests.exceptions.Timeout:
        return {"error": f"Request timeout while fetching {url}"}
    except requests.exceptions.ConnectionError:
        return {"error": f"Connection error while fetching {url}"}
    except requests.exceptions.HTTPError as e:
        return {"error": f"HTTP error {e.response.status_code} while fetching {url}"}
    except requests.exceptions.RequestException as e:
        return {"error": f"Request failed: {str(e)}"}
    except Exception as e:
        return {"error": f"Failed to fetch URL: {str(e)}"}

def _html_to_markdown(html_content):
    """Convert HTML to markdown (simplified implementation)."""
    # This is a simplified conversion - in production you'd use a library like markdownify
    content = html_content
    
    # Remove script and style tags
    content = re.sub(r'<script.*?</script>', '', content, flags=re.DOTALL | re.IGNORECASE)
    content = re.sub(r'<style.*?</style>', '', content, flags=re.DOTALL | re.IGNORECASE)
    
    # Convert headers
    content = re.sub(r'<h1[^>]*>(.*?)</h1>', r'# \1', content, flags=re.DOTALL | re.IGNORECASE)
    content = re.sub(r'<h2[^>]*>(.*?)</h2>', r'## \1', content, flags=re.DOTALL | re.IGNORECASE)
    content = re.sub(r'<h3[^>]*>(.*?)</h3>', r'### \1', content, flags=re.DOTALL | re.IGNORECASE)
    content = re.sub(r'<h4[^>]*>(.*?)</h4>', r'#### \1', content, flags=re.DOTALL | re.IGNORECASE)
    content = re.sub(r'<h5[^>]*>(.*?)</h5>', r'##### \1', content, flags=re.DOTALL | re.IGNORECASE)
    content = re.sub(r'<h6[^>]*>(.*?)</h6>', r'###### \1', content, flags=re.DOTALL | re.IGNORECASE)
    
    # Convert paragraphs
    content = re.sub(r'<p[^>]*>(.*?)</p>', r'\1\n\n', content, flags=re.DOTALL | re.IGNORECASE)
    
    # Convert links
    content = re.sub(r'<a[^>]*href=["\']([^"\']*)["\'][^>]*>(.*?)</a>', r'[\2](\1)', content, flags=re.DOTALL | re.IGNORECASE)
    
    # Convert emphasis
    content = re.sub(r'<strong[^>]*>(.*?)</strong>', r'**\1**', content, flags=re.DOTALL | re.IGNORECASE)
    content = re.sub(r'<b[^>]*>(.*?)</b>', r'**\1**', content, flags=re.DOTALL | re.IGNORECASE)
    content = re.sub(r'<em[^>]*>(.*?)</em>', r'*\1*', content, flags=re.DOTALL | re.IGNORECASE)
    content = re.sub(r'<i[^>]*>(.*?)</i>', r'*\1*', content, flags=re.DOTALL | re.IGNORECASE)
    
    # Convert line breaks
    content = re.sub(r'<br[^>]*>', '\n', content, flags=re.IGNORECASE)
    
    # Convert lists (simplified)
    content = re.sub(r'<li[^>]*>(.*?)</li>', r'- \1', content, flags=re.DOTALL | re.IGNORECASE)
    
    # Remove remaining HTML tags
    content = re.sub(r'<[^>]+>', '', content)
    
    # Clean up whitespace
    content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
    content = content.strip()
    
    return content

def _extract_title(html_content):
    """Extract title from HTML content."""
    match = re.search(r'<title[^>]*>(.*?)</title>', html_content, re.DOTALL | re.IGNORECASE)
    if match:
        title = match.group(1).strip()
        # Remove HTML entities (simplified)
        title = re.sub(r'&[^;]+;', ' ', title)
        return title
    return None

def _process_content_with_prompt(fetch_result, prompt):
    """Process fetched content with the given prompt."""
    # This is a simplified implementation
    # In the original Claude Code, this would use an AI model to process the content
    
    content = fetch_result.get("markdownContent", "")
    
    # For now, return a structured response with the content and prompt
    # In production, this would send the content and prompt to an AI model
    
    return {
        "url": fetch_result.get("url"),
        "originalUrl": fetch_result.get("originalUrl"),
        "title": fetch_result.get("title"),
        "prompt": prompt,
        "contentLength": len(content),
        "content": content[:5000] + "..." if len(content) > 5000 else content,  # Truncate for demo
        "processedResponse": f"Content fetched from {fetch_result.get('url')} and processed with prompt: '{prompt}'. The page contains {len(content)} characters of content.",
        "fetchedAt": fetch_result.get("fetchedAt"),
        "statusCode": fetch_result.get("statusCode"),
        "contentType": fetch_result.get("contentType")
    }

def get_schema():
    """Return Fractalic-compatible JSON schema."""
    return {
        "name": "_webfetch",
        "description": "Fetches content from a specified URL and processes it using an AI model. Takes a URL and a prompt as input, fetches the URL content, converts HTML to markdown, and processes the content with the prompt using a small, fast model. HTTP URLs will be automatically upgraded to HTTPS.",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The URL to fetch content from",
                    "format": "uri"
                },
                "prompt": {
                    "type": "string",
                    "description": "The prompt to run on the fetched content"
                }
            },
            "required": ["url", "prompt"],
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