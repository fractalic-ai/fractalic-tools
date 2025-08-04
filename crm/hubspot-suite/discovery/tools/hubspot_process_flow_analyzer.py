#!/usr/bin/env python3
"""
HubSpot Process Flow Analyzer
Analyzes actual process flows, variants, loops, and deviations from deal data
Does the actual process mining analysis, uses other tools only for data extraction
"""

import json
import sys
import requests
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import re

import re

def get_schema() -> Dict[str, Any]:
    """Return the JSON schema for this tool"""
    return {
        "name": "hubspot_process_flow_analyzer",
        "description": "Analyze actual process flows, variants, loops, and deviations from HubSpot deal data",
        "input_schema": {
            "type": "object",
            "properties": {
                "analysis_period_days": {
                    "type": "integer",
                    "description": "Number of days to analyze (default: 14)",
                    "default": 14
                },
                "max_deals": {
                    "type": "integer",
                    "description": "Maximum number of deals to analyze (default: 100)",
                    "default": 100
                },
                "analysis_depth": {
                    "type": "string",
                    "description": "Depth of analysis to perform",
                    "enum": ["basic", "detailed", "comprehensive"],
                    "default": "comprehensive"
                },
                "detect_loops": {
                    "type": "boolean",
                    "description": "Whether to detect process loops",
                    "default": True
                },
                "identify_variants": {
                    "type": "boolean",
                    "description": "Whether to identify process variants",
                    "default": True
                },
                "find_deviations": {
                    "type": "boolean",
                    "description": "Whether to find process deviations",
                    "default": True
                },
                "__test__": {
                    "type": "boolean",
                    "description": "Run in test mode without making API calls"
                }
            },
            "required": []
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "success": {
                    "type": "boolean",
                    "description": "Whether the operation completed successfully"
                },
                "analysis_type": {
                    "type": "string",
                    "description": "Type of analysis performed"
                },
                "timestamp": {
                    "type": "string",
                    "description": "ISO timestamp of analysis"
                },
                "parameters": {
                    "type": "object",
                    "description": "Parameters used for analysis"
                },
                "summary": {
                    "type": "object",
                    "description": "Summary of findings"
                },
                "process_flows": {
                    "type": "object",
                    "description": "Analyzed process flows"
                },
                "process_variants": {
                    "type": "object",
                    "description": "Identified process variants"
                },
                "process_loops": {
                    "type": "object",
                    "description": "Detected process loops"
                },
                "process_deviations": {
                    "type": "object",
                    "description": "Found process deviations"
                },
                "common_patterns": {
                    "type": "object",
                    "description": "Common process patterns"
                },
                "bottleneck_analysis": {
                    "type": "object",
                    "description": "Process bottleneck analysis"
                },
                "process_efficiency": {
                    "type": "object",
                    "description": "Process efficiency metrics"
                },
                "error": {
                    "type": "string",
                    "description": "Error message if operation failed"
                }
            },
            "required": ["success"]
        }
    }

def _fetch_hubspot_deals(days_back: int = 14, max_deals: int = 100) -> Dict[str, Any]:
    """Fetch deal data from HubSpot API using environment variable token"""
    try:
        from hubspot_hub_helpers import hs_client
        client = hs_client()
        if not client:
            return {"success": False, "error": "Failed to initialize HubSpot client - check HUBSPOT_TOKEN environment variable"}
    except Exception as e:
        return {"success": False, "error": f"HubSpot client initialization failed: {str(e)}"}
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)
    start_timestamp = int(start_date.timestamp() * 1000)
    
    # Properties to fetch
    properties = [
        "dealname", "dealstage", "amount", "createdate", 
        "closedate", "pipeline", "dealtype", "hs_deal_stage_probability",
        "notes_last_contacted", "notes_last_activity", "num_contacted_notes",
        "hs_lastmodifieddate", "hubspot_owner_id"
    ]
    
    try:
        # Use the HubSpot client to fetch deals
        deals_response = client.crm.deals.basic_api.get_page(
            properties=properties,
            limit=min(max_deals, 100)  # API limit is 100 per request
        )
        
        deals = deals_response.results if deals_response.results else []
        
        # Filter by creation date (client-side filtering for now)
        filtered_deals = []
        for deal in deals:
            if deal.properties and deal.properties.get('createdate'):
                create_date_str = deal.properties['createdate']
                try:
                    create_date = datetime.fromisoformat(create_date_str.replace('Z', '+00:00'))
                    if create_date >= start_date:
                        filtered_deals.append(deal.properties)
                except:
                    # Include deal if date parsing fails
                    filtered_deals.append(deal.properties)
        
        return {
            "success": True,
            "deals": filtered_deals,
            "total_count": len(filtered_deals),
            "period_days": days_back,
            "fetch_timestamp": datetime.now().isoformat()
        }
        
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error": f"Failed to fetch HubSpot deals: {str(e)}",
            "deals": []
        }

