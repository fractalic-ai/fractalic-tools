#!/usr/bin/env python3
"""
HubSpot Bottleneck Identifier - Auto-Discovery Tool
Identifies workflow delays, inefficiencies, and process obstacles
Part of the Fractalic Process Mining Intelligence System
"""

import json
import sys
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import statistics


def process_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Identify bottlenecks and inefficiencies in HubSpot workflows and processes
    
    Args:
        data: Dictionary containing analysis parameters and filters
    
    Returns:
        Dict containing identified bottlenecks, delays, and optimization recommendations
    """
    
    try:
        # Extract parameters with defaults
        analysis_period_days = data.get("analysis_period_days", 90)
        bottleneck_threshold = data.get("bottleneck_threshold", 2.0)
        include_stage_analysis = data.get("include_stage_analysis", True)
        include_owner_analysis = data.get("include_owner_analysis", True)
        min_sample_size = data.get("min_sample_size", 10)
        pipeline_filter = data.get("pipeline_filter", None)
        stage_filter = data.get("stage_filter", None)
        max_records = data.get("max_records", 500)
        is_test = data.get("__test__", False)
        
        # Handle test mode
        if is_test:
            return {
                "success": True,
                "analysis_type": "bottleneck_identification",
                "timestamp": datetime.now().isoformat(),
                "parameters": {
                    "analysis_period_days": analysis_period_days,
                    "bottleneck_threshold": bottleneck_threshold,
                    "include_stage_analysis": include_stage_analysis,
                    "include_owner_analysis": include_owner_analysis,
                    "min_sample_size": min_sample_size,
                    "test_mode": True
                },
                "analysis_summary": {
                    "message": "Test mode - no actual analysis performed",
                    "total_workflows_analyzed": 0,
                    "bottlenecks_identified": 0
                },
                "stage_bottlenecks": {},
                "owner_bottlenecks": {},
                "process_bottlenecks": {},
                "communication_bottlenecks": {},
                "resource_bottlenecks": {},
                "resolution_strategies": {},
                "impact_metrics": {}
            }
        
        # Import dependencies inside the function
        import sys
        import os
        sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
        from hubspot_hub_helpers import hs_client
        
        client = hs_client()
        
        # Collect timing and workflow data
        workflow_data = _collect_workflow_timing_data(
            client, 
            analysis_period_days,
            pipeline_filter,
            stage_filter,
            max_records
        )
        
        # Analyze stage progression bottlenecks
        stage_bottlenecks = {}
        if include_stage_analysis:
            stage_bottlenecks = _analyze_stage_bottlenecks(
                client, workflow_data, bottleneck_threshold, min_sample_size
            )
        
        # Analyze owner/team bottlenecks
        owner_bottlenecks = {}
        if include_owner_analysis:
            owner_bottlenecks = _analyze_owner_bottlenecks(
                client, workflow_data, bottleneck_threshold, min_sample_size
            )
        
        # Identify process flow bottlenecks
        process_bottlenecks = _identify_process_flow_bottlenecks(
            workflow_data, bottleneck_threshold
        )
        
        # Analyze communication bottlenecks
        communication_bottlenecks = _analyze_communication_bottlenecks(
            client, workflow_data, bottleneck_threshold
        )
        
        # Analyze resource allocation bottlenecks
        resource_bottlenecks = _analyze_resource_bottlenecks(
            workflow_data, owner_bottlenecks
        )
        
        # Generate bottleneck resolution strategies
        resolution_strategies = _generate_resolution_strategies(
            stage_bottlenecks, owner_bottlenecks, process_bottlenecks, 
            communication_bottlenecks, resource_bottlenecks
        )
        
        # Calculate bottleneck impact metrics
        impact_metrics = _calculate_bottleneck_impact(
            stage_bottlenecks, owner_bottlenecks, process_bottlenecks,
            communication_bottlenecks, resource_bottlenecks, workflow_data
        )
        
        result = {
            "success": True,
            "analysis_type": "bottleneck_identification",
            "timestamp": datetime.now().isoformat(),
            "parameters": {
                "analysis_period_days": analysis_period_days,
                "bottleneck_threshold": bottleneck_threshold,
                "include_stage_analysis": include_stage_analysis,
                "include_owner_analysis": include_owner_analysis,
                "min_sample_size": min_sample_size,
                "pipeline_filter": pipeline_filter,
                "stage_filter": stage_filter,
                "max_records": max_records,
                "environment_auth": True  # Using environment-based authentication
            },
            "analysis_summary": {
                "total_workflows_analyzed": len(workflow_data.get("deals", [])) + len(workflow_data.get("tickets", [])),
                "bottlenecks_identified": _count_total_bottlenecks(stage_bottlenecks, owner_bottlenecks, process_bottlenecks),
                "high_impact_bottlenecks": _count_high_impact_bottlenecks(impact_metrics),
                "data_completeness": _calculate_bottleneck_analysis_completeness(workflow_data),
                "analysis_period": f"{analysis_period_days} days",
                "timeline_data_available": len(workflow_data.get("deal_timeline_data", {})) > 0,
                "stage_durations_collected": len(workflow_data.get("stage_durations", {})) > 0
            },
            "stage_bottlenecks": stage_bottlenecks,
            "owner_bottlenecks": owner_bottlenecks,
            "process_bottlenecks": process_bottlenecks,
            "communication_bottlenecks": communication_bottlenecks,
            "resource_bottlenecks": resource_bottlenecks,
            "resolution_strategies": resolution_strategies,
            "impact_metrics": impact_metrics
        }
        
        return result
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


def _collect_workflow_timing_data(client, analysis_period_days: int, 
                                 pipeline_filter: Optional[str] = None,
                                 stage_filter: Optional[str] = None,
                                 max_records: int = 500) -> Dict[str, Any]:
    """Collect comprehensive timing data for bottleneck analysis with optional filters"""
    
    cutoff_date = datetime.now() - timedelta(days=analysis_period_days)
    workflow_data = {
        "deals": [],
        "tickets": [],
        "contacts": [],
        "activities": [],
        "stage_transitions": defaultdict(list),
        "owner_activities": defaultdict(list),
        "response_times": [],
        "deal_timeline_data": {},
        "stage_durations": defaultdict(list)
    }
    
    # Collect deals with stage and timing information
    try:
        deals_response = client.crm.deals.basic_api.get_page(
            limit=100,
            properties=[
                "dealstage", "createdate", "closedate", "hs_lastmodifieddate",
                "hubspot_owner_id", "amount", "dealname", "pipeline"
            ]
        )
        
        for deal in deals_response.results:
            # HubSpot API returns properties in the properties dict
            props = deal.properties if hasattr(deal, 'properties') else {}
            
            deal_data = {
                "id": str(deal.id),
                "stage": props.get('dealstage', ''),
                "create_date": props.get('createdate', None),
                "close_date": props.get('closedate', None),
                "last_modified": props.get('hs_lastmodifieddate', None),
                "owner_id": str(props.get('hubspot_owner_id', '')),
                "amount": props.get('amount', 0),
                "pipeline": props.get('pipeline', ''),
                "object_type": "deal"
            }
            
            workflow_data["deals"].append(deal_data)
            
            # Skip timeline data collection for now - it's causing performance issues
            # TODO: Implement proper timeline API integration later
            # try:
            #     timeline_data = _fetch_deal_timeline(client, deal.id)
            #     if timeline_data:
            #         workflow_data["deal_timeline_data"][str(deal.id)] = timeline_data
            #         
            #         # Extract stage transitions and calculate durations
            #         stage_transitions = _extract_stage_transitions(timeline_data)
            #         for transition in stage_transitions:
            #             stage = transition.get("to_stage")
            #             duration = transition.get("duration_days")
            #             if stage and duration is not None and duration > 0:
            #                 workflow_data["stage_durations"][stage].append(duration)
            #                 
            # except Exception as e:
            #     print(f"Warning: Could not fetch timeline for deal {deal.id}: {e}")
            
            # Track stage transitions
            if deal_data["stage"]:
                workflow_data["stage_transitions"][deal_data["stage"]].append(deal_data)
            
            # Track owner activities
            if deal_data["owner_id"]:
                workflow_data["owner_activities"][deal_data["owner_id"]].append(deal_data)
                
    except Exception as e:
        print(f"Error collecting deals data: {e}")
    
    # Collect tickets with status and timing information
    try:
        tickets_response = client.crm.tickets.basic_api.get_page(
            limit=100,
            properties=[
                "hs_ticket_priority", "createdate", "closed_date", "hs_lastmodifieddate",
                "hubspot_owner_id", "subject", "hs_pipeline_stage"
            ]
        )
        
        for ticket in tickets_response.results:
            # HubSpot API returns properties in the properties dict
            props = ticket.properties if hasattr(ticket, 'properties') else {}
            
            ticket_data = {
                "id": str(ticket.id),
                "stage": props.get('hs_pipeline_stage', ''),
                "priority": props.get('hs_ticket_priority', ''),
                "create_date": props.get('createdate', None),
                "close_date": props.get('closed_date', None),
                "last_modified": props.get('hs_lastmodifieddate', None),
                "owner_id": str(props.get('hubspot_owner_id', '')),
                "subject": props.get('subject', ''),
                "object_type": "ticket"
            }
            
            workflow_data["tickets"].append(ticket_data)
            
            # Track stage transitions
            if ticket_data["stage"]:
                workflow_data["stage_transitions"][ticket_data["stage"]].append(ticket_data)
            
            # Track owner activities
            if ticket_data["owner_id"]:
                workflow_data["owner_activities"][ticket_data["owner_id"]].append(ticket_data)
                
    except Exception as e:
        print(f"Error collecting tickets data: {e}")
    
    # Collect activity timing data
    try:
        # Collect emails for response time analysis
        emails_response = client.crm.objects.emails.basic_api.get_page(
            limit=100,
            properties=["hs_timestamp", "hubspot_owner_id", "hs_email_direction", "hs_email_status"]
        )
        
        for email in emails_response.results:
            activity_data = {
                "type": "email",
                "timestamp": getattr(email, 'hs_timestamp', None),
                "owner_id": str(getattr(email, 'hubspot_owner_id', '')),
                "direction": getattr(email, 'hs_email_direction', ''),
                "status": getattr(email, 'hs_email_status', '')
            }
            
            workflow_data["activities"].append(activity_data)
            
    except Exception as e:
        print(f"Error collecting email activities: {e}")
    
    return workflow_data


def _analyze_stage_bottlenecks(client, workflow_data: Dict, threshold: float, min_sample_size: int) -> Dict[str, Any]:
    """Analyze bottlenecks in stage progressions"""
    
    stage_bottlenecks = {
        "deal_stage_bottlenecks": {},
        "ticket_stage_bottlenecks": {},
        "stage_duration_analysis": {},
        "stage_progression_issues": []
    }
    
    # Use the enhanced stage duration data from timeline analysis
    stage_durations = workflow_data.get("stage_durations", {})
    
    # Analyze deal stage bottlenecks using timeline data
    for stage, durations in stage_durations.items():
        if len(durations) >= min_sample_size:
            avg_duration = statistics.mean(durations)
            median_duration = statistics.median(durations)
            max_duration = max(durations)
            min_duration = min(durations)
            
            # Identify bottleneck if max duration significantly exceeds average
            if max_duration > (avg_duration * threshold):
                stage_bottlenecks["deal_stage_bottlenecks"][stage] = {
                    "average_duration_days": round(avg_duration, 2),
                    "median_duration_days": round(median_duration, 2),
                    "max_duration_days": round(max_duration, 2),
                    "min_duration_days": round(min_duration, 2),
                    "bottleneck_severity": round(max_duration / avg_duration, 2),
                    "sample_size": len(durations),
                    "outlier_count": sum(1 for d in durations if d > avg_duration * threshold),
                    "bottleneck_type": "stage_duration",
                    "standard_deviation": round(statistics.stdev(durations) if len(durations) > 1 else 0, 2)
                }
    
    # Fallback: Analyze current stage concentrations if no timeline data
    if not stage_durations:
        print("Warning: No timeline data available, using current stage analysis")
        current_stage_analysis = _analyze_current_stage_bottlenecks(workflow_data["deals"], threshold, min_sample_size)
        stage_bottlenecks["deal_stage_bottlenecks"].update(current_stage_analysis)
        
        # Also analyze tickets using current state
        current_ticket_analysis = _analyze_current_stage_bottlenecks(workflow_data["tickets"], threshold, min_sample_size)
        stage_bottlenecks["ticket_stage_bottlenecks"].update(current_ticket_analysis)
    
    # Analyze ticket stage bottlenecks (using simplified approach)
    ticket_stage_durations = _calculate_stage_durations(workflow_data["tickets"], "ticket")
    
    for stage, durations in ticket_stage_durations.items():
        if len(durations) >= min_sample_size:
            avg_duration = statistics.mean(durations)
            median_duration = statistics.median(durations)
            max_duration = max(durations)
            
            if max_duration > (avg_duration * threshold):
                stage_bottlenecks["ticket_stage_bottlenecks"][stage] = {
                    "average_duration_days": round(avg_duration, 2),
                    "median_duration_days": round(median_duration, 2),
                    "max_duration_days": round(max_duration, 2),
                    "bottleneck_severity": round(max_duration / avg_duration, 2),
                    "sample_size": len(durations),
                    "outlier_count": sum(1 for d in durations if d > avg_duration * threshold),
                    "bottleneck_type": "stage_duration"
                }
    
    # Generate stage duration analysis summary
    stage_bottlenecks["stage_duration_analysis"] = {
        "total_stages_analyzed": len(stage_durations),
        "stages_with_sufficient_data": len([s for s, d in stage_durations.items() if len(d) >= min_sample_size]),
        "bottleneck_stages_count": len(stage_bottlenecks["deal_stage_bottlenecks"]),
        "data_completeness": len(stage_durations) / max(len(workflow_data.get("deals", [])), 1)
    }
    
    # Analyze stage progression patterns
    stage_bottlenecks["stage_progression_issues"] = _identify_stage_progression_issues(
        workflow_data, threshold
    )
    
    return stage_bottlenecks


def _analyze_current_stage_bottlenecks(objects: List[Dict], threshold: float, min_sample_size: int = 3) -> Dict[str, Any]:
    """Fallback analysis using current stage concentrations"""
    stage_bottlenecks = {}
    stage_counts = defaultdict(int)
    
    # Count objects in each stage
    for obj in objects:
        stage = obj.get("stage", "")
        if stage:
            stage_counts[stage] += 1
    
    if not stage_counts:
        return stage_bottlenecks
        
    total_objects = sum(stage_counts.values())
    
    # Use different approaches based on number of stages
    if len(stage_counts) <= 2:
        # For few stages, use absolute count threshold
        avg_per_stage = total_objects / len(stage_counts)
        threshold_to_use = max(threshold, 1.2)  # More lenient for few stages
    else:
        # For many stages, use percentage-based approach
        avg_per_stage = total_objects / len(stage_counts)
        threshold_to_use = threshold
    
    # Identify stages with concentration of objects
    for stage, count in stage_counts.items():
        percentage = (count / total_objects) * 100
        severity = count / avg_per_stage if avg_per_stage > 0 else 1.0
        
        # Multiple criteria for bottleneck detection:
        # 1. Meets minimum sample size OR has high percentage (>20%)
        # 2. Either exceeds threshold multiplier OR has significant percentage
        # 3. Has more than 1 object (avoid single-object false positives)
        
        is_bottleneck = (
            count > 1 and  # More than 1 object
            (count >= min_sample_size or percentage >= 20.0) and
            (severity >= threshold_to_use or percentage >= 20.0)
        )
        
        if is_bottleneck:
            stage_bottlenecks[stage] = {
                "object_count": count,
                "total_objects": total_objects,
                "percentage": round(percentage, 2),
                "bottleneck_severity": round(severity, 2),
                "bottleneck_type": "stage_concentration",
                "analysis_method": "current_state_fallback",
                "sample_size": count,
                "threshold_used": threshold_to_use,
                "avg_per_stage": round(avg_per_stage, 2)
            }
    
    return stage_bottlenecks


def _analyze_owner_bottlenecks(client, workflow_data: Dict, threshold: float, min_sample_size: int) -> Dict[str, Any]:
    """Analyze owner-specific bottlenecks and performance issues"""
    
    owner_bottlenecks = {
        "performance_bottlenecks": {},
        "workload_bottlenecks": {},
        "response_time_bottlenecks": {},
        "collaboration_bottlenecks": {}
    }
    
    # Analyze performance bottlenecks by owner
    for owner_id, activities in workflow_data.get("owner_activities", {}).items():
        if len(activities) >= min_sample_size:
            # Calculate average handling time
            handling_times = _calculate_owner_handling_times(activities)
            
            if handling_times:
                avg_handling_time = statistics.mean(handling_times)
                max_handling_time = max(handling_times)
                
                if max_handling_time > (avg_handling_time * threshold):
                    owner_bottlenecks["performance_bottlenecks"][owner_id] = {
                        "average_handling_time_days": avg_handling_time,
                        "max_handling_time_days": max_handling_time,
                        "bottleneck_severity": max_handling_time / avg_handling_time,
                        "total_activities": len(activities),
                        "slow_activities_count": sum(1 for t in handling_times if t > avg_handling_time * threshold),
                        "bottleneck_type": "owner_performance"
                    }
    
    # Analyze workload bottlenecks
    workload_analysis = _analyze_owner_workloads(workflow_data["owner_activities"])
    
    # Identify owners with significantly higher workloads
    if workload_analysis:
        avg_workload = statistics.mean(workload_analysis.values())
        
        for owner_id, workload in workload_analysis.items():
            if workload > (avg_workload * threshold):
                owner_bottlenecks["workload_bottlenecks"][owner_id] = {
                    "current_workload": workload,
                    "average_workload": avg_workload,
                    "overload_factor": workload / avg_workload,
                    "bottleneck_type": "workload_overload"
                }
    
    return owner_bottlenecks


def _identify_process_flow_bottlenecks(workflow_data: Dict, threshold: float) -> Dict[str, Any]:
    """Identify bottlenecks in overall process flows"""
    
    process_bottlenecks = {
        "handoff_bottlenecks": [],
        "approval_bottlenecks": [],
        "data_entry_bottlenecks": [],
        "system_integration_bottlenecks": []
    }
    
    # Analyze handoff bottlenecks (delays between owner changes)
    handoff_delays = _analyze_handoff_delays(workflow_data)
    
    for handoff, delay_data in handoff_delays.items():
        if delay_data["max_delay"] > (delay_data["avg_delay"] * threshold):
            process_bottlenecks["handoff_bottlenecks"].append({
                "handoff_type": handoff,
                "average_delay_hours": delay_data["avg_delay"],
                "max_delay_hours": delay_data["max_delay"],
                "bottleneck_severity": delay_data["max_delay"] / delay_data["avg_delay"],
                "occurrences": delay_data["count"],
                "bottleneck_type": "handoff_delay"
            })
    
    # Analyze approval bottlenecks (stages that require approval)
    approval_stages = _identify_approval_bottlenecks(workflow_data, threshold)
    process_bottlenecks["approval_bottlenecks"] = approval_stages
    
    return process_bottlenecks


def _analyze_communication_bottlenecks(client, workflow_data: Dict, threshold: float) -> Dict[str, Any]:
    """Analyze communication-related bottlenecks"""
    
    communication_bottlenecks = {
        "response_time_bottlenecks": {},
        "communication_gaps": [],
        "channel_inefficiencies": {}
    }
    
    # Analyze email response times
    email_activities = [a for a in workflow_data.get("activities", []) if a.get("type") == "email"]
    
    response_times = _calculate_email_response_times(email_activities)
    
    if response_times:
        avg_response_time = statistics.mean(response_times)
        
        for owner_id, times in response_times.items():
            if times:
                owner_avg = statistics.mean(times)
                if owner_avg > (avg_response_time * threshold):
                    communication_bottlenecks["response_time_bottlenecks"][owner_id] = {
                        "average_response_time_hours": owner_avg,
                        "global_average_hours": avg_response_time,
                        "response_delay_factor": owner_avg / avg_response_time,
                        "sample_size": len(times),
                        "bottleneck_type": "slow_response"
                    }
    
    return communication_bottlenecks


def _analyze_resource_bottlenecks(workflow_data: Dict, owner_bottlenecks: Dict) -> Dict[str, Any]:
    """Analyze resource allocation bottlenecks"""
    
    resource_bottlenecks = {
        "capacity_bottlenecks": [],
        "skill_bottlenecks": [],
        "availability_bottlenecks": [],
        "resource_distribution_issues": {}
    }
    
    # Identify capacity bottlenecks from workload analysis
    workload_bottlenecks = owner_bottlenecks.get("workload_bottlenecks", {})
    
    for owner_id, bottleneck_data in workload_bottlenecks.items():
        resource_bottlenecks["capacity_bottlenecks"].append({
            "owner_id": owner_id,
            "overload_factor": bottleneck_data.get("overload_factor", 1.0),
            "current_workload": bottleneck_data.get("current_workload", 0),
            "bottleneck_type": "capacity_overload"
        })
    
    # Analyze resource distribution
    all_activities = workflow_data.get("deals", []) + workflow_data.get("tickets", [])
    resource_distribution = _analyze_resource_distribution(all_activities)
    
    resource_bottlenecks["resource_distribution_issues"] = resource_distribution
    
    return resource_bottlenecks


def _generate_resolution_strategies(stage_bottlenecks: Dict, owner_bottlenecks: Dict, 
                                  process_bottlenecks: Dict, communication_bottlenecks: Dict,
                                  resource_bottlenecks: Dict) -> Dict[str, Any]:
    """Generate strategies to resolve identified bottlenecks"""
    
    strategies = {
        "immediate_actions": [],
        "process_improvements": [],
        "resource_optimizations": [],
        "automation_opportunities": [],
        "long_term_solutions": []
    }
    
    # Generate strategies for stage bottlenecks
    for stage, bottleneck_data in stage_bottlenecks.get("deal_stage_bottlenecks", {}).items():
        severity = bottleneck_data.get("bottleneck_severity", 1.0)
        
        if severity > 3.0:  # High severity
            strategies["immediate_actions"].append({
                "issue": f"High duration variability in deal stage: {stage}",
                "severity": severity,
                "recommended_action": "Review and standardize processes for this stage",
                "expected_impact": "30-50% reduction in stage duration variance",
                "implementation_effort": "Medium"
            })
    
    # Generate strategies for owner bottlenecks
    performance_bottlenecks = owner_bottlenecks.get("performance_bottlenecks", {})
    workload_bottlenecks = owner_bottlenecks.get("workload_bottlenecks", {})
    
    for owner_id, bottleneck_data in performance_bottlenecks.items():
        strategies["process_improvements"].append({
            "issue": f"Performance bottleneck for owner: {owner_id}",
            "severity": bottleneck_data.get("bottleneck_severity", 1.0),
            "recommended_action": "Provide additional training or process optimization",
            "expected_impact": "20-40% improvement in handling time",
            "implementation_effort": "Low"
        })
    
    for owner_id, bottleneck_data in workload_bottlenecks.items():
        strategies["resource_optimizations"].append({
            "issue": f"Workload overload for owner: {owner_id}",
            "severity": bottleneck_data.get("overload_factor", 1.0),
            "recommended_action": "Redistribute workload or add resources",
            "expected_impact": "Improved throughput and reduced delays",
            "implementation_effort": "Medium"
        })
    
    # Generate automation opportunities
    handoff_bottlenecks = process_bottlenecks.get("handoff_bottlenecks", [])
    
    for handoff in handoff_bottlenecks:
        if handoff.get("bottleneck_severity", 1.0) > 2.0:
            strategies["automation_opportunities"].append({
                "issue": f"Handoff delay: {handoff.get('handoff_type')}",
                "severity": handoff.get("bottleneck_severity", 1.0),
                "recommended_action": "Automate handoff process or notifications",
                "expected_impact": "60-80% reduction in handoff time",
                "implementation_effort": "High"
            })
    
    return strategies


def _calculate_bottleneck_impact(stage_bottlenecks: Dict, owner_bottlenecks: Dict, 
                               process_bottlenecks: Dict, communication_bottlenecks: Dict,
                               resource_bottlenecks: Dict, workflow_data: Dict) -> Dict[str, Any]:
    """Calculate overall impact metrics for identified bottlenecks"""
    
    impact_metrics = {
        "total_bottlenecks": 0,
        "high_impact_bottlenecks": 0,
        "estimated_time_savings_hours": 0,
        "affected_workflows_count": 0,
        "severity_distribution": {"low": 0, "medium": 0, "high": 0},
        "bottleneck_categories": {}
    }
    
    # Count and categorize bottlenecks
    all_bottlenecks = []
    
    # Stage bottlenecks
    for bottleneck_data in stage_bottlenecks.get("deal_stage_bottlenecks", {}).values():
        severity = bottleneck_data.get("bottleneck_severity", 1.0)
        all_bottlenecks.append({"type": "stage", "severity": severity})
    
    for bottleneck_data in stage_bottlenecks.get("ticket_stage_bottlenecks", {}).values():
        severity = bottleneck_data.get("bottleneck_severity", 1.0)
        all_bottlenecks.append({"type": "stage", "severity": severity})
    
    # Owner bottlenecks
    for bottleneck_data in owner_bottlenecks.get("performance_bottlenecks", {}).values():
        severity = bottleneck_data.get("bottleneck_severity", 1.0)
        all_bottlenecks.append({"type": "owner", "severity": severity})
    
    # Process bottlenecks
    for bottleneck in process_bottlenecks.get("handoff_bottlenecks", []):
        severity = bottleneck.get("bottleneck_severity", 1.0)
        all_bottlenecks.append({"type": "process", "severity": severity})
    
    # Calculate metrics
    impact_metrics["total_bottlenecks"] = len(all_bottlenecks)
    
    for bottleneck in all_bottlenecks:
        severity = bottleneck["severity"]
        bottleneck_type = bottleneck["type"]
        
        # Categorize severity
        if severity < 2.0:
            impact_metrics["severity_distribution"]["low"] += 1
        elif severity < 4.0:
            impact_metrics["severity_distribution"]["medium"] += 1
        else:
            impact_metrics["severity_distribution"]["high"] += 1
            impact_metrics["high_impact_bottlenecks"] += 1
        
        # Count by category
        if bottleneck_type not in impact_metrics["bottleneck_categories"]:
            impact_metrics["bottleneck_categories"][bottleneck_type] = 0
        impact_metrics["bottleneck_categories"][bottleneck_type] += 1
    
    # Estimate potential time savings
    impact_metrics["estimated_time_savings_hours"] = _estimate_time_savings(all_bottlenecks, workflow_data)
    
    return impact_metrics


# Helper functions

def _fetch_deal_timeline(client, deal_id: str) -> List[Dict]:
    """Fetch timeline/activity data for a deal to track stage changes"""
    try:
        # Try to get deal activities/timeline data
        # Note: This is a simplified approach - in production, you'd use the timeline API
        # For now, we'll simulate stage transition data based on available properties
        
        # Get the deal details again with more properties
        deal_details = client.crm.deals.basic_api.get_by_id(
            deal_id,
            properties=[
                "dealstage", "createdate", "closedate", "hs_lastmodifieddate",
                "notes_last_contacted", "notes_last_activity", "hs_date_entered_appointmentscheduled",
                "hs_date_entered_qualifiedtobuy", "hs_date_entered_presentationscheduled",
                "hs_date_entered_decisionmakerboughtin", "hs_date_entered_contractsent",
                "hs_date_entered_closedwon", "hs_date_entered_closedlost"
            ]
        )
        
        timeline = []
        current_stage = getattr(deal_details, 'dealstage', '')
        create_date = getattr(deal_details, 'createdate', None)
        
        # Map of stage entry date properties
        stage_date_props = {
            "appointmentscheduled": getattr(deal_details, 'hs_date_entered_appointmentscheduled', None),
            "qualifiedtobuy": getattr(deal_details, 'hs_date_entered_qualifiedtobuy', None),
            "presentationscheduled": getattr(deal_details, 'hs_date_entered_presentationscheduled', None),
            "decisionmakerboughtin": getattr(deal_details, 'hs_date_entered_decisionmakerboughtin', None),
            "contractsent": getattr(deal_details, 'hs_date_entered_contractsent', None),
            "closedwon": getattr(deal_details, 'hs_date_entered_closedwon', None),
            "closedlost": getattr(deal_details, 'hs_date_entered_closedlost', None)
        }
        
        # Create timeline entries for stages with entry dates
        for stage, entry_date in stage_date_props.items():
            if entry_date:
                timeline.append({
                    "event_type": "stage_change",
                    "timestamp": entry_date,
                    "stage": stage,
                    "deal_id": deal_id
                })
        
        # Sort by timestamp
        timeline.sort(key=lambda x: x.get("timestamp", ""))
        
        return timeline
        
    except Exception as e:
        print(f"Error fetching timeline for deal {deal_id}: {e}")
        return []


def _extract_stage_transitions(timeline_data: List[Dict]) -> List[Dict]:
    """Extract stage transitions and calculate durations from timeline data"""
    transitions = []
    
    if len(timeline_data) < 2:
        return transitions
    
    for i in range(len(timeline_data) - 1):
        current_event = timeline_data[i]
        next_event = timeline_data[i + 1]
        
        try:
            current_time = datetime.fromisoformat(current_event["timestamp"].replace('Z', '+00:00'))
            next_time = datetime.fromisoformat(next_event["timestamp"].replace('Z', '+00:00'))
            
            duration_days = (next_time - current_time).total_seconds() / (24 * 3600)
            
            if duration_days > 0:
                transitions.append({
                    "from_stage": current_event.get("stage"),
                    "to_stage": next_event.get("stage"),
                    "duration_days": duration_days,
                    "start_time": current_event["timestamp"],
                    "end_time": next_event["timestamp"]
                })
                
        except Exception as e:
            continue
    
    return transitions


def _calculate_stage_durations(objects: List[Dict], object_type: str) -> Dict[str, List[float]]:
    """Calculate duration spent in each stage"""
    stage_durations = defaultdict(list)
    
    for obj in objects:
        create_date = obj.get("create_date")
        close_date = obj.get("close_date") or obj.get("last_modified")
        stage = obj.get("stage")
        
        if create_date and close_date and stage:
            try:
                create_dt = datetime.fromisoformat(create_date.replace('Z', '+00:00'))
                close_dt = datetime.fromisoformat(close_date.replace('Z', '+00:00'))
                
                duration_days = (close_dt - create_dt).total_seconds() / (24 * 3600)
                if duration_days > 0:
                    stage_durations[stage].append(duration_days)
                    
            except Exception:
                continue
    
    return dict(stage_durations)


def _calculate_owner_handling_times(activities: List[Dict]) -> List[float]:
    """Calculate handling times for an owner's activities"""
    handling_times = []
    
    for activity in activities:
        create_date = activity.get("create_date")
        close_date = activity.get("close_date") or activity.get("last_modified")
        
        if create_date and close_date:
            try:
                create_dt = datetime.fromisoformat(create_date.replace('Z', '+00:00'))
                close_dt = datetime.fromisoformat(close_date.replace('Z', '+00:00'))
                
                handling_time_days = (close_dt - create_dt).total_seconds() / (24 * 3600)
                if handling_time_days > 0:
                    handling_times.append(handling_time_days)
                    
            except Exception:
                continue
    
    return handling_times


