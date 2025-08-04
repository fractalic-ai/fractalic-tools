# Fractalic Tools Marketplace

A comprehensive collection of automation tools for the Fractalic AI workflow platform. All tools follow the Simple Autodiscovery JSON Schema Logic for seamless integration.

## Tool Packs

### 🤖 Fractalic (3 tools)
Core Fractalic workflow platform tools and utilities

- **[Fractalic Operation Generator](./fractalic/fractalic_opgen.py)** - Generate Fractalic operation blocks (YAML) from JSON input
- **[Exit Plan Mode](./fractalic/exitplanmode.py)** - Plan mode management and workflow control
- **[UI Server](./fractalic/ui_server.py)** - UI server implementation for Fractalic interface

### 🏢 CRM (47 tools)
Complete HubSpot CRM automation suite with process mining capabilities

#### Management Tools (16 tools)
- **[Contact Get/Create](./crm/hubspot-suite/manage/hubspot_contact_get_or_create.py)** - Find existing contacts or create new ones with smart deduplication
- **[Contact Update](./crm/hubspot-suite/manage/hubspot_contact_update.py)** - Update contact fields with selective updates
- **[Deal Create](./crm/hubspot-suite/manage/hubspot_deal_create_standalone.py)** - Create deals independently with enhanced validation
- **[Deal Search](./crm/hubspot-suite/manage/hubspot_deal_search.py)** - Search deals by email, ID, name, amount, or custom properties
- **[Deal Update](./crm/hubspot-suite/manage/hubspot_deal_update.py)** - Update deal properties with validation
- **[Deal Stage Update](./crm/hubspot-suite/manage/hubspot_deal_update_stage.py)** - Move deals through pipeline stages
- **[Ticket Create](./crm/hubspot-suite/manage/hubspot_ticket_create_smart.py)** - Create tickets with intelligent discovery
- **[Ticket Update](./crm/hubspot-suite/manage/hubspot_ticket_update.py)** - Update ticket status and properties
- **[Task Create Advanced](./crm/hubspot-suite/manage/hubspot_task_create_advanced.py)** - Create sophisticated tasks with relative dates
- **[Email Send](./crm/hubspot-suite/manage/hubspot_email_send.py)** - Send emails with automatic timestamp generation
- **[Associate Objects](./crm/hubspot-suite/manage/hubspot_associate.py)** - Create associations between CRM objects
- **[Bulk Update](./crm/hubspot-suite/manage/hubspot_bulk_update.py)** - Batch operations for up to 100 objects
- **[Intelligent Batch](./crm/hubspot-suite/manage/hubspot_intelligent_batch.py)** - Smart batch processing with fallback
- **[Owner Round Robin](./crm/hubspot-suite/manage/hubspot_owner_round_robin.py)** - Fair distribution of ownership assignments
- **[Schema Cache](./crm/hubspot-suite/manage/hubspot_schema_cache.py)** - Intelligent schema caching system
- **[Smart Validator](./crm/hubspot-suite/manage/hubspot_smart_validator.py)** - Pre-flight validation with auto-discovery

#### Discovery & Process Mining Tools (19 tools)
- **[Properties Discover](./crm/hubspot-suite/discovery/tools/hubspot_properties_discover.py)** - Context-efficient property discovery
- **[Pipelines Discover](./crm/hubspot-suite/discovery/tools/hubspot_pipelines_discover.py)** - Discover valid pipeline stages
- **[Universal Enumerator](./crm/hubspot-suite/discovery/tools/hubspot_universal_enumerator.py)** - Comprehensive object enumeration
- **[Process Mining Analysis](./crm/hubspot-suite/discovery/tools/process_mining_analysis.py)** - Comprehensive process mining data extraction
- **[Full Process Mining](./crm/hubspot-suite/discovery/tools/run_full_process_mining.py)** - Complete process mining pipeline
- **[Activity Pattern Miner](./crm/hubspot-suite/discovery/tools/hubspot_activity_pattern_miner.py)** - Activity pattern analysis
- **[Bottleneck Identifier](./crm/hubspot-suite/discovery/tools/hubspot_bottleneck_identifier.py)** - Process bottleneck detection
- **[Customer Journey Mapper](./crm/hubspot-suite/discovery/tools/hubspot_customer_journey_mapper.py)** - Customer journey analysis
- **[Deal Timeline Extractor](./crm/hubspot-suite/discovery/tools/hubspot_deal_timeline_extractor.py)** - Deal timeline analysis
- **[Process Flow Analyzer](./crm/hubspot-suite/discovery/tools/hubspot_process_flow_analyzer.py)** - Process sequence analysis
- **[Account Discovery](./crm/hubspot-suite/discovery/tools/hubspot_account_discovery.py)** - Account structure extraction
- **[Automation Recommender](./crm/hubspot-suite/discovery/tools/hubspot_automation_recommender.py)** - Workflow automation insights
- **[Connection Tracer](./crm/hubspot-suite/discovery/tools/hubspot_connection_tracer.py)** - Object relationship tracing
- **[Data Relationship Mapper](./crm/hubspot-suite/discovery/tools/hubspot_data_relationship_mapper.py)** - Data relationship mapping
- **[Detailed Process Extractor](./crm/hubspot-suite/discovery/tools/hubspot_detailed_process_extractor.py)** - Detailed process extraction
- **[Graph Process Miner](./crm/hubspot-suite/discovery/tools/hubspot_graph_process_miner.py)** - Graph-based process mining
- **[Graph Visualizer](./crm/hubspot-suite/discovery/tools/hubspot_graph_visualizer.py)** - Process flow visualization
- **[Integration Gap Finder](./crm/hubspot-suite/discovery/tools/hubspot_integration_gap_finder.py)** - Integration gap analysis
- **[Object Association Analyzer](./crm/hubspot-suite/discovery/tools/hubspot_object_association_analyzer.py)** - Association pattern analysis

