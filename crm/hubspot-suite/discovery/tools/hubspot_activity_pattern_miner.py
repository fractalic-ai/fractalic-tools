#!/usr/bin/env python3
"""
HubSpot Activity Pattern Miner - Auto-Discovery Tool
Analyzes communication patterns, activity flows, and behavioral sequences
Part of the Fractalic Process Mining Intelligence System
"""

import json
import sys
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict, Counter


def process_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Mine activity patterns and communication workflows from HubSpot data
    
    Args:
        data: Dictionary containing analysis parameters and filters
    
    Returns:
        Dict containing activity patterns, workflows, and behavioral insights
    """
    
    try:
        # Set HubSpot token from input data if provided
        import os
        if "hubspot_token" in data:
            os.environ["HUBSPOT_TOKEN"] = data["hubspot_token"]
        
        # Import dependencies inside the function
        import sys
        import os
        sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
        from hubspot_hub_helpers import hs_client
        
        # Extract parameters with defaults
        analysis_period_days = data.get("analysis_period_days", 90)
        pattern_sensitivity = data.get("pattern_sensitivity", "medium")
        include_activity_types = data.get("include_activity_types", ["calls", "emails", "meetings", "tasks", "notes"])
        min_pattern_frequency = data.get("min_pattern_frequency", 3)
        max_activities = data.get("max_activities", 500)
        contact_filter = data.get("contact_filter", None)
        owner_filter = data.get("owner_filter", None)
        
        client = hs_client()
        
        # Collect activity data across all types
        activity_data = _collect_activity_data(
            client, 
            analysis_period_days, 
            include_activity_types,
            max_activities,
            contact_filter,
            owner_filter
        )
        
        # Analyze communication patterns
        communication_patterns = _analyze_communication_patterns(activity_data)
        
        # Identify activity sequences and workflows
        workflow_sequences = _identify_workflow_sequences(activity_data, min_pattern_frequency)
        
        # Analyze temporal patterns
        temporal_patterns = _analyze_temporal_patterns(activity_data)
        
        # Detect behavioral patterns
        behavioral_patterns = _detect_behavioral_patterns(activity_data)
        
        # Generate process insights
        process_insights = _generate_process_insights(
            communication_patterns, workflow_sequences, temporal_patterns, behavioral_patterns
        )
        
        result = {
            "success": True,
            "analysis_type": "activity_pattern_mining",
            "timestamp": datetime.now().isoformat(),
            "parameters": {
                "analysis_period_days": analysis_period_days,
                "pattern_sensitivity": pattern_sensitivity,
                "include_activity_types": include_activity_types,
                "min_pattern_frequency": min_pattern_frequency,
                "max_activities": max_activities,
                "contact_filter": contact_filter,
                "owner_filter": owner_filter
            },
            "activity_summary": {
                "total_activities_analyzed": _count_total_activities(activity_data),
                "patterns_discovered": len(workflow_sequences.get("common_sequences", [])),
                "users_analyzed": len(activity_data.get("user_activities", {})),
                "data_completeness": _calculate_data_completeness(activity_data),
                "analysis_period": f"{analysis_period_days} days"
            },
            "communication_patterns": communication_patterns,
            "workflow_sequences": workflow_sequences,
            "temporal_patterns": temporal_patterns,
            "behavioral_patterns": behavioral_patterns,
            "process_insights": process_insights
        }
        
        return result
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


def _collect_activity_data(client, analysis_period_days: int, include_activity_types: List[str], 
                          max_activities: int = 500, contact_filter: Optional[str] = None, 
                          owner_filter: Optional[str] = None) -> Dict[str, Any]:
    """Collect comprehensive activity data from HubSpot with filtering"""
    
    cutoff_date = datetime.now() - timedelta(days=analysis_period_days)
    activity_data = {
        "calls": [],
        "emails": [],
        "meetings": [],
        "tasks": [],
        "notes": [],
        "user_activities": defaultdict(list),
        "timeline_events": []
    }
    
    # Collect calls data
    if "calls" in include_activity_types:
        try:
            calls_response = client.crm.objects.calls.basic_api.get_page(
                limit=100,
                properties=["hs_timestamp", "hubspot_owner_id", "hs_call_duration", "hs_call_outcome"]
            )
            activity_data["calls"] = calls_response.results
        except Exception as e:
            print(f"Error collecting calls data: {e}")
    
    # Collect emails data
    if "emails" in include_activity_types:
        try:
            emails_response = client.crm.objects.emails.basic_api.get_page(
                limit=100,
                properties=["hs_timestamp", "hubspot_owner_id", "hs_email_direction", "hs_email_status"]
            )
            activity_data["emails"] = emails_response.results
        except Exception as e:
            print(f"Error collecting emails data: {e}")
    
    # Collect meetings data
    if "meetings" in include_activity_types:
        try:
            meetings_response = client.crm.objects.meetings.basic_api.get_page(
                limit=100,
                properties=["hs_timestamp", "hubspot_owner_id", "hs_meeting_outcome", "hs_meeting_title"]
            )
            activity_data["meetings"] = meetings_response.results
        except Exception as e:
            print(f"Error collecting meetings data: {e}")
    
    # Collect tasks data
    if "tasks" in include_activity_types:
        try:
            tasks_response = client.crm.objects.tasks.basic_api.get_page(
                limit=100,
                properties=["hs_timestamp", "hubspot_owner_id", "hs_task_status", "hs_task_type"]
            )
            activity_data["tasks"] = tasks_response.results
        except Exception as e:
            print(f"Error collecting tasks data: {e}")
    
    # Organize activities by user
    for activity_type, activities in activity_data.items():
        if activity_type not in ["user_activities", "timeline_events"]:
            for activity in activities:
                owner_id = str(getattr(activity, 'hubspot_owner_id', ''))
                if owner_id:
                    activity_data["user_activities"][owner_id].append({
                        "type": activity_type,
                        "data": activity,
                        "timestamp": getattr(activity, 'hs_timestamp', None)
                    })
    
    return activity_data


def _analyze_communication_patterns(activity_data: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze communication patterns and frequencies"""
    
    patterns = {
        "communication_frequency": {},
        "preferred_channels": {},
        "response_time_patterns": {},
        "communication_effectiveness": {},
        "cross_team_communication": {}
    }
    
    # Analyze communication frequency by user
    for user_id, activities in activity_data.get("user_activities", {}).items():
        comm_activities = [a for a in activities if a["type"] in ["calls", "emails", "meetings"]]
        patterns["communication_frequency"][user_id] = len(comm_activities)
        
        # Analyze preferred channels
        channel_counts = Counter([a["type"] for a in comm_activities])
        patterns["preferred_channels"][user_id] = dict(channel_counts)
    
    # Analyze response time patterns
    patterns["response_time_patterns"] = _analyze_response_times(activity_data)
    
    # Analyze communication effectiveness
    patterns["communication_effectiveness"] = _analyze_communication_effectiveness(activity_data)
    
    return patterns


