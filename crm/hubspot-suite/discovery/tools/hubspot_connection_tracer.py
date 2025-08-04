#!/usr/bin/env python3
"""
HubSpot Connection Tracer

Efficiently trace and map connections between HubSpot objects across modules.
Provides surgical control over connection discovery with context management.

• Trace object connections with depth control
• Map cross-module relationships
• Follow customer journey paths
• Extract attribution chains
• Discover process participants
"""
from __future__ import annotations

import json
import logging
import sys
import time
from typing import Any, Dict, List, Optional, Set, Tuple

# Configure logging
log = logging.getLogger(__name__)

def convert_associations_to_serializable(associations) -> Dict[str, List[Dict[str, str]]]:
    """Convert HubSpot association objects to JSON-serializable format."""
    if not associations:
        return {}
    
    serializable = {}
    for assoc_type, assoc_data in associations.items():
        if hasattr(assoc_data, 'results'):
            serializable[assoc_type] = [
                {"id": assoc_obj.id, "type": getattr(assoc_obj, 'type', assoc_type)}
                for assoc_obj in assoc_data.results
            ]
        else:
            serializable[assoc_type] = []
    
    return serializable

def get_object_with_associations(client, object_id: str, object_type: str, connection_types: List[str] = None) -> Dict[str, Any]:
    """Get an object with its associations."""
    try:
        # Default association types based on object type
        if not connection_types:
            association_map = {
                "contacts": ["deals", "tickets", "companies", "engagements"],
                "deals": ["contacts", "tickets", "companies", "line_items"],
                "tickets": ["contacts", "deals", "companies"],
                "companies": ["contacts", "deals", "tickets"],
                "tasks": ["contacts", "deals", "tickets"]
            }
            connection_types = association_map.get(object_type, ["contacts", "deals", "tickets"])
        
        # Get object with associations
        if object_type == "contacts":
            obj = client.crm.contacts.basic_api.get_by_id(object_id, associations=connection_types)
        elif object_type == "deals":
            obj = client.crm.deals.basic_api.get_by_id(object_id, associations=connection_types)
        elif object_type == "tickets":
            obj = client.crm.tickets.basic_api.get_by_id(object_id, associations=connection_types)
        elif object_type == "companies":
            obj = client.crm.companies.basic_api.get_by_id(object_id, associations=connection_types)
        else:
            # Try generic API
            obj = client.crm.objects.basic_api.get_by_id(object_type=object_type, object_id=object_id, associations=connection_types)
        
        return {
            "id": obj.id,
            "type": object_type,
            "properties": obj.properties if hasattr(obj, 'properties') else {},
            "associations": convert_associations_to_serializable(obj.associations) if hasattr(obj, 'associations') else {}
        }
        
    except Exception as e:
        log.debug(f"Could not get {object_type}:{object_id}: {e}")
        return {"id": object_id, "type": object_type, "error": str(e)}

def trace_single_object_connections(client, params: Dict[str, Any]) -> Dict[str, Any]:
    """Trace connections from a single object."""
    try:
        start_obj = params["startObject"]
        max_depth = params.get("maxDepth", 3)
        connection_types = params.get("connectionTypes", [])
        extract_properties = params.get("extractProperties", True)
        limit = params.get("limit", 100)
        
        visited = set()
        connections = []
        queue = [(start_obj["id"], start_obj["type"], 0)]
        
        while queue and len(connections) < limit:
            obj_id, obj_type, depth = queue.pop(0)
            
            if depth > max_depth or f"{obj_type}:{obj_id}" in visited:
                continue
                
            visited.add(f"{obj_type}:{obj_id}")
            
            # Get object with associations
            obj_data = get_object_with_associations(client, obj_id, obj_type, connection_types)
            
            if "error" not in obj_data:
                connection_info = {
                    "object": {
                        "id": obj_id,
                        "type": obj_type,
                        "depth": depth
                    }
                }
                
                if extract_properties:
                    connection_info["object"]["properties"] = obj_data["properties"]
                
                # Process associations
                associated_objects = []
                if obj_data.get("associations"):
                    for assoc_type, assoc_data in obj_data["associations"].items():
                        if hasattr(assoc_data, 'results'):
                            for assoc_obj in assoc_data.results:
                                associated_objects.append({
                                    "id": assoc_obj.id,
                                    "type": assoc_type,
                                    "association_type": getattr(assoc_obj, 'type', 'unknown')
                                })
                                
                                # Add to queue for further tracing
                                if depth < max_depth:
                                    queue.append((assoc_obj.id, assoc_type, depth + 1))
                
                connection_info["associations"] = associated_objects
                connections.append(connection_info)
        
        return {
            "start_object": start_obj,
            "max_depth": max_depth,
            "total_connections": len(connections),
            "connections": connections
        }
        
    except Exception as e:
        log.error(f"Error tracing single object connections: {e}")
        return {"error": str(e)}

