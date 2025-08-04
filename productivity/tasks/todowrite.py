#!/usr/bin/env python3
"""TodoWrite Tool - Fractalic Compatible Implementation

Manages and updates todo lists with structured task tracking including status,
priority, and unique identification for each task item.
"""

import json
import sys
import time
from typing import List, Dict, Any

def process_data(data):
    """Main processing function for todo list management."""
    try:
        # Extract and validate parameters
        todos = data.get("todos")
        
        if not todos:
            return {"status": "error", "error": "todos parameter is required"}
        
        if not isinstance(todos, list):
            return {"status": "error", "error": "todos must be an array"}
        
        # Validate each todo item
        validated_todos = []
        for i, todo in enumerate(todos):
            validation_result = _validate_todo_item(todo, i + 1)
            if "error" in validation_result:
                return {"status": "error", "error": validation_result["error"]}
            validated_todos.append(validation_result["todo"])
        
        # Process the todo list
        result = _process_todo_list(validated_todos)
        
        return {
            "status": "success",
            "data": result
        }
        
    except Exception as e:
        return {"status": "error", "error": str(e)}

def _validate_todo_item(todo, item_number):
    """Validate a single todo item."""
    if not isinstance(todo, dict):
        return {"error": f"Todo item {item_number} must be an object"}
    
    # Required fields
    required_fields = ["content", "status", "priority", "id"]
    for field in required_fields:
        if field not in todo:
            return {"error": f"Todo item {item_number} missing required field: {field}"}
    
    # Validate content
    content = todo["content"]
    if not isinstance(content, str) or len(content.strip()) == 0:
        return {"error": f"Todo item {item_number}: content must be a non-empty string"}
    
    # Validate status
    status = todo["status"]
    valid_statuses = ["pending", "in_progress", "completed"]
    if status not in valid_statuses:
        return {"error": f"Todo item {item_number}: status must be one of {valid_statuses}"}
    
    # Validate priority
    priority = todo["priority"]
    valid_priorities = ["high", "medium", "low"]
    if priority not in valid_priorities:
        return {"error": f"Todo item {item_number}: priority must be one of {valid_priorities}"}
    
    # Validate ID
    todo_id = todo["id"]
    if not isinstance(todo_id, str) or len(todo_id.strip()) == 0:
        return {"error": f"Todo item {item_number}: id must be a non-empty string"}
    
    # Return validated todo with additional metadata
    validated_todo = {
        "content": content.strip(),
        "status": status,
        "priority": priority,
        "id": todo_id.strip(),
        "lastUpdated": int(time.time())
    }
    
    # Add optional fields if present
    if "createdAt" in todo:
        validated_todo["createdAt"] = todo["createdAt"]
    else:
        validated_todo["createdAt"] = int(time.time())
    
    if "tags" in todo and isinstance(todo["tags"], list):
        validated_todo["tags"] = todo["tags"]
    
    if "description" in todo and isinstance(todo["description"], str):
        validated_todo["description"] = todo["description"].strip()
    
    if "dueDate" in todo:
        validated_todo["dueDate"] = todo["dueDate"]
    
    if "assignee" in todo and isinstance(todo["assignee"], str):
        validated_todo["assignee"] = todo["assignee"].strip()
    
    return {"todo": validated_todo}

def _process_todo_list(todos):
    """Process and analyze the todo list."""
    # Count by status
    status_counts = {"pending": 0, "in_progress": 0, "completed": 0}
    
    # Count by priority
    priority_counts = {"high": 0, "medium": 0, "low": 0}
    
    # Detect duplicate IDs
    seen_ids = set()
    duplicate_ids = set()
    
    # Validate in_progress constraint (only one item should be in progress)
    in_progress_items = []
    
    for todo in todos:
        # Count status
        status_counts[todo["status"]] += 1
        
        # Count priority
        priority_counts[todo["priority"]] += 1
        
        # Check for duplicate IDs
        todo_id = todo["id"]
        if todo_id in seen_ids:
            duplicate_ids.add(todo_id)
        seen_ids.add(todo_id)
        
        # Track in_progress items
        if todo["status"] == "in_progress":
            in_progress_items.append(todo)
    
    # Generate warnings
    warnings = []
    if len(in_progress_items) > 1:
        warnings.append(f"Multiple items in progress ({len(in_progress_items)}). Consider focusing on one task at a time.")
    
    if duplicate_ids:
        warnings.append(f"Duplicate IDs found: {', '.join(duplicate_ids)}")
    
    # Calculate completion percentage
    total_items = len(todos)
    completed_items = status_counts["completed"]
    completion_percentage = (completed_items / total_items * 100) if total_items > 0 else 0
    
    # Generate summary
    summary = _generate_summary(todos, status_counts, priority_counts)
    
    return {
        "todos": todos,
        "totalItems": total_items,
        "statusCounts": status_counts,
        "priorityCounts": priority_counts,
        "completionPercentage": round(completion_percentage, 1),
        "summary": summary,
        "warnings": warnings,
        "lastUpdated": int(time.time()),
        "statistics": {
            "totalPending": status_counts["pending"],
            "totalInProgress": status_counts["in_progress"], 
            "totalCompleted": status_counts["completed"],
            "highPriority": priority_counts["high"],
            "mediumPriority": priority_counts["medium"],
            "lowPriority": priority_counts["low"]
        }
    }

