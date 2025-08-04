# 🔍 Quick 360° HubSpot Process Discovery Prompt

**Execute a comprehensive business process discovery across this HubSpot account. Follow this systematic approach to build a complete operational understanding:**

## Phase 1: Environment Scan
```
1. hubspot_account_discovery: {"scope": "all", "includeCustomObjects": true}
2. hubspot_organization_analyzer: {"analysis_scope": "all", "time_range_days": 90}
3. hubspot_property_usage_analyzer: {"object_types": ["contacts", "deals", "companies", "tickets"], "sample_size": 100}
```

## Phase 2: Process Analysis  
```
4. hubspot_process_flow_analyzer: {"analysis_type": "cross_object", "time_period_days": 90, "include_stages": true}
5. hubspot_graph_process_miner: {"object_type": "deals", "analysis_mode": "network", "max_depth": 3}
6. hubspot_customer_journey_mapper: {"journey_type": "complete_lifecycle", "include_touchpoints": true}
```

## Phase 3: Optimization Discovery
```
7. hubspot_automation_recommender: {"analysis_scope": "comprehensive", "include_roi_estimates": true}
8. hubspot_workflow_optimizer: {"focus": "bottlenecks", "include_recommendations": true}
9. hubspot_integration_gap_finder: {"scope": "comprehensive", "include_recommendations": true}
```

## Final Output Required:
**Provide a structured report with:**
- **Executive Summary**: Account state, process maturity, top opportunities
- **Process Map**: Key business flows and bottlenecks identified
- **Quick Wins**: 3-5 immediate optimization opportunities  
- **Strategic Roadmap**: Prioritized automation and process improvement plan
- **ROI Assessment**: Expected benefits and implementation effort

**Focus on actionable insights, not data dumps. Synthesize findings across all tools to create a coherent operational intelligence report.**
