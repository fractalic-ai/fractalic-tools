# HubSpot Discovery & Process Mining Archive

This directory contains process mining, analysis, and discovery tools for understanding HubSpot workflows and business processes.

## Directory Structure

### `/reports/`
- **COMPLETE_PROCESS_DISCOVERY_REPORT.md** - Final comprehensive process discovery report
- **FINAL_COMPLETION_REPORT.md** - Project completion summary
- **PHASE_1_FIX_PROGRESS_REPORT.md** - Phase 1 progress tracking
- **PHASE_2_COMPLETION_REPORT.md** - Phase 2 completion status
- **STANDARDIZATION_COMPLETION_REPORT.md** - Tool standardization results

### `/analysis_docs/`
- **FRACTALIC_FEEDBACK_ANALYSIS.md** - Fractalic integration feedback analysis
- **SMART_TOOLS_SUMMARY.md** - Summary of smart tools development
- **hubspot-common-properties-reference.md** - Common HubSpot properties reference
- **hubspot-integration-guide.md** - HubSpot integration guide
- **hubspot-properties-improvement-analysis.md** - Properties improvement analysis
- **hubspot-sdk-analysis-smart-tools.md** - SDK analysis for smart tools
- **hubspot-testing-pipeline.md** - Testing pipeline documentation

### `/workflow_examples/`
- **3d-printing-lead-workflow.md** - 3D printing lead workflow example
- **ads-streaming-lead-workflow.md** - Ads streaming lead workflow example
- **electronics-marketplace-workflow.md** - Electronics marketplace workflow
- **logistics-delivery-workflow.md** - Logistics delivery workflow example

### `/templates/`
- **\*.template** - Template versions of tools before standardization
- Used for reference and comparison during development

### `/debug/`
- **debug_hubspot_structure.py** - HubSpot API structure debugging
- **debug_process_mining.py** - Process mining debugging utilities

### `/archived_data/`
- **hubspot_graph_process_mining_\*.json** - Archived process mining results
- **hubspot_graph_process_mining_\*.dot** - Graph visualization data
- **deal_data_sample.json** - Sample deal data for testing

### `/tools/`
Core HubSpot operation tools (moved from main directory):
- **hubspot_associate.py** - Object association management
- **hubspot_bulk_update.py** - Bulk update operations
- **hubspot_contact_get_or_create.py** - Contact management
- **hubspot_contact_update.py** - Contact updates
- **hubspot_deal_create_standalone.py** - Deal creation
- **hubspot_deal_search.py** - Deal search functionality
- **hubspot_deal_update.py** - Deal updates
- **hubspot_deal_update_stage.py** - Deal stage updates
- **hubspot_email_send.py** - Email sending
- **hubspot_intelligent_batch.py** - Intelligent batch operations
- **hubspot_owner_round_robin.py** - Owner assignment
- **hubspot_pipelines_discover.py** - Pipeline discovery
- **hubspot_properties_discover.py** - Properties discovery
- **hubspot_schema_cache.py** - Schema caching
- **hubspot_smart_validator.py** - Smart validation
- **hubspot_task_create_advanced.py** - Advanced task creation
- **hubspot_ticket_create_smart.py** - Smart ticket creation
- **hubspot_ticket_update.py** - Ticket updates

Experimental and discovery tools:
- **hubspot_account_discovery.py** - Account structure discovery
- **hubspot_automation_recommender.py** - Automation recommendations
- **hubspot_connection_tracer.py** - Connection tracing
- **hubspot_customer_journey_mapper.py** - Customer journey mapping
- **hubspot_deal_timeline_extractor.py** - Deal timeline extraction
- **hubspot_graph_process_miner.py** - Graph-based process mining
- **hubspot_graph_visualizer.py** - Process visualization
- **hubspot_integration_gap_finder.py** - Integration gap analysis
- **hubspot_object_association_analyzer.py** - Object relationship analysis
- **hubspot_object_audit_trail.py** - Audit trail extraction
- **hubspot_organization_analyzer.py** - Organization structure analysis
- **hubspot_process_sequence_detector.py** - Process sequence detection
- **hubspot_property_usage_analyzer.py** - Property usage analytics
- **hubspot_universal_enumerator.py** - Universal data enumeration
- **hubspot_workflow_optimizer.py** - Workflow optimization
- **run_full_process_mining.py** - Comprehensive process mining runner

### Root Level Documents
- **fractalic-process-mining-system-prompt.md** - Fractalic system integration prompt
- **universal_data_access_architecture.md** - Universal data access design
- **universal_process_discovery_system_prompt.md** - Universal discovery system prompt
- **universal_process_discovery_system_proposal.md** - System proposal document

## Core Standardized Tools (Remain in Parent Directory)

The following tools have been standardized with Fractalic integration and remain in the main directory:
- **hubspot_activity_pattern_miner.py** - Activity pattern detection and analysis
- **hubspot_bottleneck_identifier.py** - Workflow bottleneck identification  
- **hubspot_data_relationship_mapper.py** - Data relationship mapping and analysis
- **hubspot_detailed_process_extractor.py** - Detailed process extraction
- **hubspot_process_flow_analyzer.py** - Process flow analysis and variants
- **process_mining_analysis.py** - Comprehensive process mining analysis
- **hubspot_hub_helpers.py** - Core HubSpot client helper functions

## Usage

These archived tools and documents serve as:
1. **Reference Material** - For understanding the discovery process
2. **Template Source** - For creating new similar tools
3. **Historical Context** - Documentation of the development journey
4. **Research Data** - Archived results and analysis
