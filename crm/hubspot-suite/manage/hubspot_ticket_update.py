#!/usr/bin/env python3
"""
Update HubSpot ticket status and properties.
"""
from __future__ import annotations

import json
import sys
from typing import Any, Dict


def process_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Update ticket properties in HubSpot."""
    try:
        # Import dependencies inside the function to avoid top-level import issues
        from hubspot.crm.tickets import SimplePublicObjectInput
        from hubspot_hub_helpers import hs_client
        
        ticket_id = data.get("ticketId")
        properties = data.get("properties", {})
        
        if not ticket_id:
            return {"error": "ticketId parameter is required"}
        
        if not properties:
            return {"error": "properties parameter is required with at least one property to update"}
        
        cli = hs_client()
        
        # Validate and prepare properties
        update_properties = {}
        
        # Standard properties mapping
        property_mappings = {
            "title": "subject",
            "subject": "subject",
            "status": "hs_ticket_status",
            "priority": "hs_ticket_priority",
            "category": "hs_ticket_category",
            "stage": "hs_ticket_pipeline_stage",
            "description": "content",
            "content": "content"
        }
        
        # Valid status values
        valid_statuses = {
            "NEW": "1",
            "WAITING_ON_CONTACT": "2", 
            "WAITING_ON_US": "3",
            "CLOSED": "4",
            "1": "1",
            "2": "2", 
            "3": "3",
            "4": "4"
        }
        
        # Valid priority values
        valid_priorities = {
            "LOW": "LOW",
            "MEDIUM": "MEDIUM", 
            "HIGH": "HIGH"
        }
        
        # Valid category values
        valid_categories = {
            "PRODUCT_ISSUE": "PRODUCT_ISSUE",
            "BILLING_ISSUE": "BILLING_ISSUE",
            "FEATURE_REQUEST": "FEATURE_REQUEST", 
            "GENERAL_INQUIRY": "GENERAL_INQUIRY"
        }
        
        for key, value in properties.items():
            # Map standard properties or use as-is for custom properties
            prop_name = property_mappings.get(key, key)
            
            # Validate and convert specific properties
            if prop_name == "hs_ticket_status":
                if str(value).upper() in valid_statuses:
                    update_properties[prop_name] = valid_statuses[str(value).upper()]
                else:
                    return {
                        "error": f"Invalid status: {value}",
                        "valid_statuses": list(valid_statuses.keys())
                    }
            elif prop_name == "hs_ticket_priority":
                if str(value).upper() in valid_priorities:
                    update_properties[prop_name] = valid_priorities[str(value).upper()]
                else:
                    return {
                        "error": f"Invalid priority: {value}",
                        "valid_priorities": list(valid_priorities.keys())
                    }
            elif prop_name == "hs_ticket_category":
                if str(value).upper() in valid_categories:
                    update_properties[prop_name] = valid_categories[str(value).upper()]
                else:
                    return {
                        "error": f"Invalid category: {value}",
                        "valid_categories": list(valid_categories.keys())
                    }
            else:
                update_properties[prop_name] = str(value) if value is not None else ""
        
        try:
            # Get current ticket for verification
            current_ticket = cli.crm.tickets.basic_api.get_by_id(ticket_id=str(ticket_id))
            
            # Update the ticket
            updated_ticket = cli.crm.tickets.basic_api.update(
                ticket_id=str(ticket_id),
                simple_public_object_input=SimplePublicObjectInput(properties=update_properties)
            )
            
            return {
                "status": "success",
                "ticketId": ticket_id,
                "updatedProperties": update_properties,
                "previousProperties": current_ticket.properties,
                "newProperties": updated_ticket.properties
            }
            
        except Exception as err:
            return {
                "error": f"Failed to update ticket: {str(err)}",
                "ticketId": ticket_id,
                "attemptedProperties": update_properties
            }
    
    except Exception as e:
        return {"error": f"Ticket update failed: {str(e)}"}


def main() -> None:
    # Test mode for autodiscovery (REQUIRED)
    if len(sys.argv) == 2 and sys.argv[1] == '{"__test__": true}':
        print(json.dumps({"success": True, "_simple": True}))
        return
    
    # Optional: Rich schema for better LLM integration
    if len(sys.argv) == 2 and sys.argv[1] == "--fractalic-dump-schema":
        schema = {
            "description": "Update HubSpot ticket status and properties. Essential for tracking support ticket progress and resolution.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticketId": {
                        "type": ["integer", "string"],
                        "description": "ID of the ticket to update (required)"
                    },
                    "properties": {
                        "type": "object",
                        "description": "Properties to update (required)",
                        "properties": {
                            "title": {
                                "type": "string",
                                "description": "Ticket title/subject"
                            },
                            "status": {
                                "type": "string",
                                "enum": ["NEW", "WAITING_ON_CONTACT", "WAITING_ON_US", "CLOSED", "1", "2", "3", "4"],
                                "description": "Ticket status"
                            },
                            "priority": {
                                "type": "string",
                                "enum": ["LOW", "MEDIUM", "HIGH"],
                                "description": "Ticket priority"
                            },
                            "category": {
                                "type": "string",
                                "enum": ["PRODUCT_ISSUE", "BILLING_ISSUE", "FEATURE_REQUEST", "GENERAL_INQUIRY"],
                                "description": "Ticket category"
                            },
                            "description": {
                                "type": "string",
                                "description": "Ticket description/content"
                            },
                            "resolution_notes": {
                                "type": "string",
                                "description": "Resolution notes or comments"
                            }
                        },
                        "additionalProperties": True
                    }
                },
                "required": ["ticketId", "properties"]
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