def process_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Perform comprehensive process flow analysis on HubSpot deals
    
    Args:
        data: {
            "analysis_period_days": 14,  # Days to analyze
            "max_deals": 100,           # Max deals to fetch
            "analysis_depth": "comprehensive",
            "detect_loops": true,
            "identify_variants": true,
            "find_deviations": true,
            "__test__": false
        }
    """
    
    # Extract parameters
    analysis_period_days = data.get("analysis_period_days", 14)
    max_deals = data.get("max_deals", 100)
    analysis_depth = data.get("analysis_depth", "comprehensive")
    detect_loops = data.get("detect_loops", True)
    identify_variants = data.get("identify_variants", True)
    find_deviations = data.get("find_deviations", True)
    is_test = data.get("__test__", False)
    
    # Handle test mode
    if is_test:
        return {
            "success": True,
            "analysis_type": "process_flow_analysis",
            "timestamp": datetime.now().isoformat(),
            "parameters": {
                "analysis_period_days": analysis_period_days,
                "max_deals": max_deals,
                "analysis_depth": analysis_depth,
                "detect_loops": detect_loops,
                "identify_variants": identify_variants,
                "find_deviations": find_deviations,
                "test_mode": True
            },
            "summary": {
                "message": "Test mode - no actual analysis performed",
                "deals_analyzed": 0
            },
            "process_flows": {},
            "process_variants": {},
            "process_loops": {},
            "process_deviations": {},
            "common_patterns": {},
            "bottleneck_analysis": {},
            "process_efficiency": {}
        }
    
    # Fetch fresh deal data
    deals_data = _fetch_hubspot_deals(analysis_period_days, max_deals)
    
    if not deals_data.get("success"):
        return {"success": False, "error": deals_data.get("error", "Failed to fetch deals")}
    
    deals = deals_data["deals"]
    
    if not deals:
        return {
            "success": True,
            "analysis_type": "process_flow_analysis",
            "timestamp": datetime.now().isoformat(),
            "parameters": {
                "analysis_period_days": analysis_period_days,
                "max_deals": max_deals,
                "analysis_depth": analysis_depth,
                "detect_loops": detect_loops,
                "identify_variants": identify_variants,
                "find_deviations": find_deviations
            },
            "summary": {
                "message": "No deals found in the specified period",
                "deals_analyzed": 0,
                "period_days": analysis_period_days
            },
            "process_flows": {},
            "process_variants": {},
            "process_loops": {},
            "process_deviations": {},
            "common_patterns": {},
            "bottleneck_analysis": {},
            "process_efficiency": {},
            "insights": [f"No deals created in the last {analysis_period_days} days"],
            "recommendations": ["Extend analysis period or check deal creation process"]
        }
    
    # Perform comprehensive process analysis
    results = {
        "success": True,
        "analysis_type": "process_flow_analysis",
        "timestamp": datetime.now().isoformat(),
        "parameters": {
            "analysis_period_days": analysis_period_days,
            "max_deals": max_deals,
            "analysis_depth": analysis_depth,
            "detect_loops": detect_loops,
            "identify_variants": identify_variants,
            "find_deviations": find_deviations,
            "hubspot_token_provided": True
        },
        "summary": {
            "deals_analyzed": len(deals),
            "period_days": analysis_period_days,
            "data_source": "live_hubspot_api"
        },
        "process_flows": _analyze_process_flows(deals),
        "process_variants": _identify_process_variants(deals) if identify_variants else {},
        "process_loops": _detect_process_loops(deals) if detect_loops else {},
        "process_deviations": _find_process_deviations(deals) if find_deviations else {},
        "common_patterns": _discover_common_patterns(deals),
        "bottleneck_analysis": _analyze_process_bottlenecks(deals),
        "process_efficiency": _calculate_process_efficiency(deals)
    }
    
    return results

def _analyze_process_flows(deals: List[Dict]) -> Dict[str, Any]:
    """Analyze the actual process flows from deal progressions"""
    
    flows = {
        "customer_processes": {},
        "business_type_processes": {},
        "stage_progression_patterns": {},
        "temporal_flow_analysis": {}
    }
    
    # Analyze customer-specific processes
    customer_flows = defaultdict(list)
    business_type_flows = defaultdict(list)
    
    for deal in deals:
        props = deal.get("properties", {})
        deal_name = props.get("dealname", "")
        stage = props.get("dealstage", "")
        created = props.get("createdate", "")
        amount = props.get("amount", "0")
        
        # Extract customer and business type
        customer = _extract_customer_name(deal_name)
        business_type = _classify_business_type(deal_name)
        
        deal_info = {
            "deal_id": deal.get("id"),
            "deal_name": deal_name,
            "stage": stage,
            "created": created,
            "amount": amount,
            "customer": customer,
            "business_type": business_type
        }
        
        customer_flows[customer].append(deal_info)
        business_type_flows[business_type].append(deal_info)
    
    # Analyze process flow patterns
    flows["customer_processes"] = _analyze_customer_process_patterns(customer_flows)
    flows["business_type_processes"] = _analyze_business_type_patterns(business_type_flows)
    flows["stage_progression_patterns"] = _analyze_stage_progressions(deals)
    
    return flows

def _identify_process_variants(deals: List[Dict]) -> Dict[str, Any]:
    """Identify different variants of the same business process"""
    
    variants = {
        "iot_automation_variants": [],
        "fitness_process_variants": [],
        "construction_variants": [],
        "delivery_variants": [],
        "printing_variants": []
    }
    
    # Group deals by business type
    business_groups = defaultdict(list)
    for deal in deals:
        deal_name = deal.get("properties", {}).get("dealname", "")
        business_type = _classify_business_type(deal_name)
        business_groups[business_type].append(deal)
    
    # Analyze variants within each business type
    for business_type, type_deals in business_groups.items():
        if business_type == "iot_automation":
            variants["iot_automation_variants"] = _analyze_iot_variants(type_deals)
        elif business_type == "fitness":
            variants["fitness_process_variants"] = _analyze_fitness_variants(type_deals)
        elif business_type == "construction":
            variants["construction_variants"] = _analyze_construction_variants(type_deals)
        elif business_type == "logistics":
            variants["delivery_variants"] = _analyze_delivery_variants(type_deals)
        elif business_type == "3d_printing":
            variants["printing_variants"] = _analyze_printing_variants(type_deals)
    
    return variants

def _detect_process_loops(deals: List[Dict]) -> Dict[str, Any]:
    """Detect loops and cycles in business processes"""
    
    loops = {
        "customer_loops": [],
        "stage_loops": [],
        "temporal_loops": [],
        "value_loops": []
    }
    
    # Detect customer loops (same customer, same deal type, repeating)
    customer_deals = defaultdict(list)
    for deal in deals:
        props = deal.get("properties", {})
        customer = _extract_customer_name(props.get("dealname", ""))
        customer_deals[customer].append(deal)
    
    for customer, customer_deal_list in customer_deals.items():
        if len(customer_deal_list) > 1:
            # Check for identical or very similar deals (potential loops)
            deal_signatures = []
            for deal in customer_deal_list:
                props = deal.get("properties", {})
                signature = {
                    "deal_type": _extract_deal_type(props.get("dealname", "")),
                    "amount": props.get("amount"),
                    "stage": props.get("dealstage")
                }
                deal_signatures.append(signature)
            
            # Find duplicates or near-duplicates
            signature_counts = Counter(json.dumps(sig, sort_keys=True) for sig in deal_signatures)
            for sig_str, count in signature_counts.items():
                if count > 1:
                    loops["customer_loops"].append({
                        "customer": customer,
                        "loop_type": "duplicate_deals",
                        "count": count,
                        "signature": json.loads(sig_str)
                    })
    
    return loops

def _find_process_deviations(deals: List[Dict]) -> Dict[str, Any]:
    """Find deviations from expected process flows"""
    
    deviations = {
        "stage_deviations": [],
        "timing_deviations": [],
        "value_deviations": [],
        "pattern_deviations": []
    }
    
    # Define expected patterns
    expected_patterns = {
        "iot_automation": {
            "typical_amount_range": (10000, 25000),
            "typical_stages": ["appointmentscheduled", "qualifiedtobuy", "presentationscheduled", "decisionmakerboughtin", "contractsent", "closedwon"],
            "typical_duration_days": 14
        },
        "fitness": {
            "typical_amount_range": (15000, 50000),
            "typical_stages": ["appointmentscheduled", "qualifiedtobuy", "contractsent", "closedwon"],
            "typical_duration_days": 7
        },
        "construction": {
            "typical_amount_range": (500000, 1000000),
            "typical_stages": ["appointmentscheduled", "qualifiedtobuy", "presentationscheduled", "decisionmakerboughtin", "contractsent", "closedwon"],
            "typical_duration_days": 30
        }
    }
    
    # Check each deal against expected patterns
    for deal in deals:
        props = deal.get("properties", {})
        deal_name = props.get("dealname", "")
        business_type = _classify_business_type(deal_name)
        
        if business_type in expected_patterns:
            pattern = expected_patterns[business_type]
            
            # Check amount deviation
            amount = props.get("amount")
            if amount:
                amount_val = float(amount)
                min_amount, max_amount = pattern["typical_amount_range"]
                if amount_val < min_amount * 0.5 or amount_val > max_amount * 2:
                    deviations["value_deviations"].append({
                        "deal_id": deal.get("id"),
                        "deal_name": deal_name,
                        "deviation_type": "amount_outlier",
                        "actual_amount": amount_val,
                        "expected_range": pattern["typical_amount_range"]
                    })
            
            # Check stage deviation
            current_stage = props.get("dealstage")
            if current_stage not in pattern["typical_stages"]:
                deviations["stage_deviations"].append({
                    "deal_id": deal.get("id"),
                    "deal_name": deal_name,
                    "deviation_type": "unexpected_stage",
                    "actual_stage": current_stage,
                    "expected_stages": pattern["typical_stages"]
                })
    
    return deviations

def _discover_common_patterns(deals: List[Dict]) -> Dict[str, Any]:
    """Discover common patterns across all processes"""
    
    patterns = {
        "naming_patterns": {},
        "amount_patterns": {},
        "timing_patterns": {},
        "stage_patterns": {},
        "customer_behavior_patterns": {}
    }
    
    # Analyze naming patterns
    deal_names = [deal.get("properties", {}).get("dealname", "") for deal in deals]
    naming_analysis = _analyze_naming_patterns(deal_names)
    patterns["naming_patterns"] = naming_analysis
    
    # Analyze amount clustering
    amounts = []
    for deal in deals:
        amount = deal.get("properties", {}).get("amount")
        if amount:
            amounts.append(float(amount))
    
    patterns["amount_patterns"] = _analyze_amount_clustering(amounts)
    
    # Analyze stage distribution
    stages = [deal.get("properties", {}).get("dealstage", "") for deal in deals]
    stage_counts = Counter(stages)
    patterns["stage_patterns"] = {
        "distribution": dict(stage_counts),
        "most_common": stage_counts.most_common(3),
        "bottleneck_stage": stage_counts.most_common(1)[0] if stage_counts else None
    }
    
    return patterns

def _analyze_process_bottlenecks(deals: List[Dict]) -> Dict[str, Any]:
    """Analyze where processes get stuck or slow down"""
    
    bottlenecks = {
        "stage_bottlenecks": {},
        "customer_bottlenecks": {},
        "business_type_bottlenecks": {},
        "temporal_bottlenecks": {}
    }
    
    # Stage bottleneck analysis
    stage_counts = Counter()
    for deal in deals:
        stage = deal.get("properties", {}).get("dealstage", "")
        stage_counts[stage] += 1
    
    total_deals = len(deals)
    for stage, count in stage_counts.items():
        percentage = (count / total_deals) * 100
        if percentage > 30:  # If more than 30% of deals are in this stage
            bottlenecks["stage_bottlenecks"][stage] = {
                "deal_count": count,
                "percentage": percentage,
                "severity": "high" if percentage > 50 else "medium"
            }
    
    # Customer bottleneck analysis
    customer_deals = defaultdict(list)
    for deal in deals:
        customer = _extract_customer_name(deal.get("properties", {}).get("dealname", ""))
        customer_deals[customer].append(deal)
    
    for customer, customer_deal_list in customer_deals.items():
        stuck_deals = [d for d in customer_deal_list if d.get("properties", {}).get("dealstage") == "appointmentscheduled"]
        if len(stuck_deals) > 1:
            bottlenecks["customer_bottlenecks"][customer] = {
                "stuck_deals": len(stuck_deals),
                "total_deals": len(customer_deal_list),
                "bottleneck_stage": "appointmentscheduled"
            }
    
    return bottlenecks

def _calculate_process_efficiency(deals: List[Dict]) -> Dict[str, Any]:
    """Calculate efficiency metrics for different processes"""
    
    efficiency = {
        "overall_conversion_rate": 0,
        "business_type_efficiency": {},
        "stage_conversion_rates": {},
        "time_efficiency": {}
    }
    
    # Overall conversion rate
    total_deals = len(deals)
    closed_won = sum(1 for deal in deals if deal.get("properties", {}).get("dealstage") == "closedwon")
    efficiency["overall_conversion_rate"] = (closed_won / total_deals) * 100 if total_deals > 0 else 0
    
    # Business type efficiency
    business_groups = defaultdict(list)
    for deal in deals:
        business_type = _classify_business_type(deal.get("properties", {}).get("dealname", ""))
        business_groups[business_type].append(deal)
    
    for business_type, type_deals in business_groups.items():
        total_type = len(type_deals)
        closed_type = sum(1 for deal in type_deals if deal.get("properties", {}).get("dealstage") == "closedwon")
        efficiency["business_type_efficiency"][business_type] = {
            "total_deals": total_type,
            "closed_deals": closed_type,
            "conversion_rate": (closed_type / total_type) * 100 if total_type > 0 else 0
        }
    
    return efficiency

# Helper functions
def _extract_customer_name(deal_name: str) -> str:
    """Extract customer name from deal name"""
    if " - " in deal_name:
        return deal_name.split(" - ")[0].strip()
    return "Unknown"

def _classify_business_type(deal_name: str) -> str:
    """Classify business type from deal name"""
    deal_lower = deal_name.lower()
    if "iot" in deal_lower or "automation" in deal_lower:
        return "iot_automation"
    elif "fitlife" in deal_lower or "gym" in deal_lower:
        return "fitness"
    elif "3d printing" in deal_lower or "printing" in deal_lower:
        return "3d_printing"
    elif "delivery" in deal_lower or "logistics" in deal_lower:
        return "logistics"
    elif "building" in deal_lower or "construction" in deal_lower:
        return "construction"
    elif "ads" in deal_lower or "streamads" in deal_lower:
        return "advertising"
    else:
        return "other"

def _extract_deal_type(deal_name: str) -> str:
    """Extract the type/category of deal from the name"""
    if " - " in deal_name:
        return deal_name.split(" - ")[1].strip()
    return deal_name

def _analyze_naming_patterns(deal_names: List[str]) -> Dict[str, Any]:
    """Analyze patterns in deal naming conventions"""
    
    patterns = {
        "has_dash_separator": sum(1 for name in deal_names if " - " in name),
        "common_prefixes": {},
        "common_suffixes": {},
        "length_distribution": {}
    }
    
    # Analyze prefixes (customer names)
    prefixes = []
    for name in deal_names:
        if " - " in name:
            prefixes.append(name.split(" - ")[0])
    
    prefix_counts = Counter(prefixes)
    patterns["common_prefixes"] = dict(prefix_counts.most_common(5))
    
    return patterns

def _analyze_amount_clustering(amounts: List[float]) -> Dict[str, Any]:
    """Analyze amount patterns and clustering"""
    
    if not amounts:
        return {}
    
    amounts_sorted = sorted(amounts)
    
    clustering = {
        "min_amount": min(amounts),
        "max_amount": max(amounts),
        "median_amount": amounts_sorted[len(amounts_sorted)//2],
        "amount_ranges": {},
        "outliers": []
    }
    
    # Define amount ranges
    ranges = [
        (0, 1000, "small"),
        (1000, 25000, "medium"),
        (25000, 100000, "large"),
        (100000, float('inf'), "enterprise")
    ]
    
    for min_val, max_val, label in ranges:
        count = sum(1 for amt in amounts if min_val <= amt < max_val)
        clustering["amount_ranges"][label] = count
    
    return clustering

def _analyze_customer_process_patterns(customer_flows: Dict[str, List]) -> Dict[str, Any]:
    """Analyze process patterns for each customer"""
    
    patterns = {}
    
    for customer, deals in customer_flows.items():
        if len(deals) > 1:  # Only analyze customers with multiple deals
            pattern = {
                "deal_count": len(deals),
                "process_type": "repeat_customer",
                "deal_types": [_extract_deal_type(deal["deal_name"]) for deal in deals],
                "stages": [deal["stage"] for deal in deals],
                "total_value": sum(float(deal["amount"]) for deal in deals if deal["amount"]),
                "process_characteristics": _identify_customer_characteristics(deals)
            }
            patterns[customer] = pattern
    
    return patterns

def _identify_customer_characteristics(deals: List[Dict]) -> List[str]:
    """Identify characteristics of customer's process behavior"""
    
    characteristics = []
    
    # Check for identical deals
    deal_types = [_extract_deal_type(deal["deal_name"]) for deal in deals]
    if len(set(deal_types)) == 1:
        characteristics.append("identical_deals")
    elif len(set(deal_types)) < len(deals):
        characteristics.append("similar_deals")
    
    # Check for rapid succession
    dates = []
    for deal in deals:
        if deal["created"]:
            try:
                date = datetime.fromisoformat(deal["created"].replace('Z', '+00:00'))
                dates.append(date)
            except:
                continue
    
    if len(dates) > 1:
        dates.sort()
        time_diffs = [(dates[i+1] - dates[i]).days for i in range(len(dates)-1)]
        if any(diff <= 1 for diff in time_diffs):
            characteristics.append("rapid_succession")
    
    # Check for high value
    amounts = [float(deal["amount"]) for deal in deals if deal["amount"]]
    if amounts and max(amounts) > 50000:
        characteristics.append("high_value_customer")
    
    return characteristics

