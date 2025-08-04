#!/usr/bin/env python3
"""
Create a single association between two HubSpot records.
"""
from __future__ import annotations

import json
import sys
from typing import Any, Dict


def process_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a single association between two HubSpot CRM records."""
    try:
        # Import dependencies inside the function to avoid top-level import issues
        from hubspot.crm.associations import (
            BatchInputPublicAssociation,
            PublicAssociation,
        )
        from hubspot_hub_helpers import hs_client
        
        # Validate required parameters
        required_fields = ["fromType", "fromId", "toType", "toId", "assocType"]
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return {
                "success": False,
                "error": "MISSING_PARAMETERS",
                "message": f"Missing required parameters: {', '.join(missing_fields)}"
            }

        # Validate parameter types
        if not isinstance(data["fromId"], int):
            return {
                "success": False,
                "error": "INVALID_PARAMETER_TYPE",
                "message": "fromId must be an integer"
            }
            
        if not isinstance(data["toId"], int):
            return {
                "success": False,
                "error": "INVALID_PARAMETER_TYPE", 
                "message": "toId must be an integer"
            }

        # Get HubSpot client
        cli = hs_client()
        
        # Create the association
        batch = BatchInputPublicAssociation(
            inputs=[PublicAssociation(
                _from=str(data["fromId"]), 
                to=str(data["toId"]), 
                type=data["assocType"]
            )]
        )
        
        cli.crm.associations.batch_api.create(data["fromType"], data["toType"], batch)
        
        # Return success response
        return {
            "success": True,
            "message": f"Successfully created association between {data['fromType']} {data['fromId']} and {data['toType']} {data['toId']}",
            "association": {
                "fromType": data["fromType"],
                "fromId": data["fromId"],
                "toType": data["toType"], 
                "toId": data["toId"],
                "assocType": data["assocType"]
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": "HS_ASSOC_FAILED",
            "message": f"Failed to create HubSpot association: {str(e)}",
            "context": data
        }


def main() -> None:
    # Handle test mode (REQUIRED for Simple JSON Convention)
    if len(sys.argv) == 2 and sys.argv[1] == '{"__test__": true}':
        print(json.dumps({"success": True, "_simple": True}))
        return

    # Handle schema dump (OPTIONAL but recommended)
    if len(sys.argv) == 2 and sys.argv[1] == "--fractalic-dump-schema":
        schema = {
            "description": "Create a single association between two HubSpot CRM records. This links objects together, such as associating a contact with a deal, or a deal with a company.",
            "parameters": {
                "type": "object",
                "properties": {
                    "fromType": {
                        "type": "string",
                        "description": "The type of the source HubSpot object (e.g., 'contacts', 'deals', 'companies', 'tickets')"
                    },
                    "fromId": {
                        "type": "integer",
                        "description": "The ID of the source HubSpot object to associate from"
                    },
                    "toType": {
                        "type": "string", 
                        "description": "The type of the target HubSpot object (e.g., 'contacts', 'deals', 'companies', 'tickets')"
                    },
                    "toId": {
                        "type": "integer",
                        "description": "The ID of the target HubSpot object to associate to"
                    },
                    "assocType": {
                        "type": "string",
                        "description": "The type of association to create (e.g., 'contact_to_deal', 'deal_to_company', 'ticket_to_contact')"
                    }
                },
                "required": ["fromType", "fromId", "toType", "toId", "assocType"]
            }
        }
        print(json.dumps(schema, ensure_ascii=False))
        return

    # Process JSON input
    try:
        if len(sys.argv) != 2:
            error_response = {
                "success": False,
                "error": "INVALID_ARGS", 
                "message": "Expected exactly one JSON argument"
            }
            print(json.dumps(error_response, ensure_ascii=False))
            return

        params = json.loads(sys.argv[1])
        
        # Validate required parameters
        required_fields = ["fromType", "fromId", "toType", "toId", "assocType"]
        missing_fields = [field for field in required_fields if field not in params]
        if missing_fields:
            error_response = {
                "success": False,
                "error": "MISSING_PARAMETERS",
                "message": f"Missing required parameters: {', '.join(missing_fields)}"
            }
            print(json.dumps(error_response, ensure_ascii=False))
            return

        # Validate parameter types
        if not isinstance(params["fromId"], int):
            error_response = {
                "success": False,
                "error": "INVALID_PARAMETER_TYPE",
                "message": "fromId must be an integer"
            }
            print(json.dumps(error_response, ensure_ascii=False))
            return
            
        if not isinstance(params["toId"], int):
            error_response = {
                "success": False,
                "error": "INVALID_PARAMETER_TYPE", 
                "message": "toId must be an integer"
            }
            print(json.dumps(error_response, ensure_ascii=False))
            return

        # Get HubSpot client
        from hubspot.crm.associations import (
            BatchInputPublicAssociation,
            PublicAssociation,
        )
        from hubspot_hub_helpers import hs_client
        
        cli = hs_client()
        
        # Create the association
        batch = BatchInputPublicAssociation(
            inputs=[PublicAssociation(
                _from=str(params["fromId"]), 
                to=str(params["toId"]), 
                type=params["assocType"]
            )]
        )
        
        cli.crm.associations.batch_api.create(params["fromType"], params["toType"], batch)
        
        # Return success response
        success_response = {
            "success": True,
            "message": f"Successfully created association between {params['fromType']} {params['fromId']} and {params['toType']} {params['toId']}",
            "association": {
                "fromType": params["fromType"],
                "fromId": params["fromId"],
                "toType": params["toType"], 
                "toId": params["toId"],
                "assocType": params["assocType"]
            }
        }
        print(json.dumps(success_response, ensure_ascii=False))
        
    except json.JSONDecodeError as e:
        error_response = {
            "success": False,
            "error": "INVALID_JSON",
            "message": f"Invalid JSON input: {str(e)}"
        }
        print(json.dumps(error_response, ensure_ascii=False))
        
    except Exception as e:
        error_response = {
            "success": False,
            "error": "HS_ASSOC_FAILED",
            "message": f"Failed to create HubSpot association: {str(e)}",
            "context": params if 'params' in locals() else None
        }
        print(json.dumps(error_response, ensure_ascii=False))


if __name__ == "__main__":
    main()