def _generate_summary(todos, status_counts, priority_counts):
    """Generate a human-readable summary of the todo list."""
    total = len(todos)
    
    if total == 0:
        return "No todo items"
    
    summary_parts = []
    
    # Status summary
    if status_counts["completed"] > 0:
        summary_parts.append(f"{status_counts['completed']} completed")
    
    if status_counts["in_progress"] > 0:
        summary_parts.append(f"{status_counts['in_progress']} in progress")
    
    if status_counts["pending"] > 0:
        summary_parts.append(f"{status_counts['pending']} pending")
    
    # Priority summary for non-completed items
    active_items = status_counts["pending"] + status_counts["in_progress"]
    if active_items > 0:
        high_priority_active = len([t for t in todos if t["status"] in ["pending", "in_progress"] and t["priority"] == "high"])
        if high_priority_active > 0:
            summary_parts.append(f"{high_priority_active} high priority")
    
    summary = f"Total: {total} items - " + ", ".join(summary_parts)
    
    # Add completion status
    completion_pct = (status_counts["completed"] / total * 100) if total > 0 else 0
    if completion_pct == 100:
        summary += " ✅ All tasks completed!"
    elif completion_pct >= 75:
        summary += f" 🎯 {completion_pct:.0f}% complete"
    elif completion_pct >= 50:
        summary += f" 📈 {completion_pct:.0f}% complete"
    else:
        summary += f" 🚀 {completion_pct:.0f}% complete"
    
    return summary

def get_schema():
    """Return Fractalic-compatible JSON schema."""
    return {
        "name": "_todowrite",
        "description": "Manages and updates todo lists with structured task tracking. Use this tool to create and manage a structured task list for your current coding session. This helps you track progress, organize complex tasks, and demonstrate thoroughness to the user.",
        "parameters": {
            "type": "object",
            "properties": {
                "todos": {
                    "type": "array",
                    "description": "The updated todo list",
                    "items": {
                        "type": "object",
                        "properties": {
                            "content": {
                                "type": "string",
                                "description": "The todo item content/description",
                                "minLength": 1
                            },
                            "status": {
                                "type": "string",
                                "enum": ["pending", "in_progress", "completed"],
                                "description": "Current status of the todo item"
                            },
                            "priority": {
                                "type": "string",
                                "enum": ["high", "medium", "low"],
                                "description": "Priority level of the todo item"
                            },
                            "id": {
                                "type": "string",
                                "description": "Unique identifier for the todo item"
                            },
                            "tags": {
                                "type": "array",
                                "description": "Optional tags for categorization",
                                "items": {"type": "string"}
                            },
                            "description": {
                                "type": "string",
                                "description": "Optional detailed description"
                            },
                            "dueDate": {
                                "type": "string",
                                "description": "Optional due date (ISO format)"
                            },
                            "assignee": {
                                "type": "string",
                                "description": "Optional assignee name"
                            }
                        },
                        "required": ["content", "status", "priority", "id"],
                        "additionalProperties": False
                    }
                }
            },
            "required": ["todos"],
            "additionalProperties": False
        }
    }

def main():
    """Main entry point for the tool."""
    # Discovery test (REQUIRED)
    if len(sys.argv) == 2 and sys.argv[1] == '{"__test__": true}':
        print(json.dumps({"success": True, "_simple": True}))
        return
    
    # Schema dump (REQUIRED)
    if len(sys.argv) == 2 and sys.argv[1] == "--fractalic-dump-schema":
        print(json.dumps(get_schema(), indent=2))
        return
    
    # Main execution
    if len(sys.argv) != 2:
        print(json.dumps({"status": "error", "error": "Expected exactly one JSON argument"}))
        sys.exit(1)
    
    try:
        params = json.loads(sys.argv[1])
        if not isinstance(params, dict):
            raise ValueError("Input must be a JSON object")
        
        result = process_data(params)
        print(json.dumps(result, ensure_ascii=False))
        
        # Exit with appropriate code
        if result.get("status") == "error":
            sys.exit(1)
        
    except json.JSONDecodeError as e:
        print(json.dumps({"status": "error", "error": f"Invalid JSON input: {str(e)}"}))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"status": "error", "error": str(e)}))
        sys.exit(1)

if __name__ == "__main__":
    main()