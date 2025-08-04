#!/usr/bin/env python3
"""
HubSpot Graph Visualizer - Auto-Discovery Tool
Visualizes process flows, relationships, and data connections as graphs
Part of the Fractalic Process Mining Intelligence System
"""

import json
import sys
from typing import Dict, List, Any, Optional
from datetime import datetime


def process_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate graph visualizations from HubSpot process and relationship data
    
    Returns:
        Dict containing graph visualization data and metadata
    """
    
    # Handle test mode early
    if data.get("__test__") is True:
        return {"success": True, "_simple": True}
    
    try:
        # Extract parameters with defaults
        graph_type = data.get("graph_type", "process_flow")
        visualization_format = data.get("visualization_format", "json")
        include_labels = data.get("include_labels", True)
        max_nodes = data.get("max_nodes", 100)
        
        # Input data for visualization
        nodes_data = data.get("nodes", [])
        edges_data = data.get("edges", [])
        
        # Generate visualization based on type
        if graph_type == "process_flow":
            graph_data = _generate_process_flow_graph(nodes_data, edges_data, include_labels)
        elif graph_type == "relationship_map":
            graph_data = _generate_relationship_map(nodes_data, edges_data, include_labels)
        elif graph_type == "organizational_chart":
            graph_data = _generate_organizational_chart(nodes_data, edges_data, include_labels)
        else:
            graph_data = _generate_generic_graph(nodes_data, edges_data, include_labels)
        
        # Apply node limit if specified
        if max_nodes and len(graph_data.get("nodes", [])) > max_nodes:
            graph_data = _limit_graph_size(graph_data, max_nodes)
        
        # Format visualization output
        visualization_output = _format_visualization(graph_data, visualization_format)
        
        result = {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "graph_type": graph_type,
            "visualization_format": visualization_format,
            "graph_data": graph_data,
            "visualization_output": visualization_output,
            "metadata": {
                "total_nodes": len(graph_data.get("nodes", [])),
                "total_edges": len(graph_data.get("edges", [])),
                "labels_included": include_labels,
                "size_limited": max_nodes and len(nodes_data) > max_nodes
            }
        }
        
        return result
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


def _generate_process_flow_graph(nodes: List[Dict], edges: List[Dict], include_labels: bool) -> Dict[str, Any]:
    """Generate a process flow graph visualization"""
    
    graph_nodes = []
    graph_edges = []
    
    # Process nodes
    for i, node in enumerate(nodes):
        graph_node = {
            "id": node.get("id", f"node_{i}"),
            "type": "process_step",
            "shape": "rectangle",
            "color": "#4A90E2"
        }
        
        if include_labels:
            graph_node["label"] = node.get("name", node.get("id", f"Step {i+1}"))
            
        graph_nodes.append(graph_node)
    
    # Process edges
    for edge in edges:
        graph_edge = {
            "from": edge.get("from", edge.get("source")),
            "to": edge.get("to", edge.get("target")),
            "type": "flow",
            "arrow": True,
            "color": "#666666"
        }
        
        if include_labels and edge.get("label"):
            graph_edge["label"] = edge["label"]
            
        graph_edges.append(graph_edge)
    
    return {
        "type": "process_flow",
        "nodes": graph_nodes,
        "edges": graph_edges,
        "layout": "hierarchical"
    }


def _generate_relationship_map(nodes: List[Dict], edges: List[Dict], include_labels: bool) -> Dict[str, Any]:
    """Generate a relationship map visualization"""
    
    graph_nodes = []
    graph_edges = []
    
    # Process nodes with different colors by type
    node_colors = {
        "contact": "#E74C3C",
        "company": "#3498DB", 
        "deal": "#2ECC71",
        "ticket": "#F39C12",
        "default": "#95A5A6"
    }
    
    for i, node in enumerate(nodes):
        node_type = node.get("type", "default")
        graph_node = {
            "id": node.get("id", f"node_{i}"),
            "type": node_type,
            "shape": "circle",
            "color": node_colors.get(node_type, node_colors["default"])
        }
        
        if include_labels:
            graph_node["label"] = node.get("name", node.get("id", f"Node {i+1}"))
            
        graph_nodes.append(graph_node)
    
    # Process edges
    for edge in edges:
        graph_edge = {
            "from": edge.get("from", edge.get("source")),
            "to": edge.get("to", edge.get("target")),
            "type": "relationship",
            "color": "#BDC3C7"
        }
        
        if include_labels and edge.get("relationship_type"):
            graph_edge["label"] = edge["relationship_type"]
            
        graph_edges.append(graph_edge)
    
    return {
        "type": "relationship_map",
        "nodes": graph_nodes,
        "edges": graph_edges,
        "layout": "force_directed"
    }


def _generate_organizational_chart(nodes: List[Dict], edges: List[Dict], include_labels: bool) -> Dict[str, Any]:
    """Generate an organizational chart visualization"""
    
    graph_nodes = []
    graph_edges = []
    
    # Process nodes
    for i, node in enumerate(nodes):
        graph_node = {
            "id": node.get("id", f"node_{i}"),
            "type": "person",
            "shape": "box",
            "color": "#9B59B6"
        }
        
        if include_labels:
            name = node.get("name", f"Person {i+1}")
            role = node.get("role", "")
            graph_node["label"] = f"{name}\\n{role}" if role else name
            
        graph_nodes.append(graph_node)
    
    # Process hierarchical edges
    for edge in edges:
        graph_edge = {
            "from": edge.get("from", edge.get("manager")),
            "to": edge.get("to", edge.get("report")),
            "type": "hierarchy",
            "arrow": True,
            "color": "#8E44AD"
        }
        
        graph_edges.append(graph_edge)
    
    return {
        "type": "organizational_chart",
        "nodes": graph_nodes,
        "edges": graph_edges,
        "layout": "hierarchical_top_down"
    }


def _generate_generic_graph(nodes: List[Dict], edges: List[Dict], include_labels: bool) -> Dict[str, Any]:
    """Generate a generic graph visualization"""
    
    graph_nodes = []
    graph_edges = []
    
    # Process nodes
    for i, node in enumerate(nodes):
        graph_node = {
            "id": node.get("id", f"node_{i}"),
            "type": "generic",
            "shape": "circle",
            "color": "#34495E"
        }
        
        if include_labels:
            graph_node["label"] = node.get("name", node.get("id", f"Node {i+1}"))
            
        graph_nodes.append(graph_node)
    
    # Process edges
    for edge in edges:
        graph_edge = {
            "from": edge.get("from", edge.get("source")),
            "to": edge.get("to", edge.get("target")),
            "type": "connection",
            "color": "#7F8C8D"
        }
        
        graph_edges.append(graph_edge)
    
    return {
        "type": "generic",
        "nodes": graph_nodes,
        "edges": graph_edges,
        "layout": "force_directed"
    }


def _limit_graph_size(graph_data: Dict, max_nodes: int) -> Dict[str, Any]:
    """Limit graph size to specified number of nodes"""
    
    # Keep the most connected nodes
    node_connections = {}
    for edge in graph_data.get("edges", []):
        from_node = edge.get("from")
        to_node = edge.get("to")
        
        node_connections[from_node] = node_connections.get(from_node, 0) + 1
        node_connections[to_node] = node_connections.get(to_node, 0) + 1
    
    # Sort nodes by connection count
    sorted_nodes = sorted(graph_data.get("nodes", []), 
                         key=lambda n: node_connections.get(n["id"], 0), 
                         reverse=True)
    
    # Keep top nodes
    kept_nodes = sorted_nodes[:max_nodes]
    kept_node_ids = {node["id"] for node in kept_nodes}
    
    # Filter edges to only include connections between kept nodes
    kept_edges = [edge for edge in graph_data.get("edges", [])
                 if edge.get("from") in kept_node_ids and edge.get("to") in kept_node_ids]
    
    return {
        **graph_data,
        "nodes": kept_nodes,
        "edges": kept_edges
    }


def _format_visualization(graph_data: Dict, format_type: str) -> Dict[str, Any]:
    """Format the visualization for different output types"""
    
    if format_type == "json":
        return graph_data
    elif format_type == "dot":
        return _format_as_dot(graph_data)
    elif format_type == "cytoscape":
        return _format_as_cytoscape(graph_data)
    else:
        return graph_data


def _format_as_dot(graph_data: Dict) -> Dict[str, str]:
    """Format graph as DOT notation for Graphviz"""
    
    dot_lines = ["digraph G {"]
    
    # Add nodes
    for node in graph_data.get("nodes", []):
        node_id = node["id"]
        label = node.get("label", node_id)
        color = node.get("color", "#000000")
        shape = node.get("shape", "circle")
        
        dot_lines.append(f'  "{node_id}" [label="{label}", color="{color}", shape="{shape}"];')
    
    # Add edges
    for edge in graph_data.get("edges", []):
        from_node = edge["from"]
        to_node = edge["to"]
        label = edge.get("label", "")
        
        edge_attrs = f'[label="{label}"]' if label else ""
        dot_lines.append(f'  "{from_node}" -> "{to_node}" {edge_attrs};')
    
    dot_lines.append("}")
    
    return {
        "format": "dot",
        "content": "\\n".join(dot_lines)
    }


def _format_as_cytoscape(graph_data: Dict) -> Dict[str, Any]:
    """Format graph for Cytoscape.js"""
    
    elements = []
    
    # Add nodes
    for node in graph_data.get("nodes", []):
        elements.append({
            "data": {
                "id": node["id"],
                "label": node.get("label", node["id"])
            },
            "style": {
                "background-color": node.get("color", "#666"),
                "shape": node.get("shape", "ellipse")
            }
        })
    
    # Add edges
    for edge in graph_data.get("edges", []):
        elements.append({
            "data": {
                "id": f"{edge['from']}-{edge['to']}",
                "source": edge["from"],
                "target": edge["to"],
                "label": edge.get("label", "")
            }
        })
    
    return {
        "format": "cytoscape",
        "elements": elements,
        "layout": {"name": graph_data.get("layout", "grid")}
    }


def main():
    """Main function to handle CLI arguments and process data"""
    if len(sys.argv) > 1 and sys.argv[1] == "--fractalic-dump-schema":
        schema = {
            "description": "Visualize process flows, relationships, and data connections as graphs",
            "parameters": {
                "type": "object",
                "properties": {
                    "graph_type": {
                        "type": "string",
                        "description": "Type of graph visualization to generate",
                        "enum": ["process_flow", "relationship_map", "organizational_chart", "generic"],
                        "default": "process_flow"
                    },
                    "visualization_format": {
                        "type": "string",
                        "description": "Output format for visualization",
                        "enum": ["json", "dot", "cytoscape"],
                        "default": "json"
                    },
                    "include_labels": {
                        "type": "boolean",
                        "description": "Whether to include labels on nodes and edges",
                        "default": True
                    },
                    "max_nodes": {
                        "type": "integer",
                        "description": "Maximum number of nodes to include in visualization",
                        "default": 100
                    },
                    "nodes": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": "Array of node objects for visualization"
                    },
                    "edges": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": "Array of edge objects for visualization"
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
            input_data = '{"nodes": [], "edges": []}'
        
        data = json.loads(input_data)
        
        # Process the data
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
