#!/usr/bin/env python3
"""
HubSpot Universal Object Enumerator

Provides flexible, efficient enumeration of any HubSpot object type with
surgical control over extraction scope. Supports connection-aware extraction
and context-efficient data access.

• Enumerate objects by type with filtering
• Extract objects with their associations
• Follow association chains with depth control
• Bulk extraction with connection mapping
• Context-efficient sampling and limiting
"""
from __future__ import annotations

import json
import logging
import os
import sys
import time
from typing import Any, Dict, List, Optional

# Add parent directories to sys.path to allow importing hubspot_hub_helpers
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'manage'))

from hubspot_hub_helpers import auto_probe, hs_client, ok, fatal

# Configure logging
log = logging.getLogger(__name__)

def get_smart_properties(object_type: str, extraction_mode: str) -> List[str]:
    """Get smart default properties based on object type and extraction mode."""
    
    base_properties = {
        "contacts": ["email", "firstname", "lastname", "company", "createdate", "lastmodifieddate"],
        "deals": ["dealname", "amount", "dealstage", "pipeline", "createdate", "closedate"],
        "tickets": ["hs_ticket_priority", "subject", "content", "hs_pipeline_stage", "createdate"],
        "companies": ["name", "domain", "industry", "city", "state", "country", "createdate"],
        "tasks": ["hs_task_subject", "hs_task_body", "hs_task_status", "hs_timestamp", "hs_task_priority"],
        "products": ["name", "description", "price", "hs_sku", "createdate"]
    }
    
    detailed_properties = {
        "contacts": ["email", "firstname", "lastname", "company", "phone", "website", "jobtitle", 
                    "lifecyclestage", "hubspotscore", "createdate", "lastmodifieddate", "notes_last_updated"],
        "deals": ["dealname", "amount", "dealstage", "pipeline", "dealtype", "description", 
                 "createdate", "closedate", "lastmodifieddate", "hubspot_owner_id"],
        "tickets": ["hs_ticket_priority", "subject", "content", "hs_pipeline_stage", "source_type",
                   "createdate", "hs_lastmodifieddate", "hubspot_owner_id"],
        "companies": ["name", "domain", "industry", "city", "state", "country", "phone", "website",
                     "description", "createdate", "lastmodifieddate", "hubspot_owner_id"]
    }
    
    if extraction_mode in ["detailed", "with_associations"]:
        return detailed_properties.get(object_type, base_properties.get(object_type, []))
    else:
        return base_properties.get(object_type, [])

