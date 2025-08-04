#!/usr/bin/env python3
"""
Search for HubSpot deals by email, deal ID, or custom properties.
"""
from __future__ import annotations

import json
import sys
from typing import Any, Dict


def process_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Search for deals in HubSpot using various criteria."""
    try:
        # Import dependencies inside the function to avoid top-level import issues
        from hubspot.crm.deals import Filter, FilterGroup, PublicObjectSearchRequest
        from hubspot_hub_helpers import hs_client
        
        search_by = data.get("searchBy", "email")
        value = data.get("value")
        filters = data.get("filters", {})
        limit = data.get("limit", 10)
        
        if not value:
            return {"error": "value parameter is required for search"}
        
        # Validate search parameters based on known limitations
        if search_by == "amount" and isinstance(value, str) and "-" in value:
            return {
                "error": "Amount range searches (e.g., '1000-5000') are not supported by HubSpot API. Use dealname, email, or specific amount values instead.",
                "suggestion": "Try searching by dealname, email, or use filters parameter for complex queries"
            }
        
        # Validate supported search types
        supported_search_types = ["dealId", "email", "dealname", "amount", "customProperty"]
        if search_by not in supported_search_types:
            return {
                "error": f"searchBy '{search_by}' is not supported",
                "supported_types": supported_search_types
            }
        
        cli = hs_client()
        
        # Build search filters based on search type
        filter_groups = []
        
        if search_by == "dealId":
            # Search by deal ID directly
            try:
                deal = cli.crm.deals.basic_api.get_by_id(deal_id=str(value))
                return {
                    "status": "success", 
                    "searchBy": search_by,
                    "value": value,
                    "total": 1,
                    "deals": [{
                        "id": deal.id,
                        "properties": deal.properties
                    }]
                }
            except Exception as err:
                return {"error": f"Deal not found: {str(err)}"}
        
        elif search_by == "email":
            # Search deals associated with contact by email
            # First find contact by email
            try:
                contact_search = PublicObjectSearchRequest(
                    filter_groups=[FilterGroup(filters=[
                        Filter(property_name="email", operator="EQ", value=value)
                    ])],
                    limit=1
                )
                contacts = cli.crm.contacts.search_api.do_search(public_object_search_request=contact_search)
                
                if not contacts.results:
                    return {
                        "status": "success",
                        "searchBy": search_by, 
                        "value": value,
                        "total": 0,
                        "deals": [],
                        "message": "No contact found with this email"
                    }
                
                contact_id = contacts.results[0].id
                
                # Now search deals associated with this contact
                filter_groups.append(FilterGroup(filters=[
                    Filter(property_name="associations.contact", operator="EQ", value=str(contact_id))
                ]))
                
            except Exception as err:
                return {"error": f"Contact search failed: {str(err)}"}
        
        elif search_by == "customProperty":
            # Search by custom property
            property_name = data.get("propertyName")
            if not property_name:
                return {"error": "propertyName is required when searchBy is customProperty"}
            
            filter_groups.append(FilterGroup(filters=[
                Filter(property_name=property_name, operator="EQ", value=str(value))
            ]))
        
        else:
            # Search by standard deal property
            filter_groups.append(FilterGroup(filters=[
                Filter(property_name=search_by, operator="EQ", value=str(value))
            ]))
        
        # Add additional filters
        additional_filters = []
        for prop, criteria in filters.items():
            if isinstance(criteria, dict):
                operator = list(criteria.keys())[0]
                filter_value = criteria[operator]
                # Map operators
                operator_map = {"gt": "GT", "lt": "LT", "gte": "GTE", "lte": "LTE", "eq": "EQ", "ne": "NEQ"}
                operator = operator_map.get(operator, "EQ")
                additional_filters.append(Filter(property_name=prop, operator=operator, value=str(filter_value)))
            else:
                additional_filters.append(Filter(property_name=prop, operator="EQ", value=str(criteria)))
        
        if additional_filters:
            filter_groups.append(FilterGroup(filters=additional_filters))
        
        # Execute search
        try:
            search_request = PublicObjectSearchRequest(
                filter_groups=filter_groups,
                limit=limit,
                properties=["dealname", "amount", "dealstage", "pipeline", "closedate", "createdate"]
            )
            
            results = cli.crm.deals.search_api.do_search(public_object_search_request=search_request)
            
            deals = []
            for deal in results.results:
                deals.append({
                    "id": deal.id,
                    "properties": deal.properties
                })
            
            return {
                "status": "success",
                "searchBy": search_by,
                "value": value,
                "total": len(deals),
                "deals": deals
            }
            
        except Exception as err:
            return {"error": f"Deal search failed: {str(err)}"}
    
    except Exception as e:
        return {"error": f"Search operation failed: {str(e)}"}


def main() -> None:
    # Test mode for autodiscovery (REQUIRED)
    if len(sys.argv) == 2 and sys.argv[1] == '{"__test__": true}':
        print(json.dumps({"success": True, "_simple": True}))
        return
    
    # Optional: Rich schema for better LLM integration
    if len(sys.argv) == 2 and sys.argv[1] == "--fractalic-dump-schema":
        schema = {
            "description": "Search for HubSpot deals using various criteria including email, deal ID, or custom properties. Essential for finding deals during payment processing and workflow management.",
            "parameters": {
                "type": "object",
                "properties": {
                    "searchBy": {
                        "type": "string",
                        "enum": ["email", "dealId", "customProperty", "dealname", "amount", "pipeline"],
                        "description": "Field to search by"
                    },
                    "value": {
                        "type": "string",
                        "description": "Value to search for (required)"
                    },
                    "propertyName": {
                        "type": "string", 
                        "description": "Custom property name (required when searchBy is customProperty)"
                    },
                    "filters": {
                        "type": "object",
                        "description": "Additional filters (e.g., {'amount': {'gt': 1000}})"
                    },
                    "limit": {
                        "type": "integer",
                        "default": 10,
                        "description": "Maximum number of results to return"
                    }
                },
                "required": ["searchBy", "value"]
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
