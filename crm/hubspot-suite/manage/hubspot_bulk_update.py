#!/usr/bin/env python3
"""
Perform bulk updates on HubSpot objects for improved efficiency.
"""
from __future__ import annotations

import json
import sys
from typing import Any, Dict, List


def process_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Perform bulk updates on HubSpot objects."""
    try:
        # Import dependencies inside the function to avoid top-level import issues
        from hubspot.crm.deals import SimplePublicObjectBatchInput, BatchInputSimplePublicObjectBatchInput
        from hubspot.crm.contacts import SimplePublicObjectBatchInput as ContactBatchInput, BatchInputSimplePublicObjectBatchInput as ContactBatchInputContainer
        from hubspot.crm.tickets import SimplePublicObjectBatchInput as TicketBatchInput, BatchInputSimplePublicObjectBatchInput as TicketBatchInputContainer
        from hubspot_hub_helpers import hs_client
        
        object_type = data.get("objectType", "deals")
        operations = data.get("operations", [])
        
        if not operations:
            return {"error": "operations parameter is required with at least one operation"}
        
        if not isinstance(operations, list):
            return {"error": "operations must be an array of update operations"}
        
        if len(operations) > 100:
            return {"error": "Maximum 100 operations allowed per batch"}
        
        cli = hs_client()
        
        # Prepare batch operations
        batch_inputs = []
        for operation in operations:
            object_id = operation.get("id")
            properties = operation.get("properties", {})
            
            if not object_id:
                continue
            
            # Convert properties to strings
            string_properties = {}
            for key, value in properties.items():
                string_properties[key] = str(value) if value is not None else ""
            
            batch_inputs.append(SimplePublicObjectBatchInput(
                id=str(object_id),
                properties=string_properties
            ))
        
        if not batch_inputs:
            return {"error": "No valid operations found"}
        
        try:
            # Execute batch update based on object type
            if object_type == "deals":
                batch_request = BatchInputSimplePublicObjectBatchInput(inputs=batch_inputs)
                response = cli.crm.deals.batch_api.update(batch_input_simple_public_object_batch_input=batch_request)
            elif object_type == "contacts":
                batch_request = ContactBatchInputContainer(inputs=batch_inputs)
                response = cli.crm.contacts.batch_api.update(batch_input_simple_public_object_batch_input=batch_request)
            elif object_type == "tickets":
                batch_request = TicketBatchInputContainer(inputs=batch_inputs)
                response = cli.crm.tickets.batch_api.update(batch_input_simple_public_object_batch_input=batch_request)
            else:
                return {"error": f"Unsupported object type: {object_type}. Supported types: deals, contacts, tickets"}
            
            # Process results
            successful_updates = []
            failed_updates = []
            
            if hasattr(response, 'results') and response.results:
                for result in response.results:
                    successful_updates.append({
                        "id": result.id,
                        "properties": result.properties
                    })
            
            if hasattr(response, 'errors') and response.errors:
                for error in response.errors:
                    failed_updates.append({
                        "id": error.id if hasattr(error, 'id') else "unknown",
                        "error": str(error)
                    })
            
            return {
                "status": "success",
                "objectType": object_type,
                "totalOperations": len(operations),
                "successfulUpdates": len(successful_updates),
                "failedUpdates": len(failed_updates),
                "results": successful_updates,
                "errors": failed_updates
            }
            
        except Exception as err:
            return {
                "error": f"Bulk update failed: {str(err)}",
                "objectType": object_type,
                "totalOperations": len(operations)
            }
    
    except Exception as e:
        return {"error": f"Bulk operation failed: {str(e)}"}


def main() -> None:
    # Test mode for autodiscovery (REQUIRED)
    if len(sys.argv) == 2 and sys.argv[1] == '{"__test__": true}':
        print(json.dumps({"success": True, "_simple": True}))
        return
    
    # Optional: Rich schema for better LLM integration
    if len(sys.argv) == 2 and sys.argv[1] == "--fractalic-dump-schema":
        schema = {
            "description": "Perform bulk updates on HubSpot objects for improved efficiency. Can update up to 100 objects in a single API call.",
            "parameters": {
                "type": "object",
                "properties": {
                    "objectType": {
                        "type": "string",
                        "enum": ["deals", "contacts", "tickets"],
                        "default": "deals",
                        "description": "Type of HubSpot objects to update"
                    },
                    "operations": {
                        "type": "array",
                        "maxItems": 100,
                        "description": "Array of update operations (max 100)",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {
                                    "type": ["string", "integer"],
                                    "description": "Object ID to update"
                                },
                                "properties": {
                                    "type": "object",
                                    "description": "Properties to update",
                                    "additionalProperties": True
                                }
                            },
                            "required": ["id", "properties"]
                        }
                    }
                },
                "required": ["operations"],
                "examples": [
                    {
                        "objectType": "deals",
                        "operations": [
                            {"id": 123, "properties": {"dealstage": "closedwon"}},
                            {"id": 124, "properties": {"amount": "2000", "dealstage": "qualifiedtobuy"}}
                        ]
                    }
                ]
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
