#!/usr/bin/env python3
"""
HubSpot Data Relationship Mapper - Auto-Discovery Tool
Discovers hidden object relationships, data flows, and association patterns
Part of the Fractalic Process Mining Intelligence System
"""

import json
import sys
import os
from typing import Dict, List, Any, Optional, Set, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, Counter

# Add parent directories to sys.path to allow importing hubspot_hub_helpers
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'manage'))


def process_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Map data relationships and discover hidden connection patterns in HubSpot
    
    Args:
        data: Dictionary containing analysis parameters and filters
    
    Returns:
        Dict containing relationship maps, data flows, and connection insights
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
        
        # Extract parameters with defaults
        discovery_scope = data.get("discovery_scope", "comprehensive")
        relationship_depth = data.get("relationship_depth", 3)
        include_custom_objects = data.get("include_custom_objects", True)
        min_relationship_strength = data.get("min_relationship_strength", 0.1)
        max_objects_to_analyze = data.get("max_objects_to_analyze", 100)
        include_properties_analysis = data.get("include_properties_analysis", True)
        analysis_period_days = data.get("analysis_period_days", 30)
        
        client = hs_client()
        
        # Discover object schemas and structures
        schema_data = _discover_object_schemas(client, include_custom_objects)
        
        # Map direct associations
        association_map = _map_direct_associations(client, schema_data)
        
        # Discover hidden relationships through data patterns
        hidden_relationships = _discover_hidden_relationships(client, schema_data, relationship_depth)
        
        # Analyze data flow patterns
        data_flows = _analyze_data_flow_patterns(client, association_map, hidden_relationships)
        
        # Build comprehensive relationship graph
        relationship_graph = _build_relationship_graph(association_map, hidden_relationships, data_flows)
        
        # Generate relationship insights
        insights = _generate_relationship_insights(relationship_graph, schema_data)
        
        result = {
            "success": True,
            "analysis_type": "data_relationship_mapping",
            "timestamp": datetime.now().isoformat(),
            "parameters": {
                "discovery_scope": discovery_scope,
                "relationship_depth": relationship_depth,
                "include_custom_objects": include_custom_objects,
                "min_relationship_strength": min_relationship_strength,
                "max_objects_to_analyze": max_objects_to_analyze,
                "include_properties_analysis": include_properties_analysis,
                "analysis_period_days": analysis_period_days
            },
            "analysis_summary": {
                "objects_analyzed": len(schema_data.get("object_types", [])),
                "direct_associations_found": len(association_map.get("associations", [])),
                "hidden_relationships_discovered": len(hidden_relationships.get("patterns", [])),
                "relationship_strength_threshold": min_relationship_strength,
                "discovery_completeness": _calculate_discovery_completeness(schema_data, association_map)
            },
            "object_schemas": schema_data,
            "direct_associations": association_map,
            "hidden_relationships": hidden_relationships,
            "data_flows": data_flows,
            "relationship_graph": _serialize_graph(relationship_graph),
            "relationship_insights": insights
        }
        
        return result
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


def _discover_object_schemas(client, include_custom_objects: bool) -> Dict[str, Any]:
    """Discover all object schemas and their properties"""
    
    schema_data = {
        "object_types": [],
        "standard_objects": {},
        "custom_objects": {},
        "property_schemas": {},
        "object_relationships": {}
    }
    
    try:
        # Get all object schemas
        schemas_response = client.crm.schemas.core_api.get_all()
        
        for schema in schemas_response.results:
            object_type = schema.name
            schema_data["object_types"].append(object_type)
            
            # Categorize as standard or custom
            if schema.name in ["contacts", "companies", "deals", "tickets"]:
                schema_data["standard_objects"][object_type] = {
                    "id": schema.id,
                    "name": schema.name,
                    "labels": schema.labels,
                    "properties": []
                }
            elif include_custom_objects:
                schema_data["custom_objects"][object_type] = {
                    "id": schema.id,
                    "name": schema.name,
                    "labels": schema.labels,
                    "properties": []
                }
            
            # Get properties for each object type
            try:
                properties_response = client.crm.properties.core_api.get_all(object_type=object_type)
                properties = []
                
                for prop in properties_response.results:
                    properties.append({
                        "name": prop.name,
                        "label": prop.label,
                        "type": prop.type,
                        "field_type": prop.field_type,
                        "has_unique_value": getattr(prop, 'has_unique_value', False),
                        "referenced_object_type": getattr(prop, 'referenced_object_type', None)
                    })
                
                schema_data["property_schemas"][object_type] = properties
                
                # Add properties to object definition
                if object_type in schema_data["standard_objects"]:
                    schema_data["standard_objects"][object_type]["properties"] = properties
                elif object_type in schema_data["custom_objects"]:
                    schema_data["custom_objects"][object_type]["properties"] = properties
                    
            except Exception as e:
                print(f"Error getting properties for {object_type}: {e}")
                
    except Exception as e:
        print(f"Error discovering object schemas: {e}")
    
    return schema_data


