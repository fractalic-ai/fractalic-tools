#!/usr/bin/env python3

import sys
import os
import json

# Add parent directories to sys.path to allow importing hubspot_hub_helpers
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'manage'))

from hubspot_hub_helpers import hs_client

def analyze_object_associations(parameters):
    """
    Extract comprehensive object associations and relationships across HubSpot
    to understand the complete business process flow and customer journey.
    
    This tool extracts data only - all analysis is performed by the AI agent.
    """
    
    client = hs_client()
    results = {
        "status": "success",
        "analysis_type": "object_associations",
        "parameters": parameters,
        "deals": [],
        "contacts": [],
        "companies": [],
        "tickets": [],
        "tasks": [],
        "associations": {},
        "relationship_mapping": {}
    }
    
    try:
        # Extract deals with associations
        deals_response = client.crm.deals.get_all(
            properties=['dealname', 'dealstage', 'pipeline', 'amount', 'closedate', 'createdate', 
                       'hs_lastmodifieddate', 'hubspot_owner_id', 'dealtype', 'description',
                       'hs_object_id', 'hs_created_by_user_id', 'hs_updated_by_user_id'],
            associations=['contacts', 'companies', 'tickets', 'line_items', 'quotes', 'calls', 'emails', 'meetings', 'notes', 'tasks'],
            limit=100
        )
        
        for deal in deals_response:
            deal_data = {
                "id": deal.id,
                "properties": deal.properties,
                "associations": {}
            }
            
            # Extract all associations for this deal
            if hasattr(deal, 'associations') and deal.associations:
                for assoc_type, assoc_data in deal.associations.items():
                    if hasattr(assoc_data, 'results'):
                        deal_data["associations"][assoc_type] = [
                            {"id": item.id, "type": item.type} for item in assoc_data.results
                        ]
            
            results["deals"].append(deal_data)
        
        # Extract contacts with associations
        contacts_response = client.crm.contacts.get_all(
            properties=['firstname', 'lastname', 'email', 'phone', 'company', 'lifecyclestage',
                       'createdate', 'lastmodifieddate', 'hs_object_id', 'hs_created_by_user_id'],
            associations=['deals', 'companies', 'tickets', 'calls', 'emails', 'meetings', 'notes', 'tasks'],
            limit=100
        )
        
        for contact in contacts_response:
            contact_data = {
                "id": contact.id,
                "properties": contact.properties,
                "associations": {}
            }
            
            if hasattr(contact, 'associations') and contact.associations:
                for assoc_type, assoc_data in contact.associations.items():
                    if hasattr(assoc_data, 'results'):
                        contact_data["associations"][assoc_type] = [
                            {"id": item.id, "type": item.type} for item in assoc_data.results
                        ]
            
            results["contacts"].append(contact_data)
        
        # Extract companies with associations
        companies_response = client.crm.companies.get_all(
            properties=['name', 'domain', 'industry', 'city', 'state', 'country',
                       'createdate', 'hs_lastmodifieddate', 'hs_object_id'],
            associations=['contacts', 'deals', 'tickets', 'calls', 'emails', 'meetings', 'notes'],
            limit=100
        )
        
        for company in companies_response:
            company_data = {
                "id": company.id,
                "properties": company.properties,
                "associations": {}
            }
            
            if hasattr(company, 'associations') and company.associations:
                for assoc_type, assoc_data in company.associations.items():
                    if hasattr(assoc_data, 'results'):
                        company_data["associations"][assoc_type] = [
                            {"id": item.id, "type": item.type} for item in assoc_data.results
                        ]
            
            results["companies"].append(company_data)
        
        # Extract tickets with associations
        tickets_response = client.crm.tickets.get_all(
            properties=['subject', 'content', 'hs_pipeline_stage', 'hs_ticket_priority',
                       'createdate', 'hs_lastmodifieddate', 'hs_object_id'],
            associations=['contacts', 'deals', 'companies', 'calls', 'emails', 'meetings', 'notes'],
            limit=100
        )
        
        for ticket in tickets_response:
            ticket_data = {
                "id": ticket.id,
                "properties": ticket.properties,
                "associations": {}
            }
            
            if hasattr(ticket, 'associations') and ticket.associations:
                for assoc_type, assoc_data in ticket.associations.items():
                    if hasattr(assoc_data, 'results'):
                        ticket_data["associations"][assoc_type] = [
                            {"id": item.id, "type": item.type} for item in assoc_data.results
                        ]
            
            results["tickets"].append(ticket_data)
        
        # Extract tasks/engagements - this is optional and may not be available in all HubSpot instances
        try:
            # Try different approaches to get tasks
            tasks_response = None
            
            # First try: basic API get_page
            try:
                tasks_response = client.crm.objects.tasks.basic_api.get_page(
                    properties=['hs_task_subject', 'hs_task_body', 'hs_task_status', 'hs_task_priority',
                               'hs_timestamp', 'hs_task_type', 'hubspot_owner_id', 'hs_createdate'],
                    associations=['contacts', 'deals', 'companies', 'tickets'],
                    limit=100
                )
            except:
                # Second try: generic objects API
                try:
                    tasks_response = client.crm.objects.get_all(
                        object_type="tasks",
                        properties=['hs_task_subject', 'hs_task_body', 'hs_task_status', 'hs_task_priority',
                                   'hs_timestamp', 'hs_task_type', 'hubspot_owner_id', 'hs_createdate'],
                        limit=100
                    )
                except:
                    pass  # Tasks not available or accessible
            
            if tasks_response:
                # get_page returns a response with .results attribute
                task_list = tasks_response.results if hasattr(tasks_response, 'results') else tasks_response
                
                for task in task_list:
                    task_data = {
                        "id": task.id,
                        "properties": task.properties,
                        "associations": {}
                    }
                    
                    if hasattr(task, 'associations') and task.associations:
                        for assoc_type, assoc_data in task.associations.items():
                            if hasattr(assoc_data, 'results'):
                                task_data["associations"][assoc_type] = [
                                    {"id": item.id, "type": item.type} for item in assoc_data.results
                                ]
                    
                    results["tasks"].append(task_data)
        except Exception as e:
            results["tasks_error"] = str(e)
        
        # Build association mapping
        results["associations"] = {
            "deal_to_contact": {},
            "deal_to_company": {},
            "contact_to_company": {},
            "deal_to_ticket": {},
            "contact_to_ticket": {},
            "engagement_associations": {}
        }
        
        # Map deal associations
        for deal in results["deals"]:
            deal_id = deal["id"]
            
            if "contacts" in deal["associations"]:
                results["associations"]["deal_to_contact"][deal_id] = [
                    c["id"] for c in deal["associations"]["contacts"]
                ]
            
            if "companies" in deal["associations"]:
                results["associations"]["deal_to_company"][deal_id] = [
                    c["id"] for c in deal["associations"]["companies"]
                ]
            
            if "tickets" in deal["associations"]:
                results["associations"]["deal_to_ticket"][deal_id] = [
                    t["id"] for t in deal["associations"]["tickets"]
                ]
        
        # Map contact associations
        for contact in results["contacts"]:
            contact_id = contact["id"]
            
            if "companies" in contact["associations"]:
                results["associations"]["contact_to_company"][contact_id] = [
                    c["id"] for c in contact["associations"]["companies"]
                ]
            
            if "tickets" in contact["associations"]:
                results["associations"]["contact_to_ticket"][contact_id] = [
                    t["id"] for t in contact["associations"]["tickets"]
                ]
        
        # Calculate relationship statistics
        results["relationship_mapping"] = {
            "total_deals": len(results["deals"]),
            "total_contacts": len(results["contacts"]),
            "total_companies": len(results["companies"]),
            "total_tickets": len(results["tickets"]),
            "total_tasks": len(results["tasks"]),
            "deals_with_contacts": len([d for d in results["deals"] if "contacts" in d["associations"]]),
            "deals_with_companies": len([d for d in results["deals"] if "companies" in d["associations"]]),
            "contacts_with_companies": len([c for c in results["contacts"] if "companies" in c["associations"]]),
            "orphaned_deals": len([d for d in results["deals"] if not d["associations"]]),
            "orphaned_contacts": len([c for c in results["contacts"] if not c["associations"]])
        }
        
    except Exception as e:
        results["status"] = "error"
        results["error"] = str(e)
        
    return results