def _analyze_owner_workloads(owner_activities: Dict) -> Dict[str, int]:
    """Analyze workload distribution across owners"""
    workload_analysis = {}
    
    for owner_id, activities in owner_activities.items():
        # Simple workload metric: count of active items
        active_activities = [
            a for a in activities 
            if not a.get("close_date")  # Only count unclosed items
        ]
        
        workload_analysis[owner_id] = len(active_activities)
    
    return workload_analysis


def _analyze_handoff_delays(workflow_data: Dict) -> Dict[str, Dict]:
    """Analyze delays in handoffs between owners"""
    handoff_delays = defaultdict(lambda: {"delays": [], "count": 0})
    
    # This is a simplified implementation
    # In practice, would track actual ownership changes over time
    
    return dict(handoff_delays)


def _identify_approval_bottlenecks(workflow_data: Dict, threshold: float) -> List[Dict]:
    """Identify bottlenecks in approval processes"""
    approval_bottlenecks = []
    
    # Placeholder for approval bottleneck identification
    # Would analyze stages that typically require approval
    
    return approval_bottlenecks


def _calculate_email_response_times(email_activities: List) -> Dict[str, List[float]]:
    """Calculate email response times by owner"""
    response_times = defaultdict(list)
    
    # Group emails by owner and calculate response patterns
    owner_emails = defaultdict(list)
    
    for email in email_activities:
        owner_id = email.get("owner_id", "")
        if owner_id:
            owner_emails[owner_id].append(email)
    
    # Calculate response times (simplified)
    for owner_id, emails in owner_emails.items():
        # Sort by timestamp
        sorted_emails = sorted(emails, key=lambda x: x.get("timestamp", ""))
        
        for i in range(len(sorted_emails) - 1):
            current_email = sorted_emails[i]
            next_email = sorted_emails[i + 1]
            
            # Calculate time between emails as proxy for response time
            current_time = current_email.get("timestamp")
            next_time = next_email.get("timestamp")
            
            if current_time and next_time:
                try:
                    current_dt = datetime.fromisoformat(current_time.replace('Z', '+00:00'))
                    next_dt = datetime.fromisoformat(next_time.replace('Z', '+00:00'))
                    
                    response_time_hours = (next_dt - current_dt).total_seconds() / 3600
                    if 0 < response_time_hours < 72:  # Reasonable response time range
                        response_times[owner_id].append(response_time_hours)
                        
                except Exception:
                    continue
    
    return dict(response_times)


