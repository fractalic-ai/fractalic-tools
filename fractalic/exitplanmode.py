#!/usr/bin/env python3
"""ExitPlanMode Tool - Fractalic Compatible Implementation

Used when in plan mode to present a plan to the user for approval.
This tool signals the completion of planning phase and transition to execution.
"""

import json
import sys
import time
import hashlib

def process_data(data):
    """Main processing function for plan mode exit."""
    try:
        # Extract and validate parameters
        plan = data.get("plan")
        
        if not plan:
            return {"status": "error", "error": "plan parameter is required"}
        
        if not isinstance(plan, str) or len(plan.strip()) == 0:
            return {"status": "error", "error": "plan must be a non-empty string"}
        
        # Process the plan
        result = _process_plan_submission(plan)
        
        return {
            "status": "success",
            "data": result
        }
        
    except Exception as e:
        return {"status": "error", "error": str(e)}

def _process_plan_submission(plan):
    """Process the submitted plan and prepare for user approval."""
    
    # Clean and format the plan
    formatted_plan = plan.strip()
    
    # Generate plan metadata
    plan_lines = formatted_plan.split('\n')
    plan_hash = hashlib.md5(formatted_plan.encode()).hexdigest()[:8]
    
    # Analyze plan structure
    analysis = _analyze_plan_structure(formatted_plan)
    
    # Generate response
    return {
        "plan": formatted_plan,
        "planId": plan_hash,
        "submittedAt": int(time.time()),
        "action": "exit_plan_mode",
        "status": "submitted_for_approval",
        "analysis": analysis,
        "metadata": {
            "lineCount": len(plan_lines),
            "wordCount": len(formatted_plan.split()),
            "characterCount": len(formatted_plan),
            "estimatedReadTime": max(1, len(formatted_plan.split()) // 200)  # ~200 words per minute
        },
        "message": "Plan submitted for user approval. Waiting for confirmation to proceed with execution."
    }

def _analyze_plan_structure(plan):
    """Analyze the structure and content of the plan."""
    analysis = {
        "hasHeaders": False,
        "hasSteps": False,
        "hasTimeline": False,
        "hasImplementationDetails": False,
        "sections": [],
        "complexity": "simple"
    }
    
    lines = plan.split('\n')
    
    # Look for markdown headers
    header_count = 0
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('#'):
            analysis["hasHeaders"] = True
            header_count += 1
            # Extract section name
            section_name = stripped.lstrip('#').strip()
            if section_name:
                analysis["sections"].append(section_name)
    
    # Look for numbered steps or bullet points
    step_patterns = [
        r'^\d+\.',  # Numbered lists
        r'^\*\s',   # Bullet points with *
        r'^-\s',    # Bullet points with -
        r'^\[\s*\]', # Checkboxes
    ]
    
    step_count = 0
    for line in lines:
        stripped = line.strip()
        for pattern in step_patterns:
            if __import__('re').match(pattern, stripped):
                step_count += 1
                break
    
    if step_count > 2:
        analysis["hasSteps"] = True
    
    # Look for implementation keywords
    implementation_keywords = [
        "implement", "create", "build", "develop", "code", "write",
        "function", "class", "method", "test", "deploy", "install"
    ]
    
    plan_lower = plan.lower()
    implementation_mentions = sum(1 for keyword in implementation_keywords if keyword in plan_lower)
    if implementation_mentions > 3:
        analysis["hasImplementationDetails"] = True
    
    # Look for timeline indicators
    timeline_keywords = [
        "first", "then", "next", "after", "finally", "step",
        "phase", "stage", "before", "during", "complete"
    ]
    
    timeline_mentions = sum(1 for keyword in timeline_keywords if keyword in plan_lower)
    if timeline_mentions > 2:
        analysis["hasTimeline"] = True
    
    # Determine complexity
    complexity_score = 0
    if analysis["hasHeaders"]:
        complexity_score += 1
    if analysis["hasSteps"]:
        complexity_score += 1
    if analysis["hasImplementationDetails"]:
        complexity_score += 1
    if analysis["hasTimeline"]:
        complexity_score += 1
    if len(analysis["sections"]) > 3:
        complexity_score += 1
    if len(plan.split()) > 500:
        complexity_score += 1
    
    if complexity_score >= 4:
        analysis["complexity"] = "complex"
    elif complexity_score >= 2:
        analysis["complexity"] = "moderate"
    else:
        analysis["complexity"] = "simple"
    
    return analysis

def get_schema():
    """Return Fractalic-compatible JSON schema."""
    return {
        "name": "_exitplanmode",
        "description": "Use this tool when you are in plan mode and have finished presenting your plan and are ready to code. This will prompt the user to exit plan mode. IMPORTANT: Only use this tool when the task requires planning the implementation steps of a task that requires writing code. For research tasks where you're gathering information, searching files, reading files or in general trying to understand the codebase - do NOT use this tool.",
        "parameters": {
            "type": "object",
            "properties": {
                "plan": {
                    "type": "string",
                    "description": "The plan you came up with, that you want to run by the user for approval. Supports markdown. The plan should be pretty concise."
                }
            },
            "required": ["plan"],
            "additionalProperties": False
        }
    }

def main():
    """Main entry point for the tool."""
    # Discovery test (REQUIRED)
    if len(sys.argv) == 2 and sys.argv[1] == '{"__test__": true}':
        print(json.dumps({"success": True, "_simple": True}))
        return
    
    # Schema dump (REQUIRED)
    if len(sys.argv) == 2 and sys.argv[1] == "--fractalic-dump-schema":
        print(json.dumps(get_schema(), indent=2))
        return
    
    # Main execution
    if len(sys.argv) != 2:
        print(json.dumps({"status": "error", "error": "Expected exactly one JSON argument"}))
        sys.exit(1)
    
    try:
        params = json.loads(sys.argv[1])
        if not isinstance(params, dict):
            raise ValueError("Input must be a JSON object")
        
        result = process_data(params)
        print(json.dumps(result, ensure_ascii=False))
        
        # Exit with appropriate code
        if result.get("status") == "error":
            sys.exit(1)
        
    except json.JSONDecodeError as e:
        print(json.dumps({"status": "error", "error": f"Invalid JSON input: {str(e)}"}))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"status": "error", "error": str(e)}))
        sys.exit(1)

if __name__ == "__main__":
    main()