def enumerate_objects(client, object_type: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Enumerate objects with specified parameters."""
    try:
        extraction_mode = params.get("extractionMode", "sample")
        limit = params.get("limit", 50)
        properties = params.get("properties", get_smart_properties(object_type, extraction_mode))
        
        # Build API parameters
        api_params = {
            "limit": limit,
            "properties": properties
        }
        
        # Add associations if requested
        include_associations = params.get("includeAssociations", [])
        if include_associations and extraction_mode in ["with_associations", "connection_focused"]:
            api_params["associations"] = include_associations
        
        # Apply filters if specified
        filters = params.get("filters", {})
        if filters:
            api_params.update(build_filters(filters))
        
        # Apply sorting
        sort_by = params.get("sortBy", "createdate")
        # Note: Sorting is handled at the property level, not as a separate parameter
        # We'll rely on the default sorting behavior of the API
        
        # Execute API call based on object type
        results = []
        if object_type == "contacts":
            response = client.crm.contacts.basic_api.get_page(**api_params)
        elif object_type == "deals":
            response = client.crm.deals.basic_api.get_page(**api_params)
        elif object_type == "tickets":
            response = client.crm.tickets.basic_api.get_page(**api_params)
        elif object_type == "companies":
            response = client.crm.companies.basic_api.get_page(**api_params)
        else:
            # Try generic object API
            response = client.crm.objects.basic_api.get_page(object_type=object_type, **api_params)
        
        # Process results based on extraction mode
        if extraction_mode == "list":
            results = [{"id": obj.id} for obj in response.results]
        elif extraction_mode == "sample":
            results = [{"id": obj.id, "properties": obj.properties} for obj in response.results]
        elif extraction_mode in ["detailed", "with_associations"]:
            results = []
            for obj in response.results:
                obj_data = {
                    "id": obj.id,
                    "properties": obj.properties
                }
                if hasattr(obj, 'associations') and obj.associations:
                    # Convert associations to serializable format
                    serializable_associations = {}
                    for assoc_type, assoc_data in obj.associations.items():
                        if hasattr(assoc_data, 'results'):
                            serializable_associations[assoc_type] = [
                                {"id": assoc_obj.id, "type": getattr(assoc_obj, 'type', assoc_type)}
                                for assoc_obj in assoc_data.results
                            ]
                        else:
                            serializable_associations[assoc_type] = []
                    obj_data["associations"] = serializable_associations
                results.append(obj_data)
        elif extraction_mode == "connection_focused":
            # Sort by connection count if associations are available
            results = []
            for obj in response.results:
                connection_count = 0
                serializable_associations = {}
                
                if hasattr(obj, 'associations') and obj.associations:
                    for assoc_type, assoc_data in obj.associations.items():
                        if hasattr(assoc_data, 'results'):
                            assoc_list = [
                                {"id": assoc_obj.id, "type": getattr(assoc_obj, 'type', assoc_type)}
                                for assoc_obj in assoc_data.results
                            ]
                            serializable_associations[assoc_type] = assoc_list
                            connection_count += len(assoc_list)
                        else:
                            serializable_associations[assoc_type] = []
                
                results.append({
                    "id": obj.id,
                    "properties": obj.properties,
                    "connection_count": connection_count,
                    "associations": serializable_associations
                })
            
            # Sort by connection count
            results.sort(key=lambda x: x["connection_count"], reverse=True)
        
        return {
            "object_type": object_type,
            "extraction_mode": extraction_mode,
            "total_extracted": len(results),
            "objects": results,
            "has_more": hasattr(response, 'paging') and response.paging is not None
        }
        
    except Exception as e:
        log.error(f"Error enumerating {object_type}: {e}")
        raise

def build_filters(filters: Dict[str, Any]) -> Dict[str, Any]:
    """Build HubSpot API filters from filter specification."""
    api_filters = {}
    
    # Date range filters
    if "dateRange" in filters:
        date_filter = filters["dateRange"]
        if "property" in date_filter and "startDate" in date_filter:
            api_filters["filters"] = [
                {
                    "propertyName": date_filter["property"],
                    "operator": "GTE",
                    "value": date_filter["startDate"]
                }
            ]
            if "endDate" in date_filter:
                api_filters["filters"].append({
                    "propertyName": date_filter["property"],
                    "operator": "LTE", 
                    "value": date_filter["endDate"]
                })
    
    # Property filters
    if "propertyFilters" in filters:
        if "filters" not in api_filters:
            api_filters["filters"] = []
        
        for prop_filter in filters["propertyFilters"]:
            api_filters["filters"].append({
                "propertyName": prop_filter["property"],
                "operator": prop_filter.get("operator", "EQ"),
                "value": prop_filter["value"]
            })
    
    return api_filters

def follow_association_chain(client, start_object_id: str, object_type: str, max_depth: int = 2) -> Dict[str, Any]:
    """Follow association chains from a starting object."""
    try:
        visited = set()
        result = {"start_object": start_object_id, "chains": []}
        
        def trace_object(obj_id: str, obj_type: str, depth: int, path: List[str]):
            if depth > max_depth or obj_id in visited:
                return
                
            visited.add(obj_id)
            path.append(f"{obj_type}:{obj_id}")
            
            try:
                # Get object with associations
                if obj_type == "contacts":
                    obj = client.crm.contacts.basic_api.get_by_id(obj_id, associations=["deals", "tickets", "companies"])
                elif obj_type == "deals":
                    obj = client.crm.deals.basic_api.get_by_id(obj_id, associations=["contacts", "tickets", "companies"])
                elif obj_type == "tickets":
                    obj = client.crm.tickets.basic_api.get_by_id(obj_id, associations=["contacts", "deals", "companies"])
                else:
                    return
                
                # Process associations
                if hasattr(obj, 'associations') and obj.associations:
                    for assoc_type, assoc_data in obj.associations.items():
                        if hasattr(assoc_data, 'results'):
                            for assoc_obj in assoc_data.results:
                                new_path = path.copy()
                                trace_object(assoc_obj.id, assoc_type, depth + 1, new_path)
                
                # Store the path if it's complete
                if len(path) > 1:
                    result["chains"].append(path.copy())
                    
            except Exception as e:
                log.debug(f"Could not trace {obj_type}:{obj_id}: {e}")
            
            path.pop()
        
        trace_object(start_object_id, object_type, 0, [])
        return result
        
    except Exception as e:
        log.error(f"Error following association chain: {e}")
        return {"error": str(e)}

def process_data(params: Dict[str, Any]) -> Dict[str, Any]:
    """Process the enumeration request."""
    try:
        client = hs_client()
        object_type = params["objectType"]
        extraction_mode = params.get("extractionMode", "sample")
        
        # Special handling for connection chain tracing
        if "traceConnections" in params:
            start_object_id = params["traceConnections"]["startObjectId"]
            max_depth = params["traceConnections"].get("maxDepth", 2)
            result = follow_association_chain(client, start_object_id, object_type, max_depth)
            result["status"] = "success"
            return result
        
        # Standard enumeration
        result = enumerate_objects(client, object_type, params)
        result["status"] = "success"
        
        return result
        
    except Exception as e:
        return {"error": f"Object enumeration failed: {e}"}

def main() -> None:
    """Main entry point."""
    # Test mode for autodiscovery (REQUIRED)
    if len(sys.argv) == 2 and sys.argv[1] == '{"__test__": true}':
        print(json.dumps({"success": True, "_simple": True}))
        return
    
    # Rich schema for better LLM integration
    if len(sys.argv) == 2 and sys.argv[1] == "--fractalic-dump-schema":
        schema = {
            "description": "Flexible extraction of any HubSpot object type with surgical control over scope and associations",
            "parameters": {
                "type": "object",
                "properties": {
                    "objectType": {
                        "type": "string",
                        "enum": ["contacts", "deals", "tickets", "companies", "products", "tasks", "calls", "emails", "meetings", "notes"],
                        "description": "Type of HubSpot object to enumerate"
                    },
                    "extractionMode": {
                        "type": "string",
                        "enum": ["list", "sample", "detailed", "with_associations", "connection_focused"],
                        "description": "Extraction depth: list (IDs only), sample (basic properties), detailed (full properties), with_associations (include relationships), connection_focused (sorted by relationship count)",
                        "default": "sample"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of objects to extract",
                        "default": 50,
                        "maximum": 100
                    },
                    "includeAssociations": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Object types to include as associations (e.g., ['contacts', 'deals'])"
                    },
                    "sortBy": {
                        "type": "string",
                        "enum": ["createdate", "lastmodifieddate", "connection_count", "activity_level"],
                        "description": "Sorting criteria",
                        "default": "createdate"
                    },
                    "filters": {
                        "type": "object",
                        "properties": {
                            "dateRange": {
                                "type": "object",
                                "properties": {
                                    "property": {"type": "string"},
                                    "startDate": {"type": "string"},
                                    "endDate": {"type": "string"}
                                }
                            },
                            "propertyFilters": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "property": {"type": "string"},
                                        "operator": {"type": "string"},
                                        "value": {"type": "string"}
                                    },
                                    "required": ["property", "value"]
                                }
                            }
                        },
                        "description": "Filters to apply to extraction"
                    }
                },
                "required": ["objectType"],
                "additionalProperties": False
            }
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