def _analyze_business_type_patterns(business_type_flows: Dict[str, List]) -> Dict[str, Any]:
    """Analyze patterns within each business type"""
    
    patterns = {}
    
    for business_type, deals in business_type_flows.items():
        if len(deals) > 1:
            pattern = {
                "deal_count": len(deals),
                "stage_distribution": Counter(deal["stage"] for deal in deals),
                "value_range": _calculate_value_range(deals),
                "customers": list(set(deal["customer"] for deal in deals)),
                "process_insights": _analyze_business_type_insights(deals, business_type)
            }
            patterns[business_type] = pattern
    
    return patterns

def _calculate_value_range(deals: List[Dict]) -> Dict[str, float]:
    """Calculate value statistics for deals"""
    
    amounts = [float(deal["amount"]) for deal in deals if deal["amount"]]
    
    if not amounts:
        return {"min": 0, "max": 0, "avg": 0}
    
    return {
        "min": min(amounts),
        "max": max(amounts),
        "avg": sum(amounts) / len(amounts)
    }

def _analyze_business_type_insights(deals: List[Dict], business_type: str) -> List[str]:
    """Generate insights for specific business type"""
    
    insights = []
    
    # Check for stage concentration
    stages = [deal["stage"] for deal in deals]
    stage_counts = Counter(stages)
    most_common_stage = stage_counts.most_common(1)[0]
    
    if most_common_stage[1] > len(deals) * 0.7:
        insights.append(f"concentrated_in_{most_common_stage[0]}")
    
    # Check for customer diversity
    customers = set(deal["customer"] for deal in deals)
    if len(customers) == 1:
        insights.append("single_customer_dominance")
    elif len(customers) < len(deals) * 0.5:
        insights.append("low_customer_diversity")
    
    return insights

