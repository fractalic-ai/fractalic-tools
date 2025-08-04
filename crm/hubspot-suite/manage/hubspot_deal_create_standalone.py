#!/usr/bin/env python3
"""
Create a HubSpot deal without requiring a ticket dependency.
"""
from __future__ import annotations

import json
import sys
from typing import Any, Dict


def process_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a deal independently without ticket dependency."""
    try:
        # Import dependencies inside the function to avoid top-level import issues
        from hubspot.crm.associations import (
            BatchInputPublicAssociation,
            PublicAssociation,
        )
        from hubspot.crm.deals import SimplePublicObjectInput
        from hubspot_hub_helpers import hs_client
        
        contact_id = data.get("contactId")
        deal_name = data.get("dealName")
        pipeline = data.get("pipeline", "default")
        stage = data.get("stage")
        
        if not contact_id:
            return {"error": "contactId parameter is required"}
        if not deal_name:
            return {"error": "dealName parameter is required"}
            
        cli = hs_client()
        
        # Discover valid pipeline and stages
        pipeline_info = _discover_valid_pipeline_and_stages(cli)
        
        # Discover valid properties to prevent errors
        valid_properties = _discover_valid_properties(cli)
        
        # Use discovered pipeline ID if default
        if pipeline == "default":
            pipeline = pipeline_info["pipeline_id"]
            
        # Use discovered stage ID if not specified
        if not stage and pipeline_info["stages"]:
            stage = list(pipeline_info["stages"].values())[0]  # Take the first available stage ID

        # Prepare deal properties with validation
        deal_properties = {
            "dealname": deal_name
        }
        
        # Add pipeline if specified (use pipeline ID, not name)
        if pipeline and pipeline != "default":
            deal_properties["pipeline"] = pipeline_info["pipeline_id"]
        
        # Add stage if specified (ensure it's a stage ID)
        if stage:
            # Check if it's a stage label, convert to ID
            stages = pipeline_info["stages"]
            if stage in stages.values():
                deal_properties["dealstage"] = stage  # Already an ID
            elif stage.lower() in [s.lower() for s in stages.keys()]:
                # Convert label to ID
                stage_id = next(v for k, v in stages.items() if k.lower() == stage.lower())
                deal_properties["dealstage"] = stage_id
            else:
                deal_properties["dealstage"] = stage  # Use as-is, let API validate
        # Add standard properties with validation
        if "amount" in data:
            deal_properties["amount"] = str(data["amount"])
        if "closedate" in data:
            deal_properties["closedate"] = data["closedate"]
        if "description" in data:
            deal_properties["description"] = data["description"]
        
        # Validate and add custom properties
        custom_properties = data.get("properties", {})
        for prop_name, prop_value in custom_properties.items():
            if prop_name in valid_properties:
                deal_properties[prop_name] = prop_value
            else:
                # Log invalid property but don't fail the operation
                print(f"Warning: Property '{prop_name}' does not exist, skipping", file=sys.stderr)

        try:
            deal = cli.crm.deals.basic_api.create(
                SimplePublicObjectInput(properties=deal_properties)
            )
        except Exception as err:
            return {
                "error": f"Failed to create deal: {str(err)}",
                "attempted_properties": deal_properties,
                "available_pipeline": pipeline_info,
                "available_properties": list(valid_properties.keys())[:10]  # Show first 10 for debugging
            }

        # Associate with contact
        try:
            assoc = BatchInputPublicAssociation(
                inputs=[PublicAssociation(_from=deal.id, to=str(contact_id), type="deal_to_contact")]
            )
            cli.crm.associations.batch_api.create(
                from_object_type="deals", to_object_type="contacts", batch_input_public_association=assoc
            )
        except Exception as err:
            return {"error": f"Failed to associate deal with contact: {str(err)}"}

        return {
            "status": "success",
            "dealId": deal.id,
            "dealName": deal_name,
            "contactId": contact_id,
            "pipeline": pipeline,
            "stage": stage,
            "properties": deal_properties
        }
    
    except Exception as e:
        return {"error": f"Deal creation failed: {str(e)}"}


def _discover_valid_pipeline_and_stages(cli) -> Dict[str, Any]:
    """Discover valid deal pipelines and stages."""
    try:
        pipelines = cli.crm.pipelines.pipelines_api.get_all(object_type="deals")
        if pipelines.results:
            first_pipeline = pipelines.results[0]
            stages = {}
            if first_pipeline.stages:
                stages = {stage.label.lower(): stage.id for stage in first_pipeline.stages}
            
            return {
                "pipeline_id": first_pipeline.id,
                "pipeline_name": first_pipeline.label,
                "stages": stages
            }
    except Exception:
        pass
    return {"pipeline_id": "default", "pipeline_name": "default", "stages": {}}


def _discover_valid_properties(cli) -> Dict[str, Any]:
    """Discover valid deal properties to avoid PROPERTY_DOESNT_EXIST errors."""
    try:
        properties = cli.crm.properties.core_api.get_all(object_type="deals")
        valid_props = {}
        for prop in properties.results:
            valid_props[prop.name] = {
                "type": prop.type,
                "options": [opt.value for opt in prop.options] if hasattr(prop, 'options') and prop.options else None
            }
        return valid_props
    except Exception:
        return {}


def main() -> None:
    # Test mode for autodiscovery (REQUIRED)
    if len(sys.argv) == 2 and sys.argv[1] == '{"__test__": true}':
        print(json.dumps({"success": True, "_simple": True}))
        return
    
    # Optional: Rich schema for better LLM integration
    if len(sys.argv) == 2 and sys.argv[1] == "--fractalic-dump-schema":
        schema = {
            "description": "Create a HubSpot deal independently without requiring a ticket. Associates the deal with a contact.",
            "parameters": {
                "type": "object",
                "properties": {
                    "contactId": {
                        "type": "integer",
                        "description": "ID of the contact to associate with the deal (required)"
                    },
                    "dealName": {
                        "type": "string",
                        "description": "Name/title of the deal (required)"
                    },
                    "pipeline": {
                        "type": "string",
                        "description": "Pipeline name for the deal (optional, defaults to default pipeline)"
                    },
                    "stage": {
                        "type": "string",
                        "description": "Stage ID or name for the deal (optional)"
                    },
                    "amount": {
                        "type": "number",
                        "description": "Deal amount/value (optional)"
                    },
                    "closedate": {
                        "type": "string",
                        "format": "date",
                        "description": "Expected close date in YYYY-MM-DD format (optional)"
                    },
                    "description": {
                        "type": "string",
                        "description": "Deal description (optional)"
                    },
                    "properties": {
                        "type": "object",
                        "description": "Additional custom properties for the deal (optional)"
                    }
                },
                "required": ["contactId", "dealName"]
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