def _map_direct_associations(client, schema_data: Dict[str, Any]) -> Dict[str, Any]:
    """Map direct associations between objects"""
    
    association_map = {
        "associations": [],
        "association_types": {},
        "association_counts": {},
        "bidirectional_associations": []
    }
    
    try:
        # Get association schema
        association_schema = client.crm.associations.v4.schema.definitions_api.get_all()
        
        for association in association_schema.results:
            from_object = association.from_object_type_id
            to_object = association.to_object_type_id
            association_type = association.name
            
            association_map["associations"].append({
                "from_object": from_object,
                "to_object": to_object,
                "association_type": association_type,
                "association_id": association.id
            })
            
            # Track association types
            key = f"{from_object}-{to_object}"
            if key not in association_map["association_types"]:
                association_map["association_types"][key] = []
            association_map["association_types"][key].append(association_type)
        
        # Discover actual association counts and strength
        association_map["association_counts"] = _count_actual_associations(client, association_map["associations"])
        
    except Exception as e:
        print(f"Error mapping direct associations: {e}")
    
    return association_map


def _discover_hidden_relationships(client, schema_data: Dict[str, Any], depth: int) -> Dict[str, Any]:
    """Discover hidden relationships through data pattern analysis"""
    
    hidden_relationships = {
        "patterns": [],
        "indirect_relationships": [],
        "data_correlation_patterns": [],
        "temporal_relationships": [],
        "property_correlations": []
    }
    
    object_types = schema_data.get("object_types", [])
    
    for object_type in object_types:
        try:
            # Sample data from each object type
            sample_data = _sample_object_data(client, object_type)
            
            # Analyze property correlations
            correlations = _analyze_property_correlations(sample_data, object_type)
            hidden_relationships["property_correlations"].extend(correlations)
            
            # Find indirect relationships through common properties
            indirect_rels = _find_indirect_relationships(client, object_type, sample_data, object_types)
            hidden_relationships["indirect_relationships"].extend(indirect_rels)
            
            # Analyze temporal relationships
            temporal_rels = _analyze_temporal_relationships(sample_data, object_type)
            hidden_relationships["temporal_relationships"].extend(temporal_rels)
            
        except Exception as e:
            print(f"Error analyzing hidden relationships for {object_type}: {e}")
    
    # Find cross-object patterns
    cross_patterns = _find_cross_object_patterns(client, object_types)
    hidden_relationships["patterns"].extend(cross_patterns)
    
    return hidden_relationships


def _analyze_data_flow_patterns(client, association_map: Dict, hidden_relationships: Dict) -> Dict[str, Any]:
    """Analyze how data flows between objects and processes"""
    
    data_flows = {
        "flow_patterns": [],
        "data_pipelines": [],
        "information_cascades": [],
        "update_propagation": [],
        "workflow_triggers": []
    }
    
    # Analyze association-based flows
    associations = association_map.get("associations", [])
    
    # Group associations by flow patterns
    flow_groups = defaultdict(list)
    for assoc in associations:
        flow_key = f"{assoc['from_object']}_{assoc['to_object']}"
        flow_groups[flow_key].append(assoc)
    
    # Analyze each flow pattern
    for flow_key, flow_associations in flow_groups.items():
        flow_pattern = _analyze_flow_pattern(client, flow_associations)
        if flow_pattern:
            data_flows["flow_patterns"].append(flow_pattern)
    
    # Identify data pipelines (multi-step flows)
    data_pipelines = _identify_data_pipelines(associations, hidden_relationships)
    data_flows["data_pipelines"].extend(data_pipelines)
    
    # Analyze information cascades
    cascades = _analyze_information_cascades(client, associations)
    data_flows["information_cascades"].extend(cascades)
    
    return data_flows


