# 360-Degree HubSpot Process Discovery - Complete Example Prompt

## 🎯 **Objective**
Perform a comprehensive 360-degree analysis of all business processes in this HubSpot account to create a complete operational map, identify optimization opportunities, and provide actionable recommendations for process improvement and automation.

## 🔍 **Discovery Mission**

**Your task is to systematically discover, analyze, and map ALL business processes across this HubSpot account using the Universal Process Discovery System. Follow this structured approach to build a complete 360-degree view:**

---

## 📋 **Phase 1: Environmental Discovery**

### **1.1 Account Landscape Analysis**
Start by understanding the complete HubSpot environment:

```
Use hubspot_account_discovery with comprehensive scope to map:
- What HubSpot modules are enabled (Sales, Marketing, Service, Operations, CMS)
- What object types exist (standard + custom)
- What integrations are connected
- What workflows and automations are configured
- API limits and account tier information

Parameters: {"scope": "all", "includeCustomObjects": true, "includeLimits": true}
```

### **1.2 Organizational Structure Mapping**
Understand who's doing what:

```
Use hubspot_organization_analyzer to discover:
- Team structure and hierarchies
- Owner assignments and workload distribution
- Performance patterns across teams
- Resource allocation and bottlenecks

Parameters: {"analysis_scope": "all", "include_metrics": true, "time_range_days": 90}
```

---

## 📊 **Phase 2: Object & Data Discovery**

### **2.1 Property Landscape Analysis**
Understand data utilization patterns:

```
Use hubspot_property_usage_analyzer to identify:
- Which properties are actually being used vs. ignored
- Data quality issues and inconsistencies
- Custom property adoption patterns
- Optimization opportunities for data collection

Parameters: {"object_types": ["contacts", "deals", "companies", "tickets"], "sample_size": 200, "analyze_data_quality": true}
```

### **2.2 Pipeline & Stage Configuration**
Map all configured processes:

```
Use hubspot_pipelines_discover to catalog:
- All pipelines across object types
- Stage configurations and progression rules
- Custom vs. standard pipeline usage
- Stage transition patterns

Parameters: {"object_types": ["deals", "tickets"], "include_usage_stats": true}
```

### **2.3 Properties Schema Discovery**
Get complete field inventory:

```
Use hubspot_properties_discover to document:
- All available properties per object type
- Field types, options, and dependencies
- Custom property implementations
- Required vs. optional field usage

Parameters: {"object_types": ["contacts", "deals", "companies", "tickets"], "include_options": true}
```

---

## 🔄 **Phase 3: Process Flow Analysis**

### **3.1 Cross-Object Process Mapping**
Understand end-to-end business processes:

```
Use hubspot_process_flow_analyzer to analyze:
- Deal progression patterns and bottlenecks
- Contact lifecycle stages and transitions
- Ticket resolution processes and escalation paths
- Cross-object interactions and dependencies

Parameters: {"analysis_type": "cross_object", "time_period_days": 90, "include_stages": true, "include_timing": true}
```

### **3.2 Graph-Based Process Mining**
Discover hidden process networks:

```
Use hubspot_graph_process_miner to uncover:
- Complex relationship networks between objects
- Process flow paths and decision points
- Cluster analysis of similar processes
- Network bottlenecks and critical paths

Parameters: {"object_type": "deals", "analysis_mode": "network", "include_visualization": true, "max_depth": 3}
```

### **3.3 Process Sequence Detection**
Identify common patterns:

```
Use hubspot_process_sequence_detector to find:
- Recurring process sequences and patterns
- Common task progressions and workflows
- Deviation patterns from standard processes
- Optimization opportunities for automation

Parameters: {"focus_area": "comprehensive", "pattern_types": ["sequences", "deviations", "bottlenecks"]}
```

---

## 🔗 **Phase 4: Relationship & Connection Analysis**

### **4.1 Object Association Deep Dive**
Map how objects connect:

```
Use hubspot_object_association_analyzer to understand:
- How different object types relate to each other
- Association patterns and relationship strength
- Missing or weak connections
- Opportunities for better data linking

Parameters: {"analysis_scope": "comprehensive", "include_strength_metrics": true}
```

### **4.2 Customer Journey Mapping**
Trace complete customer experiences:

