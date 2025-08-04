#!/usr/bin/env python3
"""
Update HubSpot deal properties including amount, quote data, and custom fields.
"""
from __future__ import annotations

import json
import sys
from typing import Any, Dict


def process_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Update deal properties in HubSpot."""
    try:
        # Import dependencies inside the function to avoid top-level import issues
        from hubspot.crm.deals import SimplePublicObjectInput
        from hubspot_hub_helpers import hs_client
        
        deal_id = data.get("dealId")
        properties = data.get("properties", {})
        
        if not deal_id:
            return {"error": "dealId parameter is required"}
        
        if not properties:
            return {"error": "properties parameter is required with at least one property to update"}
        
        cli = hs_client()
        
        # Validate and prepare properties
        update_properties = {}
        
        # Standard properties mapping
        property_mappings = {
            "dealName": "dealname",
            "amount": "amount",
            "closeDate": "closedate", 
            "description": "description",
            "stage": "dealstage",
            "pipeline": "pipeline"
        }
        
        for key, value in properties.items():
            # Map standard properties or use as-is for custom properties
            prop_name = property_mappings.get(key, key)
            
            # Convert values appropriately
            if prop_name in ["amount"] and value is not None:
                update_properties[prop_name] = str(value)
            elif prop_name in ["closedate"] and value is not None:
                # Ensure date format
                update_properties[prop_name] = str(value)
            else:
                update_properties[prop_name] = str(value) if value is not None else ""
        
        try:
            # Get current deal for verification
            current_deal = cli.crm.deals.basic_api.get_by_id(deal_id=str(deal_id))
            
            # Update the deal
            updated_deal = cli.crm.deals.basic_api.update(
                deal_id=str(deal_id),
                simple_public_object_input=SimplePublicObjectInput(properties=update_properties)
            )
            
            return {
                "status": "success",
                "dealId": deal_id,
                "updatedProperties": update_properties,
                "previousProperties": current_deal.properties,
                "newProperties": updated_deal.properties
            }
            
        except Exception as err:
            return {
                "error": f"Failed to update deal: {str(err)}",
                "dealId": deal_id,
                "attemptedProperties": update_properties
            }
    
    except Exception as e:
        return {"error": f"Deal update failed: {str(e)}"}


def main() -> None:
    # Test mode for autodiscovery (REQUIRED)
    if len(sys.argv) == 2 and sys.argv[1] == '{"__test__": true}':
        print(json.dumps({"success": True, "_simple": True}))
        return
    
    # Optional: Rich schema for better LLM integration
    if len(sys.argv) == 2 and sys.argv[1] == "--fractalic-dump-schema":
        schema = {
            "description": "Update HubSpot deal properties including amount, quote data, file URLs, and custom fields. Essential for recording quote amounts, payment status, and workflow progression.",
            "parameters": {
                "type": "object",
                "properties": {
                    "dealId": {
                        "type": ["integer", "string"],
                        "description": "ID of the deal to update (required)"
                    },
                    "properties": {
                        "type": "object",
                        "description": "Properties to update (required)",
                        "properties": {
                            "dealName": {
                                "type": "string",
                                "description": "Deal name/title"
                            },
                            "amount": {
                                "type": "number",
                                "description": "Deal amount/value"
                            },
                            "closeDate": {
                                "type": "string",
                                "format": "date",
                                "description": "Expected close date (YYYY-MM-DD)"
                            },
                            "description": {
                                "type": "string",
                                "description": "Deal description"
                            },
                            "quote_amount": {
                                "type": "number",
                                "description": "Quoted amount for 3D printing project"
                            },
                            "calc_confidence": {
                                "type": "number",
                                "description": "Confidence score from price calculator (0-1)"
                            },
                            "part_volume": {
                                "type": "number",
                                "description": "Part volume in cm³"
                            },
                            "amount_paid": {
                                "type": "number",
                                "description": "Amount paid by customer"
                            },
                            "file_url": {
                                "type": "string",
                                "description": "URL to 3D model file"
                            }
                        },
                        "additionalProperties": True
                    }
                },
                "required": ["dealId", "properties"]
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