def _build_relationship_graph(association_map: Dict, hidden_relationships: Dict, data_flows: Dict) -> Dict[str, Any]:
    """Build a comprehensive relationship graph using simple data structures"""
    
    # Simple graph representation
    graph = {
        "nodes": set(),
        "edges": [],
        "adjacency": defaultdict(list)
    }
    
    # Add direct associations as edges
    for assoc in association_map.get("associations", []):
        from_obj = assoc["from_object"]
        to_obj = assoc["to_object"]
        
        graph["nodes"].add(from_obj)
        graph["nodes"].add(to_obj)
        
        edge = {
            "source": from_obj,
            "target": to_obj,
            "relationship_type": "direct",
            "association_type": assoc["association_type"],
            "strength": 1.0
        }
        
        graph["edges"].append(edge)
        graph["adjacency"][from_obj].append(to_obj)
    
    # Add hidden relationships as edges
    for pattern in hidden_relationships.get("patterns", []):
        if "from_object" in pattern and "to_object" in pattern:
            edge = {
                "source": pattern["from_object"],
                "target": pattern["to_object"],
                "relationship_type": "hidden",
                "pattern_type": pattern.get("type", "unknown"),
                "strength": pattern.get("strength", 0.5)
            }
            
            graph["edges"].append(edge)
            graph["adjacency"][pattern["from_object"]].append(pattern["to_object"])
    
    # Add data flow relationships
    for flow in data_flows.get("flow_patterns", []):
        if "source" in flow and "target" in flow:
            edge = {
                "source": flow["source"],
                "target": flow["target"],
                "relationship_type": "data_flow",
                "flow_type": flow.get("type", "unknown"),
                "strength": flow.get("strength", 0.3)
            }
            
            graph["edges"].append(edge)
            graph["adjacency"][flow["source"]].append(flow["target"])
    
    return graph


def _generate_relationship_insights(relationship_graph: Dict[str, Any], schema_data: Dict) -> Dict[str, Any]:
    """Generate insights from the relationship analysis"""
    
    insights = {
        "network_analysis": {},
        "key_objects": [],
        "relationship_gaps": [],
        "optimization_opportunities": [],
        "data_quality_issues": []
    }
    
    # Network analysis
    num_nodes = len(relationship_graph.get("nodes", []))
    num_edges = len(relationship_graph.get("edges", []))
    
    insights["network_analysis"] = {
        "total_nodes": num_nodes,
        "total_edges": num_edges,
        "density": num_edges / (num_nodes * (num_nodes - 1)) if num_nodes > 1 else 0,
        "average_connections_per_node": num_edges / num_nodes if num_nodes > 0 else 0
    }
    
    # Identify key objects (high degree)
    node_degrees = _calculate_node_degrees(relationship_graph)
    
    for node, degree in node_degrees.items():
        insights["key_objects"].append({
            "object_type": node,
            "degree": degree,
            "importance_score": degree / num_nodes if num_nodes > 0 else 0
        })
    
    # Sort by importance
    insights["key_objects"].sort(key=lambda x: x["importance_score"], reverse=True)
    
    # Identify relationship gaps
    standard_objects = schema_data.get("standard_objects", {}).keys()
    for obj1 in standard_objects:
        for obj2 in standard_objects:
            if obj1 != obj2 and not _has_edge(relationship_graph, obj1, obj2):
                # Check if there should be a relationship
                gap_strength = _calculate_relationship_gap_strength(obj1, obj2, schema_data)
                if gap_strength > 0.5:
                    insights["relationship_gaps"].append({
                        "from_object": obj1,
                        "to_object": obj2,
                        "gap_strength": gap_strength,
                        "suggested_relationship": _suggest_relationship_type(obj1, obj2)
                    })
    
    # Optimization opportunities
    insights["optimization_opportunities"] = _identify_optimization_opportunities(relationship_graph, schema_data)
    
    return insights


def _sample_object_data(client, object_type: str, sample_size: int = 100) -> List[Dict]:
    """Sample data from an object type for analysis"""
    try:
        if object_type == "contacts":
            response = client.crm.contacts.basic_api.get_page(limit=sample_size)
        elif object_type == "companies":
            response = client.crm.companies.basic_api.get_page(limit=sample_size)
        elif object_type == "deals":
            response = client.crm.deals.basic_api.get_page(limit=sample_size)
        elif object_type == "tickets":
            response = client.crm.tickets.basic_api.get_page(limit=sample_size)
        else:
            # For custom objects, use generic approach
            response = client.crm.objects.basic_api.get_page(object_type=object_type, limit=sample_size)
        
        return [obj.to_dict() if hasattr(obj, 'to_dict') else obj for obj in response.results]
    
    except Exception as e:
        print(f"Error sampling data for {object_type}: {e}")
        return []


