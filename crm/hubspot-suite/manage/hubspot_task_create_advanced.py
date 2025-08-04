#!/usr/bin/env python3
"""
Create advanced HubSpot tasks with due dates, assignments, and multiple associations.
"""
from __future__ import annotations

import json
import sys
from typing import Any, Dict
from datetime import datetime, timedelta
import re


def process_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Create advanced tasks with flexible due dates and associations."""
    try:
        # Import dependencies inside the function to avoid top-level import issues
        from hubspot.crm.objects.tasks import SimplePublicObjectInput
        from hubspot.crm.associations import BatchInputPublicAssociation, PublicAssociation
        from hubspot_hub_helpers import hs_client
        
        task_type = data.get("type", "CALL")
        title = data.get("title")
        due_date = data.get("dueDate")
        assigned_to = data.get("assignedTo")
        priority = data.get("priority", "MEDIUM")
        description = data.get("description", "")
        associated_objects = data.get("associatedObjects", [])
        
        # Auto-generate title if not provided for predefined task types
        if not title:
            predefined_titles = {
                "Manual price check": "Manual Price Check Required",
                "Follow-up call": "Follow-up Call",
                "Call to request file": "Call to Request File",
                "Print part": "Print Part",
                "Ask for review": "Ask for Review"
            }
            title = predefined_titles.get(task_type, task_type)
        
        if not due_date:
            return {"error": "dueDate parameter is required"}
        
        cli = hs_client()
        
        # Parse due date - supports relative dates like "+24h", "+1h", "+3d"
        due_timestamp = _parse_due_date(due_date)
        if not due_timestamp:
            return {"error": f"Invalid dueDate format: {due_date}. Use ISO format or relative format like '+24h', '+1h', '+3d'"}
        
        # Determine owner ID
        owner_id = None
        if assigned_to:
            if str(assigned_to).isdigit():
                owner_id = int(assigned_to)
            else:
                # Try to resolve owner by email or name
                try:
                    owners = cli.crm.owners.owners_api.get_page()
                    for owner in owners.results:
                        if (owner.email and owner.email.lower() == assigned_to.lower()) or \
                           (owner.first_name and owner.last_name and 
                            f"{owner.first_name} {owner.last_name}".lower() == assigned_to.lower()):
                            owner_id = owner.id
                            break
                    
                    if not owner_id:
                        return {"error": f"Owner not found: {assigned_to}"}
                        
                except Exception as err:
                    return {"error": f"Owner lookup failed: {str(err)}"}
        
        # Map task types and priorities
        task_type_map = {
            "Manual price check": "TODO",
            "Follow-up call": "CALL",
            "Call to request file": "CALL", 
            "Print part": "TODO",
            "Ask for review": "TODO",
            "CALL": "CALL",
            "TODO": "TODO",
            "EMAIL": "EMAIL"
        }
        
        priority_map = {
            "LOW": "LOW",
            "MEDIUM": "MEDIUM", 
            "HIGH": "HIGH",
            "URGENT": "HIGH"  # HubSpot doesn't have URGENT, map to HIGH
        }
        
        task_properties = {
            "hs_task_subject": title,
            "hs_timestamp": str(due_timestamp),
            "hs_task_status": "NOT_STARTED",
            "hs_task_type": task_type_map.get(task_type, "TODO"),
            "hs_task_priority": priority_map.get(priority, "MEDIUM")
        }
        
        if description:
            task_properties["hs_task_body"] = description
        
        if owner_id:
            task_properties["hubspot_owner_id"] = str(owner_id)
        
        try:
            # Create the task
            task = cli.crm.objects.tasks.basic_api.create(
                SimplePublicObjectInput(properties=task_properties)
            )
            
            # Create associations with multiple objects
            associations_created = []
            for obj in associated_objects:
                if isinstance(obj, dict):
                    obj_type = obj.get("type", "deals")
                    obj_id = obj.get("id")
                else:
                    # Assume it's a deal ID if just a number/string
                    obj_type = "deals"
                    obj_id = obj
                
                if obj_id:
                    try:
                        # Create association
                        assoc_type_map = {
                            "deals": "task_to_deal",
                            "contacts": "task_to_contact", 
                            "tickets": "task_to_ticket",
                            "companies": "task_to_company"
                        }
                        
                        assoc = BatchInputPublicAssociation(
                            inputs=[PublicAssociation(
                                _from=task.id,
                                to=str(obj_id), 
                                type=assoc_type_map.get(obj_type, "task_to_deal")
                            )]
                        )
                        
                        cli.crm.associations.batch_api.create(
                            from_object_type="tasks",
                            to_object_type=obj_type,
                            batch_input_public_association=assoc
                        )
                        
                        associations_created.append({
                            "objectType": obj_type,
                            "objectId": obj_id,
                            "associationType": assoc_type_map.get(obj_type, "task_to_deal")
                        })
                        
                    except Exception as err:
                        # Continue with other associations even if one fails
                        associations_created.append({
                            "objectType": obj_type,
                            "objectId": obj_id,
                            "error": str(err)
                        })
            
            return {
                "status": "success",
                "taskId": task.id,
                "title": title,
                "type": task_type_map.get(task_type, "TODO"),
                "dueDate": due_date,
                "dueTimestamp": due_timestamp,
                "priority": priority_map.get(priority, "MEDIUM"),
                "ownerId": owner_id,
                "assignedTo": assigned_to,
                "associations": associations_created,
                "properties": task_properties
            }
            
        except Exception as err:
            return {"error": f"Failed to create task: {str(err)}"}
    
    except Exception as e:
        return {"error": f"Task creation failed: {str(e)}"}


def _parse_due_date(due_date_str: str) -> int:
    """Parse due date string into timestamp."""
    try:
        # Handle relative dates like "+24h", "+1h", "+3d"
        if due_date_str.startswith("+"):
            match = re.match(r'\+(\d+)([hdmw])', due_date_str.lower())
            if match:
                amount = int(match.group(1))
                unit = match.group(2)
                
                now = datetime.now()
                if unit == 'h':
                    target_time = now + timedelta(hours=amount)
                elif unit == 'd':
                    target_time = now + timedelta(days=amount)
                elif unit == 'm':
                    target_time = now + timedelta(minutes=amount)
                elif unit == 'w':
                    target_time = now + timedelta(weeks=amount)
                else:
                    return None
                
                return int(target_time.timestamp() * 1000)  # HubSpot expects milliseconds
        
        # Handle ISO format dates
        try:
            target_time = datetime.fromisoformat(due_date_str.replace('Z', '+00:00'))
            return int(target_time.timestamp() * 1000)
        except:
            pass
        
        # Handle simple date formats
        try:
            target_time = datetime.strptime(due_date_str, "%Y-%m-%d")
            return int(target_time.timestamp() * 1000)
        except:
            pass
        
        return None
        
    except Exception:
        return None


def main() -> None:
    # Test mode for autodiscovery (REQUIRED)
    if len(sys.argv) == 2 and sys.argv[1] == '{"__test__": true}':
        print(json.dumps({"success": True, "_simple": True}))
        return
    
    # Optional: Rich schema for better LLM integration
    if len(sys.argv) == 2 and sys.argv[1] == "--fractalic-dump-schema":
        schema = {
            "description": "Create advanced HubSpot tasks with flexible due dates, assignments, and multiple object associations. Supports relative due dates like '+24h', '+1h', '+3d'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Task title/subject (required)"
                    },
                    "type": {
                        "type": "string",
                        "enum": ["Manual price check", "Follow-up call", "Call to request file", "Print part", "Ask for review", "CALL", "TODO", "EMAIL"],
                        "default": "TODO",
                        "description": "Type of task"
                    },
                    "dueDate": {
                        "type": "string",
                        "description": "Due date - supports ISO format or relative format ('+24h', '+1h', '+3d') (required)"
                    },
                    "assignedTo": {
                        "type": ["string", "integer"],
                        "description": "Owner ID, email, or full name to assign task to"
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["LOW", "MEDIUM", "HIGH", "URGENT"],
                        "default": "MEDIUM",
                        "description": "Task priority level"
                    },
                    "description": {
                        "type": "string",
                        "description": "Task description/notes"
                    },
                    "associatedObjects": {
                        "type": "array",
                        "description": "Objects to associate with the task",
                        "items": {
                            "oneOf": [
                                {
                                    "type": "object",
                                    "properties": {
                                        "type": {
                                            "type": "string",
                                            "enum": ["deals", "contacts", "tickets", "companies"]
                                        },
                                        "id": {
                                            "type": ["string", "integer"]
                                        }
                                    },
                                    "required": ["type", "id"]
                                },
                                {
                                    "type": ["string", "integer"],
                                    "description": "Deal ID (assumes deals type)"
                                }
                            ]
                        }
                    }
                },
                "required": ["title", "dueDate"]
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