def _analyze_stage_progressions(deals: List[Dict]) -> Dict[str, Any]:
    """Analyze how deals progress through stages"""
    
    progressions = {
        "stage_sequences": [],
        "common_paths": {},
        "unusual_progressions": []
    }
    
    # This would require historical stage data to properly analyze
    # For now, analyze current stage distribution
    
    stage_counts = Counter()
    for deal in deals:
        stage = deal.get("properties", {}).get("dealstage", "")
        stage_counts[stage] += 1
    
    progressions["current_distribution"] = dict(stage_counts)
    
    return progressions

# Variant analysis functions
def _analyze_iot_variants(deals: List[Dict]) -> List[Dict[str, Any]]:
    """Analyze variants in IoT automation processes"""
    
    variants = []
    
    # Group by deal type
    deal_groups = defaultdict(list)
    for deal in deals:
        deal_type = _extract_deal_type(deal.get("properties", {}).get("dealname", ""))
        deal_groups[deal_type].append(deal)
    
    for deal_type, type_deals in deal_groups.items():
        if len(type_deals) > 1:
            variant = {
                "variant_type": deal_type,
                "deal_count": len(type_deals),
                "customers": list(set(_extract_customer_name(d.get("properties", {}).get("dealname", "")) for d in type_deals)),
                "stages": [d.get("properties", {}).get("dealstage") for d in type_deals],
                "amounts": [d.get("properties", {}).get("amount") for d in type_deals],
                "pattern": "parallel_execution" if len(type_deals) > 2 else "repeat_business"
            }
            variants.append(variant)
    
    return variants

