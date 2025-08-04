#!/usr/bin/env python3
"""
Full Process Mining Pipeline - Orchestration Tool
Runs complete process mining analysis by orchestrating multiple discovery tools
"""

import json
import os
import sys
from subprocess import run, PIPE

# Add parent directories to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'manage'))


def run_full_process_mining(data):
    """
    Run comprehensive process mining analysis by orchestrating multiple tools
    
    Args:
        data: Configuration for the analysis
    
    Returns:
        Complete process mining results
    """
    
    # Handle test mode early
    if data.get("__test__") is True:
        return {"success": True, "_simple": True}
    
    try:
        # Step 1: Get deals data from manage tools directory  
        deals_search_path = os.path.join(os.path.dirname(__file__), '..', '..', 'manage', 'hubspot_deal_search.py')
        
        result = run(['python', deals_search_path, '{"searchBy": "dealname", "value": "*", "limit": 100}'], 
                     capture_output=True, text=True)
        
        if result.returncode != 0:
            return {"success": False, "error": f"Error getting deals: {result.stderr}"}
        
        deals_data = json.loads(result.stdout)
        
        # Step 2: Run process mining analysis
        mining_input = {"deals_data": deals_data}
        process_mining_path = os.path.join(os.path.dirname(__file__), 'process_mining_analysis.py')
        
        result = run(['python', process_mining_path, json.dumps(mining_input)], 
                     capture_output=True, text=True)
        
        if result.returncode != 0:
            return {"success": False, "error": f"Error in process mining: {result.stderr}"}
        
        process_results = json.loads(result.stdout)
        
        return {
            "success": True,
            "deals_count": len(deals_data.get("deals", [])),
            "process_mining_results": process_results,
            "pipeline_steps": ["deal_extraction", "process_mining_analysis"]
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}


def main():
    """Main function to handle CLI arguments and process data"""
    if len(sys.argv) > 1 and sys.argv[1] == "--fractalic-dump-schema":
        schema = {
            "description": "Run comprehensive process mining analysis by orchestrating multiple discovery tools",
            "parameters": {
                "type": "object",
                "properties": {
                    "analysis_scope": {
                        "type": "string",
                        "description": "Scope of the full process mining analysis",
                        "enum": ["basic", "comprehensive", "focused"],
                        "default": "comprehensive"
                    },
                    "max_deals": {
                        "type": "integer",
                        "description": "Maximum number of deals to analyze",
                        "default": 100
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
            input_data = '{}'
        
        data = json.loads(input_data)
        
        # Process the data
        result = run_full_process_mining(data)
        print(json.dumps(result))
        
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
