#!/usr/bin/env python3
"""
Efficiently discover HubSpot object properties with smart filtering and summary modes.
Prevents context overload by providing concise summaries and targeted detail requests.
"""
from __future__ import annotations

import json
import sys
from typing import Any, Dict, List


def _filter_properties(properties: List[Any], filter_name: str = None, filter_type: str = None) -> List[Any]:
    """Filter properties by name pattern and/or type."""
    filtered = properties
    
    if filter_name:
        # Case-insensitive pattern matching
        filtered = [p for p in filtered if filter_name.lower() in p.name.lower()]
    
    if filter_type:
        # Filter by property type
        filtered = [p for p in filtered if p.type.lower() == filter_type.lower()]
    
    return filtered


def process_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Smart property discovery with filtering and summary modes."""
    try:
        # Import dependencies inside the function to avoid top-level import issues
        from hubspot_hub_helpers import hs_client
        
        # Try to import cache - if not available, continue without caching
        try:
            from hubspot_schema_cache import get_cache
            cache_available = True
        except ImportError:
            cache_available = False
        
        object_type = data.get("objectType", "tickets")
        mode = data.get("mode", "summary")  # "summary" or "detail"
        property_name = data.get("propertyName")  # Specific property to get details for
        filter_name = data.get("filterName")  # Filter by name pattern
        filter_type = data.get("filterType")  # Filter by type (enumeration, string, etc.)
        include_options = data.get("includeOptions", False)  # Include option arrays
        use_cache = data.get("useCache", True)  # Whether to use cache
        
        if not object_type:
            return {"error": "objectType parameter is required (e.g., 'tickets', 'deals', 'contacts')"}
        
        # Check cache first if available and enabled
        if cache_available and use_cache:
            cache = get_cache()
            cached_result = cache.get_properties(object_type, mode, filter_name)
            if cached_result:
                return {
                    **cached_result,
                    "cache_hit": True,
                    "cache_timestamp": "cached"
                }
        
        cli = hs_client()
        
        try:
            # Get properties for any object type using the generic API
            properties_api = cli.crm.properties.core_api.get_all(object_type=object_type)
            
            # Apply filters
            filtered_properties = _filter_properties(
                properties_api.results, 
                filter_name=filter_name, 
                filter_type=filter_type
            )
            
            # Handle specific property request (detail mode)
            if property_name:
                matching_prop = None
                for prop in filtered_properties:
                    if prop.name == property_name:
                        matching_prop = prop
                        break
                
                if not matching_prop:
                    return {"error": f"Property '{property_name}' not found for {object_type}"}
                
                prop_detail = {
                    "name": matching_prop.name,
                    "label": matching_prop.label,
                    "type": matching_prop.type,
                    "description": matching_prop.description if hasattr(matching_prop, 'description') else None
                }
                
                # Always include options for specific property requests
                if hasattr(matching_prop, 'options') and matching_prop.options:
                    prop_detail["options"] = [
                        {"value": opt.value, "label": opt.label}
                        for opt in matching_prop.options
                    ]
                    prop_detail["optionsCount"] = len(matching_prop.options)
                
                return {
                    "objectType": object_type,
                    "mode": "detail",
                    "property": property_name,
                    "details": prop_detail
                }
            
            # Summary mode - efficient overview
            if mode == "summary":
                summary = {
                    "objectType": object_type,
                    "mode": "summary",
                    "totalProperties": len(filtered_properties),
                    "filters": {
                        "nameFilter": filter_name,
                        "typeFilter": filter_type
                    },
                    "propertiesSummary": []
                }
                
                type_counts = {}
                
                for prop in filtered_properties:
                    # Count options if present
                    options_count = 0
                    if hasattr(prop, 'options') and prop.options:
                        options_count = len(prop.options)
                    
                    # Track type counts
                    prop_type = prop.type
                    type_counts[prop_type] = type_counts.get(prop_type, 0) + 1
                    
                    summary["propertiesSummary"].append({
                        "name": prop.name,
                        "label": prop.label,
                        "type": prop.type,
                        "hasOptions": options_count > 0,
                        "optionsCount": options_count,
                        "description": (prop.description[:100] + "...") if hasattr(prop, 'description') and prop.description and len(prop.description) > 100 else (prop.description if hasattr(prop, 'description') else None)
                    })
                
                summary["typeBreakdown"] = type_counts
                
                # Cache the result if cache is available
                if cache_available and use_cache:
                    cache.set_properties(object_type, summary, mode, filter_name)
                
                return summary
            
            # Detail mode - full information but still efficient
            elif mode == "detail":
                result = {
                    "objectType": object_type,
                    "mode": "detail",
                    "totalProperties": len(filtered_properties),
                    "filters": {
                        "nameFilter": filter_name,
                        "typeFilter": filter_type
                    },
                    "properties": {}
                }
                
                for prop in filtered_properties:
                    prop_info = {
                        "name": prop.name,
                        "label": prop.label,
                        "type": prop.type,
                        "description": prop.description if hasattr(prop, 'description') else None
                    }
                    
                    # Only include options if explicitly requested or if small
                    if hasattr(prop, 'options') and prop.options:
                        options_count = len(prop.options)
                        prop_info["optionsCount"] = options_count
                        
                        if include_options or options_count <= 10:
                            # Include options for small lists or when explicitly requested
                            prop_info["options"] = [
                                {"value": opt.value, "label": opt.label}
                                for opt in prop.options
                            ]
                        else:
                            # For large option lists, provide summary
                            prop_info["optionsPreview"] = [
                                {"value": opt.value, "label": opt.label}
                                for opt in prop.options[:5]  # First 5 options
                            ]
                            prop_info["note"] = f"Large option list ({options_count} options). Use propertyName='{prop.name}' to get full options."
                    
                    result["properties"][prop.name] = prop_info
                
                # Cache the result if cache is available
                if cache_available and use_cache:
                    cache.set_properties(object_type, result, mode, filter_name)
                
                return result
            
            else:
                return {"error": f"Invalid mode '{mode}'. Use 'summary' or 'detail'"}
            
        except Exception as err:
            return {"error": f"Failed to get properties: {str(err)}"}
    
    except Exception as e:
        return {"error": f"Property discovery failed: {str(e)}"}


def main() -> None:
    # Test mode for autodiscovery (REQUIRED)
    if len(sys.argv) == 2 and sys.argv[1] == '{"__test__": true}':
        print(json.dumps({"success": True, "_simple": True}))
        return
    
    # Optional: Rich schema for better LLM integration
    if len(sys.argv) == 2 and sys.argv[1] == "--fractalic-dump-schema":
        schema = {
            "description": "Efficiently discover HubSpot object properties with smart filtering and summary modes. Prevents context overload by providing concise summaries and targeted detail requests.",
            "parameters": {
                "type": "object",
                "properties": {
                    "objectType": {
                        "type": "string",
                        "description": "Type of HubSpot object. Supports all CRM objects including standard (contacts, deals, tickets, companies), commerce (products, line_items, quotes), engagements (calls, emails, meetings, notes, tasks, communications, postal_mail), and custom objects.",
                        "examples": ["contacts", "deals", "tickets", "companies", "products", "line_items", "quotes", "calls", "emails", "meetings", "notes", "tasks", "communications", "postal_mail"]
                    },
                    "mode": {
                        "type": "string",
                        "description": "Discovery mode: 'summary' for overview with counts, 'detail' for full info",
                        "enum": ["summary", "detail"]
                    },
                    "propertyName": {
                        "type": "string",
                        "description": "Get details for a specific property (overrides mode, always returns full details)"
                    },
                    "filterName": {
                        "type": "string",
                        "description": "Filter properties by name pattern (case-insensitive, e.g. 'email', 'phone', 'timeline')"
                    },
                    "filterType": {
                        "type": "string",
                        "description": "Filter properties by type (e.g. 'enumeration', 'string', 'number', 'datetime')"
                    },
                    "includeOptions": {
                        "type": "boolean",
                        "description": "Include full option arrays in detail mode (default: false, shows preview only)"
                    }
                },
                "required": ["objectType"]
            },
            "examples": [
                {
                    "description": "Get summary of all contact properties",
                    "input": {"objectType": "contacts", "mode": "summary"}
                },
                {
                    "description": "Find email-related properties",
                    "input": {"objectType": "contacts", "filterName": "email", "mode": "summary"}
                },
                {
                    "description": "Get all enumeration properties (dropdowns)",
                    "input": {"objectType": "deals", "filterType": "enumeration", "mode": "detail"}
                },
                {
                    "description": "Get full details for specific property",
                    "input": {"objectType": "tickets", "propertyName": "hs_ticket_category"}
                }
            ]
        }
        print(json.dumps(schema, ensure_ascii=False))
        return
    
    # Process JSON input (REQUIRED)
    try:
        if len(sys.argv) != 2:
            raise ValueError("Expected exactly one JSON argument")
        
        params = json.loads(sys.argv[1])
        result = process_data(params)
        print(json.dumps(result, ensure_ascii=False))
        
    except Exception as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    main()
