#!/usr/bin/env python3
"""
HubSpot Smart Validator - Pre-flight data validation using cached schemas.
Prevents API errors by validating data against HubSpot schemas before API calls.
"""
from __future__ import annotations

import json
import sys
from typing import Any, Dict, List, Optional, Tuple, Set
import re
from difflib import get_close_matches


def get_property_suggestions(invalid_property: str, valid_properties: List[str], max_suggestions: int = 3) -> List[str]:
    """Get suggestions for invalid property names."""
    # Use difflib to find close matches
    suggestions = get_close_matches(invalid_property, valid_properties, n=max_suggestions, cutoff=0.6)
    
    # Add common property mappings
    common_mappings = {
        "stage": ["hs_pipeline_stage", "dealstage"],
        "status": ["hs_pipeline_stage", "hs_ticket_priority"],
        "pipeline_stage": ["hs_pipeline_stage"],
        "deal_stage": ["dealstage"],
        "ticket_stage": ["hs_pipeline_stage"],
        "priority": ["hs_ticket_priority"],
        "owner": ["hubspot_owner_id"],
        "assigned_to": ["hubspot_owner_id"],
        "title": ["subject", "dealname", "hs_task_subject"],
        "description": ["content", "hs_task_body"],
        "name": ["dealname", "firstname", "lastname"],
        "email_address": ["email"],
        "phone_number": ["phone"],
        "company_name": ["company"],
    }
    
    if invalid_property.lower() in common_mappings:
        mapped_suggestions = [prop for prop in common_mappings[invalid_property.lower()] if prop in valid_properties]
        suggestions.extend(mapped_suggestions)
    
    # Remove duplicates while preserving order
    seen = set()
    unique_suggestions = []
    for suggestion in suggestions:
        if suggestion not in seen:
            seen.add(suggestion)
            unique_suggestions.append(suggestion)
    
    return unique_suggestions[:max_suggestions]


