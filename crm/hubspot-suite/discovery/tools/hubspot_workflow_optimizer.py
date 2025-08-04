#!/usr/bin/env python3
"""
HubSpot Workflow Optimizer - Auto-Discovery Tool
Suggests process improvements and workflow optimizations
Part of the Fractalic Process Mining Intelligence System
"""

import json
import sys
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict, Counter


def process_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze workflows and suggest optimizations
    
    Returns:
        Dict containing workflow optimization suggestions and improvements
    """
    
    try:
        # Import dependencies inside the function
        from hubspot_hub_helpers import hs_client
        
        # Extract parameters with defaults
        analysis_period_days = data.get("analysis_period_days", 90)
        optimization_focus = data.get("optimization_focus", "all")  # all, speed, efficiency, automation
        min_impact_threshold = data.get("min_impact_threshold", 0.1)
        
        client = hs_client()
        
        # Collect workflow data
        workflow_data = _collect_workflow_data(client, analysis_period_days)
        
        # Analyze current workflow performance
        performance_analysis = _analyze_workflow_performance(workflow_data)
        
        # Identify optimization opportunities
        optimization_opportunities = _identify_optimization_opportunities(
            workflow_data, performance_analysis, optimization_focus, min_impact_threshold
        )
        
        # Generate specific recommendations
        recommendations = _generate_workflow_recommendations(
            optimization_opportunities, performance_analysis
        )
        
        # Calculate potential impact
        impact_analysis = _calculate_optimization_impact(recommendations, workflow_data)
        
        # Prioritize recommendations
        prioritized_recommendations = _prioritize_recommendations(
            recommendations, impact_analysis
        )
        
        result = {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "analysis_period": f"{analysis_period_days} days",
            "optimization_focus": optimization_focus,
            "workflow_performance": performance_analysis,
            "optimization_opportunities": optimization_opportunities,
            "recommendations": prioritized_recommendations,
            "impact_analysis": impact_analysis,
            "metadata": {
                "workflows_analyzed": len(workflow_data.get("workflows", [])),
                "opportunities_found": len(optimization_opportunities),
                "high_impact_recommendations": len([r for r in prioritized_recommendations if r.get("impact_score", 0) > 0.7]),
                "estimated_total_savings_hours": impact_analysis.get("total_time_savings", 0)
            }
        }
        
        return result
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


def _collect_workflow_data(client, analysis_period_days: int) -> Dict[str, Any]:
    """Collect workflow data for optimization analysis"""
    
    workflow_data = {
        "workflows": [],
        "deals": [],
        "tickets": [],
        "tasks": [],
        "activities": [],
        "stage_progressions": defaultdict(list)
    }
    
    # Collect deals with progression data
    try:
        deals_response = client.crm.deals.basic_api.get_page(
            limit=100,
            properties=["dealstage", "createdate", "closedate", "hubspot_owner_id", "amount"]
        )
        
        for deal in deals_response.results:
            workflow_data["deals"].append({
                "id": str(deal.id),
                "stage": getattr(deal, 'dealstage', ''),
                "create_date": getattr(deal, 'createdate', None),
                "close_date": getattr(deal, 'closedate', None),
                "owner_id": str(getattr(deal, 'hubspot_owner_id', '')),
                "amount": getattr(deal, 'amount', 0)
            })
            
    except Exception as e:
        print(f"Error collecting deals: {e}")
    
    # Collect tickets
    try:
        tickets_response = client.crm.tickets.basic_api.get_page(
            limit=100,
            properties=["hs_pipeline_stage", "createdate", "closed_date", "hubspot_owner_id", "hs_ticket_priority"]
        )
        
        for ticket in tickets_response.results:
            workflow_data["tickets"].append({
                "id": str(ticket.id),
                "stage": getattr(ticket, 'hs_pipeline_stage', ''),
                "create_date": getattr(ticket, 'createdate', None),
                "close_date": getattr(ticket, 'closed_date', None),
                "owner_id": str(getattr(ticket, 'hubspot_owner_id', '')),
                "priority": getattr(ticket, 'hs_ticket_priority', '')
            })
            
    except Exception as e:
        print(f"Error collecting tickets: {e}")
    
    # Collect tasks
    try:
        tasks_response = client.crm.objects.tasks.basic_api.get_page(
            limit=100,
            properties=["hs_timestamp", "hubspot_owner_id", "hs_task_status", "hs_task_type"]
        )
        
        workflow_data["tasks"] = [
            {
                "id": str(task.id),
                "timestamp": getattr(task, 'hs_timestamp', None),
                "owner_id": str(getattr(task, 'hubspot_owner_id', '')),
                "status": getattr(task, 'hs_task_status', ''),
                "type": getattr(task, 'hs_task_type', '')
            }
            for task in tasks_response.results
        ]
        
    except Exception as e:
        print(f"Error collecting tasks: {e}")
    
    return workflow_data


def _analyze_workflow_performance(workflow_data: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze current workflow performance metrics"""
    
    performance_analysis = {
        "average_deal_cycle_time": 0,
        "average_ticket_resolution_time": 0,
        "task_completion_rates": {},
        "stage_conversion_rates": {},
        "bottleneck_stages": [],
        "efficiency_metrics": {}
    }
    
    # Analyze deal cycle times
    deal_cycle_times = []
    for deal in workflow_data.get("deals", []):
        create_date = deal.get("create_date")
        close_date = deal.get("close_date")
        
        if create_date and close_date:
            try:
                create_dt = datetime.fromisoformat(create_date.replace('Z', '+00:00'))
                close_dt = datetime.fromisoformat(close_date.replace('Z', '+00:00'))
                cycle_time = (close_dt - create_dt).total_seconds() / (24 * 3600)  # days
                deal_cycle_times.append(cycle_time)
            except Exception:
                continue
    
    if deal_cycle_times:
        performance_analysis["average_deal_cycle_time"] = sum(deal_cycle_times) / len(deal_cycle_times)
    
    # Analyze ticket resolution times
    ticket_resolution_times = []
    for ticket in workflow_data.get("tickets", []):
        create_date = ticket.get("create_date")
        close_date = ticket.get("close_date")
        
        if create_date and close_date:
            try:
                create_dt = datetime.fromisoformat(create_date.replace('Z', '+00:00'))
                close_dt = datetime.fromisoformat(close_date.replace('Z', '+00:00'))
                resolution_time = (close_dt - create_dt).total_seconds() / (24 * 3600)  # days
                ticket_resolution_times.append(resolution_time)
            except Exception:
                continue
    
    if ticket_resolution_times:
        performance_analysis["average_ticket_resolution_time"] = sum(ticket_resolution_times) / len(ticket_resolution_times)
    
    # Analyze task completion rates
    task_statuses = Counter(task.get("status", "") for task in workflow_data.get("tasks", []))
    total_tasks = sum(task_statuses.values())
    
    if total_tasks > 0:
        performance_analysis["task_completion_rates"] = {
            status: count / total_tasks for status, count in task_statuses.items()
        }
    
    return performance_analysis


