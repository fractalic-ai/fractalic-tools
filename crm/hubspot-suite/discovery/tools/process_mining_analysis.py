#!/usr/bin/env python3
"""
Comprehensive Process Mining Analysis for HubSpot
Analyzes actual business processes from deal data, customer journeys, and workflows
Part of the Fractalic Process Mining Intelligence System
"""

import json
import sys
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from typing import Dict, List, Any, Optional, Tuple


def process_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Comprehensive process mining analysis with configurable parameters
    
    Args:
        data: Dictionary containing analysis parameters and filters
    
    Returns:
        Dict containing comprehensive process mining results
    """
    try:
        # Import dependencies inside the function
        import sys
        import os
        sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
        from hubspot_hub_helpers import hs_client
        
        # Extract parameters with defaults
        analysis_scope = data.get("analysis_scope", "comprehensive")
        analysis_period_days = data.get("analysis_period_days", 90)
        max_deals = data.get("max_deals", 100)  # Add reasonable limit
        include_closed_deals = data.get("include_closed_deals", True)
        min_deal_amount = data.get("min_deal_amount", 0)
        max_deal_amount = data.get("max_deal_amount", 1000000)  # 1M default max
        pipeline_filter = data.get("pipeline_filter", None)
        stage_filter = data.get("stage_filter", None)
        owner_filter = data.get("owner_filter", None)
        business_type_analysis_depth = data.get("business_type_analysis_depth", "standard")
        
        client = hs_client()
        
        print(f"🔍 Running comprehensive process mining analysis...", file=sys.stderr)
        
        # Fetch deal data with filters (with reasonable limits)
        deals_data = _fetch_filtered_deals(
            client, 
            analysis_period_days,
            max_deals,
            include_closed_deals,
            min_deal_amount,
            max_deal_amount,
            pipeline_filter,
            stage_filter,
            owner_filter
        )
        
        if not deals_data or not deals_data.get('deals'):
            return {
                "success": False,
                "error": "No deal data found matching the specified filters",
                "timestamp": datetime.now().isoformat()
            }
        
        # Perform comprehensive process mining
        process_analysis = analyze_deal_processes(deals_data, business_type_analysis_depth)
        bottleneck_analysis = identify_process_bottlenecks(deals_data)
        workflow_analysis = map_customer_workflows(deals_data)
        temporal_analysis = _analyze_temporal_patterns(deals_data, analysis_period_days)
        
        key_insights = _generate_key_insights(process_analysis, bottleneck_analysis, workflow_analysis, temporal_analysis)
        recommendations = _generate_recommendations(process_analysis, bottleneck_analysis, workflow_analysis, temporal_analysis)
        
        # Compile comprehensive results
        results = {
            "success": True,
            "analysis_type": "comprehensive_process_mining",
            "timestamp": datetime.now().isoformat(),
            "parameters": {
                "analysis_period_days": analysis_period_days,
                "max_deals": max_deals,
                "include_closed_deals": include_closed_deals,
                "min_deal_amount": min_deal_amount,
                "max_deal_amount": max_deal_amount,
                "pipeline_filter": pipeline_filter,
                "stage_filter": stage_filter,
                "owner_filter": owner_filter,
                "business_type_analysis_depth": business_type_analysis_depth
            },
            "deal_summary": {
                "total_deals_analyzed": len(deals_data.get('deals', [])),
                "total_pipeline_value": process_analysis['amount_analysis']['total_value'],
                "closed_won_value": process_analysis['amount_analysis']['closed_won_value'],
                "active_pipeline_value": process_analysis['amount_analysis']['pipeline_value'],
                "analysis_period": f"{analysis_period_days} days"
            },
            "process_analysis": process_analysis,
            "bottleneck_analysis": bottleneck_analysis,
            "workflow_analysis": workflow_analysis,
            "temporal_analysis": temporal_analysis,
            "key_insights": key_insights,
            "recommendations": recommendations
        }
        
        return results
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


def _fetch_filtered_deals(client, analysis_period_days: int, max_deals: int, 
                         include_closed_deals: bool, min_deal_amount: Optional[float],
                         max_deal_amount: Optional[float], pipeline_filter: Optional[str],
                         stage_filter: Optional[str], owner_filter: Optional[str]) -> Dict[str, Any]:
    """Fetch deals with comprehensive filtering"""
    
    # Calculate date range
    cutoff_date = datetime.now() - timedelta(days=analysis_period_days)
    
    # Build properties list
    properties = [
        'dealstage', 'dealname', 'amount', 'pipeline', 'createdate',
        'closedate', 'hs_lastmodifieddate', 'hubspot_owner_id',
        'deal_currency_code', 'hs_deal_stage_probability', 'dealtype',
        'hs_deal_amount_calculation_preference', 'hs_projected_amount'
    ]
    
    # Fetch deals
    try:
        deals_response = client.crm.deals.basic_api.get_page(
            limit=max_deals,
            properties=properties,
            associations=['contacts', 'companies']
        )
        
        deals = []
        for deal in deals_response.results:
            # The properties are already a dict
            deal_dict = {
                'id': deal.id,
                'properties': deal.properties,  # Already a dict
                'associations': getattr(deal, 'associations', {})
            }
            
            # Apply filters using the properties dict
            if not _passes_deal_filters(deal_dict['properties'], include_closed_deals, min_deal_amount, 
                                      max_deal_amount, pipeline_filter, stage_filter, 
                                      owner_filter, cutoff_date):
                continue
                
            deals.append(deal_dict)
        
        return {"deals": deals}
        
    except Exception as e:
        raise Exception(f"Error fetching deals: {str(e)}")


def _passes_deal_filters(props: Dict[str, Any], include_closed_deals: bool, 
                        min_deal_amount: Optional[float], max_deal_amount: Optional[float],
                        pipeline_filter: Optional[str], stage_filter: Optional[str],
                        owner_filter: Optional[str], cutoff_date: datetime) -> bool:
    """Check if deal passes all specified filters"""
    
    # Date filter
    if props.get('createdate'):
        try:
            create_date = datetime.fromisoformat(props['createdate'].replace('Z', '+00:00'))
            if create_date < cutoff_date:
                return False
        except:
            pass
    
    # Closed deals filter
    if not include_closed_deals:
        stage = props.get('dealstage', '')
        if stage in ['closedwon', 'closedlost']:
            return False
    
    # Amount filters
    if min_deal_amount is not None or max_deal_amount is not None:
        amount = props.get('amount')
        if amount:
            try:
                amount_val = float(amount)
                if min_deal_amount is not None and amount_val < min_deal_amount:
                    return False
                if max_deal_amount is not None and amount_val > max_deal_amount:
                    return False
            except:
                pass
    
    # Pipeline filter
    if pipeline_filter and props.get('pipeline') != pipeline_filter:
        return False
    
    # Stage filter
    if stage_filter and props.get('dealstage') != stage_filter:
        return False
    
    # Owner filter
    if owner_filter and props.get('hubspot_owner_id') != owner_filter:
        return False
    
    return True


def _analyze_temporal_patterns(deals_data: Dict[str, Any], analysis_period_days: int) -> Dict[str, Any]:
    """Analyze temporal patterns in deal creation and progression"""
    
    deals = deals_data.get('deals', [])
    daily_patterns = defaultdict(int)
    weekly_patterns = defaultdict(int)
    monthly_patterns = defaultdict(int)
    stage_transitions = defaultdict(list)
    
    for deal in deals:
        props = deal.get('properties', {})
        
        # Creation patterns
        if props.get('createdate'):
            try:
                create_date = datetime.fromisoformat(props['createdate'].replace('Z', '+00:00'))
                daily_patterns[create_date.strftime('%A')] += 1
                weekly_patterns[create_date.strftime('%U')] += 1
                monthly_patterns[create_date.strftime('%B')] += 1
            except:
                pass
    
    return {
        "daily_creation_patterns": dict(daily_patterns),
        "weekly_patterns": dict(weekly_patterns),
        "monthly_patterns": dict(monthly_patterns),
        "analysis_period_days": analysis_period_days,
        "peak_creation_day": max(daily_patterns.items(), key=lambda x: x[1])[0] if daily_patterns else None
    }

def analyze_deal_processes(deals_data: Dict[str, Any], business_type_depth: int = 10) -> Dict[str, Any]:
    """
    Analyze deal processes and identify business patterns
    """
    deals = deals_data.get('deals', [])
    
    # Process analysis
    stage_distribution = Counter()
    pipeline_analysis = defaultdict(list)
    amount_analysis = {'total_value': 0, 'closed_won_value': 0, 'pipeline_value': 0}
    temporal_patterns = defaultdict(list)
    
    # Business process categories
    business_types = defaultdict(list)
    customer_patterns = defaultdict(list)
    
    for deal in deals:
        props = deal.get('properties', {})
        
        # Extract key data
        stage = props.get('dealstage', 'unknown')
        amount = props.get('amount')
        deal_name = props.get('dealname') or ''  # Ensure it's never None
        created = props.get('createdate')
        modified = props.get('hs_lastmodifieddate')
        close_date = props.get('closedate')
        
        # Stage distribution
        stage_distribution[stage] += 1
        
        # Amount analysis
        if amount:
            amount_val = float(amount)
            amount_analysis['total_value'] += amount_val
            
            if stage == 'closedwon':
                amount_analysis['closed_won_value'] += amount_val
            else:
                amount_analysis['pipeline_value'] += amount_val
        
        # Business type classification
        if deal_name and isinstance(deal_name, str):
            deal_lower = deal_name.lower()
            if '3d printing' in deal_lower or 'printing' in deal_lower:
                business_types['3d_printing'].append(deal)
            elif 'streamads' in deal_lower or 'ads' in deal_lower:
                business_types['advertising'].append(deal)
            elif 'iot' in deal_lower or 'automation' in deal_lower:
                business_types['iot_automation'].append(deal)
            elif 'delivery' in deal_lower or 'logistics' in deal_lower:
                business_types['logistics'].append(deal)
            elif 'fitlife' in deal_lower or 'gym' in deal_lower:
                business_types['fitness'].append(deal)
            elif 'building' in deal_lower or 'construction' in deal_lower:
                business_types['construction'].append(deal)
            else:
                business_types['other'].append(deal)
        else:
            business_types['unknown'].append(deal)
        
        # Customer pattern analysis
        if ' - ' in deal_name:
            customer = deal_name.split(' - ')[0]
            customer_patterns[customer].append({
                'stage': stage,
                'amount': amount,
                'created': created,
                'deal_name': deal_name
            })
    
    return {
        'stage_distribution': dict(stage_distribution),
        'amount_analysis': amount_analysis,
        'business_types': {k: len(v) for k, v in business_types.items()},
        'business_types_details': business_types,
        'customer_patterns': dict(customer_patterns),
        'process_insights': _generate_process_insights(deals, stage_distribution, business_types, customer_patterns)
    }

def _generate_process_insights(deals, stage_distribution, business_types, customer_patterns):
    """Generate business process insights"""
    insights = []
    
    # Sales process analysis
    total_deals = len(deals)
    closed_won = stage_distribution.get('closedwon', 0)
    conversion_rate = (closed_won / total_deals * 100) if total_deals > 0 else 0
    
    insights.append(f"Sales Conversion Rate: {conversion_rate:.1f}% ({closed_won}/{total_deals} deals closed)")
    
    # Pipeline health
    active_stages = ['appointmentscheduled', 'qualifiedtobuy', 'presentationscheduled', 'decisionmakerboughtin', 'contractsent']
    active_deals = sum(stage_distribution.get(stage, 0) for stage in active_stages)
    insights.append(f"Active Pipeline: {active_deals} deals in progress")
    
    # Business process patterns
    try:
        business_counts = {k: len(v) for k, v in business_types.items() if isinstance(v, (list, tuple))}
        if business_counts:
            top_business = max(business_counts.items(), key=lambda x: x[1])
            insights.append(f"Primary Business Process: {top_business[0]} ({top_business[1]} deals)")
    except Exception as e:
        insights.append(f"Business process analysis error: {str(e)}")
    
    # Customer behavior patterns
    try:
        repeat_customers = [customer for customer, deals in customer_patterns.items() if isinstance(deals, (list, tuple)) and len(deals) > 1]
        if repeat_customers:
            insights.append(f"Repeat Customer Process: {len(repeat_customers)} customers with multiple deals")
    except Exception as e:
        insights.append(f"Customer pattern analysis error: {str(e)}")
    
    return insights

def identify_process_bottlenecks(deals_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Identify process bottlenecks and inefficiencies
    """
    deals = deals_data.get('deals', [])
    
    # Stage duration analysis
    stage_analysis = defaultdict(list)
    bottlenecks = []
    
    for deal in deals:
        props = deal.get('properties', {})
        stage = props.get('dealstage', 'unknown')
        created = props.get('createdate')
        modified = props.get('hs_lastmodifieddate')
        
        if created and modified:
            try:
                created_dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                modified_dt = datetime.fromisoformat(modified.replace('Z', '+00:00'))
                duration = (modified_dt - created_dt).days
                stage_analysis[stage].append(duration)
            except:
                continue
    
    # Identify bottlenecks
    for stage, durations in stage_analysis.items():
        if durations:
            avg_duration = sum(durations) / len(durations)
            if avg_duration > 7:  # More than a week
                bottlenecks.append({
                    'stage': stage,
                    'avg_duration_days': round(avg_duration, 1),
                    'deal_count': len(durations)
                })
    
    return {
        'bottlenecks': bottlenecks,
        'stage_performance': {stage: {
            'avg_duration': round(sum(durations) / len(durations), 1),
            'deal_count': len(durations)
        } for stage, durations in stage_analysis.items() if durations}
    }