def main():
    """Main entry point."""
    # Test mode for autodiscovery (REQUIRED)
    if len(sys.argv) == 2 and sys.argv[1] == '{"__test__": true}':
        print(json.dumps({"success": True, "_simple": True}))
        return
    
    # Rich schema for better LLM integration
    if len(sys.argv) == 2 and sys.argv[1] == "--fractalic-dump-schema":
        schema = {
            "description": "Analyze comprehensive object associations and relationships across HubSpot to understand business process flows and customer journeys",
            "parameters": {
                "type": "object",
                "properties": {
                    "analysisScope": {
                        "type": "string",
                        "enum": ["full", "recent", "targeted"],
                        "description": "Scope of association analysis",
                        "default": "recent"
                    },
                    "objectTypes": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Object types to analyze associations for",
                        "default": ["deals", "contacts", "companies", "tickets"]
                    },
                    "includeActivities": {
                        "type": "boolean",
                        "description": "Whether to include activity associations (calls, emails, meetings)",
                        "default": True
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of objects to analyze per type",
                        "default": 100,
                        "maximum": 500
                    },
                    "daysBack": {
                        "type": "integer",
                        "description": "Number of days back to analyze recent associations",
                        "default": 90
                    }
                },
                "additionalProperties": False
            }
        }
        print(json.dumps(schema, ensure_ascii=False))
        return
    
    # Process JSON input (REQUIRED)
    try:
        if len(sys.argv) != 2:
            raise ValueError("Expected exactly one JSON argument")
            
        parameters = json.loads(sys.argv[1])
        result = analyze_object_associations(parameters)
        print(json.dumps(result, ensure_ascii=False))
        
    except Exception as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False))
        sys.exit(1)

if __name__ == "__main__":
    main()
