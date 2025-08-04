#!/usr/bin/env python3
"""
HubSpot Customer Journey Mapper

This tool analyzes customer journey patterns in HubSpot by mapping contact lifecycle stages,
deal progression paths, interaction touchpoints, and identifying common journey variations.
Part of the Fractalic Process Mining Intelligence Suite.
"""

from typing import Dict, Any, List, Tuple, Optional
import json
import sys
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import statistics

def process_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze customer journey patterns and map common paths through the CRM.
    
    Args:
        data: Dictionary containing analysis parameters
    
    Returns:
        Dictionary containing customer journey analysis results
    """
    try:
        # Import dependencies inside the function
        import sys
        import os
        sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
        from hubspot_hub_helpers import hs_client
        from hubspot.crm.contacts import ApiException as ContactsApiException
        from hubspot.crm.deals import ApiException as DealsApiException
        
        # Get the HubSpot client instance
        client = hs_client()
        
        # Extract parameters
        limit = data.get('limit', 100)
        days_back = data.get('days_back', 90)
        include_interactions = data.get('include_interactions', True)
        min_journey_length = data.get('min_journey_length', 2)
        
        cutoff_date = datetime.now() - timedelta(days=days_back)
        cutoff_timestamp = int(cutoff_date.timestamp() * 1000)
        
        print(f"🔍 Analyzing customer journeys from the past {days_back} days...")
        
        # Initialize analysis containers
        journey_paths = []
        stage_transitions = defaultdict(int)
        touchpoint_sequences = defaultdict(list)
        journey_metrics = {
            'total_contacts_analyzed': 0,
            'complete_journeys': 0,
            'active_journeys': 0,
            'common_patterns': [],
            'stage_conversion_rates': {},
            'average_journey_length': 0,
            'journey_duration_stats': {}
        }
        
        # Get contacts with lifecycle stage history
        try:
            print("📊 Fetching contact lifecycle data...")
            contacts_response = client.crm.contacts.basic_api.get_page(
                limit=limit,
                properties=['firstname', 'lastname', 'email', 'lifecyclestage', 'createdate', 'lastmodifieddate'],
                archived=False
            )
            
            contacts = contacts_response.results if contacts_response.results else []
            journey_metrics['total_contacts_analyzed'] = len(contacts)
            
            # Analyze each contact's journey
            for contact in contacts:
                contact_id = contact.id
                properties = contact.properties
                
                # Get contact's lifecycle stage history
                try:
                    # Use search to get contacts with activity history
                    from hubspot.crm.contacts import PublicObjectSearchRequest, Filter, FilterGroup
                    
                    filter_group = FilterGroup(filters=[
                        Filter(property_name="hs_object_id", operator="EQ", value=str(contact_id))
                    ])
                    
                    search_request = PublicObjectSearchRequest(
                        filter_groups=[filter_group],
                        properties=['lifecyclestage', 'hs_analytics_source', 'hs_analytics_source_data_1'],
                        limit=1
                    )
                    
                    contact_detail = client.crm.contacts.search_api.do_search(search_request)
                    
                    if contact_detail.results:
                        contact_data = contact_detail.results[0]
                        
                        # Build journey path (simplified - in real implementation would track stage changes over time)
                        current_stage = contact_data.properties.get('lifecyclestage', 'unknown')
                        source = contact_data.properties.get('hs_analytics_source', 'unknown')
                        
                        journey_path = {
                            'contact_id': contact_id,
                            'stages': [current_stage],
                            'source': source,
                            'created_date': properties.get('createdate'),
                            'last_modified': properties.get('lastmodifieddate')
                        }
                        
                        journey_paths.append(journey_path)
                        
                        # Track stage transitions (simplified)
                        if current_stage != 'unknown':
                            stage_transitions[f"entry_{current_stage}"] += 1
                
                except Exception as e:
                    print(f"⚠️ Error analyzing contact {contact_id}: {str(e)}")
                    continue
            
        except ContactsApiException as e:
            print(f"⚠️ Error fetching contacts: {e}")
            return {"error": f"Failed to fetch contacts: {str(e)}"}
        
        # Analyze deals for pipeline progression patterns
        try:
            print("💼 Analyzing deal progression patterns...")
            deals_response = client.crm.deals.basic_api.get_page(
                limit=limit,
                properties=['dealname', 'dealstage', 'pipeline', 'createdate', 'closedate', 'amount'],
                archived=False
            )
            
            deals = deals_response.results if deals_response.results else []
            
            # Track deal stage progressions
            deal_journeys = []
            pipeline_patterns = defaultdict(list)
            
            for deal in deals:
                deal_properties = deal.properties
                pipeline = deal_properties.get('pipeline', 'default')
                stage = deal_properties.get('dealstage', 'unknown')
                
                deal_journey = {
                    'deal_id': deal.id,
                    'pipeline': pipeline,
                    'current_stage': stage,
                    'created_date': deal_properties.get('createdate'),
                    'close_date': deal_properties.get('closedate'),
                    'amount': deal_properties.get('amount')
                }
                
                deal_journeys.append(deal_journey)
                pipeline_patterns[pipeline].append(stage)
            
            # Calculate pipeline conversion patterns
            pipeline_stats = {}
            for pipeline, stages in pipeline_patterns.items():
                stage_counts = Counter(stages)
                pipeline_stats[pipeline] = {
                    'total_deals': len(stages),
                    'stage_distribution': dict(stage_counts),
                    'most_common_stage': stage_counts.most_common(1)[0] if stage_counts else ('unknown', 0)
                }
            
            journey_metrics['pipeline_patterns'] = pipeline_stats
            journey_metrics['total_deals_analyzed'] = len(deals)
            
        except DealsApiException as e:
            print(f"⚠️ Error fetching deals: {e}")
            journey_metrics['pipeline_patterns'] = {}
        
        # Analyze interaction touchpoints if requested
        if include_interactions:
            try:
                print("📞 Analyzing interaction touchpoints...")
                
                # Get recent activities (simplified - would need timeline API for full analysis)
                from hubspot.crm.objects.calls import BasicApi as CallsApi
                
                try:
                    calls_response = client.crm.objects.calls.basic_api.get_page(
                        limit=50,
                        properties=['hs_call_title', 'hs_call_duration', 'hs_call_outcome', 'hs_timestamp']
                    )
                    
                    calls = calls_response.results if calls_response.results else []
                    
                    touchpoint_analysis = {
                        'total_calls': len(calls),
                        'call_outcomes': Counter(),
                        'average_duration': 0
                    }
                    
                    if calls:
                        durations = []
                        for call in calls:
                            call_props = call.properties
                            outcome = call_props.get('hs_call_outcome', 'unknown')
                            touchpoint_analysis['call_outcomes'][outcome] += 1
                            
                            try:
                                duration = int(call_props.get('hs_call_duration', 0))
                                if duration > 0:
                                    durations.append(duration)
                            except (ValueError, TypeError):
                                pass
                        
                        if durations:
                            touchpoint_analysis['average_duration'] = statistics.mean(durations)
                    
                    journey_metrics['touchpoint_analysis'] = touchpoint_analysis
                    
                except Exception as e:
                    print(f"⚠️ Error analyzing calls: {str(e)}")
                    journey_metrics['touchpoint_analysis'] = {'error': str(e)}
                
            except Exception as e:
                print(f"⚠️ Error in touchpoint analysis: {str(e)}")
                journey_metrics['touchpoint_analysis'] = {'error': str(e)}
        
        # Calculate journey insights
        if journey_paths:
            # Identify common journey patterns
            stage_patterns = Counter()
            sources = Counter()
            
            for journey in journey_paths:
                # Track entry points
                if journey['source'] != 'unknown':
                    sources[journey['source']] += 1
                
                # Track stage patterns (simplified)
                for stage in journey['stages']:
                    stage_patterns[stage] += 1
            
            journey_metrics['common_entry_sources'] = dict(sources.most_common(5))
            journey_metrics['stage_distribution'] = dict(stage_patterns)
            journey_metrics['total_journeys_mapped'] = len(journey_paths)
        
        # Generate insights and recommendations
        insights = []
        recommendations = []
        
        if journey_metrics['total_contacts_analyzed'] > 0:
            insights.append(f"Analyzed {journey_metrics['total_contacts_analyzed']} contact journeys")
            
            if 'stage_distribution' in journey_metrics:
                most_common_stage = max(journey_metrics['stage_distribution'].items(), key=lambda x: x[1])
                insights.append(f"Most common lifecycle stage: {most_common_stage[0]} ({most_common_stage[1]} contacts)")
        
        if 'pipeline_patterns' in journey_metrics:
            pipeline_count = len(journey_metrics['pipeline_patterns'])
            if pipeline_count > 0:
                insights.append(f"Found {pipeline_count} active sales pipelines")
                recommendations.append("Consider standardizing pipeline stages across all pipelines for consistency")
        
        if 'common_entry_sources' in journey_metrics and journey_metrics['common_entry_sources']:
            top_source = max(journey_metrics['common_entry_sources'].items(), key=lambda x: x[1])
            insights.append(f"Top customer acquisition source: {top_source[0]} ({top_source[1]} contacts)")
            recommendations.append(f"Optimize processes for {top_source[0]} channel to improve conversion rates")
        
        recommendations.extend([
            "Implement automated nurturing sequences for common journey paths",
            "Set up stage-specific triggers and notifications",
            "Create dashboards to monitor journey conversion rates",
            "Establish SLAs for stage progression times"
        ])
        
        return {
            "status": "success",
            "analysis_type": "customer_journey_mapping",
            "timestamp": datetime.now().isoformat(),
            "parameters": {
                "limit": limit,
                "days_back": days_back,
                "include_interactions": include_interactions,
                "min_journey_length": min_journey_length
            },
            "metrics": journey_metrics,
            "insights": insights,
            "recommendations": recommendations,
            "data_summary": {
                "contacts_analyzed": journey_metrics.get('total_contacts_analyzed', 0),
                "deals_analyzed": journey_metrics.get('total_deals_analyzed', 0),
                "journeys_mapped": journey_metrics.get('total_journeys_mapped', 0),
                "patterns_identified": len(journey_metrics.get('pipeline_patterns', {}))
            }
        }
    
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "analysis_type": "customer_journey_mapping",
            "timestamp": datetime.now().isoformat()
        }

def main():
    """Main entry point."""
    # Test mode for autodiscovery (REQUIRED)
    if len(sys.argv) == 2 and sys.argv[1] == '{"__test__": true}':
        print(json.dumps({"success": True, "_simple": True}))
        return
    
    # Rich schema for better LLM integration
    if len(sys.argv) == 2 and sys.argv[1] == "--fractalic-dump-schema":
        schema = {
            "name": "hubspot_customer_journey_mapper",
            "description": "Analyze customer journey patterns in HubSpot by mapping contact lifecycle stages, deal progression paths, and interaction touchpoints",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of contacts to analyze",
                        "default": 100,
                        "maximum": 500
                    },
                    "days_back": {
                        "type": "integer",
                        "description": "Number of days back to analyze journey data",
                        "default": 90
                    },
                    "include_interactions": {
                        "type": "boolean",
                        "description": "Whether to include interaction touchpoints in journey mapping",
                        "default": True
                    },
                    "min_journey_length": {
                        "type": "integer",
                        "description": "Minimum number of touchpoints to consider a complete journey",
                        "default": 2
                    },
                    "journey_types": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Types of journeys to analyze",
                        "default": ["lifecycle", "deal_progression", "support"]
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
            
        data = json.loads(sys.argv[1])
        result = process_data(data)
        print(json.dumps(result, ensure_ascii=False))
        
    except Exception as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False))
        sys.exit(1)

if __name__ == "__main__":
    main()