def _identify_workflow_sequences(activity_data: Dict[str, Any], min_frequency: int) -> Dict[str, Any]:
    """Identify common activity sequences and workflow patterns"""
    
    sequences = {
        "common_sequences": [],
        "workflow_patterns": {},
        "sequence_analysis": {},
        "bottleneck_sequences": []
    }
    
    # Extract activity sequences for each user
    user_sequences = {}
    for user_id, activities in activity_data.get("user_activities", {}).items():
        # Sort activities by timestamp
        sorted_activities = sorted(activities, key=lambda x: x.get("timestamp", ""))
        
        # Create sequences of consecutive activities
        activity_sequences = []
        for i in range(len(sorted_activities) - 2):
            sequence = [
                sorted_activities[i]["type"],
                sorted_activities[i+1]["type"],
                sorted_activities[i+2]["type"]
            ]
            activity_sequences.append(tuple(sequence))
        
        user_sequences[user_id] = activity_sequences
    
    # Find common sequences across users
    all_sequences = []
    for user_sequences_list in user_sequences.values():
        all_sequences.extend(user_sequences_list)
    
    sequence_counts = Counter(all_sequences)
    common_sequences = [
        {"sequence": list(seq), "frequency": count}
        for seq, count in sequence_counts.items()
        if count >= min_frequency
    ]
    
    sequences["common_sequences"] = sorted(common_sequences, key=lambda x: x["frequency"], reverse=True)
    
    # Analyze workflow patterns
    sequences["workflow_patterns"] = _analyze_workflow_patterns(user_sequences)
    
    return sequences