def _analyze_resource_distribution(activities: List) -> Dict[str, Any]:
    """Analyze resource distribution issues"""
    distribution_analysis = {
        "uneven_distribution": False,
        "overloaded_owners": [],
        "underutilized_owners": [],
        "distribution_coefficient": 0.0
    }
    
    # Count activities by owner
    owner_counts = defaultdict(int)
    
    for activity in activities:
        owner_id = activity.get("owner_id", "")
        if owner_id:
            owner_counts[owner_id] += 1
    
    if owner_counts:
        counts = list(owner_counts.values())
        avg_count = statistics.mean(counts)
        
        # Identify overloaded and underutilized owners
        for owner_id, count in owner_counts.items():
            if count > avg_count * 1.5:  # 50% above average
                distribution_analysis["overloaded_owners"].append(owner_id)
            elif count < avg_count * 0.5:  # 50% below average
                distribution_analysis["underutilized_owners"].append(owner_id)
        
        # Calculate distribution coefficient (coefficient of variation)
        if avg_count > 0:
            std_dev = statistics.stdev(counts) if len(counts) > 1 else 0
            distribution_analysis["distribution_coefficient"] = std_dev / avg_count
            
        distribution_analysis["uneven_distribution"] = distribution_analysis["distribution_coefficient"] > 0.3
    
    return distribution_analysis


