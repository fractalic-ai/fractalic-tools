#!/usr/bin/env python3
"""
HubSpot Graph-Based Process Mining Tool

This tool implements true process mining by:
1. Building a graph for each process instance (deal, ticket, etc.) representing its state transitions and activities
2. Merging all individual graphs into an overall process graph
3. Analyzing the merged graph for patterns, loops, deviations, and branches
4. Providing actionable insights based on graph analysis
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from typing import Dict, List, Set, Tuple, Optional, Any
import networkx as nx
from dataclasses import dataclass
import matplotlib.pyplot as plt
import seaborn as sns

# Add the parent directory to the path so we can import our HubSpot modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import moved inside functions to prevent timeout

@dataclass
class ProcessEvent:
    """Represents a single event in a process instance"""
    timestamp: datetime
    event_type: str  # 'state_change', 'activity', 'association'
    from_state: Optional[str]
    to_state: Optional[str]
    activity: Optional[str]
    object_type: str
    object_id: str
    details: Dict[str, Any]

@dataclass
class ProcessInstance:
    """Represents a complete process instance with all its events"""
    instance_id: str
    object_type: str
    events: List[ProcessEvent]
    start_time: datetime
    end_time: Optional[datetime]
    final_state: Optional[str]

class GraphProcessMiner:
    """Graph-based process mining implementation"""
    
    def __init__(self):
        from hubspot_hub_helpers import hs_client
        self.client = hs_client()
        self.logger = self._setup_logging()
        self.process_instances: List[ProcessInstance] = []
        self.individual_graphs: Dict[str, nx.DiGraph] = {}
        self.merged_graph: nx.DiGraph = nx.DiGraph()
        
    def _setup_logging(self) -> logging.Logger:
        """Set up logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        return logging.getLogger(__name__)
    
    def extract_deal_process_instances(self, limit: int = 200) -> List[ProcessInstance]:
        """Extract process instances from deals with their complete history"""
        self.logger.info("Extracting deal process instances...")
        
        try:
            # Get deals with properties and associations
            deals_response = self.client.crm.deals.basic_api.get_page(
                limit=limit,
                properties=[
                    'dealstage', 'dealname', 'amount', 'pipeline', 'createdate',
                    'closedate', 'hs_lastmodifieddate', 'hubspot_owner_id',
                    'deal_currency_code', 'hs_deal_stage_probability'
                ],
                associations=['contacts', 'companies', 'tickets', 'tasks']
            )
            
            instances = []
            
            for deal in deals_response.results:
                try:
                    instance = self._build_deal_process_instance(deal)
                    if instance and len(instance.events) > 1:  # Only include deals with activity
                        instances.append(instance)
                except Exception as e:
                    self.logger.warning(f"Error processing deal {deal.id}: {e}")
                    continue
            
            self.logger.info(f"Extracted {len(instances)} deal process instances")
            return instances
            
        except Exception as e:
            self.logger.error(f"Error extracting deal process instances: {e}")
            return []
    
    def _build_deal_process_instance(self, deal) -> Optional[ProcessInstance]:
        """Build a process instance from a deal with all its events"""
        try:
            deal_id = deal.id
            events = []
            
            # Get deal timeline/activities
            try:
                timeline_response = self.client.crm.timeline.timeline_api.get_page(
                    object_type='deal',
                    object_id=deal_id,
                    limit=100
                )
                
                # Process timeline events
                for event in timeline_response.results:
                    event_time = datetime.fromisoformat(event.created_at.replace('Z', '+00:00'))
                    
                    if event.event_type == 'deal_stage_changed':
                        # State transition event
                        from_stage = event.details.get('from_stage')
                        to_stage = event.details.get('to_stage')
                        
                        events.append(ProcessEvent(
                            timestamp=event_time,
                            event_type='state_change',
                            from_state=from_stage,
                            to_state=to_stage,
                            activity=None,
                            object_type='deal',
                            object_id=deal_id,
                            details=event.details
                        ))
                    else:
                        # Activity event
                        events.append(ProcessEvent(
                            timestamp=event_time,
                            event_type='activity',
                            from_state=None,
                            to_state=None,
                            activity=event.event_type,
                            object_type='deal',
                            object_id=deal_id,
                            details=event.details
                        ))
                        
            except Exception as e:
                self.logger.warning(f"Could not get timeline for deal {deal_id}: {e}")
            
            # Add property change events from deal properties
            create_date = deal.properties.get('createdate')
            if create_date:
                create_time = datetime.fromisoformat(create_date.replace('Z', '+00:00'))
                events.append(ProcessEvent(
                    timestamp=create_time,
                    event_type='state_change',
                    from_state=None,
                    to_state='created',
                    activity=None,
                    object_type='deal',
                    object_id=deal_id,
                    details={'initial_stage': deal.properties.get('dealstage')}
                ))
            
            # Add current stage as final state
            current_stage = deal.properties.get('dealstage')
            last_modified = deal.properties.get('hs_lastmodifieddate')
            if last_modified:
                mod_time = datetime.fromisoformat(last_modified.replace('Z', '+00:00'))
                events.append(ProcessEvent(
                    timestamp=mod_time,
                    event_type='state_change',
                    from_state=None,
                    to_state=current_stage,
                    activity=None,
                    object_type='deal',
                    object_id=deal_id,
                    details={'current_stage': current_stage}
                ))
            
            # Add association events
            if hasattr(deal, 'associations'):
                for assoc_type, associations in deal.associations.items():
                    for assoc in associations.results:
                        events.append(ProcessEvent(
                            timestamp=create_time if create_date else datetime.now(),
                            event_type='association',
                            from_state=None,
                            to_state=None,
                            activity=f'associated_with_{assoc_type}',
                            object_type='deal',
                            object_id=deal_id,
                            details={'associated_id': assoc.id, 'association_type': assoc_type}
                        ))
            
            # Sort events by timestamp
            events.sort(key=lambda x: x.timestamp)
            
            if not events:
                return None
            
            # Determine final state and end time
            final_state = current_stage
            end_time = None
            close_date = deal.properties.get('closedate')
            if close_date:
                end_time = datetime.fromisoformat(close_date.replace('Z', '+00:00'))
            
            return ProcessInstance(
                instance_id=deal_id,
                object_type='deal',
                events=events,
                start_time=events[0].timestamp,
                end_time=end_time,
                final_state=final_state
            )
            
        except Exception as e:
            self.logger.error(f"Error building process instance for deal {deal.id}: {e}")
            return None
    
    def build_individual_graphs(self, instances: List[ProcessInstance]) -> Dict[str, nx.DiGraph]:
        """Build individual process graphs for each instance"""
        self.logger.info("Building individual process graphs...")
        
        graphs = {}
        
        for instance in instances:
            graph = nx.DiGraph()
            
            # Add nodes for each state and activity
            states = set()
            activities = set()
            
            for event in instance.events:
                if event.from_state:
                    states.add(event.from_state)
                if event.to_state:
                    states.add(event.to_state)
                if event.activity:
                    activities.add(event.activity)
            
            # Add state nodes
            for state in states:
                graph.add_node(f"state_{state}", type='state', label=state)
            
            # Add activity nodes
            for activity in activities:
                graph.add_node(f"activity_{activity}", type='activity', label=activity)
            
            # Add edges based on event sequence
            prev_node = None
            
            for event in instance.events:
                current_node = None
                
                if event.event_type == 'state_change' and event.to_state:
                    current_node = f"state_{event.to_state}"
                elif event.event_type == 'activity' and event.activity:
                    current_node = f"activity_{event.activity}"
                elif event.event_type == 'association' and event.activity:
                    current_node = f"activity_{event.activity}"
                
                if prev_node and current_node and prev_node != current_node:
                    # Add edge with timing information
                    if graph.has_edge(prev_node, current_node):
                        # Increment weight for repeated transitions
                        graph[prev_node][current_node]['weight'] += 1
                    else:
                        graph.add_edge(prev_node, current_node, weight=1, 
                                     timestamp=event.timestamp.isoformat())
                
                if current_node:
                    prev_node = current_node
            
            graphs[instance.instance_id] = graph
        
        self.logger.info(f"Built {len(graphs)} individual process graphs")
        return graphs
    
    def merge_graphs(self, individual_graphs: Dict[str, nx.DiGraph]) -> nx.DiGraph:
        """Merge all individual graphs into a single process graph"""
        self.logger.info("Merging individual graphs...")
        
        merged = nx.DiGraph()
        edge_weights = defaultdict(int)
        node_frequencies = defaultdict(int)
        
        # Collect all nodes and edges with frequencies
        for graph_id, graph in individual_graphs.items():
            # Add nodes with frequency tracking
            for node, data in graph.nodes(data=True):
                if not merged.has_node(node):
                    merged.add_node(node, **data)
                node_frequencies[node] += 1
            
            # Add edges with weight accumulation
            for u, v, data in graph.edges(data=True):
                edge_key = (u, v)
                edge_weights[edge_key] += data.get('weight', 1)
                
                if merged.has_edge(u, v):
                    merged[u][v]['weight'] += data.get('weight', 1)
                    merged[u][v]['frequency'] += 1
                else:
                    merged.add_edge(u, v, weight=data.get('weight', 1), frequency=1)
        
        # Update node attributes with frequencies
        for node in merged.nodes():
            merged.nodes[node]['frequency'] = node_frequencies[node]
        
        self.logger.info(f"Merged graph has {merged.number_of_nodes()} nodes and {merged.number_of_edges()} edges")
        return merged
    
    def analyze_graph_patterns(self, graph: nx.DiGraph) -> Dict[str, Any]:
        """Analyze the merged graph for patterns, loops, and anomalies"""
        self.logger.info("Analyzing graph patterns...")
        
        analysis = {
            'graph_stats': {
                'nodes': graph.number_of_nodes(),
                'edges': graph.number_of_edges(),
                'density': nx.density(graph),
                'is_strongly_connected': nx.is_strongly_connected(graph),
                'number_of_components': nx.number_weakly_connected_components(graph)
            },
            'most_frequent_paths': [],
            'loops': [],
            'bottlenecks': [],
            'dead_ends': [],
            'starting_points': [],
            'anomalous_branches': []
        }
        
        # Find most frequent edges (common transitions)
        edge_frequencies = [(u, v, data['frequency']) for u, v, data in graph.edges(data=True)]
        edge_frequencies.sort(key=lambda x: x[2], reverse=True)
        
        analysis['most_frequent_transitions'] = [
            {
                'from': u.replace('state_', '').replace('activity_', ''),
                'to': v.replace('state_', '').replace('activity_', ''),
                'frequency': freq,
                'from_type': 'state' if u.startswith('state_') else 'activity',
                'to_type': 'state' if v.startswith('state_') else 'activity'
            }
            for u, v, freq in edge_frequencies[:20]
        ]
        
        # Find nodes with highest frequency (common states/activities)
        node_frequencies = [(node, data['frequency']) for node, data in graph.nodes(data=True)]
        node_frequencies.sort(key=lambda x: x[1], reverse=True)
        
        analysis['most_frequent_nodes'] = [
            {
                'node': node.replace('state_', '').replace('activity_', ''),
                'frequency': freq,
                'type': 'state' if node.startswith('state_') else 'activity'
            }
            for node, freq in node_frequencies[:15]
        ]
        
        # Find loops (cycles)
        try:
            cycles = list(nx.simple_cycles(graph))
            analysis['loops'] = [
                {
                    'cycle': [n.replace('state_', '').replace('activity_', '') for n in cycle],
                    'length': len(cycle),
                    'cycle_strength': min([graph[cycle[i]][cycle[(i+1) % len(cycle)]]['frequency'] 
                                         for i in range(len(cycle))])
                }
                for cycle in cycles[:10]  # Top 10 cycles
            ]
        except Exception as e:
            self.logger.warning(f"Error finding cycles: {e}")
            analysis['loops'] = []
        
        # Find bottlenecks (nodes with high in-degree and out-degree)
        bottlenecks = []
        for node in graph.nodes():
            in_degree = graph.in_degree(node)
            out_degree = graph.out_degree(node)
            if in_degree > 3 and out_degree > 3:  # Threshold for bottleneck
                bottlenecks.append({
                    'node': node.replace('state_', '').replace('activity_', ''),
                    'in_degree': in_degree,
                    'out_degree': out_degree,
                    'type': 'state' if node.startswith('state_') else 'activity'
                })
        
        analysis['bottlenecks'] = sorted(bottlenecks, key=lambda x: x['in_degree'] + x['out_degree'], reverse=True)[:10]
        
        # Find dead ends (nodes with no outgoing edges)
        dead_ends = [node for node in graph.nodes() if graph.out_degree(node) == 0]
        analysis['dead_ends'] = [
            {
                'node': node.replace('state_', '').replace('activity_', ''),
                'type': 'state' if node.startswith('state_') else 'activity',
                'frequency': graph.nodes[node]['frequency']
            }
            for node in dead_ends
        ]
        
        # Find starting points (nodes with no incoming edges)
        starting_points = [node for node in graph.nodes() if graph.in_degree(node) == 0]
        analysis['starting_points'] = [
            {
                'node': node.replace('state_', '').replace('activity_', ''),
                'type': 'state' if node.startswith('state_') else 'activity',
                'frequency': graph.nodes[node]['frequency']
            }
            for node in starting_points
        ]
        
        # Find anomalous branches (nodes with unusually low frequency compared to their neighbors)
        anomalous = []
        for node in graph.nodes():
            node_freq = graph.nodes[node]['frequency']
            neighbor_frequencies = []
            
            for neighbor in graph.predecessors(node):
                neighbor_frequencies.append(graph.nodes[neighbor]['frequency'])
            for neighbor in graph.successors(node):
                neighbor_frequencies.append(graph.nodes[neighbor]['frequency'])
            
            if neighbor_frequencies:
                avg_neighbor_freq = sum(neighbor_frequencies) / len(neighbor_frequencies)
                if node_freq < avg_neighbor_freq * 0.1:  # Less than 10% of average neighbor frequency
                    anomalous.append({
                        'node': node.replace('state_', '').replace('activity_', ''),
                        'frequency': node_freq,
                        'avg_neighbor_frequency': avg_neighbor_freq,
                        'type': 'state' if node.startswith('state_') else 'activity'
                    })
        
        analysis['anomalous_branches'] = sorted(anomalous, key=lambda x: x['frequency'])[:10]
        
        return analysis
    
    def find_process_variants(self, instances: List[ProcessInstance]) -> Dict[str, Any]:
        """Find different process variants (different paths through the process)"""
        self.logger.info("Finding process variants...")
        
        # Extract sequences of states for each instance
        sequences = []
        for instance in instances:
            sequence = []
            for event in instance.events:
                if event.event_type == 'state_change' and event.to_state:
                    sequence.append(event.to_state)
            if sequence:
                sequences.append(tuple(sequence))
        
        # Count variant frequencies
        variant_counts = Counter(sequences)
        
        # Calculate variant statistics
        total_instances = len(sequences)
        variants = []
        
        for sequence, count in variant_counts.most_common(20):
            variants.append({
                'sequence': list(sequence),
                'frequency': count,
                'percentage': (count / total_instances) * 100,
                'length': len(sequence)
            })
        
        return {
            'total_variants': len(variant_counts),
            'total_instances': total_instances,
            'top_variants': variants,
            'variant_diversity': len(variant_counts) / total_instances
        }
    
    def generate_insights(self, analysis: Dict[str, Any], variants: Dict[str, Any]) -> Dict[str, Any]:
        """Generate actionable insights from the analysis"""
        insights = {
            'process_complexity': {
                'assessment': 'High' if analysis['graph_stats']['density'] > 0.1 else 'Medium' if analysis['graph_stats']['density'] > 0.05 else 'Low',
                'variant_diversity': variants['variant_diversity'],
                'recommendation': ''
            },
            'bottleneck_analysis': {
                'critical_bottlenecks': analysis['bottlenecks'][:3],
                'recommendation': ''
            },
            'efficiency_issues': {
                'loops_detected': len(analysis['loops']),
                'dead_ends': len(analysis['dead_ends']),
                'anomalous_branches': len(analysis['anomalous_branches']),
                'recommendation': ''
            },
            'process_standardization': {
                'most_common_variant_percentage': variants['top_variants'][0]['percentage'] if variants['top_variants'] else 0,
                'top_3_variants_percentage': sum(v['percentage'] for v in variants['top_variants'][:3]) if len(variants['top_variants']) >= 3 else 0,
                'recommendation': ''
            }
        }
        
        # Generate recommendations
        if insights['process_complexity']['assessment'] == 'High':
            insights['process_complexity']['recommendation'] = "Consider simplifying the process by reducing the number of possible paths and states."
        
        if analysis['bottlenecks']:
            insights['bottleneck_analysis']['recommendation'] = f"Focus on optimizing the '{analysis['bottlenecks'][0]['node']}' stage which shows the highest congestion."
        
        if analysis['loops']:
            insights['efficiency_issues']['recommendation'] = "Review process loops - some may indicate rework or inefficiencies that could be eliminated."
        
        if insights['process_standardization']['most_common_variant_percentage'] < 50:
            insights['process_standardization']['recommendation'] = "Process shows high variability. Consider standardizing the most common successful paths."
        
        return insights
    
    def save_results(self, analysis: Dict[str, Any], variants: Dict[str, Any], 
                    insights: Dict[str, Any], instances: List[ProcessInstance]) -> str:
        """Save all results to a comprehensive JSON file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"hubspot_graph_process_mining_{timestamp}.json"
        
        results = {
            'metadata': {
                'analysis_timestamp': datetime.now().isoformat(),
                'total_instances_analyzed': len(instances),
                'analysis_type': 'graph_based_process_mining'
            },
            'graph_analysis': analysis,
            'process_variants': variants,
            'insights': insights,
            'instance_summary': [
                {
                    'instance_id': inst.instance_id,
                    'object_type': inst.object_type,
                    'start_time': inst.start_time.isoformat(),
                    'end_time': inst.end_time.isoformat() if inst.end_time else None,
                    'final_state': inst.final_state,
                    'event_count': len(inst.events)
                }
                for inst in instances[:50]  # Sample of instances
            ]
        }
        
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        return filename
    
    def run_complete_analysis(self, limit: int = 200) -> str:
        """Run the complete graph-based process mining analysis"""
        self.logger.info("Starting complete graph-based process mining analysis...")
        
        try:
            # Step 1: Extract process instances
            instances = self.extract_deal_process_instances(limit)
            if not instances:
                self.logger.error("No process instances extracted")
                return ""
            
            # Step 2: Build individual graphs
            individual_graphs = self.build_individual_graphs(instances)
            if not individual_graphs:
                self.logger.error("No individual graphs built")
                return ""
            
            # Step 3: Merge graphs
            merged_graph = self.merge_graphs(individual_graphs)
            
            # Step 4: Analyze patterns
            analysis = self.analyze_graph_patterns(merged_graph)
            
            # Step 5: Find process variants
            variants = self.find_process_variants(instances)
            
            # Step 6: Generate insights
            insights = self.generate_insights(analysis, variants)
            
            # Step 7: Save results
            filename = self.save_results(analysis, variants, insights, instances)
            
            # Store for potential visualization
            self.process_instances = instances
            self.individual_graphs = individual_graphs
            self.merged_graph = merged_graph
            
            self.logger.info(f"Complete analysis saved to {filename}")
            return filename
            
        except Exception as e:
            self.logger.error(f"Error in complete analysis: {e}")
            return ""

def process_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run graph-based process mining analysis on HubSpot data
    
    Args:
        data: Dictionary containing analysis parameters
    
    Returns:
        Dictionary containing complete process mining results
    """
    try:
        from hubspot_hub_helpers import hs_client
        
        # Get the HubSpot client instance
        client = hs_client()
        
        # Extract parameters with defaults
        object_type = data.get("object_type", "deals")
        analysis_mode = data.get("analysis_mode", "network")
        include_visualization = data.get("include_visualization", False)
        max_depth = data.get("max_depth", 3)
        sample_size = data.get("sample_size", 100)
        
        # Initialize the miner
        miner = GraphProcessMiner()
        
        # Step 1: Extract process instances  
        instances = miner.extract_deal_process_instances(sample_size)
        if not instances:
            return {
                "success": False,
                "error": "No process instances extracted",
                "timestamp": datetime.now().isoformat()
            }
        
        # Step 2: Build individual graphs
        individual_graphs = miner.build_individual_graphs(instances)
        if not individual_graphs:
            return {
                "success": False,
                "error": "No individual graphs built", 
                "timestamp": datetime.now().isoformat()
            }
        
        # Step 3: Merge graphs
        merged_graph = miner.merge_graphs(individual_graphs)
        
        # Step 4: Analyze patterns
        analysis = miner.analyze_graph_patterns(merged_graph)
        
        # Step 5: Find process variants
        variants = miner.find_process_variants(instances)
        
        # Step 6: Generate insights
        insights = miner.generate_insights(analysis, variants)
        
        # Return the complete results as JSON
        return {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "analysis_type": "graph_based_process_mining",
            "parameters": {
                "object_type": object_type,
                "analysis_mode": analysis_mode,
                "sample_size": sample_size,
                "max_depth": max_depth
            },
            "metadata": {
                "total_instances_analyzed": len(instances),
                "individual_graphs_built": len(individual_graphs),
                "merged_graph_nodes": merged_graph.number_of_nodes(),
                "merged_graph_edges": merged_graph.number_of_edges()
            },
            "graph_analysis": analysis,
            "process_variants": variants,
            "insights": insights,
            "instance_summary": [
                {
                    "instance_id": inst.instance_id,
                    "object_type": inst.object_type,
                    "start_time": inst.start_time.isoformat(),
                    "end_time": inst.end_time.isoformat() if inst.end_time else None,
                    "final_state": inst.final_state,
                    "event_count": len(inst.events)
                }
                for inst in instances[:50]  # Sample of instances
            ]
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


def get_schema() -> Dict[str, Any]:
    """Return the JSON schema for this tool's input parameters."""
    return {
        "type": "object",
        "properties": {
            "limit": {
                "type": "integer",
                "description": "Maximum number of process instances to analyze",
                "default": 100,
                "minimum": 10,
                "maximum": 1000
            },
            "hubspot_token": {
                "type": "string",
                "description": "HubSpot API token (required for live analysis)"
            }
        },
        "required": []
    }

if __name__ == "__main__":
    import sys
    
    # Test mode for autodiscovery (REQUIRED)
    if len(sys.argv) == 2 and sys.argv[1] == '{"__test__": true}':
        print(json.dumps({"success": True, "_simple": True}))
        sys.exit(0)
    
    # Handle command line arguments for schema export
    if len(sys.argv) == 2 and sys.argv[1] == "--fractalic-dump-schema":
        schema = {
            "name": "hubspot_graph_process_miner",
            "description": "Advanced graph analysis of process flows and object relationships using network analysis",
            "parameters": {
                "type": "object",
                "properties": {
                    "object_type": {
                        "type": "string",
                        "enum": ["deals", "contacts", "tickets", "companies"],
                        "description": "Primary object type to analyze",
                        "default": "deals"
                    },
                    "analysis_mode": {
                        "type": "string",
                        "enum": ["network", "paths", "clusters", "flows"],
                        "description": "Type of graph analysis to perform",
                        "default": "network"
                    },
                    "include_visualization": {
                        "type": "boolean",
                        "description": "Generate graph visualizations",
                        "default": False
                    },
                    "max_depth": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 5,
                        "description": "Maximum relationship depth to analyze",
                        "default": 3
                    },
                    "sample_size": {
                        "type": "integer",
                        "minimum": 10,
                        "maximum": 1000,
                        "description": "Number of objects to analyze",
                        "default": 100
                    }
                }
            }
        }
        print(json.dumps(schema, ensure_ascii=False))
        sys.exit(0)
    
    # Process JSON input (REQUIRED)
    try:
        if len(sys.argv) != 2:
            raise ValueError("Expected exactly one JSON argument")
        
        params = json.loads(sys.argv[1])
        result = process_data(params)
        print(json.dumps(result, ensure_ascii=False, default=str))
        
    except Exception as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False))
        sys.exit(1)