def _analyze_property_correlations(sample_data: List[Dict], object_type: str) -> List[Dict]:
    """Analyze correlations between properties within an object type"""
    correlations = []
    
    if not sample_data:
        return correlations
    
    # Extract properties from sample data
    properties = {}
    for obj in sample_data:
        if hasattr(obj, 'properties'):
            for prop_name, prop_value in obj.properties.items():
                if prop_name not in properties:
                    properties[prop_name] = []
                properties[prop_name].append(prop_value)
    
    # Find correlations between properties
    prop_names = list(properties.keys())
    for i, prop1 in enumerate(prop_names):
        for prop2 in prop_names[i+1:]:
            correlation_strength = _calculate_property_correlation(properties[prop1], properties[prop2])
            if correlation_strength > 0.5:
                correlations.append({
                    "object_type": object_type,
                    "property1": prop1,
                    "property2": prop2,
                    "correlation_strength": correlation_strength,
                    "type": "property_correlation"
                })
    
    return correlations


def _find_indirect_relationships(client, object_type: str, sample_data: List, all_object_types: List) -> List[Dict]:
    """Find indirect relationships through common properties or patterns"""
    indirect_relationships = []
    
    # Look for properties that reference other object types
    for obj in sample_data[:10]:  # Limit for performance
        if hasattr(obj, 'properties'):
            for prop_name, prop_value in obj.properties.items():
                # Check if property value looks like an ID of another object
                if prop_value and isinstance(prop_value, str) and len(prop_value) > 8:
                    for other_object_type in all_object_types:
                        if other_object_type != object_type:
                            # Check if this might be a reference to the other object type
                            relationship_strength = _calculate_indirect_relationship_strength(
                                object_type, other_object_type, prop_name, prop_value
                            )
                            if relationship_strength > 0.3:
                                indirect_relationships.append({
                                    "from_object": object_type,
                                    "to_object": other_object_type,
                                    "relationship_type": "indirect",
                                    "via_property": prop_name,
                                    "strength": relationship_strength
                                })
    
    return indirect_relationships


def _analyze_temporal_relationships(sample_data: List, object_type: str) -> List[Dict]:
    """Analyze temporal relationships in the data"""
    temporal_relationships = []
    
    # Look for date/timestamp properties
    date_properties = []
    for obj in sample_data[:5]:
        if hasattr(obj, 'properties'):
            for prop_name, prop_value in obj.properties.items():
                if prop_value and ('date' in prop_name.lower() or 'time' in prop_name.lower()):
                    date_properties.append(prop_name)
    
    # Analyze temporal sequences
    for prop in date_properties:
        temporal_relationships.append({
            "object_type": object_type,
            "temporal_property": prop,
            "type": "temporal_sequence",
            "analysis": "timestamp_based_workflow"
        })
    
    return temporal_relationships


def _find_cross_object_patterns(client, object_types: List) -> List[Dict]:
    """Find patterns that span across multiple object types"""
    patterns = []
    
    # This is a simplified version - in practice, this would be much more sophisticated
    for i, obj_type1 in enumerate(object_types):
        for obj_type2 in object_types[i+1:]:
            pattern_strength = _calculate_cross_object_pattern_strength(obj_type1, obj_type2)
            if pattern_strength > 0.4:
                patterns.append({
                    "from_object": obj_type1,
                    "to_object": obj_type2,
                    "type": "cross_object_pattern",
                    "strength": pattern_strength,
                    "pattern_description": f"Common workflow pattern between {obj_type1} and {obj_type2}"
                })
    
    return patterns


def _count_actual_associations(client, associations: List) -> Dict[str, int]:
    """Count actual associations in the system"""
    counts = {}
    
    for assoc in associations:
        try:
            # This is a simplified count - in practice, you'd use the associations API
            # to get actual counts of associated records
            key = f"{assoc['from_object']}-{assoc['to_object']}"
            counts[key] = 0  # Placeholder - would implement actual counting
        except Exception as e:
            print(f"Error counting associations: {e}")
    
    return counts


def _analyze_flow_pattern(client, flow_associations: List) -> Optional[Dict]:
    """Analyze a specific flow pattern"""
    if not flow_associations:
        return None
    
    return {
        "source": flow_associations[0]["from_object"],
        "target": flow_associations[0]["to_object"],
        "type": "association_flow",
        "strength": len(flow_associations) / 10.0,  # Normalize
        "association_count": len(flow_associations)
    }