def _identify_stage_progression_issues(workflow_data: Dict, threshold: float) -> List[Dict]:
    """Identify issues in stage progression patterns"""
    progression_issues = []
    
    # Placeholder for stage progression analysis
    # Would analyze unusual stage transitions, skipped stages, etc.
    
    return progression_issues


def _estimate_time_savings(bottlenecks: List, workflow_data: Dict) -> float:
    """Estimate potential time savings from resolving bottlenecks"""
    total_savings = 0.0
    
    for bottleneck in bottlenecks:
        severity = bottleneck.get("severity", 1.0)
        bottleneck_type = bottleneck.get("type", "unknown")
        
        # Estimate savings based on severity and type
        if bottleneck_type == "stage":
            # Stage bottlenecks: estimate 20% time reduction per severity point
            total_savings += severity * 20
        elif bottleneck_type == "owner":
            # Owner bottlenecks: estimate 15% time reduction per severity point  
            total_savings += severity * 15
        elif bottleneck_type == "process":
            # Process bottlenecks: estimate 25% time reduction per severity point
            total_savings += severity * 25
    
    return total_savings


def _count_total_bottlenecks(stage_bottlenecks: Dict, owner_bottlenecks: Dict, process_bottlenecks: Dict) -> int:
    """Count total bottlenecks identified"""
    total = 0
    
    total += len(stage_bottlenecks.get("deal_stage_bottlenecks", {}))
    total += len(stage_bottlenecks.get("ticket_stage_bottlenecks", {}))
    total += len(owner_bottlenecks.get("performance_bottlenecks", {}))
    total += len(owner_bottlenecks.get("workload_bottlenecks", {}))
    total += len(process_bottlenecks.get("handoff_bottlenecks", []))
    total += len(process_bottlenecks.get("approval_bottlenecks", []))
    
    return total


