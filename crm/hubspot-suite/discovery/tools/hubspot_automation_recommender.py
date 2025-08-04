#!/usr/bin/env python3
"""
HubSpot Automation Recommender - Auto-Discovery Tool
Recommends specific automation opportunities and implementation strategies
Part of the Fractalic Process Mining Intelligence System
"""

import json
import sys
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict, Counter


def process_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze workflows and recommend specific automation opportunities
    
    Returns:
        Dict containing automation recommendations with implementation details
    """
    
    try:
        # Import dependencies inside the function
        from hubspot_hub_helpers import hs_client
        
        # Extract parameters with defaults
        analysis_period_days = data.get("analysis_period_days", 90)
        automation_threshold = data.get("automation_threshold", 0.6)  # 60% automation potential
        min_frequency = data.get("min_frequency", 5)
        roi_threshold = data.get("roi_threshold", 2.0)  # 2x ROI minimum
        
        client = hs_client()
        
        # Collect automation analysis data
        automation_data = _collect_automation_data(client, analysis_period_days)
        
        # Analyze repetitive patterns
        repetitive_patterns = _analyze_repetitive_patterns(automation_data, min_frequency)
        
        # Identify rule-based processes
        rule_based_processes = _identify_rule_based_processes(automation_data)
        
        # Analyze manual intervention points
        manual_interventions = _analyze_manual_interventions(automation_data)
        
        # Calculate automation potential scores
        automation_scores = _calculate_automation_scores(
            repetitive_patterns, rule_based_processes, manual_interventions
        )
        
        # Generate specific automation recommendations
        automation_recommendations = _generate_automation_recommendations(
            automation_scores, automation_threshold, roi_threshold
        )
        
        # Calculate ROI projections
        roi_analysis = _calculate_automation_roi(automation_recommendations, automation_data)
        
        # Prioritize recommendations by feasibility and impact
        prioritized_recommendations = _prioritize_automation_recommendations(
            automation_recommendations, roi_analysis
        )
        
        result = {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "analysis_period": f"{analysis_period_days} days",
            "automation_threshold": automation_threshold,
            "repetitive_patterns": repetitive_patterns,
            "rule_based_processes": rule_based_processes,
            "manual_interventions": manual_interventions,
            "automation_recommendations": prioritized_recommendations,
            "roi_analysis": roi_analysis,
            "metadata": {
                "total_processes_analyzed": len(automation_data.get("processes", [])),
                "automation_opportunities": len(prioritized_recommendations),
                "high_roi_opportunities": len([r for r in prioritized_recommendations if r.get("roi_score", 0) > roi_threshold]),
                "estimated_total_savings": roi_analysis.get("total_annual_savings", 0),
                "automation_coverage": _calculate_automation_coverage(automation_scores)
            }
        }
        
        return result
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


def _collect_automation_data(client, analysis_period_days: int) -> Dict[str, Any]:
    """Collect data for automation analysis"""
    
    automation_data = {
        "processes": [],
        "tasks": [],
        "emails": [],
        "workflows": [],
        "manual_activities": [],
        "repetitive_actions": defaultdict(list)
    }
    
    # Collect tasks for automation analysis
    try:
        tasks_response = client.crm.objects.tasks.basic_api.get_page(
            limit=100,
            properties=[
                "hs_timestamp", "hubspot_owner_id", "hs_task_status", "hs_task_type",
                "hs_task_subject", "hs_task_body", "hs_task_priority"
            ]
        )
        
        for task in tasks_response.results:
            task_data = {
                "id": str(task.id),
                "timestamp": getattr(task, 'hs_timestamp', None),
                "owner_id": str(getattr(task, 'hubspot_owner_id', '')),
                "status": getattr(task, 'hs_task_status', ''),
                "type": getattr(task, 'hs_task_type', ''),
                "subject": getattr(task, 'hs_task_subject', ''),
                "body": getattr(task, 'hs_task_body', ''),
                "priority": getattr(task, 'hs_task_priority', '')
            }
            
            automation_data["tasks"].append(task_data)
            
            # Categorize potential automation patterns
            task_signature = _create_task_signature(task_data)
            automation_data["repetitive_actions"][task_signature].append(task_data)
            
    except Exception as e:
        print(f"Error collecting tasks: {e}")
    
    # Collect emails for communication automation analysis
    try:
        emails_response = client.crm.objects.emails.basic_api.get_page(
            limit=100,
            properties=[
                "hs_timestamp", "hubspot_owner_id", "hs_email_direction", 
                "hs_email_subject", "hs_email_text"
            ]
        )
        
        for email in emails_response.results:
            email_data = {
                "id": str(email.id),
                "timestamp": getattr(email, 'hs_timestamp', None),
                "owner_id": str(getattr(email, 'hubspot_owner_id', '')),
                "direction": getattr(email, 'hs_email_direction', ''),
                "subject": getattr(email, 'hs_email_subject', ''),
                "text": getattr(email, 'hs_email_text', '')
            }
            
            automation_data["emails"].append(email_data)
            
            # Analyze for template patterns
            if email_data["direction"] == "OUTBOUND":
                email_signature = _create_email_signature(email_data)
                automation_data["repetitive_actions"][email_signature].append(email_data)
                
    except Exception as e:
        print(f"Error collecting emails: {e}")
    
    # Collect deals for workflow automation analysis
    try:
        deals_response = client.crm.deals.basic_api.get_page(
            limit=100,
            properties=[
                "dealstage", "createdate", "hs_lastmodifieddate", "hubspot_owner_id",
                "amount", "dealname", "pipeline"
            ]
        )
        
        for deal in deals_response.results:
            process_data = {
                "id": str(deal.id),
                "type": "deal_progression",
                "stage": getattr(deal, 'dealstage', ''),
                "create_date": getattr(deal, 'createdate', None),
                "last_modified": getattr(deal, 'hs_lastmodifieddate', None),
                "owner_id": str(getattr(deal, 'hubspot_owner_id', '')),
                "amount": getattr(deal, 'amount', 0),
                "pipeline": getattr(deal, 'pipeline', '')
            }
            
            automation_data["processes"].append(process_data)
            
    except Exception as e:
        print(f"Error collecting deals: {e}")
    
    return automation_data


def _analyze_repetitive_patterns(automation_data: Dict, min_frequency: int) -> Dict[str, Any]:
    """Analyze repetitive patterns suitable for automation"""
    
    repetitive_patterns = {
        "high_frequency_tasks": [],
        "template_opportunities": [],
        "workflow_patterns": [],
        "communication_patterns": []
    }
    
    # Analyze high-frequency repetitive actions
    for signature, actions in automation_data.get("repetitive_actions", {}).items():
        if len(actions) >= min_frequency:
            pattern_analysis = _analyze_pattern_automation_potential(signature, actions)
            
            if pattern_analysis["automation_potential"] > 0.5:
                if "task" in signature:
                    repetitive_patterns["high_frequency_tasks"].append(pattern_analysis)
                elif "email" in signature:
                    repetitive_patterns["communication_patterns"].append(pattern_analysis)
                else:
                    repetitive_patterns["workflow_patterns"].append(pattern_analysis)
    
    # Analyze template opportunities
    template_opportunities = _identify_template_opportunities(automation_data)
    repetitive_patterns["template_opportunities"] = template_opportunities
    
    return repetitive_patterns


def _identify_rule_based_processes(automation_data: Dict) -> Dict[str, Any]:
    """Identify rule-based processes suitable for automation"""
    
    rule_based_processes = {
        "conditional_workflows": [],
        "approval_processes": [],
        "data_routing": [],
        "notification_triggers": []
    }
    
    # Analyze deal progression for rule-based automation
    deals = automation_data.get("processes", [])
    
    # Group deals by stage patterns
    stage_patterns = defaultdict(list)
    for deal in deals:
        if deal.get("type") == "deal_progression":
            stage = deal.get("stage", "")
            amount = deal.get("amount", 0)
            
            # Create rule signature based on stage and amount ranges
            rule_signature = _create_rule_signature(stage, amount)
            stage_patterns[rule_signature].append(deal)
    
    # Identify automation opportunities in stage patterns
    for rule_sig, deal_group in stage_patterns.items():
        if len(deal_group) >= 3:  # Minimum pattern occurrence
            rule_analysis = _analyze_rule_automation_potential(rule_sig, deal_group)
            
            if rule_analysis["automation_potential"] > 0.6:
                if "approval" in rule_sig.lower():
                    rule_based_processes["approval_processes"].append(rule_analysis)
                elif "routing" in rule_sig.lower():
                    rule_based_processes["data_routing"].append(rule_analysis)
                else:
                    rule_based_processes["conditional_workflows"].append(rule_analysis)
    
    return rule_based_processes


def _analyze_manual_interventions(automation_data: Dict) -> Dict[str, Any]:
    """Analyze manual intervention points for automation opportunities"""
    
    manual_interventions = {
        "data_entry_points": [],
        "manual_approvals": [],
        "manual_routing": [],
        "manual_follow_ups": []
    }
    
    # Analyze tasks for manual intervention patterns
    tasks = automation_data.get("tasks", [])
    
    for task in tasks:
        task_type = task.get("type", "").lower()
        task_subject = task.get("subject", "").lower()
        task_body = task.get("body", "").lower()
        
        # Identify manual intervention types
        if any(keyword in task_subject or keyword in task_body for keyword in ["enter", "input", "update", "fill"]):
            manual_interventions["data_entry_points"].append({
                "task_id": task.get("id"),
                "intervention_type": "data_entry",
                "automation_potential": _calculate_data_entry_automation_potential(task),
                "description": task.get("subject", "")
            })
        
        elif any(keyword in task_subject or keyword in task_body for keyword in ["approve", "review", "check"]):
            manual_interventions["manual_approvals"].append({
                "task_id": task.get("id"),
                "intervention_type": "approval",
                "automation_potential": _calculate_approval_automation_potential(task),
                "description": task.get("subject", "")
            })
        
        elif any(keyword in task_subject or keyword in task_body for keyword in ["assign", "route", "forward"]):
            manual_interventions["manual_routing"].append({
                "task_id": task.get("id"),
                "intervention_type": "routing",
                "automation_potential": _calculate_routing_automation_potential(task),
                "description": task.get("subject", "")
            })
        
        elif any(keyword in task_subject or keyword in task_body for keyword in ["follow up", "remind", "contact"]):
            manual_interventions["manual_follow_ups"].append({
                "task_id": task.get("id"),
                "intervention_type": "follow_up",
                "automation_potential": _calculate_followup_automation_potential(task),
                "description": task.get("subject", "")
            })
    
    return manual_interventions


def _calculate_automation_scores(repetitive_patterns: Dict, rule_based_processes: Dict, 
                               manual_interventions: Dict) -> Dict[str, Any]:
    """Calculate automation potential scores for different process types"""
    
    automation_scores = {
        "overall_automation_potential": 0.0,
        "category_scores": {},
        "high_potential_processes": [],
        "automation_readiness": {}
    }
    
    # Calculate category scores
    categories = {
        "repetitive_tasks": repetitive_patterns.get("high_frequency_tasks", []),
        "rule_based_workflows": rule_based_processes.get("conditional_workflows", []),
        "manual_interventions": sum(manual_interventions.values(), [])
    }
    
    for category, processes in categories.items():
        if processes:
            avg_potential = sum(p.get("automation_potential", 0) for p in processes) / len(processes)
            automation_scores["category_scores"][category] = avg_potential
            
            # Identify high potential processes
            high_potential = [p for p in processes if p.get("automation_potential", 0) > 0.7]
            if high_potential:
                automation_scores["high_potential_processes"].extend(high_potential)
    
    # Calculate overall automation potential
    if automation_scores["category_scores"]:
        automation_scores["overall_automation_potential"] = sum(
            automation_scores["category_scores"].values()
        ) / len(automation_scores["category_scores"])
    
    return automation_scores


def _generate_automation_recommendations(automation_scores: Dict, threshold: float, roi_threshold: float) -> List[Dict]:
    """Generate specific automation recommendations"""
    
    recommendations = []
    
    # Generate recommendations from high potential processes
    high_potential_processes = automation_scores.get("high_potential_processes", [])
    
    for process in high_potential_processes:
        if process.get("automation_potential", 0) >= threshold:
            recommendation = _create_automation_recommendation(process, roi_threshold)
            if recommendation:
                recommendations.append(recommendation)
    
    # Generate template automation recommendations
    template_rec = _create_template_automation_recommendation(automation_scores)
    if template_rec:
        recommendations.append(template_rec)
    
    # Generate workflow automation recommendations
    workflow_rec = _create_workflow_automation_recommendation(automation_scores)
    if workflow_rec:
        recommendations.append(workflow_rec)
    
    return recommendations


def _calculate_automation_roi(recommendations: List[Dict], automation_data: Dict) -> Dict[str, Any]:
    """Calculate ROI projections for automation recommendations"""
    
    roi_analysis = {
        "total_annual_savings": 0,
        "implementation_costs": 0,
        "payback_periods": {},
        "risk_assessments": {},
        "recommendation_rois": {}
    }
    
    for rec in recommendations:
        rec_id = rec.get("id", "")
        
        # Estimate implementation cost
        complexity = rec.get("implementation_complexity", "Medium")
        cost_multipliers = {"Low": 1000, "Medium": 5000, "High": 15000}
        implementation_cost = cost_multipliers.get(complexity, 5000)
        
        # Estimate annual savings
        frequency = rec.get("frequency_per_year", 100)
        time_per_instance = rec.get("time_per_instance_hours", 1)
        hourly_rate = 50  # Assumed hourly rate
        
        annual_savings = frequency * time_per_instance * hourly_rate * rec.get("automation_efficiency", 0.7)
        
        # Calculate ROI
        if implementation_cost > 0:
            roi = (annual_savings - implementation_cost) / implementation_cost
            payback_months = (implementation_cost / annual_savings) * 12 if annual_savings > 0 else float('inf')
        else:
            roi = 0
            payback_months = 0
        
        roi_analysis["recommendation_rois"][rec_id] = {
            "annual_savings": annual_savings,
            "implementation_cost": implementation_cost,
            "roi": roi,
            "payback_months": payback_months
        }
        
        roi_analysis["total_annual_savings"] += annual_savings
        roi_analysis["implementation_costs"] += implementation_cost
        roi_analysis["payback_periods"][rec_id] = payback_months
        
        # Add ROI score to recommendation
        rec["roi_score"] = roi
        rec["annual_savings"] = annual_savings
        rec["payback_months"] = payback_months
    
    return roi_analysis


def _prioritize_automation_recommendations(recommendations: List[Dict], roi_analysis: Dict) -> List[Dict]:
    """Prioritize automation recommendations by impact and feasibility"""
    
    for rec in recommendations:
        # Calculate priority score
        automation_potential = rec.get("automation_potential", 0)
        roi_score = rec.get("roi_score", 0)
        complexity = rec.get("implementation_complexity", "Medium")
        
        # Complexity scoring
        complexity_scores = {"Low": 1.0, "Medium": 0.7, "High": 0.4}
        complexity_score = complexity_scores.get(complexity, 0.7)
        
        # Combined priority score
        rec["priority_score"] = (
            automation_potential * 0.4 + 
            min(roi_score / 5.0, 1.0) * 0.4 +  # Normalize ROI to 0-1 scale
            complexity_score * 0.2
        )
    
    # Sort by priority score
    return sorted(recommendations, key=lambda x: x.get("priority_score", 0), reverse=True)


# Helper functions

def _create_task_signature(task_data: Dict) -> str:
    """Create a signature for task pattern matching"""
    task_type = task_data.get("type", "unknown")
    subject_words = task_data.get("subject", "").lower().split()[:3]  # First 3 words
    return f"task_{task_type}_{' '.join(subject_words)}"


def _create_email_signature(email_data: Dict) -> str:
    """Create a signature for email pattern matching"""
    subject_words = email_data.get("subject", "").lower().split()[:3]  # First 3 words
    return f"email_outbound_{' '.join(subject_words)}"


def _create_rule_signature(stage: str, amount: float) -> str:
    """Create a rule signature for deal processes"""
    amount_range = "low" if amount < 10000 else "medium" if amount < 50000 else "high"
    return f"deal_{stage}_{amount_range}"


def _analyze_pattern_automation_potential(signature: str, actions: List) -> Dict[str, Any]:
    """Analyze automation potential for a pattern"""
    return {
        "pattern_signature": signature,
        "frequency": len(actions),
        "automation_potential": min(len(actions) / 20.0, 1.0),  # Higher frequency = higher potential
        "pattern_type": "repetitive",
        "actions_count": len(actions)
    }


def _identify_template_opportunities(automation_data: Dict) -> List[Dict]:
    """Identify template automation opportunities"""
    templates = []
    
    # Analyze email patterns for templates
    emails = automation_data.get("emails", [])
    outbound_emails = [e for e in emails if e.get("direction") == "OUTBOUND"]
    
    if len(outbound_emails) > 10:
        templates.append({
            "type": "email_templates",
            "automation_potential": 0.8,
            "frequency": len(outbound_emails),
            "description": "Create automated email templates for common communications"
        })
    
    return templates


def _analyze_rule_automation_potential(rule_sig: str, deal_group: List) -> Dict[str, Any]:
    """Analyze rule-based automation potential"""
    return {
        "rule_signature": rule_sig,
        "frequency": len(deal_group),
        "automation_potential": 0.7,  # Rule-based processes have high automation potential
        "rule_type": "conditional_workflow",
        "affected_deals": len(deal_group)
    }


def _calculate_data_entry_automation_potential(task: Dict) -> float:
    """Calculate automation potential for data entry tasks"""
    # Data entry tasks have high automation potential
    return 0.8


def _calculate_approval_automation_potential(task: Dict) -> float:
    """Calculate automation potential for approval tasks"""
    # Approval tasks have medium automation potential (may need human judgment)
    return 0.6


def _calculate_routing_automation_potential(task: Dict) -> float:
    """Calculate automation potential for routing tasks"""
    # Routing tasks have high automation potential
    return 0.9


def _calculate_followup_automation_potential(task: Dict) -> float:
    """Calculate automation potential for follow-up tasks"""
    # Follow-up tasks have very high automation potential
    return 0.95


def _create_automation_recommendation(process: Dict, roi_threshold: float) -> Optional[Dict]:
    """Create a specific automation recommendation"""
    automation_potential = process.get("automation_potential", 0)
    
    if automation_potential < 0.6:
        return None
    
    return {
        "id": f"auto_rec_{process.get('pattern_signature', 'unknown')}",
        "title": f"Automate {process.get('pattern_type', 'Process')}",
        "description": f"Implement automation for high-frequency {process.get('pattern_type', 'process')}",
        "automation_potential": automation_potential,
        "frequency_per_year": process.get("frequency", 0) * 12,  # Estimate annual frequency
        "time_per_instance_hours": 1.0,  # Estimate time per instance
        "automation_efficiency": 0.8,  # 80% time reduction
        "implementation_complexity": "Medium",
        "recommended_tools": ["HubSpot Workflows", "Zapier", "Custom Scripts"],
        "implementation_steps": [
            "Analyze current process flow",
            "Design automation workflow",
            "Implement and test automation",
            "Deploy and monitor"
        ]
    }


def _create_template_automation_recommendation(automation_scores: Dict) -> Optional[Dict]:
    """Create template automation recommendation"""
    return {
        "id": "auto_rec_templates",
        "title": "Implement Communication Templates",
        "description": "Create automated templates for common communications",
        "automation_potential": 0.75,
        "frequency_per_year": 500,
        "time_per_instance_hours": 0.5,
        "automation_efficiency": 0.7,
        "implementation_complexity": "Low",
        "recommended_tools": ["HubSpot Email Templates", "Sequences"],
        "implementation_steps": [
            "Identify common communication patterns",
            "Create template library",
            "Set up automated sequences",
            "Train team on usage"
        ]
    }


def _create_workflow_automation_recommendation(automation_scores: Dict) -> Optional[Dict]:
    """Create workflow automation recommendation"""
    return {
        "id": "auto_rec_workflows",
        "title": "Automate Workflow Triggers",
        "description": "Implement automated workflow triggers for common processes",
        "automation_potential": 0.85,
        "frequency_per_year": 1000,
        "time_per_instance_hours": 0.25,
        "automation_efficiency": 0.9,
        "implementation_complexity": "Medium",
        "recommended_tools": ["HubSpot Workflows", "Operations Hub"],
        "implementation_steps": [
            "Map current workflow triggers",
            "Design automated trigger conditions",
            "Implement workflow automation",
            "Monitor and optimize"
        ]
    }


def _calculate_automation_coverage(automation_scores: Dict) -> float:
    """Calculate what percentage of processes could be automated"""
    category_scores = automation_scores.get("category_scores", {})
    if not category_scores:
        return 0.0
    
    # Average automation potential across categories
    return sum(category_scores.values()) / len(category_scores)


def main():
    """Main function to handle CLI arguments and process data"""
    # Test mode for autodiscovery (REQUIRED)
    if len(sys.argv) == 2 and sys.argv[1] == '{"__test__": true}':
        print(json.dumps({"success": True, "_simple": True}))
        return
    
    # Optional: Rich schema for better LLM integration
    if len(sys.argv) == 2 and sys.argv[1] == "--fractalic-dump-schema":
        schema = {
            "name": "hubspot_automation_recommender",
            "description": "Recommend specific automation opportunities and implementation strategies in HubSpot",
            "parameters": {
                "type": "object",
                "properties": {
                    "analysis_scope": {
                        "type": "string",
                        "enum": ["workflows", "processes", "tasks", "comprehensive"],
                        "description": "Scope of automation analysis",
                        "default": "comprehensive"
                    },
                    "include_roi_estimates": {
                        "type": "boolean",
                        "description": "Include ROI estimates for automation opportunities",
                        "default": True
                    },
                    "analysis_period_days": {
                        "type": "integer",
                        "minimum": 30,
                        "maximum": 365,
                        "description": "Number of days to analyze for automation opportunities",
                        "default": 90
                    },
                    "automation_threshold": {
                        "type": "number",
                        "minimum": 0.1,
                        "maximum": 1.0,
                        "description": "Minimum automation potential threshold (0-1)",
                        "default": 0.6
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