def _identify_optimization_opportunities(workflow_data: Dict, performance_analysis: Dict, 
                                       focus: str, threshold: float) -> List[Dict]:
    """Identify specific optimization opportunities"""
    
    opportunities = []
    
    # Identify long cycle time opportunities
    avg_deal_cycle = performance_analysis.get("average_deal_cycle_time", 0)
    if avg_deal_cycle > 30:  # More than 30 days
        opportunities.append({
            "type": "cycle_time_reduction",
            "description": "Deal cycle time is longer than optimal",
            "current_value": avg_deal_cycle,
            "target_value": avg_deal_cycle * 0.7,
            "impact_potential": 0.8,
            "focus_area": "speed"
        })
    
    # Identify task completion opportunities
    completion_rates = performance_analysis.get("task_completion_rates", {})
    completed_rate = completion_rates.get("COMPLETED", 0)
    
    if completed_rate < 0.8:  # Less than 80% completion
        opportunities.append({
            "type": "task_completion_improvement",
            "description": "Task completion rate is below optimal",
            "current_value": completed_rate,
            "target_value": 0.9,
            "impact_potential": 0.6,
            "focus_area": "efficiency"
        })
    
    # Identify automation opportunities
    manual_tasks = [task for task in workflow_data.get("tasks", []) if "manual" in task.get("type", "").lower()]
    if len(manual_tasks) > 10:
        opportunities.append({
            "type": "automation_opportunity",
            "description": "High volume of manual tasks suitable for automation",
            "current_value": len(manual_tasks),
            "target_value": len(manual_tasks) * 0.3,
            "impact_potential": 0.9,
            "focus_area": "automation"
        })
    
    # Filter by focus area
    if focus != "all":
        opportunities = [opp for opp in opportunities if opp.get("focus_area") == focus]
    
    # Filter by impact threshold
    opportunities = [opp for opp in opportunities if opp.get("impact_potential", 0) >= threshold]
    
    return opportunities