def trace_customer_journey(client, params: Dict[str, Any]) -> Dict[str, Any]:
    """Trace a customer's journey across all touchpoints."""
    try:
        start_obj = params["startObject"]
        max_depth = params.get("maxDepth", 4)
        time_range = params.get("timeRange", {})
        
        # Start with contact or find contact from other object
        if start_obj["type"] == "contacts":
            contact_id = start_obj["id"]
        else:
            # Find associated contact
            obj_data = get_object_with_associations(client, start_obj["id"], start_obj["type"], ["contacts"])
            contact_id = None
            contacts_assoc = obj_data.get("associations", {}).get("contacts", [])
            if contacts_assoc:
                contact_id = contacts_assoc[0]["id"]
            
            if not contact_id:
                return {"error": "Could not find associated contact for journey tracing"}
        
        # Get contact details
        contact = get_object_with_associations(client, contact_id, "contacts", ["deals", "tickets", "companies", "engagements"])
        
        journey_stages = []
        
        # Map contact lifecycle
        contact_props = contact.get("properties", {})
        journey_stages.append({
            "stage": "contact_creation",
            "timestamp": contact_props.get("createdate"),
            "object_type": "contacts",
            "object_id": contact_id,
            "details": {
                "email": contact_props.get("email"),
                "source": contact_props.get("hs_analytics_source"),
                "lifecycle_stage": contact_props.get("lifecyclestage")
            }
        })
        
        # Map deals (sales journey)
        deals_assoc = contact.get("associations", {}).get("deals", [])
        if deals_assoc:
            for deal_assoc in deals_assoc:
                deal_data = get_object_with_associations(client, deal_assoc["id"], "deals", [])
                deal_props = deal_data.get("properties", {})
                
                journey_stages.append({
                    "stage": "sales_opportunity",
                    "timestamp": deal_props.get("createdate"),
                    "object_type": "deals",
                    "object_id": deal_assoc["id"],
                    "details": {
                        "deal_name": deal_props.get("dealname"),
                        "amount": deal_props.get("amount"),
                        "stage": deal_props.get("dealstage"),
                        "close_date": deal_props.get("closedate")
                    }
                })
        
        # Map tickets (service journey) 
        tickets_assoc = contact.get("associations", {}).get("tickets", [])
        if tickets_assoc:
            for ticket_assoc in tickets_assoc:
                ticket_data = get_object_with_associations(client, ticket_assoc["id"], "tickets", [])
                ticket_props = ticket_data.get("properties", {})
                
                journey_stages.append({
                    "stage": "service_request",
                    "timestamp": ticket_props.get("createdate"),
                    "object_type": "tickets",
                    "object_id": ticket_assoc["id"],
                    "details": {
                        "subject": ticket_props.get("subject"),
                        "priority": ticket_props.get("hs_ticket_priority"),
                        "status": ticket_props.get("hs_pipeline_stage")
                    }
                })
        
        # Sort by timestamp
        journey_stages.sort(key=lambda x: x.get("timestamp", ""), reverse=False)
        
        return {
            "contact_id": contact_id,
            "contact_email": contact_props.get("email"),
            "journey_length": len(journey_stages),
            "journey_stages": journey_stages
        }
        
    except Exception as e:
        log.error(f"Error tracing customer journey: {e}")
        return {"error": str(e)}

def find_process_participants(client, params: Dict[str, Any]) -> Dict[str, Any]:
    """Find all objects participating in a process."""
    try:
        # This mode analyzes multiple related objects to find process participants
        # Could start from a deal, ticket, or contact and find all related objects
        
        start_obj = params.get("startObject")
        if not start_obj:
            return {"error": "Process participant discovery requires a starting object"}
        
        participants = {}
        all_objects = set()
        
        # Start tracing from the initial object
        connections_result = trace_single_object_connections(client, {
            "startObject": start_obj,
            "maxDepth": params.get("maxDepth", 2),
            "extractProperties": True,
            "limit": params.get("limit", 50)
        })
        
        # Organize participants by role/type
        for connection in connections_result.get("connections", []):
            obj = connection["object"]
            obj_type = obj["type"]
            
            if obj_type not in participants:
                participants[obj_type] = []
            
            participants[obj_type].append({
                "id": obj["id"],
                "properties": obj.get("properties", {}),
                "role": f"{obj_type}_participant",
                "depth": obj["depth"]
            })
        
        return {
            "start_object": start_obj,
            "participant_types": list(participants.keys()),
            "total_participants": sum(len(p) for p in participants.values()),
            "participants": participants
        }
        
    except Exception as e:
        log.error(f"Error finding process participants: {e}")
        return {"error": str(e)}