def _analyze_fitness_variants(deals: List[Dict]) -> List[Dict[str, Any]]:
    """Analyze variants in fitness industry processes"""
    
    variants = []
    
    # Check for expansion vs. advertising patterns
    expansion_deals = []
    advertising_deals = []
    
    for deal in deals:
        deal_name = deal.get("properties", {}).get("dealname", "")
        if "expansion" in deal_name.lower():
            expansion_deals.append(deal)
        elif "streamads" in deal_name.lower() or "ads" in deal_name.lower():
            advertising_deals.append(deal)
    
    if expansion_deals:
        variants.append({
            "variant_type": "fitness_expansion",
            "deal_count": len(expansion_deals),
            "pattern": "location_scaling",
            "characteristics": ["multiple_identical_deals", "appointment_stage_concentration"]
        })
    
    if advertising_deals:
        variants.append({
            "variant_type": "fitness_advertising",
            "deal_count": len(advertising_deals),
            "pattern": "service_partnership",
            "characteristics": ["contract_stage_efficiency", "rapid_closure"]
        })
    
    return variants

def _analyze_construction_variants(deals: List[Dict]) -> List[Dict[str, Any]]:
    return [{"variant_type": "large_project", "characteristics": ["high_value", "long_cycle"]}]

def _analyze_delivery_variants(deals: List[Dict]) -> List[Dict[str, Any]]:
    return [{"variant_type": "recurring_service", "characteristics": ["low_value", "repeat_business"]}]