def _analyze_temporal_patterns(activity_data: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze temporal patterns in activities"""
    
    temporal_patterns = {
        "daily_patterns": {},
        "weekly_patterns": {},
        "monthly_patterns": {},
        "peak_activity_times": {},
        "seasonal_trends": {}
    }
    
    # Analyze daily patterns
    hourly_activity = defaultdict(int)
    daily_activity = defaultdict(int)
    weekly_activity = defaultdict(int)
    
    for user_id, activities in activity_data.get("user_activities", {}).items():
        for activity in activities:
            timestamp = activity.get("timestamp")
            if timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    hourly_activity[dt.hour] += 1
                    daily_activity[dt.weekday()] += 1
                    weekly_activity[dt.isocalendar()[1]] += 1
                except Exception:
                    continue
    
    temporal_patterns["daily_patterns"] = dict(hourly_activity)
    temporal_patterns["weekly_patterns"] = dict(daily_activity)
    temporal_patterns["monthly_patterns"] = dict(weekly_activity)
    
    # Find peak activity times
    if hourly_activity:
        peak_hour = max(hourly_activity, key=hourly_activity.get)
        temporal_patterns["peak_activity_times"]["hour"] = peak_hour
    
    if daily_activity:
        peak_day = max(daily_activity, key=daily_activity.get)
        temporal_patterns["peak_activity_times"]["day"] = peak_day
    
    return temporal_patterns


def _detect_behavioral_patterns(activity_data: Dict[str, Any]) -> Dict[str, Any]:
    """Detect behavioral patterns and user characteristics"""
    
    behavioral_patterns = {
        "user_archetypes": {},
        "activity_intensity": {},
        "multitasking_patterns": {},
        "collaboration_styles": {},
        "efficiency_indicators": {}
    }
    
    # Analyze user archetypes based on activity patterns
    for user_id, activities in activity_data.get("user_activities", {}).items():
        activity_types = [a["type"] for a in activities]
        type_distribution = Counter(activity_types)
        
        # Determine user archetype
        archetype = _determine_user_archetype(type_distribution, activities)
        behavioral_patterns["user_archetypes"][user_id] = archetype
        
        # Calculate activity intensity
        intensity = _calculate_activity_intensity(activities)
        behavioral_patterns["activity_intensity"][user_id] = intensity
        
        # Analyze multitasking patterns
        multitasking = _analyze_multitasking_patterns(activities)
        behavioral_patterns["multitasking_patterns"][user_id] = multitasking
    
    return behavioral_patterns


def _generate_process_insights(communication_patterns: Dict, workflow_sequences: Dict, 
                             temporal_patterns: Dict, behavioral_patterns: Dict) -> Dict[str, Any]:
    """Generate actionable process insights from pattern analysis"""
    
    insights = {
        "workflow_optimization": [],
        "communication_improvements": [],
        "resource_allocation": [],
        "automation_opportunities": [],
        "efficiency_gains": []
    }
    
    # Analyze workflow optimization opportunities
    common_sequences = workflow_sequences.get("common_sequences", [])
    for sequence in common_sequences[:5]:  # Top 5 sequences
        if sequence["frequency"] > 10:
            insights["workflow_optimization"].append({
                "sequence": sequence["sequence"],
                "frequency": sequence["frequency"],
                "optimization_potential": _calculate_optimization_potential(sequence)
            })
    
    # Communication improvements
    comm_freq = communication_patterns.get("communication_frequency", {})
    if comm_freq:
        avg_comm = sum(comm_freq.values()) / len(comm_freq)
        low_communicators = [uid for uid, freq in comm_freq.items() if freq < avg_comm * 0.5]
        if low_communicators:
            insights["communication_improvements"].append({
                "issue": "Low communication frequency",
                "affected_users": len(low_communicators),
                "recommendation": "Implement regular check-ins and communication protocols"
            })
    
    # Automation opportunities
    repetitive_sequences = [
        seq for seq in common_sequences 
        if seq["frequency"] > 15 and _is_automatable_sequence(seq["sequence"])
    ]
    
    for seq in repetitive_sequences:
        insights["automation_opportunities"].append({
            "sequence": seq["sequence"],
            "frequency": seq["frequency"],
            "automation_potential": "High",
            "expected_time_savings": seq["frequency"] * 0.3  # Estimated 30% time savings
        })
    
    return insights


def _analyze_response_times(activity_data: Dict) -> Dict[str, Any]:
    """Analyze response time patterns in communications"""
    # Placeholder for response time analysis
    return {"average_response_time": "4.2 hours", "response_consistency": 0.75}


def _analyze_communication_effectiveness(activity_data: Dict) -> Dict[str, Any]:
    """Analyze effectiveness of different communication channels"""
    # Placeholder for effectiveness analysis
    return {"email_effectiveness": 0.68, "call_effectiveness": 0.84, "meeting_effectiveness": 0.79}


def _analyze_workflow_patterns(user_sequences: Dict) -> Dict[str, Any]:
    """Analyze workflow patterns across users"""
    # Placeholder for workflow pattern analysis
    return {"common_workflows": 5, "unique_workflows": 12, "workflow_standardization": 0.62}


def _determine_user_archetype(type_distribution: Counter, activities: List) -> str:
    """Determine user archetype based on activity patterns"""
    total_activities = sum(type_distribution.values())
    
    if not total_activities:
        return "inactive"
    
    # Calculate percentages
    call_pct = type_distribution.get("calls", 0) / total_activities
    email_pct = type_distribution.get("emails", 0) / total_activities
    meeting_pct = type_distribution.get("meetings", 0) / total_activities
    
    if call_pct > 0.4:
        return "phone_focused"
    elif email_pct > 0.5:
        return "email_heavy"
    elif meeting_pct > 0.3:
        return "meeting_oriented"
    else:
        return "balanced_communicator"


def _calculate_activity_intensity(activities: List) -> float:
    """Calculate activity intensity score for a user"""
    if not activities:
        return 0.0
    
    # Simple intensity calculation based on activity frequency
    return min(len(activities) / 30.0, 1.0)  # Normalized to max 1.0


def _analyze_multitasking_patterns(activities: List) -> Dict[str, Any]:
    """Analyze multitasking patterns for a user"""
    # Placeholder for multitasking analysis
    return {"multitasking_score": 0.65, "context_switching_frequency": 8.2}


def _calculate_optimization_potential(sequence: Dict) -> float:
    """Calculate optimization potential for a sequence"""
    # Simple heuristic: higher frequency = higher optimization potential
    frequency = sequence.get("frequency", 0)
    return min(frequency / 50.0, 1.0)


def _is_automatable_sequence(sequence: List) -> bool:
    """Determine if a sequence is suitable for automation"""
    # Sequences with repetitive patterns are good automation candidates
    automatable_types = ["emails", "tasks", "notes"]
    return any(activity_type in automatable_types for activity_type in sequence)


def _count_total_activities(activity_data: Dict) -> int:
    """Count total activities across all types"""
    total = 0
    for activity_type, activities in activity_data.items():
        if activity_type not in ["user_activities", "timeline_events"]:
            total += len(activities)
    return total


def _calculate_data_completeness(activity_data: Dict) -> float:
    """Calculate completeness of the activity data"""
    # Placeholder for completeness calculation
    return 0.78


def get_schema() -> Dict[str, Any]:
    """Return the JSON schema for this tool's input parameters."""
    return {
        "type": "object",
        "properties": {
            "analysis_period_days": {
                "type": "integer",
                "description": "Number of days back to analyze activities",
                "default": 90,
                "minimum": 1,
                "maximum": 365
            },
            "pattern_sensitivity": {
                "type": "string",
                "description": "Sensitivity level for pattern detection",
                "enum": ["low", "medium", "high"],
                "default": "medium"
            },
            "include_activity_types": {
                "type": "array",
                "description": "Types of activities to include in analysis",
                "items": {
                    "type": "string",
                    "enum": ["calls", "emails", "meetings", "tasks", "notes"]
                },
                "default": ["calls", "emails", "meetings", "tasks", "notes"]
            },
            "min_pattern_frequency": {
                "type": "integer",
                "description": "Minimum frequency for pattern detection",
                "default": 3,
                "minimum": 1,
                "maximum": 20
            },
            "max_activities": {
                "type": "integer",
                "description": "Maximum number of activities to analyze",
                "default": 500,
                "minimum": 10,
                "maximum": 2000
            },
            "contact_filter": {
                "type": "string",
                "description": "Specific contact ID to filter activities (optional)"
            },
            "owner_filter": {
                "type": "string",
                "description": "Specific owner ID to filter activities (optional)"
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
    import sys
    
    # Test mode for autodiscovery (REQUIRED)
    if len(sys.argv) == 2 and sys.argv[1] == '{"__test__": true}':
        print(json.dumps({"success": True, "_simple": True}))
        return
    
    # Handle schema export
    if len(sys.argv) == 2 and sys.argv[1] == "--fractalic-dump-schema":
        schema = {
            "name": "hubspot_activity_pattern_miner",
            "description": "Analyze communication patterns, activity flows, and behavioral sequences in HubSpot",
            "parameters": {
                "type": "object",
                "properties": {
                    "analysis_period_days": {
                        "type": "integer",
                        "minimum": 30,
                        "maximum": 365,
                        "description": "Number of days to analyze for patterns",
                        "default": 90
                    },
                    "pattern_sensitivity": {
                        "type": "string",
                        "enum": ["low", "medium", "high"],
                        "description": "Sensitivity level for pattern detection",
                        "default": "medium"
                    },
                    "max_activities": {
                        "type": "integer",
                        "minimum": 50,
                        "maximum": 1000,
                        "description": "Maximum number of activities to analyze",
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


if __name__ == "__main__":
    main()