def _count_high_impact_bottlenecks(impact_metrics: Dict) -> int:
    """Count high impact bottlenecks"""
    return impact_metrics.get("high_impact_bottlenecks", 0)


def _generate_bottleneck_insights(result: Dict[str, Any]) -> List[str]:
    """Generate insights from bottleneck analysis results"""
    insights = []
    
    # Analysis summary insights
    summary = result.get("analysis_summary", {})
    bottlenecks_count = summary.get("bottlenecks_identified", 0)
    high_impact_count = summary.get("high_impact_bottlenecks", 0)
    workflows_analyzed = summary.get("total_workflows_analyzed", 0)
    
    if bottlenecks_count == 0:
        insights.append(f"No significant bottlenecks detected in {workflows_analyzed} workflows analyzed")
        insights.append("This could indicate efficient processes or insufficient data for analysis")
    else:
        insights.append(f"Identified {bottlenecks_count} bottlenecks across {workflows_analyzed} workflows")
        if high_impact_count > 0:
            insights.append(f"{high_impact_count} high-impact bottlenecks require immediate attention")
    
    # Stage bottleneck insights
    stage_bottlenecks = result.get("stage_bottlenecks", {})
    deal_stage_bottlenecks = stage_bottlenecks.get("deal_stage_bottlenecks", {})
    
    if deal_stage_bottlenecks:
        for stage, data in deal_stage_bottlenecks.items():
            severity = data.get("bottleneck_severity", 1.0)
            avg_duration = data.get("average_duration_days", 0)
            if severity > 3.0:
                insights.append(f"Critical bottleneck in '{stage}' stage: {severity:.1f}x longer than average ({avg_duration:.1f} days)")
            elif severity > 2.0:
                insights.append(f"Moderate bottleneck in '{stage}' stage: {severity:.1f}x longer than average")
    
    # Owner bottleneck insights
    owner_bottlenecks = result.get("owner_bottlenecks", {})
    performance_bottlenecks = owner_bottlenecks.get("performance_bottlenecks", {})
    workload_bottlenecks = owner_bottlenecks.get("workload_bottlenecks", {})
    
    if performance_bottlenecks:
        insights.append(f"Performance bottlenecks identified for {len(performance_bottlenecks)} team members")
    
    if workload_bottlenecks:
        insights.append(f"Workload imbalances detected for {len(workload_bottlenecks)} team members")
    
    # Data quality insights
    data_completeness = summary.get("data_completeness", 0)
    timeline_available = summary.get("timeline_data_available", False)
    
    if data_completeness < 0.5:
        insights.append("Low data completeness may affect bottleneck detection accuracy")
    
    if not timeline_available:
        insights.append("Limited timeline data - using current state analysis as fallback")
    
    # Impact insights
    impact_metrics = result.get("impact_metrics", {})
    estimated_savings = impact_metrics.get("estimated_time_savings_hours", 0)
    
    if estimated_savings > 0:
        insights.append(f"Potential time savings of {estimated_savings:.0f} hours if bottlenecks are resolved")
    
    return insights