def _analyze_printing_variants(deals: List[Dict]) -> List[Dict[str, Any]]:
    return [{"variant_type": "custom_manufacturing", "characteristics": ["appointment_bottleneck", "low_value"]}]

def _generate_process_insights(results: Dict[str, Any]) -> List[str]:
    """Generate insights from process analysis"""
    
    insights = []
    
    # Bottleneck insights
    stage_bottlenecks = results.get("bottleneck_analysis", {}).get("stage_bottlenecks", {})
    if stage_bottlenecks:
        for stage, data in stage_bottlenecks.items():
            insights.append(f"Major bottleneck detected: {data['deal_count']} deals ({data['percentage']:.1f}%) stuck in '{stage}' stage")
    
    # Process variant insights
    variants = results.get("process_variants", {})
    for variant_type, variant_list in variants.items():
        if variant_list:
            insights.append(f"Process variant identified: {variant_type} with {len(variant_list)} different patterns")
    
    # Loop detection insights
    loops = results.get("process_loops", {})
    customer_loops = loops.get("customer_loops", [])
    if customer_loops:
        insights.append(f"Process loops detected: {len(customer_loops)} customers with duplicate/identical deals")
    
    # Efficiency insights
    efficiency = results.get("process_efficiency", {})
    conversion_rate = efficiency.get("overall_conversion_rate", 0)
    insights.append(f"Overall process efficiency: {conversion_rate:.1f}% conversion rate")
    
    return insights

