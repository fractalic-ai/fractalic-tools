#!/usr/bin/env python3

import sys
import os
import json
from datetime import datetime

# Add parent directories to sys.path to allow importing hubspot_hub_helpers
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'manage'))

def process_data(data):
    """
    Extract detailed process data including stage progression, timing, and step sequences
    for specific deal patterns or process types.
    
    Args:
        data: Dictionary containing extraction parameters and filters
    
    Returns:
        Dict containing detailed process extraction results
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
        
        # Import dependencies
        from hubspot_hub_helpers import hs_client
        client = hs_client()
        
        # Extract parameters with defaults
        max_deals = data.get("max_deals", 100)
        include_stage_timing = data.get("include_stage_timing", True)
        include_property_history = data.get("include_property_history", True)
        pipeline_filter = data.get("pipeline_filter", None)
        stage_filter = data.get("stage_filter", None)
        owner_filter = data.get("owner_filter", None)
        date_range_days = data.get("date_range_days", 90)
        
    except Exception as e:
        return {"success": False, "error": f"HubSpot connection failed: {str(e)}"}
        
    results = {
        "success": True,
        "analysis_type": "detailed_process_extraction", 
        "timestamp": datetime.now().isoformat(),
        "parameters": {
            "max_deals": max_deals,
            "include_stage_timing": include_stage_timing,
            "include_property_history": include_property_history,
            "pipeline_filter": pipeline_filter,
            "stage_filter": stage_filter,
            "owner_filter": owner_filter,
            "date_range_days": date_range_days
        },
        "deals": [],
        "stage_progression_data": [],
        "timing_data": [],
        "property_history": []
    }
    
    try:
        # Get all deals with detailed properties including stage tracking
        properties = [
            'dealname', 'dealstage', 'pipeline', 'amount', 'closedate', 'createdate',
            'hs_lastmodifieddate', 'hubspot_owner_id', 'dealtype', 'description',
            # Stage entry dates
            'hs_date_entered_appointmentscheduled', 'hs_date_entered_qualifiedtobuy',
            'hs_date_entered_presentationscheduled', 'hs_date_entered_decisionmakerboughtin',
            'hs_date_entered_contractsent', 'hs_date_entered_closedwon', 'hs_date_entered_closedlost',
            # Stage exit dates  
            'hs_date_exited_appointmentscheduled', 'hs_date_exited_qualifiedtobuy',
            'hs_date_exited_presentationscheduled', 'hs_date_exited_decisionmakerboughtin',
            'hs_date_exited_contractsent', 'hs_date_exited_closedwon', 'hs_date_exited_closedlost',
            # Time in stages
            'hs_time_in_appointmentscheduled', 'hs_time_in_qualifiedtobuy',
            'hs_time_in_presentationscheduled', 'hs_time_in_decisionmakerboughtin',
            'hs_time_in_contractsent', 'hs_time_in_closedwon', 'hs_time_in_closedlost',
            # V2 timing data
            'hs_v2_date_entered_appointmentscheduled', 'hs_v2_date_entered_qualifiedtobuy',
            'hs_v2_date_entered_presentationscheduled', 'hs_v2_date_entered_decisionmakerboughtin',
            'hs_v2_date_entered_contractsent', 'hs_v2_date_entered_closedwon', 'hs_v2_date_entered_closedlost',
            'hs_v2_cumulative_time_in_appointmentscheduled', 'hs_v2_cumulative_time_in_qualifiedtobuy',
            'hs_v2_cumulative_time_in_presentationscheduled', 'hs_v2_cumulative_time_in_decisionmakerboughtin',
            'hs_v2_cumulative_time_in_contractsent', 'hs_v2_cumulative_time_in_closedwon'
        ]
        
        # Extract all deals with comprehensive properties
        deals_response = client.crm.deals.get_all(
            properties=properties,
            limit=100
        )
        
        if not deals_response:
            results["deals"] = []
            results["error"] = "No deals found or API error"
            return results
            
        deals = list(deals_response)
        results["total_deals"] = len(deals)
        
        # Process each deal to extract detailed progression data
        for deal in deals:
            deal_id = deal.id
            properties_data = deal.properties
            
            # Basic deal info
            deal_info = {
                "id": deal_id,
                "name": properties_data.get('dealname', ''),
                "current_stage": properties_data.get('dealstage', ''),
                "pipeline": properties_data.get('pipeline', ''),
                "amount": properties_data.get('amount', ''),
                "created": properties_data.get('createdate', ''),
                "modified": properties_data.get('hs_lastmodifieddate', ''),
                "closedate": properties_data.get('closedate', ''),
                "dealtype": properties_data.get('dealtype', ''),
                "description": properties_data.get('description', '')
            }
            
            # Extract stage progression sequence
            stage_sequence = []
            stage_timings = {}
            
            # Define stage order for process flow analysis
            stages = [
                'appointmentscheduled', 'qualifiedtobuy', 'presentationscheduled',
                'decisionmakerboughtin', 'contractsent', 'closedwon', 'closedlost'
            ]
            
            for stage in stages:
                entered_date = properties_data.get(f'hs_date_entered_{stage}') or properties_data.get(f'hs_v2_date_entered_{stage}')
                exited_date = properties_data.get(f'hs_date_exited_{stage}')
                time_in_stage = properties_data.get(f'hs_time_in_{stage}') or properties_data.get(f'hs_v2_cumulative_time_in_{stage}')
                
                if entered_date:
                    stage_data = {
                        "stage": stage,
                        "entered": entered_date,
                        "exited": exited_date,
                        "time_in_stage": time_in_stage
                    }
                    stage_sequence.append(stage_data)
                    stage_timings[stage] = stage_data
            
            # Sort stages by entry date to get actual progression sequence
            stage_sequence.sort(key=lambda x: x['entered'] if x['entered'] else '9999-12-31')
            
            deal_info["stage_progression"] = stage_sequence
            deal_info["stage_timings"] = stage_timings
            
            # Calculate process metrics
            if stage_sequence:
                deal_info["process_length"] = len(stage_sequence)
                deal_info["first_stage"] = stage_sequence[0]['stage'] if stage_sequence else None
                deal_info["last_stage"] = stage_sequence[-1]['stage'] if stage_sequence else None
                
                # Calculate total process duration
                if len(stage_sequence) > 1:
                    first_date = stage_sequence[0]['entered']
                    last_date = stage_sequence[-1]['entered']
                    if first_date and last_date:
                        deal_info["process_duration_data"] = {
                            "start": first_date,
                            "end": last_date
                        }
            
            results["deals"].append(deal_info)
        
        # Group deals by pattern for process variant analysis
        results["process_patterns"] = {}
        for deal in results["deals"]:
            # Create pattern key based on stage progression
            if deal.get("stage_progression"):
                pattern_key = " → ".join([stage["stage"] for stage in deal["stage_progression"]])
            else:
                pattern_key = f"direct_to_{deal['current_stage']}"
            
            if pattern_key not in results["process_patterns"]:
                results["process_patterns"][pattern_key] = []
            results["process_patterns"][pattern_key].append({
                "deal_id": deal["id"],
                "deal_name": deal["name"],
                "amount": deal["amount"],
                "duration": deal.get("process_duration_data")
            })
        
        # Calculate pattern statistics
        results["pattern_statistics"] = {}
        for pattern, deals in results["process_patterns"].items():
            results["pattern_statistics"][pattern] = {
                "frequency": len(deals),
                "percentage": round((len(deals) / len(results["deals"])) * 100, 1) if results["deals"] else 0,
                "sample_deals": deals[:3]  # First 3 deals as examples
            }
            
    except Exception as e:
        results["status"] = "error"
        results["error"] = str(e)
        
    return results

def get_schema():
    """Return the JSON schema for this tool's input parameters."""
    return {
        "description": "Extract detailed process data including stage progression, timing, and step sequences for specific deal patterns or process types",
        "parameters": {
            "type": "object",
            "properties": {
                "max_deals": {
                    "type": "integer",
                    "description": "Maximum number of deals to extract",
                    "default": 100,
                    "minimum": 10,
                    "maximum": 1000
                },
                "include_stage_timing": {
                    "type": "boolean",
                    "description": "Whether to include detailed stage timing data",
                    "default": True
                },
                "include_property_history": {
                    "type": "boolean", 
                    "description": "Whether to include property change history",
                    "default": True
                },
                "pipeline_filter": {
                    "type": "string",
                    "description": "Specific pipeline to extract data from (optional filter)"
                },
                "stage_filter": {
                    "type": "string",
                    "description": "Specific deal stage to filter by (optional filter)"
                },
                "owner_filter": {
                    "type": "string",
                    "description": "Specific owner ID to filter by (optional filter)"
                },
                "date_range_days": {
                    "type": "integer",
                    "description": "Number of days to look back for analysis",
                    "default": 90
                }
            }
        }
    }


def main():
    """Main function to handle CLI arguments and process data"""
    # Handle command line arguments for schema export
    if len(sys.argv) > 1 and sys.argv[1] == "--fractalic-dump-schema":
        print(json.dumps(get_schema(), indent=2))
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
