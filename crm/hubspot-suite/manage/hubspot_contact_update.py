#!/usr/bin/env python3
"""
Update existing HubSpot contact properties with option to only update empty fields.
"""
from __future__ import annotations

import json
import sys
from typing import Any, Dict


def process_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Update contact properties in HubSpot with selective update capability."""
    try:
        # Import dependencies inside the function to avoid top-level import issues
        from hubspot.crm.contacts import SimplePublicObjectInput
        from hubspot_hub_helpers import hs_client
        
        contact_id = data.get("contactId")
        properties = data.get("properties", {})
        only_update_empty = data.get("onlyUpdateEmpty", False)
        
        if not contact_id:
            return {"error": "contactId parameter is required"}
        
        if not properties:
            return {"error": "properties parameter is required with at least one property to update"}
        
        cli = hs_client()
        
        try:
            # Get current contact to check existing values
            current_contact = cli.crm.contacts.basic_api.get_by_id(contact_id=str(contact_id))
            current_properties = current_contact.properties
            
            # Prepare update properties
            update_properties = {}
            skipped_properties = {}
            
            for key, value in properties.items():
                current_value = current_properties.get(key)
                
                if only_update_empty:
                    # Only update if current value is empty/null
                    if not current_value or current_value.strip() == "":
                        update_properties[key] = str(value) if value is not None else ""
                    else:
                        skipped_properties[key] = {
                            "current_value": current_value,
                            "attempted_value": value,
                            "reason": "field_not_empty"
                        }
                else:
                    # Always update
                    update_properties[key] = str(value) if value is not None else ""
            
            if not update_properties:
                return {
                    "status": "no_updates",
                    "contactId": contact_id,
                    "message": "No properties updated - all fields already had values",
                    "skipped_properties": skipped_properties
                }
            
            # Update the contact
            updated_contact = cli.crm.contacts.basic_api.update(
                contact_id=str(contact_id),
                simple_public_object_input=SimplePublicObjectInput(properties=update_properties)
            )
            
            return {
                "status": "success",
                "contactId": contact_id,
                "onlyUpdateEmpty": only_update_empty,
                "updatedProperties": update_properties,
                "skippedProperties": skipped_properties,
                "previousProperties": {k: current_properties.get(k) for k in update_properties.keys()},
                "newProperties": {k: updated_contact.properties.get(k) for k in update_properties.keys()}
            }
            
        except Exception as err:
            return {
                "error": f"Failed to update contact: {str(err)}",
                "contactId": contact_id,
                "attemptedProperties": properties
            }
    
    except Exception as e:
        return {"error": f"Contact update failed: {str(e)}"}


def main() -> None:
    # Test mode for autodiscovery (REQUIRED)
    if len(sys.argv) == 2 and sys.argv[1] == '{"__test__": true}':
        print(json.dumps({"success": True, "_simple": True}))
        return
    
    # Optional: Rich schema for better LLM integration
    if len(sys.argv) == 2 and sys.argv[1] == "--fractalic-dump-schema":
        schema = {
            "description": "Update existing HubSpot contact properties with option to only update empty fields. Essential for maintaining data integrity while adding new information.",
            "parameters": {
                "type": "object",
                "properties": {
                    "contactId": {
                        "type": ["integer", "string"],
                        "description": "ID of the contact to update (required)"
                    },
                    "properties": {
                        "type": "object",
                        "description": "Properties to update (required)",
                        "properties": {
                            "firstname": {
                                "type": "string",
                                "description": "First name"
                            },
                            "lastname": {
                                "type": "string",
                                "description": "Last name"
                            },
                            "email": {
                                "type": "string",
                                "format": "email",
                                "description": "Email address"
                            },
                            "phone": {
                                "type": "string",
                                "description": "Phone number"
                            },
                            "company": {
                                "type": "string",
                                "description": "Company name"
                            },
                            "address": {
                                "type": "string",
                                "description": "Address"
                            },
                            "city": {
                                "type": "string", 
                                "description": "City"
                            },
                            "state": {
                                "type": "string",
                                "description": "State/Province"
                            },
                            "zip": {
                                "type": "string",
                                "description": "ZIP/Postal code"
                            },
                            "country": {
                                "type": "string",
                                "description": "Country"
                            }
                        },
                        "additionalProperties": True
                    },
                    "onlyUpdateEmpty": {
                        "type": "boolean",
                        "default": False,
                        "description": "If true, only update fields that are currently empty or null"
                    }
                },
                "required": ["contactId", "properties"]
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