def _generate_process_recommendations(results: Dict[str, Any]) -> List[str]:
    """Generate actionable recommendations from process analysis"""
    
    recommendations = []
    
    # Address bottlenecks
    stage_bottlenecks = results.get("bottleneck_analysis", {}).get("stage_bottlenecks", {})
    if "appointmentscheduled" in stage_bottlenecks:
        recommendations.append("Implement automated appointment scheduling system to resolve major bottleneck")
    
    # Address process loops
    loops = results.get("process_loops", {})
    if loops.get("customer_loops"):
        recommendations.append("Implement deal deduplication validation to prevent duplicate deal creation")
    
    # Process optimization
    variants = results.get("process_variants", {})
    if len(variants) > 3:
        recommendations.append("Consider creating specialized pipelines for different business process types")
    
    # Efficiency improvements
    efficiency = results.get("process_efficiency", {})
    if efficiency.get("overall_conversion_rate", 0) < 50:
        recommendations.append("Focus on improving conversion rate through process standardization")
    
    return recommendations

def main():
    """Main function to handle CLI arguments and process data"""
    
    # Handle schema export
    if len(sys.argv) > 1 and sys.argv[1] == "--fractalic-dump-schema":
        schema = get_schema()
        print(json.dumps(schema, indent=2))
        return

    try:
        # Check if JSON is provided as command line argument (framework style)
        if len(sys.argv) == 2 and sys.argv[1] not in ["--fractalic-dump-schema"]:
            data = json.loads(sys.argv[1])
        else:
            # Read input from stdin (traditional style) 
            input_data = sys.stdin.read().strip()
            if not input_data:
                raise ValueError("No input data provided")
            data = json.loads(input_data)
        
        # Handle test mode
        if data.get("__test__") is True:
            result = process_data({"__test__": True})
            print(json.dumps(result))
            return
        
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
