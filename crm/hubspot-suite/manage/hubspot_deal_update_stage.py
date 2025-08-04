#!/usr/bin/env python3
"""
Move a deal to a new stage by stage label.
"""
from __future__ import annotations

import json
import sys
from typing import Any, Dict


def process_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Move an existing deal to a new stage (by label)."""
    try:
        # Import dependencies inside the function to avoid top-level import issues
        from hubspot.crm.deals import SimplePublicObjectInput
        from hubspot_hub_helpers import hs_client
        
        deal_id = data.get("dealId")
        stage = data.get("stage")
        
        if not deal_id:
            return {"error": "dealId parameter is required"}
        if not stage:
            return {"error": "stage parameter is required"}

        cli = hs_client()

        try:
            deal = cli.crm.deals.basic_api.get_by_id(deal_id, properties=["pipeline", "dealstage"])
            pipeline_id = deal.properties["pipeline"]
        except Exception as err:
            return {"error": f"Failed to fetch deal {deal_id}: {str(err)}"}

        try:
            stages = cli.crm.pipelines.pipelines_api.get_by_id("deals", pipeline_id).stages
            stage_id = next((s.id for s in stages if s.label == stage), None)
            if not stage_id:
                available_stages = [s.label for s in stages]
                return {
                    "error": f"Stage '{stage}' not found in pipeline ID {pipeline_id}",
                    "available_stages": available_stages
                }
        except Exception as err:
            return {"error": f"Failed to fetch pipeline stages: {str(err)}"}

        try:
            cli.crm.deals.basic_api.update(
                deal_id, SimplePublicObjectInput(properties={"dealstage": stage_id})
            )
            return {
                "status": "success",
                "dealId": deal_id,
                "newStage": stage,
                "newStageId": stage_id,
                "pipelineId": pipeline_id
            }
        except Exception as err:
            return {"error": f"Failed to update deal stage: {str(err)}"}
    
    except Exception as e:
        return {"error": f"Deal stage update failed: {str(e)}"}


def main() -> None:
    # Test mode for autodiscovery (REQUIRED)
    if len(sys.argv) == 2 and sys.argv[1] == '{"__test__": true}':
        print(json.dumps({"success": True, "_simple": True}))
        return
    
    # Optional: Rich schema for better LLM integration
    if len(sys.argv) == 2 and sys.argv[1] == "--fractalic-dump-schema":
        schema = {
            "description": "Move an existing HubSpot deal to a new stage within its current pipeline. Updates deal progression status.",
            "parameters": {
                "type": "object",
                "properties": {
                    "dealId": {
                        "type": "integer",
                        "description": "ID of the deal to update"
                    },
                    "stage": {
                        "type": "string",
                        "description": "Label of the new stage (e.g., 'Qualified Lead', 'Proposal', 'Closed Won')"
                    }
                },
                "required": ["dealId", "stage"]
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
