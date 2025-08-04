#!/usr/bin/env python3
"""
Discover valid pipeline stages for HubSpot objects (deals, tickets).
"""
from __future__ import annotations

import json
import sys
from typing import Any, Dict


def process_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Discover valid pipeline stages for a HubSpot object type."""
    try:
        # Import dependencies inside the function to avoid top-level import issues
        from hubspot_hub_helpers import hs_client
        
        object_type = data.get("objectType", "deals")
        pipeline_id = data.get("pipelineId")
        
        if not object_type:
            return {"error": "objectType parameter is required (e.g., 'deals', 'tickets')"}
        
        cli = hs_client()
        
        try:
            # Get pipelines for the object type
            if object_type == "deals":
                pipelines = cli.crm.pipelines.pipelines_api.get_all(object_type="deals")
            elif object_type == "tickets":
                pipelines = cli.crm.pipelines.pipelines_api.get_all(object_type="tickets")
            else:
                return {"error": f"Unsupported object type: {object_type}. Use 'deals' or 'tickets'"}
            
            result = {
                "objectType": object_type,
                "pipelines": []
            }
            
            for pipeline in pipelines.results:
                pipeline_info = {
                    "id": pipeline.id,
                    "label": pipeline.label,
                    "displayOrder": pipeline.display_order,
                    "stages": []
                }
                
                # Add stages for this pipeline
                for stage in pipeline.stages:
                    stage_info = {
                        "id": stage.id,
                        "label": stage.label,
                        "displayOrder": stage.display_order,
                        "metadata": {}
                    }
                    
                    # Add metadata if available
                    if hasattr(stage, 'metadata') and stage.metadata:
                        stage_info["metadata"] = stage.metadata
                    
                    pipeline_info["stages"].append(stage_info)
                
                result["pipelines"].append(pipeline_info)
            
            # If specific pipeline requested, return just that
            if pipeline_id:
                for pipeline in result["pipelines"]:
                    if pipeline["id"] == pipeline_id:
                        return {
                            "objectType": object_type,
                            "pipeline": pipeline
                        }
                return {"error": f"Pipeline '{pipeline_id}' not found for {object_type}"}
            
            return result
            
        except Exception as err:
            return {"error": f"Failed to get pipelines: {str(err)}"}
    
    except Exception as e:
        return {"error": f"Pipeline discovery failed: {str(e)}"}


def main() -> None:
    # Test mode for autodiscovery (REQUIRED)
    if len(sys.argv) == 2 and sys.argv[1] == '{"__test__": true}':
        print(json.dumps({"success": True, "_simple": True}))
        return
    
    # Optional: Rich schema for better LLM integration
    if len(sys.argv) == 2 and sys.argv[1] == "--fractalic-dump-schema":
        schema = {
            "description": "Discover valid pipeline stages for HubSpot objects. Essential for finding correct stage IDs for ticket and deal creation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "objectType": {
                        "type": "string",
                        "description": "Type of HubSpot object (deals or tickets)",
                        "enum": ["deals", "tickets"]
                    },
                    "pipelineId": {
                        "type": "string",
                        "description": "Specific pipeline ID to get stages for (optional, returns all if not specified)"
                    }
                },
                "required": ["objectType"]
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