def validate_property_types(properties: Dict[str, Any], property_schemas: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Validate property data types against schema."""
    validation_errors = []
    
    for prop_name, prop_value in properties.items():
        if prop_name not in property_schemas:
            continue
        
        schema = property_schemas[prop_name]
        expected_type = schema.get("type", "string")
        field_type = schema.get("fieldType", "text")
        
        # Type validation
        if expected_type == "string" and not isinstance(prop_value, str):
            if prop_value is not None:  # Allow None for optional fields
                validation_errors.append({
                    "property": prop_name,
                    "error": "type_mismatch",
                    "expected": "string",
                    "actual": type(prop_value).__name__,
                    "suggestion": f"Convert to string: '{str(prop_value)}'"
                })
        
        elif expected_type == "number" and not isinstance(prop_value, (int, float)):
            if prop_value is not None:
                try:
                    float(str(prop_value))
                except ValueError:
                    validation_errors.append({
                        "property": prop_name,
                        "error": "type_mismatch",
                        "expected": "number",
                        "actual": type(prop_value).__name__,
                        "suggestion": f"Ensure '{prop_value}' is a valid number"
                    })
        
        elif expected_type == "bool" and not isinstance(prop_value, bool):
            if prop_value is not None:
                validation_errors.append({
                    "property": prop_name,
                    "error": "type_mismatch",
                    "expected": "boolean",
                    "actual": type(prop_value).__name__,
                    "suggestion": f"Use true/false instead of '{prop_value}'"
                })
        
        elif expected_type == "datetime" and isinstance(prop_value, str):
            # Validate datetime format
            datetime_patterns = [
                r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{3})?Z?$',  # ISO format
                r'^\d{10}$',  # Unix timestamp (10 digits)
                r'^\d{13}$',  # Unix timestamp milliseconds (13 digits)
            ]
            
            if not any(re.match(pattern, str(prop_value)) for pattern in datetime_patterns):
                validation_errors.append({
                    "property": prop_name,
                    "error": "invalid_datetime_format",
                    "value": prop_value,
                    "suggestion": "Use ISO format (YYYY-MM-DDTHH:mm:ss.sssZ) or Unix timestamp"
                })
        
        # Email validation
        if field_type == "email" and isinstance(prop_value, str):
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, prop_value):
                validation_errors.append({
                    "property": prop_name,
                    "error": "invalid_email_format",
                    "value": prop_value,
                    "suggestion": "Ensure email is in valid format (user@domain.com)"
                })
        
        # Enumeration validation
        if "options" in schema and prop_value is not None:
            valid_options = [opt.get("value") for opt in schema["options"]]
            if prop_value not in valid_options:
                close_matches = get_close_matches(str(prop_value), [str(opt) for opt in valid_options], n=2, cutoff=0.6)
                validation_errors.append({
                    "property": prop_name,
                    "error": "invalid_option",
                    "value": prop_value,
                    "valid_options": valid_options,
                    "suggestions": close_matches
                })
    
    return validation_errors


def validate_required_properties(properties: Dict[str, Any], required_properties: List[str]) -> List[Dict[str, Any]]:
    """Validate that required properties are present."""
    validation_errors = []
    
    for required_prop in required_properties:
        if required_prop not in properties or properties[required_prop] is None or properties[required_prop] == "":
            validation_errors.append({
                "property": required_prop,
                "error": "required_property_missing",
                "suggestion": f"Property '{required_prop}' is required and cannot be empty"
            })
    
    return validation_errors


def process_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Smart validation tool for HubSpot data.
    """
    try:
        # Import here to avoid circular dependencies
        from hubspot_schema_cache import get_cache
        from hubspot_properties_discover import process_data as discover_properties
        from hubspot_pipelines_discover import process_data as discover_pipelines
        
        object_type = data.get("objectType")
        operation = data.get("operation", "create")  # create, update, search
        properties = data.get("properties", {})
        validate_types = data.get("validateTypes", True)
        validate_required = data.get("validateRequired", True)
        auto_discover = data.get("autoDiscover", True)
        
        if not object_type:
            return {"error": "objectType parameter is required"}
        
        if not properties:
            return {"error": "properties parameter is required"}
        
        cache = get_cache()
        validation_results = {
            "object_type": object_type,
            "operation": operation,
            "validation_passed": True,
            "errors": [],
            "warnings": [],
            "suggestions": []
        }
        
        # Get cached property schema
        cached_properties = cache.get_properties(object_type, mode="detail")
        
        if not cached_properties and auto_discover:
            # Auto-discover properties if not cached
            discover_result = discover_properties({
                "objectType": object_type,
                "mode": "detail"
            })
            
            if discover_result.get("status") == "success":
                cached_properties = discover_result
                # Cache the discovered properties
                cache.set_properties(object_type, cached_properties, mode="detail")
        
        if not cached_properties:
            return {
                "error": f"Could not retrieve property schema for {object_type}. Enable autoDiscover or populate cache first."
            }
        
        # Extract property schemas and required properties
        property_schemas = {}
        required_properties = []
        valid_property_names = []
        
        if "properties" in cached_properties:
            # Handle both list and dict formats for properties
            if isinstance(cached_properties["properties"], dict):
                # New format: properties is a dict with property name as key
                for prop_name, prop in cached_properties["properties"].items():
                    property_schemas[prop_name] = prop
                    valid_property_names.append(prop_name)
                    
                    # Check if property is required (for create operations)
                    if operation == "create" and prop.get("required", False):
                        required_properties.append(prop_name)
            else:
                # Old format: properties is a list of property objects
                for prop in cached_properties["properties"]:
                    prop_name = prop.get("name")
                    if prop_name:
                        property_schemas[prop_name] = prop
                        valid_property_names.append(prop_name)
                        
                        # Check if property is required (for create operations)
                        if operation == "create" and prop.get("required", False):
                            required_properties.append(prop_name)
        
        # Validate property names
        invalid_properties = []
        for prop_name in properties.keys():
            if prop_name not in valid_property_names:
                suggestions = get_property_suggestions(prop_name, valid_property_names)
                invalid_properties.append({
                    "property": prop_name,
                    "error": "invalid_property_name",
                    "suggestions": suggestions
                })
        
        if invalid_properties:
            validation_results["validation_passed"] = False
            validation_results["errors"].extend(invalid_properties)
        
        # Validate required properties
        if validate_required and operation == "create":
            required_errors = validate_required_properties(properties, required_properties)
            if required_errors:
                validation_results["validation_passed"] = False
                validation_results["errors"].extend(required_errors)
        
        # Validate property types
        if validate_types:
            type_errors = validate_property_types(properties, property_schemas)
            if type_errors:
                validation_results["validation_passed"] = False
                validation_results["errors"].extend(type_errors)
        
        # Add general suggestions
        if object_type in ["tickets", "deals"] and validation_results["validation_passed"]:
            # Suggest pipeline validation for tickets and deals
            if object_type == "tickets" and "hs_pipeline_stage" in properties:
                validation_results["suggestions"].append({
                    "type": "pipeline_validation",
                    "message": f"Consider validating pipeline stage '{properties['hs_pipeline_stage']}' using hubspot_pipelines_discover"
                })
            elif object_type == "deals" and "dealstage" in properties:
                validation_results["suggestions"].append({
                    "type": "pipeline_validation",
                    "message": f"Consider validating deal stage '{properties['dealstage']}' using hubspot_pipelines_discover"
                })
        
        # Success response
        validation_results["total_errors"] = len(validation_results["errors"])
        validation_results["total_warnings"] = len(validation_results["warnings"])
        validation_results["total_suggestions"] = len(validation_results["suggestions"])
        
        return {
            "status": "success",
            "validation": validation_results
        }
    
    except Exception as e:
        return {"error": f"Validation error: {str(e)}"}


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Test mode for autodiscovery (REQUIRED)
        if sys.argv[1] == '{"__test__": true}':
            print(json.dumps({"success": True, "_simple": True}))
        # Schema dump for Fractalic integration
        elif sys.argv[1] == "--fractalic-dump-schema":
            schema = {
                "description": "Smart validation tool for HubSpot data with pre-flight checks and intelligent error correction.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "objectType": {
                            "type": "string",
                            "description": "Type of HubSpot object to validate. Supports all CRM objects including standard (contacts, deals, tickets, companies), commerce (products, line_items, quotes), engagements (calls, emails, meetings, notes, tasks, communications, postal_mail), and custom objects.",
                            "examples": ["contacts", "deals", "tickets", "companies", "products", "line_items", "quotes", "calls", "emails", "meetings", "notes", "tasks", "communications", "postal_mail"]
                        },
                        "operation": {
                            "type": "string",
                            "description": "Type of operation for validation context",
                            "enum": ["create", "update", "search"],
                            "default": "create"
                        },
                        "properties": {
                            "type": "object",
                            "description": "Object properties to validate against HubSpot schema"
                        },
                        "validateTypes": {
                            "type": "boolean",
                            "description": "Whether to validate property data types",
                            "default": True
                        },
                        "validateRequired": {
                            "type": "boolean", 
                            "description": "Whether to validate required properties",
                            "default": True
                        },
                        "autoDiscover": {
                            "type": "boolean",
                            "description": "Automatically discover schemas if not cached",
                            "default": True
                        }
                    },
                    "required": ["objectType", "properties"]
                },
                "examples": [
                    {
                        "description": "Validate contact creation data",
                        "input": {
                            "objectType": "contacts",
                            "operation": "create", 
                            "properties": {
                                "email": "user@example.com",
                                "firstname": "John",
                                "lastname": "Doe"
                            }
                        }
                    },
                    {
                        "description": "Validate ticket with error detection",
                        "input": {
                            "objectType": "tickets",
                            "operation": "create",
                            "properties": {
                                "subject": "Support Request",
                                "stage": "new",
                                "invalid_property": "test"
                            }
                        }
                    }
                ]
            }
            print(json.dumps(schema, indent=2))
        else:
            try:
                input_data = json.loads(sys.argv[1])
                result = process_data(input_data)
                print(json.dumps(result, indent=2))
            except json.JSONDecodeError as e:
                print(json.dumps({"error": f"Invalid JSON input: {str(e)}"}))
            except Exception as e:
                print(json.dumps({"error": f"Execution error: {str(e)}"}))
    else:
        print(json.dumps({"error": "No input data provided"}))