def _identify_data_pipelines(associations: List, hidden_relationships: Dict) -> List[Dict]:
    """Identify multi-step data pipelines"""
    pipelines = []
    
    # Simple pipeline detection - look for chains of associations
    # This would be much more sophisticated in practice
    association_chains = {}
    
    for assoc in associations:
        from_obj = assoc["from_object"]
        to_obj = assoc["to_object"]
        
        if from_obj not in association_chains:
            association_chains[from_obj] = []
        association_chains[from_obj].append(to_obj)
    
    # Find chains longer than 2
    for start_obj, targets in association_chains.items():
        if len(targets) > 1:
            pipelines.append({
                "pipeline_start": start_obj,
                "pipeline_steps": targets,
                "pipeline_length": len(targets),
                "type": "association_pipeline"
            })
    
    return pipelines


def _analyze_information_cascades(client, associations: List) -> List[Dict]:
    """Analyze information cascades through the system"""
    cascades = []
    
    # Placeholder for cascade analysis
    # Would analyze how information flows and amplifies through the system
    
    return cascades


def _serialize_graph(graph: Dict[str, Any]) -> Dict[str, Any]:
    """Serialize graph to JSON-serializable format"""
    return {
        "nodes": list(graph.get("nodes", [])),
        "edges": graph.get("edges", []),
        "node_count": len(graph.get("nodes", [])),
        "edge_count": len(graph.get("edges", []))
    }


def _calculate_node_degrees(graph: Dict[str, Any]) -> Dict[str, int]:
    """Calculate degree (number of connections) for each node"""
    degrees = {}
    
    # Initialize all nodes with degree 0
    for node in graph.get("nodes", []):
        degrees[node] = 0
    
    # Count connections for each node
    for edge in graph.get("edges", []):
        source = edge.get("source")
        target = edge.get("target")
        
        if source in degrees:
            degrees[source] += 1
        if target in degrees:
            degrees[target] += 1
    
    return degrees


def _has_edge(graph: Dict[str, Any], node1: str, node2: str) -> bool:
    """Check if there's an edge between two nodes"""
    for edge in graph.get("edges", []):
        if (edge.get("source") == node1 and edge.get("target") == node2) or \
           (edge.get("source") == node2 and edge.get("target") == node1):
            return True
    return False


def _calculate_discovery_completeness(schema_data: Dict, association_map: Dict) -> float:
    """Calculate completeness of the discovery process"""
    # Placeholder calculation
    objects_discovered = len(schema_data.get("object_types", []))
    associations_discovered = len(association_map.get("associations", []))
    
    # Simple completeness score
    return min((objects_discovered * associations_discovered) / 100.0, 1.0)


def _calculate_property_correlation(prop1_values: List, prop2_values: List) -> float:
    """Calculate correlation between two property value lists"""
    # Simplified correlation calculation
    # In practice, would use proper statistical correlation
    if not prop1_values or not prop2_values:
        return 0.0
    
    # Simple heuristic: if both properties have values in the same records
    both_have_values = sum(1 for v1, v2 in zip(prop1_values, prop2_values) if v1 and v2)
    total_records = len(prop1_values)
    
    return both_have_values / total_records if total_records > 0 else 0.0


def _calculate_indirect_relationship_strength(obj_type1: str, obj_type2: str, prop_name: str, prop_value: str) -> float:
    """Calculate strength of an indirect relationship"""
    # Simplified calculation based on naming patterns and property characteristics
    if obj_type2.lower() in prop_name.lower():
        return 0.8
    elif 'id' in prop_name.lower():
        return 0.6
    else:
        return 0.2


def _calculate_cross_object_pattern_strength(obj_type1: str, obj_type2: str) -> float:
    """Calculate strength of cross-object patterns"""
    # Simplified pattern strength calculation
    # Common object type pairs that typically have strong relationships
    strong_pairs = [
        ("contacts", "companies"),
        ("contacts", "deals"),
        ("deals", "companies"),
        ("tickets", "contacts")
    ]
    
    if (obj_type1, obj_type2) in strong_pairs or (obj_type2, obj_type1) in strong_pairs:
        return 0.9
    else:
        return 0.3


def _calculate_relationship_gap_strength(obj1: str, obj2: str, schema_data: Dict) -> float:
    """Calculate strength of a potential relationship gap"""
    # Simplified gap analysis
    expected_relationships = {
        ("contacts", "tickets"): 0.8,
        ("deals", "tickets"): 0.6,
        ("companies", "tickets"): 0.7
    }
    
    return expected_relationships.get((obj1, obj2), 0.0)


