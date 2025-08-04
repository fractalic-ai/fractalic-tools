#!/usr/bin/env python3
"""
Find an existing contact by e-mail or create a new one.
"""
from __future__ import annotations

import json
import sys
from typing import Any, Dict


def _merge_if_empty(existing: Dict[str, str], updates: Dict[str, str]) -> Dict[str, str]:
    return {k: v for k, v in updates.items() if v and not existing.get(k)}


def process_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Find an existing contact by email or create a new one."""
    try:
        # Import dependencies inside the function to avoid top-level import issues
        from hubspot.crm.contacts import SimplePublicObjectInput, PublicObjectSearchRequest
        from hubspot_hub_helpers import hs_client
        
        email = data.get("email")
        if not email:
            return {"error": "email parameter is required"}
        
        email = email.lower()
        
        cli = hs_client()
        search_api = cli.crm.contacts.search_api

        # Create the search request object according to HubSpot SDK requirements
        search_request = PublicObjectSearchRequest(
            filter_groups=[
                {
                    "filters": [
                        {
                            "propertyName": "email", 
                            "operator": "EQ", 
                            "value": email
                        }
                    ]
                }
            ],
            properties=["firstname", "lastname", "phone", "company"],
            limit=1
        )

        try:
            res = search_api.do_search(public_object_search_request=search_request).results
        except Exception as err:
            return {"error": f"Failed to search for contact: {str(err)}"}

        # ---------- Update flow
        if res:
            contact = res[0]
            updates = _merge_if_empty(
                contact.properties,
                {
                    "firstname": data.get("first"),
                    "lastname":  data.get("last"),
                    "phone":     data.get("phone"),
                    "company":   data.get("company"),
                },
            )
            
            if updates:
                try:
                    cli.crm.contacts.basic_api.update(
                        contact.id, SimplePublicObjectInput(properties=updates)
                    )
                    return {
                        "status": "updated", 
                        "contactId": contact.id,
                        "updatedFields": updates,
                        "email": email
                    }
                except Exception as err:
                    return {"error": f"Failed to update contact: {str(err)}"}
            else:
                return {
                    "status": "found", 
                    "contactId": contact.id,
                    "email": email,
                    "message": "Contact found, no updates needed"
                }

        # ---------- Create flow
        props = {
            "email":     email,
            "firstname": data.get("first"),
            "lastname":  data.get("last"),
            "phone":     data.get("phone"),
            "company":   data.get("company"),
        }
        
        # Remove None values
        props = {k: v for k, v in props.items() if v is not None}
        
        try:
            new_contact = cli.crm.contacts.basic_api.create(
                SimplePublicObjectInput(properties=props)
            )
            return {
                "status": "created", 
                "contactId": new_contact.id,
                "email": email,
                "properties": props
            }
        except Exception as err:
            return {"error": f"Failed to create contact: {str(err)}"}
    
    except Exception as e:
        return {"error": f"Contact operation failed: {str(e)}"}


def main() -> None:
    # Test mode for autodiscovery (REQUIRED)
    if len(sys.argv) == 2 and sys.argv[1] == '{"__test__": true}':
        print(json.dumps({"success": True, "_simple": True}))
        return
    
    # Optional: Rich schema for better LLM integration
    if len(sys.argv) == 2 and sys.argv[1] == "--fractalic-dump-schema":
        schema = {
            "description": "Find an existing HubSpot contact by email address or create a new one. Updates existing contacts with new information if provided.",
            "parameters": {
                "type": "object",
                "properties": {
                    "email": {
                        "type": "string", 
                        "format": "email",
                        "description": "Email address of the contact (required)"
                    },
                    "first": {
                        "type": "string",
                        "description": "First name of the contact"
                    },
                    "last": {
                        "type": "string", 
                        "description": "Last name of the contact"
                    },
                    "phone": {
                        "type": "string",
                        "description": "Phone number of the contact"
                    },
                    "company": {
                        "type": "string",
                        "description": "Company name associated with the contact"
                    }
                },
                "required": ["email"]
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