def map_customer_workflows(deals_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Map customer workflow patterns and journeys
    """
    deals = deals_data.get('deals', [])
    
    # Group by customer
    customer_workflows = defaultdict(list)
    
    for deal in deals:
        props = deal.get('properties', {})
        
        deal_name = props.get('dealname') or ''
        
        if ' - ' in deal_name:
            customer = deal_name.split(' - ')[0]
            customer_workflows[customer].append({
                'deal_name': deal_name,
                'stage': props.get('dealstage'),
                'amount': props.get('amount'),
                'created': props.get('createdate'),
                'status': 'won' if props.get('dealstage') == 'closedwon' else 'active'
            })
    
    # Analyze workflow patterns
    workflow_patterns = {}
    for customer, deals in customer_workflows.items():
        if len(deals) > 1:
            # Calculate total value safely
            total_value = 0
            for d in deals:
                if d['amount']:
                    try:
                        total_value += float(d['amount'])
                    except (ValueError, TypeError):
                        pass
            
            workflow_patterns[customer] = {
                'deal_count': len(deals),
                'total_value': total_value,
                'workflow_type': _classify_workflow(deals),
                'deals': deals
            }
    
    return {
        'customer_workflows': dict(customer_workflows),
        'workflow_patterns': workflow_patterns,
        'insights': _generate_workflow_insights(workflow_patterns)
    }

def _classify_workflow(deals):
    """Classify customer workflow type"""
    if len(deals) > 2:
        return 'multi_project_customer'
    elif any('expansion' in d.get('deal_name', '').lower() for d in deals if d.get('deal_name')):
        return 'expansion_customer'
    else:
        return 'repeat_customer'

def _generate_workflow_insights(workflow_patterns):
    """Generate workflow insights"""
    insights = []
    
    if workflow_patterns:
        total_repeat_value = sum(p['total_value'] for p in workflow_patterns.values())
        insights.append(f"Repeat Customer Value: ${total_repeat_value:,.2f}")
        
        workflow_types = Counter(p['workflow_type'] for p in workflow_patterns.values())
        for wf_type, count in workflow_types.items():
            insights.append(f"{wf_type.replace('_', ' ').title()}: {count} customers")
    
    return insights

def _generate_key_insights(process_analysis, bottleneck_analysis, workflow_analysis, temporal_analysis):
    """Generate key business insights"""
    insights = []
    
    # Business process insights
    business_types = process_analysis.get('business_types', {})
    if business_types:
        # business_types already contains counts (integers), not lists
        top_processes = sorted(business_types.items(), key=lambda x: x[1], reverse=True)[:3]
        insights.append(f"Top Business Processes: {', '.join([f'{p[0]} ({p[1]} deals)' for p in top_processes])}")
    
    # Bottleneck insights
    if bottleneck_analysis.get('bottlenecks'):
        worst_bottleneck = max(bottleneck_analysis['bottlenecks'], key=lambda x: x.get('avg_duration_days', 0))
        insights.append(f"Major Bottleneck: {worst_bottleneck['stage']} stage ({worst_bottleneck.get('avg_duration_days', 0)} days avg)")
    
    # Customer workflow insights
    workflow_patterns = workflow_analysis.get('workflow_patterns', {})
    if workflow_patterns:
        insights.append(f"Customer Retention: {len(workflow_patterns)} repeat customers identified")
    
    # Temporal insights
    if temporal_analysis.get('peak_creation_day'):
        insights.append(f"Peak deal creation day: {temporal_analysis['peak_creation_day']}")
    
    return insights

def _generate_recommendations(process_analysis, bottleneck_analysis, workflow_analysis, temporal_analysis):
    """Generate process improvement recommendations"""
    recommendations = []
    
    # Process optimization
    stage_dist = process_analysis.get('stage_distribution', {})
    appointment_scheduled = stage_dist.get('appointmentscheduled', 0)
    if appointment_scheduled > 5:
        recommendations.append("High volume in 'Appointment Scheduled' - implement automated scheduling system")
    
    # Bottleneck resolution
    if bottleneck_analysis.get('bottlenecks'):
        recommendations.append("Address identified bottlenecks with process automation and time-based triggers")
    
    # Customer workflow optimization
    if workflow_analysis.get('workflow_patterns'):
        recommendations.append("Implement customer success workflows for repeat customers")
        recommendations.append("Create expansion opportunity alerts for existing customers")
    
    # Business process recommendations
    business_counts = process_analysis.get('business_types', {})  # Already contains counts
    if len(business_counts) > 3:
        recommendations.append("Consider specialized pipelines for different business processes")
    
    # Temporal recommendations
    if temporal_analysis.get('peak_creation_day'):
        recommendations.append(f"Optimize resources for {temporal_analysis['peak_creation_day']} - your peak deal creation day")
    
    return recommendations


def get_schema() -> Dict[str, Any]:
    """Return the JSON schema for this tool's input parameters."""
    return {
        "type": "object",
        "properties": {
            "analysis_period_days": {
                "type": "integer",
                "description": "Number of days back to analyze deals",
                "default": 90,
                "minimum": 1,
                "maximum": 365
            },
            "max_deals": {
                "type": "integer",
                "description": "Maximum number of deals to analyze",
                "default": 200,
                "minimum": 10,
                "maximum": 1000
            },
            "include_closed_deals": {
                "type": "boolean",
                "description": "Whether to include closed (won/lost) deals in analysis",
                "default": True
            },
            "min_deal_amount": {
                "type": "number",
                "description": "Minimum deal amount to include (optional filter)",
                "minimum": 0
            },
            "max_deal_amount": {
                "type": "number", 
                "description": "Maximum deal amount to include (optional filter)",
                "minimum": 0
            },
            "pipeline_filter": {
                "type": "string",
                "description": "Specific pipeline to analyze (optional filter)"
            },
            "stage_filter": {
                "type": "string",
                "description": "Specific deal stage to analyze (optional filter)"
            },
            "owner_filter": {
                "type": "string",
                "description": "Specific owner ID to analyze (optional filter)"
            },
            "business_type_analysis_depth": {
                "type": "integer",
                "description": "Number of top business types to analyze in detail",
                "default": 10,
                "minimum": 1,
                "maximum": 50
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
    
    # Handle command line arguments for schema export
def main():
    """Main function to handle CLI arguments and process data"""
    import sys
    
    # Test mode for autodiscovery (REQUIRED)
    if len(sys.argv) == 2 and sys.argv[1] == '{"__test__": true}':
        print(json.dumps({"success": True, "_simple": True}))
        return
    
    # Handle schema export
    if len(sys.argv) == 2 and sys.argv[1] == "--fractalic-dump-schema":
        schema = {
            "name": "process_mining_analysis",
            "description": "Comprehensive process mining analysis for HubSpot deal data and customer journeys",
            "parameters": {
                "type": "object",
                "properties": {
                    "analysis_scope": {
                        "type": "string",
                        "enum": ["comprehensive", "deals", "workflows", "bottlenecks"],
                        "description": "Scope of the process mining analysis",
                        "default": "comprehensive"
                    },
                    "analysis_period_days": {
                        "type": "integer",
                        "minimum": 30,
                        "maximum": 365,
                        "description": "Number of days to analyze",
                        "default": 90
                    },
                    "max_deals": {
                        "type": "integer",
                        "minimum": 10,
                        "maximum": 500,
                        "description": "Maximum number of deals to analyze",
                        "default": 100
                    }
                }
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
        print(json.dumps(result, ensure_ascii=False, default=str))
        
    except Exception as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    main()