def _suggest_relationship_type(obj1: str, obj2: str) -> str:
    """Suggest the type of relationship that should exist"""
    if obj1 == "contacts" and obj2 == "tickets":
        return "contact_to_ticket"
    elif obj1 == "deals" and obj2 == "tickets":
        return "deal_to_ticket"
    else:
        return "suggested_association"


def _identify_optimization_opportunities(relationship_graph: Dict[str, Any], schema_data: Dict) -> List[Dict]:
    """Identify opportunities for relationship optimization"""
    opportunities = []
    
    # Find isolated nodes
    node_degrees = _calculate_node_degrees(relationship_graph)
    isolated_nodes = [node for node, degree in node_degrees.items() if degree == 0]
    
    if isolated_nodes:
        opportunities.append({
            "type": "isolated_objects",
            "objects": isolated_nodes,
            "recommendation": "Consider creating associations to connect these objects to the main workflow"
        })
    
    # Find objects with very high connectivity that might be over-connected
    if node_degrees:
        max_degree = max(node_degrees.values()) if node_degrees.values() else 0
        high_connectivity_threshold = max_degree * 0.8
        
        high_connectivity_nodes = [
            node for node, degree in node_degrees.items() 
            if degree > high_connectivity_threshold and degree > 5
        ]
        
        if high_connectivity_nodes:
            opportunities.append({
                "type": "high_connectivity",
                "objects": high_connectivity_nodes,
                "recommendation": "Review these highly connected objects for potential relationship simplification"
            })
    
    return opportunities


def get_schema() -> Dict[str, Any]:
    """Return the JSON schema for this tool's input parameters."""
    return {
        "type": "object",
        "properties": {
            "discovery_scope": {
                "type": "string",
                "description": "Scope of relationship discovery",
                "enum": ["basic", "comprehensive", "deep"],
                "default": "comprehensive"
            },
            "relationship_depth": {
                "type": "integer",
                "description": "Depth of relationship discovery (1-5)",
                "default": 3,
                "minimum": 1,
                "maximum": 5
            },
            "include_custom_objects": {
                "type": "boolean",
                "description": "Whether to include custom objects in analysis",
                "default": True
            },
            "min_relationship_strength": {
                "type": "number",
                "description": "Minimum strength threshold for relationships (0.0-1.0)",
                "default": 0.1,
                "minimum": 0.0,
                "maximum": 1.0
            },
            "max_objects_to_analyze": {
                "type": "integer",
                "description": "Maximum number of objects to analyze",
                "default": 100,
                "minimum": 10,
                "maximum": 500
            },
            "include_properties_analysis": {
                "type": "boolean",
                "description": "Whether to include property-level relationship analysis",
                "default": True
            },
            "analysis_period_days": {
                "type": "integer",
                "description": "Number of days of data to analyze for relationships",
                "default": 30,
                "minimum": 1,
                "maximum": 365
            },
            "hubspot_token": {
                "type": "string",
                "description": "HubSpot API token (required for live analysis)"
            }
        },
        "required": []
    }


def main():
    """Main function to handle CLI arguments and process data"""
    if len(sys.argv) > 1 and sys.argv[1] == "--fractalic-dump-schema":
        schema = {
            "description": "Discover hidden object relationships, data flows, and association patterns in HubSpot",
            "parameters": {
                "type": "object",
                "properties": {
                    "discovery_scope": {
                        "type": "string",
                        "description": "Scope of relationship discovery",
                        "enum": ["basic", "standard", "comprehensive"],
                        "default": "comprehensive"
                    },
                    "relationship_depth": {
                        "type": "integer",
                        "description": "Depth of relationship analysis (number of hops)",
                        "default": 3
                    },
                    "include_custom_objects": {
                        "type": "boolean",
                        "description": "Whether to include custom objects in analysis",
                        "default": True
                    },
                    "min_relationship_strength": {
                        "type": "number",
                        "description": "Minimum strength threshold for relationships (0-1)",
                        "default": 0.1
                    },
                    "analysis_period_days": {
                        "type": "integer",
                        "description": "Number of days to analyze for patterns",
                        "default": 30
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
            raise ValueError("No input data provided")
        
        data = json.loads(input_data)
        
        # Process the data
        result = process_data(data)
        print(json.dumps(result))
        result = process_data(data)
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
