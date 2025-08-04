#!/usr/bin/env python3
"""
Create a HubSpot ticket with automatic discovery of valid stages and categories.
"""
from __future__ import annotations

import json
import sys
from typing import Any, Dict


def _discover_valid_stages(cli) -> Dict[str, str]:
    """Discover valid ticket stages from the first pipeline."""
    try:
        pipelines = cli.crm.pipelines.pipelines_api.get_all(object_type="tickets")
        if pipelines.results:
            first_pipeline = pipelines.results[0]
            if first_pipeline.stages:
                # Return mapping of stage labels to IDs
                return {stage.label.lower(): stage.id for stage in first_pipeline.stages}
    except Exception:
        pass
    return {}


def _discover_valid_categories(cli) -> Dict[str, str]:
    """Discover valid ticket categories."""
    try:
        properties = cli.crm.properties.core_api.get_all(object_type="tickets")
        for prop in properties.results:
            if prop.name == "hs_ticket_category" and hasattr(prop, 'options') and prop.options:
                return {opt.label.lower(): opt.value for opt in prop.options}
    except Exception:
        pass
    return {}


def _find_related_deals(cli, contact_id: str) -> list:
    """Find deals associated with the contact."""
    try:
        # Search for deals associated with this contact
        search_request = {
            "filters": [
                {
                    "propertyName": "associations.contact",
                    "operator": "EQ",
                    "value": str(contact_id)
                }
            ],
            "limit": 10
        }
        
        deals = cli.crm.deals.search_api.do_search(
            public_object_search_request=search_request
        )
        
        if deals.results:
            return [deal.id for deal in deals.results]
        return []
    except Exception:
        # If search fails, try alternative method - get associations directly
        try:
            associations = cli.crm.contacts.associations_api.get_all(
                contact_id=contact_id,
                to_object_type="deals"
            )
            return [assoc.id for assoc in associations.results] if associations.results else []
        except Exception:
            return []


def process_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a ticket with smart discovery of valid values."""
    try:
        # Import dependencies inside the function to avoid top-level import issues
        from hubspot.crm.associations import (
            BatchInputPublicAssociation,
            PublicAssociation,
        )
        from hubspot.crm.tickets import SimplePublicObjectInput
        from hubspot_hub_helpers import hs_client
        
        contact_id = data.get("contactId")
        title = data.get("title")
        
        if not contact_id:
            return {"error": "contactId parameter is required"}
        if not title:
            return {"error": "title parameter is required"}
            
        requested_category = data.get("category", "").lower()
        requested_stage = data.get("stage", "").lower()

        cli = hs_client()
        
        # Discover valid values
        valid_stages = _discover_valid_stages(cli)
        valid_categories = _discover_valid_categories(cli)
        
        # Determine stage
        stage_id = None
        if requested_stage and requested_stage in valid_stages:
            stage_id = valid_stages[requested_stage]
        elif valid_stages:
            # Use first available stage
            stage_id = list(valid_stages.values())[0]
        
        # Determine category
        category_value = None
        if requested_category and requested_category in valid_categories:
            category_value = valid_categories[requested_category]
        elif valid_categories:
            # Use first available category
            category_value = list(valid_categories.values())[0]
        
        # Build ticket properties
        ticket_properties = {
            "subject": title
        }
        
        # Add pipeline stage - use discovered stage or default to first available stage
        if stage_id:
            ticket_properties["hs_pipeline_stage"] = stage_id
        elif valid_stages:
            # Use first available stage if none specified
            ticket_properties["hs_pipeline_stage"] = list(valid_stages.values())[0]
            stage_id = list(valid_stages.values())[0]
            
        # Add category - use discovered category or default to first available
        if category_value:
            ticket_properties["hs_ticket_category"] = category_value
        elif valid_categories:
            # Use first available category if none specified
            ticket_properties["hs_ticket_category"] = list(valid_categories.values())[0] 
            category_value = list(valid_categories.values())[0]
            
        # Add additional properties
        if "priority" in data:
            ticket_properties["hs_ticket_priority"] = data["priority"]
        if "description" in data:
            ticket_properties["content"] = data["description"]

        try:
            ticket = cli.crm.tickets.basic_api.create(
                SimplePublicObjectInput(properties=ticket_properties)
            )
        except Exception as err:
            return {
                "error": f"Failed to create ticket: {str(err)}",
                "attempted_properties": ticket_properties,
                "available_stages": valid_stages,
                "available_categories": valid_categories
            }

        # Associate with contact
        try:
            assoc = BatchInputPublicAssociation(
                inputs=[PublicAssociation(_from=ticket.id, to=str(contact_id), type="ticket_to_contact")]
            )
            cli.crm.associations.batch_api.create(
                from_object_type="tickets", to_object_type="contacts", batch_input_public_association=assoc
            )
        except Exception as err:
            return {"error": f"Failed to associate ticket with contact: {str(err)}"}

        # Find and associate related deals
        related_deals = []
        deal_association_errors = []
        try:
            related_deals = _find_related_deals(cli, contact_id)
            if related_deals:
                deal_associations = [
                    PublicAssociation(_from=ticket.id, to=str(deal_id), type="ticket_to_deal")
                    for deal_id in related_deals
                ]
                assoc = BatchInputPublicAssociation(inputs=deal_associations)
                cli.crm.associations.batch_api.create(
                    from_object_type="tickets", to_object_type="deals", batch_input_public_association=assoc
                )
        except Exception as err:
            deal_association_errors.append(f"Failed to associate ticket with related deals: {str(err)}")

        return {
            "status": "success",
            "ticketId": ticket.id,
            "title": title,
            "contactId": contact_id,
            "associated_deals": related_deals,
            "stage_used": stage_id,
            "category_used": category_value,
            "properties": ticket_properties,
            "warnings": deal_association_errors if deal_association_errors else None
        }
    
    except Exception as e:
        return {"error": f"Ticket creation failed: {str(e)}"}


def main() -> None:
    # Test mode for autodiscovery (REQUIRED)
    if len(sys.argv) == 2 and sys.argv[1] == '{"__test__": true}':
        print(json.dumps({"success": True, "_simple": True}))
        return
    
    # Optional: Rich schema for better LLM integration
    if len(sys.argv) == 2 and sys.argv[1] == "--fractalic-dump-schema":
        schema = {
            "description": "Create a HubSpot ticket with automatic discovery of valid stages and categories. Will use the best available values if exact matches aren't found.",
            "parameters": {
                "type": "object",
                "properties": {
                    "contactId": {
                        "type": "integer",
                        "description": "ID of the contact to associate with the ticket (required)"
                    },
                    "title": {
                        "type": "string",
                        "description": "Subject/title of the ticket (required)"
                    },
                    "category": {
                        "type": "string",
                        "description": "Ticket category (optional, will auto-discover valid options)"
                    },
                    "stage": {
                        "type": "string",
                        "description": "Ticket stage (optional, will auto-discover valid options)"
                    },
                    "priority": {
                        "type": "string",
                        "description": "Ticket priority (optional)"
                    },
                    "description": {
                        "type": "string",
                        "description": "Ticket description/content (optional)"
                    }
                },
                "required": ["contactId", "title"]
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
