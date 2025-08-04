#!/usr/bin/env python3
"""
Tavily Search Tool - Simple JSON Discovery Tool
Accepts a single JSON argument and returns JSON output for LLM integration.
Implements the Simple JSON Discovery contract for Fractalic autodiscovery.
"""

import os
import requests
import json
import sys

TAVILY_API_KEY = os.getenv('TAVILY_API_KEY')

def get_schema():
    return {
        "name": "tavily_search",
        "description": "Interact with the Tavily Search and Extract API. Supports 'search' and 'extract' tasks.",
        "parameters": {
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "enum": ["search", "extract"],
                    "description": "API task to perform: 'search' or 'extract'"
                },
                "query": {
                    "type": "string",
                    "description": "Search query (for 'search') or comma-separated URLs (for 'extract')"
                },
                "search_depth": {
                    "type": "string",
                    "enum": ["basic", "advanced"],
                    "default": "basic",
                    "description": "Depth of the search (for 'search')"
                },
                "topic": {
                    "type": "string",
                    "enum": ["general", "news"],
                    "default": "general",
                    "description": "Search topic (for 'search')"
                },
                "days": {
                    "type": "integer",
                    "default": 3,
                    "description": "Days back for news topic (for 'search')"
                },
                "max_results": {
                    "type": "integer",
                    "default": 5,
                    "description": "Maximum number of results to return (for 'search')"
                },
                "include_images": {
                    "type": "boolean",
                    "default": False,
                    "description": "Include images in search results (for 'search')"
                },
                "include_image_descriptions": {
                    "type": "boolean",
                    "default": False,
                    "description": "Include image descriptions (requires include_images, for 'search')"
                },
                "include_answer": {
                    "type": "boolean",
                    "default": False,
                    "description": "Include a generated answer (for 'search')"
                },
                "include_raw_content": {
                    "type": "boolean",
                    "default": False,
                    "description": "Include raw content of results (for 'search')"
                },
                "include_domains": {
                    "type": "string",
                    "description": "Comma-separated list of domains to include (for 'search')"
                },
                "exclude_domains": {
                    "type": "string",
                    "description": "Comma-separated list of domains to exclude (for 'search')"
                }
            },
            "required": ["task", "query"]
        }
    }

def build_payload(params):
    if params["task"] == "search":
        payload = {
            "query": params["query"],
            "search_depth": params.get("search_depth", "basic"),
            "topic": params.get("topic", "general"),
            "days": params.get("days", 3),
            "max_results": params.get("max_results", 5),
            "include_images": params.get("include_images", False),
            "include_image_descriptions": params.get("include_image_descriptions", False),
            "include_answer": params.get("include_answer", False),
            "include_raw_content": params.get("include_raw_content", False),
            "include_domains": params.get("include_domains", "").split(",") if params.get("include_domains") else [],
            "exclude_domains": params.get("exclude_domains", "").split(",") if params.get("exclude_domains") else []
        }
    else:  # extract task
        payload = {
            "urls": [url.strip() for url in params["query"].split(",")]
        }
    return payload

def call_api(endpoint, payload):
    if not TAVILY_API_KEY:
        return {"error": "TAVILY_API_KEY environment variable is not set."}
    headers = {
        'Authorization': f'Bearer {TAVILY_API_KEY}',
        'Content-Type': 'application/json'
    }
    try:
        response = requests.post(endpoint, headers=headers, json=payload, timeout=15)
        if response.ok:
            return {"success": True, "data": response.json()}
        else:
            return {"error": f"HTTP {response.status_code}", "response": response.text}
    except Exception as e:
        return {"error": str(e)}

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
        task = params.get("task")
        query = params.get("query")
        if not task or not query:
            raise ValueError("'task' and 'query' parameters are required")
        if params.get("include_image_descriptions") and not params.get("include_images"):
            raise ValueError("'include_image_descriptions' requires 'include_images' to be true")
        endpoint = 'https://api.tavily.com/search' if task == 'search' else 'https://api.tavily.com/extract'
        payload = build_payload(params)
        result = call_api(endpoint, payload)
        print(json.dumps(result, ensure_ascii=False))
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)

if __name__ == "__main__":
    main()