```
Use hubspot_customer_journey_mapper to map:
- End-to-end customer experience paths
- Touchpoint analysis and interaction patterns
- Journey stage identification and progression
- Drop-off points and engagement gaps

Parameters: {"journey_type": "complete_lifecycle", "include_touchpoints": true, "analyze_drop_offs": true}
```

### **4.3 Connection Tracing**
Follow relationship networks:

```
Use hubspot_connection_tracer to trace:
- Customer journey paths from lead to close
- Process participant networks
- Attribution chains for deals and conversions
- Cross-module connection mapping

Parameters: {"traceMode": "customer_journey", "maxDepth": 4, "extractProperties": true}
```

---

## ⚡ **Phase 5: Automation & Optimization Analysis**

### **5.1 Automation Opportunity Discovery**
Find automation potential:

```
Use hubspot_automation_recommender to identify:
- Repetitive processes suitable for automation
- Workflow optimization opportunities
- Integration gaps that could be automated
- ROI potential for automation investments

Parameters: {"analysis_scope": "comprehensive", "include_roi_estimates": true}
```

### **5.2 Workflow Optimization Analysis**
Improve existing processes:

```
Use hubspot_workflow_optimizer to analyze:
- Current workflow efficiency and bottlenecks
- Optimization opportunities and recommendations
- Resource allocation improvements
- Process standardization opportunities

Parameters: {"focus": "bottlenecks", "include_recommendations": true}
```

### **5.3 Integration Gap Analysis**
Find missing connections:

```
Use hubspot_integration_gap_finder to discover:
- Data silos and integration opportunities
- Missing process connections
- System integration gaps
- Data flow optimization potential

Parameters: {"scope": "comprehensive", "include_recommendations": true}
```

---

## 📈 **Phase 6: Historical & Audit Analysis**

### **6.1 Process Timeline Extraction**
Understand historical patterns:

```
Use hubspot_deal_timeline_extractor to analyze:
- Deal progression timelines and patterns
- Historical process performance
- Seasonal and temporal trends
- Process evolution over time

Parameters: {"analysis_period": "comprehensive", "include_patterns": true}
```

### **6.2 Audit Trail Deep Dive**
Examine process history:

```
Use hubspot_object_audit_trail to investigate:
- Process change history and evolution
- Property modification patterns
- Activity timelines and engagement patterns
- Process compliance and governance

Parameters: {"objectType": "deals", "auditScope": "full", "timeRange": {"daysBack": 180}}
```

---

## 🎯 **Final Synthesis Instructions**

After completing all discovery phases, synthesize findings into:

### **Executive Summary**
- **Account Overview**: Modules, objects, scale, and complexity
- **Process Maturity**: Current state assessment
- **Key Opportunities**: Top 5 optimization opportunities
- **Risk Assessment**: Process vulnerabilities and single points of failure

### **Detailed Analysis**
- **Process Map**: Complete business process flowchart
- **Bottleneck Analysis**: Specific delays and inefficiencies
- **Data Quality Assessment**: Property usage and data integrity
- **Automation Roadmap**: Prioritized automation opportunities
- **Integration Strategy**: Missing connections and integration needs

### **Actionable Recommendations**
- **Quick Wins**: Immediate improvements (0-30 days)
- **Strategic Initiatives**: Medium-term optimizations (1-6 months)
- **Long-term Vision**: Comprehensive transformation roadmap
- **ROI Projections**: Expected benefits and investment requirements

---

## 🔄 **Execution Notes**

### **Progressive Discovery**
1. **Start Broad**: Account discovery and organizational mapping
2. **Go Deep**: Focus on high-impact areas identified in broad analysis
3. **Cross-Reference**: Validate findings across multiple tools and perspectives
4. **Synthesize**: Combine insights into actionable intelligence

### **Concise First Approach**
- Use default parameters initially for broad understanding
- Drill down with detailed analysis only where specific insights are needed
- Focus on actionable opportunities rather than exhaustive data dumps

### **Context Building**
- Each phase builds on previous discoveries
- Use findings from earlier phases to guide later analysis
- Cross-reference insights across different tools for validation

---

**This systematic approach will provide a complete 360-degree view of the HubSpot account's business processes, revealing optimization opportunities and providing a clear roadmap for process improvement and automation.** 🎯