#### Additional Tools (12 tools)
- **[Object Audit Trail](./crm/hubspot-suite/discovery/tools/hubspot_object_audit_trail.py)** - Comprehensive audit trails
- **[Organization Analyzer](./crm/hubspot-suite/discovery/tools/hubspot_organization_analyzer.py)** - Organizational workflow analysis
- **[Process Sequence Detector](./crm/hubspot-suite/discovery/tools/hubspot_process_sequence_detector.py)** - Business process sequences
- **[Property Usage Analyzer](./crm/hubspot-suite/discovery/tools/hubspot_property_usage_analyzer.py)** - Property usage patterns
- **[Workflow Optimizer](./crm/hubspot-suite/discovery/tools/hubspot_workflow_optimizer.py)** - Workflow efficiency analysis
- **[Hub Helpers (Main)](./crm/hubspot-suite/hubspot_hub_helpers.py)** - Core shared utilities
- **[Hub Helpers (Manage)](./crm/hubspot-suite/manage/hubspot_hub_helpers.py)** - Management utilities
- **[Hub Helpers (Discovery)](./crm/hubspot-suite/discovery/tools/hubspot_hub_helpers.py)** - Discovery utilities

### 💬 Communication (1 tool)
Communication platform integrations and messaging automation

- **[Telegram Automation](./communication/telegram/telegram_automation_simple.py)** - Complete Telegram automation with TDLib (get_chats, send_message, get_messages, etc.)

### 💻 OS (10 tools)
Operating system operations, file management, and shell utilities

- **[Read](./os/read.py)** - File reading with image support and line numbers
- **[Write](./os/write.py)** - File writing operations
- **[Edit](./os/edit.py)** - File editing operations
- **[Multi Edit](./os/multiedit.py)** - Multiple file editing
- **[Glob](./os/glob.py)** - File pattern matching
- **[Bash](./os/bash.py)** - Shell command execution
- **[Shell Tool](./os/shell_tool.py)** - Shell utilities wrapper
- **[Grep](./os/grep.py)** - Text search functionality
- **[Directory List](./os/ls.py)** - Directory listing
- **[Anchor Window Patch](./os/anchor_window_patch.py)** - Window anchoring and system utilities

### 🌐 Web (3 tools)
Web scraping, content extraction, and internet services

#### Scraping (2 tools)
- **[Web Fetch](./web/scraping/webfetch.py)** - Web content fetching
- **[Web to Markdown](./web/scraping/get_web_markdown.py)** - Web content extraction to Markdown

#### Search (1 tool)
- **[Tavily Search](./web/search/tavily_search.py)** - Tavily search API integration

### 📋 Project Management (1 tool)
Project management, task tracking, and productivity tools

- **[Todo Write](./project-management/todowrite.py)** - Task management and todo list operations

## Usage

All tools follow the Fractalic Simple Autodiscovery JSON Schema Logic:

```bash
# Test tool availability
python <tool_path> '{"__test__": true}'

# Get tool schema
python <tool_path> --fractalic-dump-schema

# Use tool with JSON parameters
python <tool_path> '{"param1": "value1", "param2": "value2"}'
```

## Tool Statistics

- **Total Tools**: 61
- **Tool Packs**: 6
- **Autodiscovery Compliant**: 100%
- **Language**: Python
- **Integration**: Fractalic AI workflow platform

## Dependencies

### HubSpot Tools (CRM Pack)
- Set environment variable: `export HUBSPOT_TOKEN="your_token"`
- All HubSpot tools share authentication and utilities

### Telegram Tools (Communication Pack)
- Run interactive setup: `python communication/telegram/telegram_automation_simple.py --init`
- Dependencies: `pip install -r communication/telegram/telegram_requirements.txt`

### OS Pack
- No external dependencies for most tools
- Self-contained Python implementations

### Fractalic Pack
- Core Fractalic platform tools
- No external dependencies

### Web Pack
- No external dependencies for basic tools
- API keys may be required for search services

### Project Management Pack
- No external dependencies
- Self-contained task management

## Pack Descriptions

### 🤖 Fractalic Pack
Essential tools for the Fractalic workflow platform including operation generation, UI management, and workflow control. These tools provide core functionality for building and managing AI workflows.

### 🏢 CRM Pack
Comprehensive HubSpot integration suite with 47 tools covering contact management, deal processing, ticket handling, and advanced process mining capabilities. Includes intelligent discovery, automation, and analytics tools.

### 💬 Communication Pack
Communication platform integrations starting with comprehensive Telegram automation. Enables chat management, message automation, and communication workflow integration.

### 💻 OS Pack
Operating system utilities covering file operations, shell execution, text processing, and system management. Provides fundamental OS-level capabilities for workflow automation.

### 🌐 Web Pack
Web interaction tools including content scraping, data extraction, and search services. Enables workflows to interact with web services and extract information from online sources.

### 📋 Project Management Pack
Project and task management tools for organizing workflows, tracking progress, and managing productivity. Includes todo management and project coordination utilities.

## Contributing

Tools must implement:
1. Discovery test: `'{"__test__": true}'` → `{"success": true, "_simple": true}`
2. Schema export: `--fractalic-dump-schema` → OpenAI-compatible schema
3. JSON input/output for all operations
4. Error handling with structured responses
5. Fast response times (<200ms for discovery)

---

*This repository serves as a tool marketplace for the Fractalic AI workflow platform, providing comprehensive business automation capabilities through standardized, autodiscoverable tools organized into functional packs.*