def trace_attribution_chain(client, params: Dict[str, Any]) -> Dict[str, Any]:
    """Trace attribution chain for a deal."""
    try:
        start_obj = params["startObject"]
        if start_obj["type"] != "deals":
            return {"error": "Attribution chain tracing requires a deal as starting object"}
        
        deal_id = start_obj["id"]
        
        # Get deal with all associations
        deal_data = get_object_with_associations(client, deal_id, "deals", ["contacts", "companies", "tickets", "engagements"])
        
        attribution_chain = []
        
        # Deal creation
        deal_props = deal_data.get("properties", {})
        attribution_chain.append({
            "touchpoint": "deal_creation",
            "timestamp": deal_props.get("createdate"),
            "object_type": "deals",
            "object_id": deal_id,
            "details": {
                "deal_name": deal_props.get("dealname"),
                "source": deal_props.get("hs_analytics_source"),
                "original_source": deal_props.get("hs_analytics_source_data_1")
            }
        })
        
        # Associated contacts (lead sources)
        if deal_data.get("associations", {}).get("contacts"):
            for contact_assoc in deal_data["associations"]["contacts"]["results"]:
                contact_data = get_object_with_associations(client, contact_assoc.id, "contacts", [])
                contact_props = contact_data.get("properties", {})
                
                attribution_chain.append({
                    "touchpoint": "contact_association",
                    "timestamp": contact_props.get("createdate"),
                    "object_type": "contacts",
                    "object_id": contact_assoc.id,
                    "details": {
                        "email": contact_props.get("email"),
                        "source": contact_props.get("hs_analytics_source"),
                        "first_touch": contact_props.get("hs_analytics_first_timestamp"),
                        "lifecycle_stage": contact_props.get("lifecyclestage")
                    }
                })
        
        # Sort by timestamp to show attribution flow
        attribution_chain.sort(key=lambda x: x.get("timestamp", ""), reverse=False)
        
        return {
            "deal_id": deal_id,
            "deal_name": deal_props.get("dealname"),
            "attribution_touchpoints": len(attribution_chain),
            "attribution_chain": attribution_chain
        }
        
    except Exception as e:
        log.error(f"Error tracing attribution chain: {e}")
        return {"error": str(e)}

def process_data(params: Dict[str, Any]) -> Dict[str, Any]:
    """Process the connection tracing request."""
    start = time.time()
    
    try:
        # Import dependencies inside the function
        import sys
        import os
        sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
        from hubspot_hub_helpers import auto_probe, hs_client, ok, fatal
        
        client = hs_client()
        trace_mode = params["traceMode"]
        
        if trace_mode == "single_object":
            result = trace_single_object_connections(client, params)
        elif trace_mode == "customer_journey":
            result = trace_customer_journey(client, params)
        elif trace_mode == "process_participants":
            result = find_process_participants(client, params)
        elif trace_mode == "attribution_chain":
            result = trace_attribution_chain(client, params)
        elif trace_mode == "cross_module_map":
            # For now, use single_object with broader connection types
            result = trace_single_object_connections(client, params)
        else:
            result = {"error": f"Unknown trace mode: {trace_mode}"}
        
        result["trace_mode"] = trace_mode
        result["timestamp"] = time.time()
        result["status"] = "success"
        
        return result
        
    except Exception as e:
        return {"error": f"Connection tracing failed: {e}"}

def main() -> None:
    """Main entry point."""
    # Test mode for autodiscovery (REQUIRED)
    if len(sys.argv) == 2 and sys.argv[1] == '{"__test__": true}':
        print(json.dumps({"success": True, "_simple": True}))
        return
    
    # Rich schema for better LLM integration
    if len(sys.argv) == 2 and sys.argv[1] == "--fractalic-dump-schema":
        schema = {
            "description": "Trace and map connections between HubSpot objects for process flow analysis and customer journey mapping",
            "parameters": {
                "type": "object",
                "properties": {
                    "traceMode": {
                        "type": "string",
                        "enum": ["single_object", "customer_journey", "process_participants", "attribution_chain", "cross_module_map"],
                        "description": "Tracing mode: single_object (one object's connections), customer_journey (follow customer path), process_participants (find all objects in a process), attribution_chain (trace deal attribution), cross_module_map (map connections across modules)"
                    },
                    "startObject": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string", "description": "Object ID"},
                            "type": {"type": "string", "description": "Object type (contacts, deals, tickets, etc.)"}
                        },
                        "required": ["id", "type"],
                        "description": "Starting object for tracing"
                    },
                    "maxDepth": {
                        "type": "integer",
                        "description": "Maximum connection depth to trace",
                        "default": 3,
                        "minimum": 1,
                        "maximum": 5
                    },
                    "includeModules": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Modules to include in tracing (crm, marketing, service, etc.)"
                    },
                    "connectionTypes": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Specific connection types to follow (e.g., ['deals', 'tickets', 'companies'])"
                    },
                    "extractProperties": {
                        "type": "boolean",
                        "description": "Extract key properties for traced objects",
                        "default": True
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of connections to trace",
                        "default": 100
                    }
                },
                "required": ["traceMode"],
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