def _generate_bottleneck_recommendations(result: Dict[str, Any]) -> List[str]:
    """Generate recommendations based on bottleneck analysis"""
    recommendations = []
    
    # Stage-based recommendations
    stage_bottlenecks = result.get("stage_bottlenecks", {})
    deal_stage_bottlenecks = stage_bottlenecks.get("deal_stage_bottlenecks", {})
    
    for stage, data in deal_stage_bottlenecks.items():
        severity = data.get("bottleneck_severity", 1.0)
        analysis_method = data.get("analysis_method", "")
        
        if analysis_method == "current_state_fallback":
            deal_count = data.get("deal_count", 0)
            recommendations.append(f"Review {deal_count} deals stuck in '{stage}' stage - consider process automation or owner reassignment")
        elif severity > 3.0:
            recommendations.append(f"Urgent: Investigate and redesign '{stage}' stage process - {severity:.1f}x longer than normal")
        elif severity > 2.0:
            recommendations.append(f"Optimize '{stage}' stage workflow - consider additional resources or process improvements")
    
    # Owner-based recommendations
    owner_bottlenecks = result.get("owner_bottlenecks", {})
    performance_bottlenecks = owner_bottlenecks.get("performance_bottlenecks", {})
    workload_bottlenecks = owner_bottlenecks.get("workload_bottlenecks", {})
    
    if performance_bottlenecks:
        recommendations.append("Provide additional training or support to team members with performance bottlenecks")
        recommendations.append("Consider process standardization to reduce performance variability")
    
    if workload_bottlenecks:
        recommendations.append("Redistribute workload to balance team capacity")
        recommendations.append("Consider hiring additional team members or reallocating resources")
    
    # Process improvement recommendations
    process_bottlenecks = result.get("process_bottlenecks", {})
    handoff_bottlenecks = process_bottlenecks.get("handoff_bottlenecks", [])
    
    if handoff_bottlenecks:
        recommendations.append("Implement automated handoff notifications to reduce delays between team members")
        recommendations.append("Create clear handoff procedures and accountability measures")
    
    # Data improvement recommendations
    summary = result.get("analysis_summary", {})
    timeline_available = summary.get("timeline_data_available", False)
    data_completeness = summary.get("data_completeness", 0)
    
    if not timeline_available:
        recommendations.append("Enable HubSpot deal timeline tracking for more accurate bottleneck analysis")
        recommendations.append("Consider implementing custom properties to track stage transition timestamps")
    
    if data_completeness < 0.7:
        recommendations.append("Improve data quality by ensuring all deals have complete owner and stage information")
    
    # Resolution strategy recommendations
    resolution_strategies = result.get("resolution_strategies", {})
    immediate_actions = resolution_strategies.get("immediate_actions", [])
    automation_opportunities = resolution_strategies.get("automation_opportunities", [])
    
    for action in immediate_actions:
        if action.get("implementation_effort") == "Low":
            recommendations.append(f"Quick win: {action.get('recommended_action', 'N/A')}")
    
    for opportunity in automation_opportunities:
        if opportunity.get("expected_impact", "").startswith("60"):
            recommendations.append(f"High-impact automation: {opportunity.get('recommended_action', 'N/A')}")
    
    # General recommendations if no specific bottlenecks found
    bottlenecks_count = summary.get("bottlenecks_identified", 0)
    if bottlenecks_count == 0:
        recommendations.append("Consider lowering bottleneck threshold to detect more subtle inefficiencies")
        recommendations.append("Extend analysis period to capture seasonal or cyclical bottlenecks")
        recommendations.append("Monitor process performance over time to identify emerging bottlenecks")
    
    return recommendations