def _generate_workflow_recommendations(opportunities: List[Dict], performance_analysis: Dict) -> List[Dict]:
    """Generate specific recommendations for workflow optimization"""
    
    recommendations = []
    
    for opportunity in opportunities:
        opp_type = opportunity.get("type")
        
        if opp_type == "cycle_time_reduction":
            recommendations.append({
                "id": f"rec_{len(recommendations) + 1}",
                "title": "Reduce Deal Cycle Time",
                "description": "Implement parallel processing and automated approvals to reduce deal cycle time",
                "opportunity_type": opp_type,
                "impact_score": opportunity.get("impact_potential", 0),
                "implementation_effort": "Medium",
                "time_to_implement": "4-6 weeks",
                "expected_improvement": f"{opportunity.get('current_value', 0):.1f} days → {opportunity.get('target_value', 0):.1f} days",
                "specific_actions": [
                    "Implement parallel approval workflows",
                    "Automate routine approval processes",
                    "Set up automated stage progression triggers",
                    "Create performance dashboards for monitoring"
                ]
            })
        
        elif opp_type == "task_completion_improvement":
            recommendations.append({
                "id": f"rec_{len(recommendations) + 1}",
                "title": "Improve Task Completion Rates",
                "description": "Implement better task management and follow-up processes",
                "opportunity_type": opp_type,
                "impact_score": opportunity.get("impact_potential", 0),
                "implementation_effort": "Low",
                "time_to_implement": "2-3 weeks",
                "expected_improvement": f"{opportunity.get('current_value', 0):.1%} → {opportunity.get('target_value', 0):.1%}",
                "specific_actions": [
                    "Set up automated task reminders",
                    "Implement task prioritization system",
                    "Create task completion tracking dashboard",
                    "Establish task review and follow-up processes"
                ]
            })
        
        elif opp_type == "automation_opportunity":
            recommendations.append({
                "id": f"rec_{len(recommendations) + 1}",
                "title": "Automate Repetitive Tasks",
                "description": "Implement automation for high-volume manual tasks",
                "opportunity_type": opp_type,
                "impact_score": opportunity.get("impact_potential", 0),
                "implementation_effort": "High",
                "time_to_implement": "8-12 weeks",
                "expected_improvement": f"{opportunity.get('current_value', 0)} → {opportunity.get('target_value', 0)} manual tasks",
                "specific_actions": [
                    "Identify automatable task patterns",
                    "Implement workflow automation tools",
                    "Create automated task templates",
                    "Set up monitoring and optimization processes"
                ]
            })
    
    return recommendations


def _calculate_optimization_impact(recommendations: List[Dict], workflow_data: Dict) -> Dict[str, Any]:
    """Calculate potential impact of optimization recommendations"""
    
    impact_analysis = {
        "total_time_savings": 0,
        "efficiency_improvements": {},
        "cost_savings_estimate": 0,
        "roi_projections": {}
    }
    
    for rec in recommendations:
        impact_score = rec.get("impact_score", 0)
        
        # Estimate time savings based on recommendation type
        if "cycle_time" in rec.get("opportunity_type", ""):
            # Assume 20% time savings for cycle time improvements
            time_savings = len(workflow_data.get("deals", [])) * 5 * impact_score  # 5 hours per deal
            impact_analysis["total_time_savings"] += time_savings
        
        elif "task_completion" in rec.get("opportunity_type", ""):
            # Assume 10% time savings for task completion improvements
            time_savings = len(workflow_data.get("tasks", [])) * 0.5 * impact_score  # 0.5 hours per task
            impact_analysis["total_time_savings"] += time_savings
        
        elif "automation" in rec.get("opportunity_type", ""):
            # Assume 60% time savings for automation
            time_savings = len(workflow_data.get("tasks", [])) * 1.5 * impact_score  # 1.5 hours per task
            impact_analysis["total_time_savings"] += time_savings
    
    # Estimate cost savings (assuming $50/hour average cost)
    impact_analysis["cost_savings_estimate"] = impact_analysis["total_time_savings"] * 50
    
    return impact_analysis


def _prioritize_recommendations(recommendations: List[Dict], impact_analysis: Dict) -> List[Dict]:
    """Prioritize recommendations by impact and feasibility"""
    
    # Add priority scores
    for rec in recommendations:
        impact_score = rec.get("impact_score", 0)
        effort = rec.get("implementation_effort", "Medium")
        
        # Effort scoring
        effort_score = {"Low": 0.9, "Medium": 0.6, "High": 0.3}.get(effort, 0.5)
        
        # Combined priority score
        rec["priority_score"] = (impact_score * 0.7) + (effort_score * 0.3)
    
    # Sort by priority score
    return sorted(recommendations, key=lambda x: x.get("priority_score", 0), reverse=True)


def main():
    """Main function to handle CLI arguments and process data"""
    # Test mode for autodiscovery (REQUIRED)
    if len(sys.argv) == 2 and sys.argv[1] == '{"__test__": true}':
        print(json.dumps({"success": True, "_simple": True}))
        return
    
    # Optional: Rich schema for better LLM integration
    if len(sys.argv) == 2 and sys.argv[1] == "--fractalic-dump-schema":
        schema = {
            "name": "hubspot_workflow_optimizer",
            "description": "Analyze workflows and suggest optimizations for improved efficiency",
            "parameters": {
                "type": "object",
                "properties": {
                    "focus": {
                        "type": "string",
                        "enum": ["bottlenecks", "efficiency", "automation", "all"],
                        "description": "Focus area for optimization analysis",
                        "default": "bottlenecks"
                    },
                    "include_recommendations": {
                        "type": "boolean",
                        "description": "Include detailed recommendations",
                        "default": True
                    },
                    "analysis_period_days": {
                        "type": "integer",
                        "minimum": 30,
                        "maximum": 365,
                        "description": "Number of days to analyze workflow data",
                        "default": 90
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
