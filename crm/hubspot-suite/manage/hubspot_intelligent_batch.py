#!/usr/bin/env python3
"""
HubSpot Intelligent Batch Processor - Smart batch operations with validation and fallbacks.
Maximizes batch efficiency while ensuring reliability with intelligent error handling.
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum


class DateTimeEncoder(json.JSONEncoder):
    """JSON encoder that handles datetime objects."""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


class FallbackStrategy(Enum):
    """Fallback strategies for failed batch operations."""
    INDIVIDUAL = "individual"  # Process items individually
    RETRY_BATCH = "retry_batch"  # Retry entire batch
    SKIP_FAILED = "skip_failed"  # Skip failed items
    PARTIAL_BATCH = "partial_batch"  # Try smaller batches


class BatchOperation:
    """Represents a single operation in a batch."""
    
    def __init__(self, operation_type: str, object_type: str, data: Dict[str, Any], operation_id: Optional[str] = None):
        self.operation_type = operation_type  # create, update, delete
        self.object_type = object_type  # contacts, deals, tickets, etc.
        self.data = data
        self.operation_id = operation_id or f"{operation_type}_{object_type}_{int(time.time())}"
        self.validated = False
        self.validation_errors = []
        self.result = None
        self.error = None


def group_operations(operations: List[BatchOperation]) -> Dict[str, List[BatchOperation]]:
    """Group operations by type and object for optimal batching."""
    groups = {}
    
    for op in operations:
        # Group by operation_type and object_type
        group_key = f"{op.operation_type}_{op.object_type}"
        if group_key not in groups:
            groups[group_key] = []
        groups[group_key].append(op)
    
    return groups


def validate_batch_operations(operations: List[BatchOperation], auto_validate: bool = True) -> Tuple[List[BatchOperation], List[BatchOperation]]:
    """Validate batch operations and return valid/invalid lists."""
    if not auto_validate:
        return operations, []
    
    try:
        from hubspot_smart_validator import process_data as validate_data
    except ImportError:
        # If validator not available, assume all valid
        return operations, []
    
    valid_operations = []
    invalid_operations = []
    
    for op in operations:
        # Determine operation type for validation
        validation_operation = "create" if op.operation_type == "create" else "update"
        
        validation_result = validate_data({
            "objectType": op.object_type,
            "operation": validation_operation,
            "properties": op.data.get("properties", {}),
            "validateTypes": True,
            "validateRequired": op.operation_type == "create",
            "autoDiscover": True
        })
        
        if validation_result.get("status") == "success":
            validation_info = validation_result.get("validation", {})
            if validation_info.get("validation_passed", False):
                op.validated = True
                valid_operations.append(op)
            else:
                op.validation_errors = validation_info.get("errors", [])
                invalid_operations.append(op)
        else:
            # If validation fails, treat as invalid but don't block
            op.validation_errors = [{"error": "validation_service_error", "message": validation_result.get("error", "Unknown validation error")}]
            invalid_operations.append(op)
    
    return valid_operations, invalid_operations


def execute_batch_group(operations: List[BatchOperation], max_batch_size: int = 100) -> List[BatchOperation]:
    """Execute a group of similar operations in batches."""
    if not operations:
        return []
    
    # Import HubSpot client
    try:
        from hubspot_hub_helpers import hs_client
    except ImportError:
        for op in operations:
            op.error = "HubSpot client not available"
        return operations
    
    cli = hs_client()
    first_op = operations[0]
    results = []
    
    # Process in chunks of max_batch_size
    for i in range(0, len(operations), max_batch_size):
        chunk = operations[i:i + max_batch_size]
        
        try:
            if first_op.operation_type == "create":
                batch_input = {
                    "inputs": [{"properties": op.data.get("properties", {})} for op in chunk]
                }
                
                if first_op.object_type == "contacts":
                    response = cli.crm.contacts.batch_api.create(batch_input)
                elif first_op.object_type == "deals":
                    response = cli.crm.deals.batch_api.create(batch_input)
                elif first_op.object_type == "tickets":
                    response = cli.crm.tickets.batch_api.create(batch_input)
                elif first_op.object_type == "companies":
                    response = cli.crm.companies.batch_api.create(batch_input)
                elif first_op.object_type == "products":
                    response = cli.crm.products.batch_api.create(batch_input)
                elif first_op.object_type == "line_items":
                    response = cli.crm.line_items.batch_api.create(batch_input)
                elif first_op.object_type == "quotes":
                    response = cli.crm.quotes.batch_api.create(batch_input)
                else:
                    # Generic object handling
                    response = cli.crm.objects.batch_api.create(object_type=first_op.object_type, batch_input_simple_public_object_batch_input=batch_input)
                
                # Process successful results
                if hasattr(response, 'results'):
                    for j, result in enumerate(response.results):
                        if j < len(chunk):
                            chunk[j].result = {
                                "id": result.id,
                                "properties": result.properties,
                                "created_at": getattr(result, 'created_at', None),
                                "updated_at": getattr(result, 'updated_at', None)
                            }
                
                # Handle errors if any
                if hasattr(response, 'errors') and response.errors:
                    for error in response.errors:
                        error_index = getattr(error, 'index', 0)
                        if error_index < len(chunk):
                            chunk[error_index].error = error.message
            
            elif first_op.operation_type == "update":
                batch_input = {
                    "inputs": [
                        {
                            "id": op.data.get("id"),
                            "properties": op.data.get("properties", {})
                        } for op in chunk if op.data.get("id")
                    ]
                }
                
                # Use specific APIs for standard objects, generic API for others
                standard_objects = ["contacts", "deals", "tickets", "companies", "products", "line_items", "quotes"]
                
                if first_op.object_type in standard_objects:
                    # Use specific batch API
                    if first_op.object_type == "contacts":
                        response = cli.crm.contacts.batch_api.update(batch_input)
                    elif first_op.object_type == "deals":
                        response = cli.crm.deals.batch_api.update(batch_input)
                    elif first_op.object_type == "tickets":
                        response = cli.crm.tickets.batch_api.update(batch_input)
                    elif first_op.object_type == "companies":
                        response = cli.crm.companies.batch_api.update(batch_input)
                    elif first_op.object_type == "products":
                        response = cli.crm.products.batch_api.update(batch_input)
                    elif first_op.object_type == "line_items":
                        response = cli.crm.line_items.batch_api.update(batch_input)
                    elif first_op.object_type == "quotes":
                        response = cli.crm.quotes.batch_api.update(batch_input)
                else:
                    # Use generic objects API for engagements and custom objects
                    response = cli.crm.objects.batch_api.update(object_type=first_op.object_type, batch_input_simple_public_object_batch_input=batch_input)
                
                # Process results similar to create
                if hasattr(response, 'results'):
                    for j, result in enumerate(response.results):
                        if j < len(chunk):
                            chunk[j].result = {
                                "id": result.id,
                                "properties": result.properties,
                                "updated_at": getattr(result, 'updated_at', None)
                            }
                
                if hasattr(response, 'errors') and response.errors:
                    for error in response.errors:
                        error_index = getattr(error, 'index', 0)
                        if error_index < len(chunk):
                            chunk[error_index].error = error.message
        
        except Exception as e:
            # Batch failed, mark all operations in chunk as failed
            for op in chunk:
                op.error = f"Batch operation failed: {str(e)}"
        
        results.extend(chunk)
    
    return results


def execute_individual_operations(operations: List[BatchOperation]) -> List[BatchOperation]:
    """Execute operations individually as fallback."""
    try:
        from hubspot_hub_helpers import hs_client
    except ImportError:
        for op in operations:
            op.error = "HubSpot client not available"
        return operations
    
    cli = hs_client()
    
    for op in operations:
        try:
            if op.operation_type == "create":
                input_data = {"properties": op.data.get("properties", {})}
                
                # Use specific APIs for standard objects, generic API for others
                standard_objects = ["contacts", "deals", "tickets", "companies", "products", "line_items", "quotes"]
                
                if op.object_type in standard_objects:
                    if op.object_type == "contacts":
                        result = cli.crm.contacts.basic_api.create(input_data)
                    elif op.object_type == "deals":
                        result = cli.crm.deals.basic_api.create(input_data)
                    elif op.object_type == "tickets":
                        result = cli.crm.tickets.basic_api.create(input_data)
                    elif op.object_type == "companies":
                        result = cli.crm.companies.basic_api.create(input_data)
                    elif op.object_type == "products":
                        result = cli.crm.products.basic_api.create(input_data)
                    elif op.object_type == "line_items":
                        result = cli.crm.line_items.basic_api.create(input_data)
                    elif op.object_type == "quotes":
                        result = cli.crm.quotes.basic_api.create(input_data)
                else:
                    # Use generic objects API for engagements and custom objects
                    result = cli.crm.objects.basic_api.create(object_type=op.object_type, simple_public_object_input_for_create=input_data)
                
                op.result = {
                    "id": result.id,
                    "properties": result.properties,
                    "created_at": getattr(result, 'created_at', None)
                }
            
            elif op.operation_type == "update":
                object_id = op.data.get("id")
                properties = op.data.get("properties", {})
                
                if not object_id:
                    op.error = "Missing object ID for update operation"
                    continue
                
                # Use specific APIs for standard objects, generic API for others
                standard_objects = ["contacts", "deals", "tickets", "companies", "products", "line_items", "quotes"]
                
                if op.object_type in standard_objects:
                    if op.object_type == "contacts":
                        result = cli.crm.contacts.basic_api.update(object_id, {"properties": properties})
                    elif op.object_type == "deals":
                        result = cli.crm.deals.basic_api.update(object_id, {"properties": properties})
                    elif op.object_type == "tickets":
                        result = cli.crm.tickets.basic_api.update(object_id, {"properties": properties})
                    elif op.object_type == "companies":
                        result = cli.crm.companies.basic_api.update(object_id, {"properties": properties})
                    elif op.object_type == "products":
                        result = cli.crm.products.basic_api.update(object_id, {"properties": properties})
                    elif op.object_type == "line_items":
                        result = cli.crm.line_items.basic_api.update(object_id, {"properties": properties})
                    elif op.object_type == "quotes":
                        result = cli.crm.quotes.basic_api.update(object_id, {"properties": properties})
                else:
                    # Use generic objects API for engagements and custom objects
                    result = cli.crm.objects.basic_api.update(object_type=op.object_type, object_id=object_id, simple_public_object_input_for_update={"properties": properties})
                
                op.result = {
                    "id": result.id,
                    "properties": result.properties,
                    "updated_at": getattr(result, 'updated_at', None)
                }
        
        except Exception as e:
            op.error = f"Individual operation failed: {str(e)}"
    
    return operations


def process_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Intelligent batch processor for HubSpot operations.
    """
    try:
        operations_data = data.get("operations", [])
        auto_validate = data.get("autoValidate", True)
        fallback_strategy = data.get("fallbackStrategy", "individual")
        max_batch_size = data.get("maxBatchSize", 100)
        retry_failed = data.get("retryFailed", True)
        
        if not operations_data:
            return {"error": "operations parameter is required"}
        
        # Convert input data to BatchOperation objects
        operations = []
        for i, op_data in enumerate(operations_data):
            operation = BatchOperation(
                operation_type=op_data.get("operationType", "create"),
                object_type=op_data.get("objectType", "contacts"),
                data=op_data.get("data", {}),
                operation_id=op_data.get("operationId", f"op_{i}")
            )
            operations.append(operation)
        
        # Validate operations if requested
        if auto_validate:
            valid_operations, invalid_operations = validate_batch_operations(operations, auto_validate)
        else:
            valid_operations = operations
            invalid_operations = []
        
        # Group operations for optimal batching
        operation_groups = group_operations(valid_operations)
        
        # Execute each group
        processed_operations = []
        failed_operations = []
        
        for group_key, group_ops in operation_groups.items():
            # Try batch execution first
            batch_results = execute_batch_group(group_ops, max_batch_size)
            
            # Check for failures and apply fallback strategy
            batch_failed = [op for op in batch_results if op.error and not op.result]
            batch_succeeded = [op for op in batch_results if op.result]
            
            processed_operations.extend(batch_succeeded)
            
            # Handle failures based on strategy
            if batch_failed and retry_failed:
                if fallback_strategy == "individual":
                    # Retry failed operations individually
                    individual_results = execute_individual_operations(batch_failed)
                    processed_operations.extend(individual_results)
                
                elif fallback_strategy == "retry_batch":
                    # Retry as smaller batches
                    smaller_batch_size = max(1, len(batch_failed) // 2)
                    retry_results = execute_batch_group(batch_failed, smaller_batch_size)
                    processed_operations.extend(retry_results)
                
                elif fallback_strategy == "skip_failed":
                    # Just record failures
                    failed_operations.extend(batch_failed)
                
                else:  # partial_batch
                    # Try progressively smaller batches
                    remaining_failed = batch_failed[:]
                    current_batch_size = max(1, len(remaining_failed) // 2)
                    
                    while remaining_failed and current_batch_size >= 1:
                        retry_results = execute_batch_group(remaining_failed[:current_batch_size], current_batch_size)
                        retry_succeeded = [op for op in retry_results if op.result]
                        retry_failed_ops = [op for op in retry_results if op.error and not op.result]
                        
                        processed_operations.extend(retry_succeeded)
                        remaining_failed = retry_failed_ops
                        current_batch_size = max(1, current_batch_size // 2)
                    
                    failed_operations.extend(remaining_failed)
            else:
                failed_operations.extend(batch_failed)
        
        # Add invalid operations to failed list
        failed_operations.extend(invalid_operations)
        
        # Compile results
        total_operations = len(operations)
        successful_operations = len([op for op in processed_operations if op.result])
        failed_operation_count = len(failed_operations)
        
        return {
            "status": "success",
            "summary": {
                "total_operations": total_operations,
                "successful_operations": successful_operations,
                "failed_operations": failed_operation_count,
                "validation_failed": len(invalid_operations),
                "fallback_strategy_used": fallback_strategy if failed_operations else None
            },
            "results": [
                {
                    "operation_id": op.operation_id,
                    "operation_type": op.operation_type,
                    "object_type": op.object_type,
                    "status": "success" if op.result else "failed",
                    "result": op.result,
                    "error": op.error,
                    "validation_errors": op.validation_errors
                } for op in processed_operations + failed_operations
            ]
        }
    
    except Exception as e:
        return {"error": f"Batch processing error: {str(e)}"}


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Test mode for autodiscovery (REQUIRED)
        if sys.argv[1] == '{"__test__": true}':
            print(json.dumps({"success": True, "_simple": True}))
        # Schema dump for Fractalic integration
        elif sys.argv[1] == "--fractalic-dump-schema":
            schema = {
                "description": "Intelligent batch processor for HubSpot operations with smart fallbacks and validation. Maximizes efficiency while ensuring reliability.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "operations": {
                            "type": "array",
                            "description": "Array of operations to process in batches",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "operationType": {
                                        "type": "string",
                                        "enum": ["create", "update", "delete"],
                                        "description": "Type of operation to perform"
                                    },
                                    "objectType": {
                                        "type": "string",
                                        "description": "Type of HubSpot object. Supports all CRM objects including standard (contacts, deals, tickets, companies), commerce (products, line_items, quotes), engagements (calls, emails, meetings, notes, tasks, communications, postal_mail), and custom objects.",
                                        "examples": ["contacts", "deals", "tickets", "companies", "products", "line_items", "quotes", "calls", "emails", "meetings", "notes", "tasks", "communications", "postal_mail"]
                                    },
                                    "data": {
                                        "type": "object",
                                        "description": "Operation data (properties for create/update, id for update/delete)"
                                    },
                                    "operationId": {
                                        "type": "string",
                                        "description": "Optional unique identifier for the operation"
                                    }
                                },
                                "required": ["operationType", "objectType", "data"]
                            }
                        },
                        "autoValidate": {
                            "type": "boolean",
                            "description": "Automatically validate operations before execution",
                            "default": True
                        },
                        "fallbackStrategy": {
                            "type": "string",
                            "description": "Strategy for handling failed batch operations",
                            "enum": ["individual", "retry_batch", "skip_failed", "partial_batch"],
                            "default": "individual"
                        },
                        "maxBatchSize": {
                            "type": "integer",
                            "description": "Maximum number of operations per batch",
                            "default": 100
                        },
                        "retryFailed": {
                            "type": "boolean",
                            "description": "Whether to retry failed operations using fallback strategy",
                            "default": True
                        }
                    },
                    "required": ["operations"]
                },
                "examples": [
                    {
                        "description": "Batch create contacts with fallback",
                        "input": {
                            "operations": [
                                {
                                    "operationType": "create",
                                    "objectType": "contacts",
                                    "data": {"properties": {"email": "user1@example.com", "firstname": "John"}},
                                    "operationId": "contact_1"
                                },
                                {
                                    "operationType": "create", 
                                    "objectType": "contacts",
                                    "data": {"properties": {"email": "user2@example.com", "firstname": "Jane"}},
                                    "operationId": "contact_2"
                                }
                            ],
                            "autoValidate": True,
                            "fallbackStrategy": "individual"
                        }
                    }
                ]
            }
            print(json.dumps(schema, indent=2))
        else:
            try:
                input_data = json.loads(sys.argv[1])
                result = process_data(input_data)
                print(json.dumps(result, indent=2, cls=DateTimeEncoder))
            except json.JSONDecodeError as e:
                print(json.dumps({"error": f"Invalid JSON input: {str(e)}"}))
            except Exception as e:
                print(json.dumps({"error": f"Execution error: {str(e)}"}))
    else:
        print(json.dumps({"error": "No input data provided"}))
