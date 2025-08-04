#!/usr/bin/env python3
"""
HubSpot Deal Timeline Extractor
Extracts detailed timeline and activity data for process mining analysis
"""

import json
import os
import sys
from typing import Dict, List, Any, Optional
from datetime import datetime

# Add parent directories to sys.path to allow importing hubspot_hub_helpers
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'manage'))

def process_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract detailed timeline data for deals to enable process flow analysis
    
    Args:
        data: {
            "deal_ids": ["id1", "id2", ...] or "all" for all deals,
            "include_activities": true,
            "include_stage_history": true,
            "include_property_history": true,
            "days_back": 90
        }
    """
    
    # Handle test mode early
    if data.get("__test__") is True:
        return {"success": True, "_simple": True}
        
    try:
        # Set HubSpot token from environment
        hubspot_token = os.getenv("HUBSPOT_TOKEN")
        if not hubspot_token and "hubspot_token" in data:
            hubspot_token = data["hubspot_token"]
        
        if not hubspot_token:
            return {
                "success": False,
                "error": "HubSpot token not provided in environment variable HUBSPOT_TOKEN",
                "timestamp": datetime.now().isoformat()
            }
        
        from hubspot_hub_helpers import hs_client
        
        client = hs_client()
        
        # Extract parameters
        deal_ids = data.get("deal_ids", "all")
        include_activities = data.get("include_activities", True)
        include_stage_history = data.get("include_stage_history", True) 
        include_property_history = data.get("include_property_history", True)
        days_back = data.get("days_back", 90)
        
        results = {
            "success": True,
            "timeline_data": [],
            "activities": [],
            "stage_transitions": [],
            "property_changes": []
        }
        
        # Get deals to analyze
        if deal_ids == "all":
            # Get all deals
            try:
                deals_response = client.crm.deals.basic_api.get_page(
                    limit=100,
                    properties=["dealname", "dealstage", "createdate", "hs_lastmodifieddate", "pipeline", "hubspot_owner_id"]
                )
                deals = deals_response.results
                deal_ids = [deal.id for deal in deals]
            except Exception as e:
                return {"error": f"Failed to get deals: {str(e)}"}
        
        # Extract timeline for each deal
        for deal_id in deal_ids:
            deal_timeline = _extract_deal_timeline(client, deal_id, include_activities, include_stage_history, include_property_history)
            if deal_timeline:
                results["timeline_data"].append(deal_timeline)
        
        return results
        
    except Exception as e:
        return {"error": f"Timeline extraction failed: {str(e)}"}

def _extract_deal_timeline(client, deal_id: str, include_activities: bool, include_stage_history: bool, include_property_history: bool) -> Dict[str, Any]:
    """Extract comprehensive timeline for a single deal"""
    
    timeline = {
        "deal_id": deal_id,
        "events": [],
        "stage_history": [],
        "property_changes": [],
        "activities": []
    }
    
    try:
        # Get deal details
        deal = client.crm.deals.basic_api.get_by_id(
            deal_id=deal_id,
            properties=["dealname", "dealstage", "createdate", "hs_lastmodifieddate", "pipeline", "hubspot_owner_id", "amount", "closedate"]
        )
        
        timeline["deal_info"] = {
            "name": deal.properties.get("dealname"),
            "current_stage": deal.properties.get("dealstage"),
            "pipeline": deal.properties.get("pipeline"),
            "owner": deal.properties.get("hubspot_owner_id"),
            "amount": deal.properties.get("amount"),
            "created": deal.properties.get("createdate"),
            "modified": deal.properties.get("hs_lastmodifieddate"),
            "closedate": deal.properties.get("closedate")
        }
        
        # Get activities if requested
        if include_activities:
            timeline["activities"] = _get_deal_activities(client, deal_id)
        
        # Get property history if requested  
        if include_property_history:
            timeline["property_changes"] = _get_property_history(client, deal_id)
            
        return timeline
        
    except Exception as e:
        print(f"Error extracting timeline for deal {deal_id}: {str(e)}")
        return None

def _get_deal_activities(client, deal_id: str) -> List[Dict[str, Any]]:
    """Get all activities associated with a deal"""
    activities = []
    
    try:
        # Get associations to get related activities
        # Note: This would need the associations API to get related engagements
        # For now, return placeholder structure
        return []
        
    except Exception as e:
        print(f"Error getting activities for deal {deal_id}: {str(e)}")
        return []

def _get_property_history(client, deal_id: str) -> List[Dict[str, Any]]:
    """Get property change history for a deal"""
    
    try:
        # Note: HubSpot doesn't directly expose property history via basic API
        # This would require the Properties History API or Audit Log access
        # For now, return placeholder structure
        return []
        
    except Exception as e:
        print(f"Error getting property history for deal {deal_id}: {str(e)}")
        return []

def main():
    """Main function to handle CLI arguments and process data"""
    if len(sys.argv) > 1 and sys.argv[1] == "--fractalic-dump-schema":
        schema = {
            "description": "Extract detailed timeline and activity data for process mining analysis",
            "parameters": {
                "type": "object",
                "properties": {
                    "deal_ids": {
                        "anyOf": [
                            {"type": "string", "enum": ["all"]},
                            {"type": "array", "items": {"type": "string"}}
                        ],
                        "description": "Deal IDs to extract timeline for, or 'all' for all deals",
                        "default": "all"
                    },
                    "include_activities": {
                        "type": "boolean",
                        "description": "Whether to include activity data",
                        "default": True
                    },
                    "include_stage_history": {
                        "type": "boolean",
                        "description": "Whether to include stage history",
                        "default": True
                    },
                    "include_property_history": {
                        "type": "boolean",
                        "description": "Whether to include property change history",
                        "default": True
                    },
                    "days_back": {
                        "type": "integer",
                        "description": "Number of days to look back for timeline data",
                        "default": 90
                    }
                }
            }
        }
        print(json.dumps(schema, indent=2))
        return

    try:
        # Handle command line JSON input
        if len(sys.argv) > 1:
            input_data = sys.argv[1]
        else:
            # Fallback to stdin for backward compatibility
            input_data = sys.stdin.read().strip()
        
        if not input_data:
            input_data = '{}'
        
        data = json.loads(input_data)
        
        # Process the data
        result = process_data(data)
        print(json.dumps(result, default=str))
        
    except json.JSONDecodeError as e:
        error_result = {"success": False, "error": f"Invalid JSON input: {str(e)}"}
        print(json.dumps(error_result))
        sys.exit(1)
    except Exception as e:
        error_result = {"success": False, "error": str(e)}
        print(json.dumps(error_result))
        sys.exit(1)


if __name__ == "__main__":
    main()