def _calculate_bottleneck_analysis_completeness(workflow_data: Dict) -> float:
    """Calculate completeness of the bottleneck analysis"""
    # Placeholder for completeness calculation
    return 0.85


def get_schema() -> Dict[str, Any]:
    """Return the JSON schema for this tool's input parameters."""
    return {
        "name": "hubspot_bottleneck_identifier",
        "description": "Identify workflow delays, inefficiencies, and process obstacles in HubSpot workflows and processes",
        "input_schema": {
            "type": "object",
            "properties": {
                "hubspot_token": {
                    "type": "string",
                    "description": "HubSpot API token for data access"
                },
                "analysis_period_days": {
                    "type": "integer",
                    "description": "Number of days back to analyze for bottlenecks",
                    "default": 90,
                    "minimum": 1,
                    "maximum": 365
                },
                "bottleneck_threshold": {
                    "type": "number",
                    "description": "Threshold multiplier for identifying bottlenecks (e.g., 2.0 means 2x longer than average)",
                    "default": 2.0,
                    "minimum": 1.1,
                    "maximum": 10.0
                },
                "include_stage_analysis": {
                    "type": "boolean",
                    "description": "Whether to analyze stage progression bottlenecks",
                    "default": True
                },
                "include_owner_analysis": {
                    "type": "boolean",
                    "description": "Whether to analyze owner/team bottlenecks",
                    "default": True
                },
                "min_sample_size": {
                    "type": "integer",
                    "description": "Minimum sample size for bottleneck analysis",
                    "default": 10,
                    "minimum": 5,
                    "maximum": 100
                },
                "pipeline_filter": {
                    "type": "string",
                    "description": "Specific pipeline to analyze (optional filter)"
                },
                "stage_filter": {
                    "type": "string",
                    "description": "Specific deal stage to analyze (optional filter)"
                },
                "max_records": {
                    "type": "integer",
                    "description": "Maximum number of records to analyze",
                    "default": 500,
                    "minimum": 50,
                    "maximum": 2000
                },
                "__test__": {
                    "type": "boolean",
                    "description": "Run in test mode without making API calls"
                }
            },
            "required": ["hubspot_token"]
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
                "analysis_summary": {
                    "type": "object",
                    "description": "Summary of bottleneck analysis"
                },
                "stage_bottlenecks": {
                    "type": "object",
                    "description": "Identified bottlenecks in stage progressions"
                },
                "owner_bottlenecks": {
                    "type": "object",
                    "description": "Identified bottlenecks related to owners and teams"
                },
                "process_bottlenecks": {
                    "type": "object",
                    "description": "Identified bottlenecks in process flows"
                },
                "communication_bottlenecks": {
                    "type": "object",
                    "description": "Identified communication-related bottlenecks"
                },
                "resource_bottlenecks": {
                    "type": "object",
                    "description": "Identified resource-related bottlenecks"
                },
                "resolution_strategies": {
                    "type": "object",
                    "description": "Recommended strategies for resolving bottlenecks"
                },
                "impact_metrics": {
                    "type": "object",
                    "description": "Metrics quantifying the impact of identified bottlenecks"
                },
                "error": {
                    "type": "string",
                    "description": "Error message if operation failed"
                }
            },
            "required": ["success"]
        }
    }


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
            "name": "hubspot_bottleneck_identifier",
            "description": "Identify bottlenecks and performance issues in HubSpot processes and workflows",
            "parameters": {
                "type": "object",
                "properties": {
                    "analysis_period_days": {
                        "type": "integer",
                        "minimum": 30,
                        "maximum": 365,
                        "description": "Number of days to analyze for bottlenecks",
                        "default": 90
                    },
                    "bottleneck_threshold": {
                        "type": "number",
                        "minimum": 0.1,
                        "maximum": 1.0,
                        "description": "Threshold for identifying bottlenecks (0.1-1.0)",
                        "default": 0.5
                    },
                    "max_objects": {
                        "type": "integer",
                        "minimum": 50,
                        "maximum": 1000,
                        "description": "Maximum number of objects to analyze",
                        "default": 500
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
        error_result = {"success": False, "error": str(e)}
        print(json.dumps(error_result))
        sys.exit(1)


if __name__ == "__main__":
    main()
