# HubSpot Management Tools

This folder contains operational HubSpot tools for data management, CRUD operations, and workflow automation.

## 📁 Tool Categories

### **Object Management**
- `hubspot_contact_get_or_create.py` - Contact creation and retrieval
- `hubspot_contact_update.py` - Contact updates
- `hubspot_deal_create_standalone.py` - Deal creation
- `hubspot_deal_search.py` - Deal search functionality
- `hubspot_deal_update.py` - Deal updates
- `hubspot_deal_update_stage.py` - Deal stage management
- `hubspot_task_create_advanced.py` - Advanced task creation
- `hubspot_ticket_create_smart.py` - Smart ticket creation
- `hubspot_ticket_update.py` - Ticket updates

### **Bulk Operations**
- `hubspot_bulk_update.py` - Bulk data updates
- `hubspot_intelligent_batch.py` - Intelligent batch processing

### **Workflow & Automation**
- `hubspot_associate.py` - Object associations
- `hubspot_email_send.py` - Email automation
- `hubspot_owner_round_robin.py` - Owner assignment automation
- `hubspot_smart_validator.py` - Data validation

### **Utilities**
- `hubspot_schema_cache.py` - Schema caching utilities

## 🎯 Purpose

These tools are designed for:
- Creating, reading, updating, and deleting HubSpot objects
- Automating routine HubSpot operations
- Bulk data management and synchronization
- Workflow automation and business process execution

## 🔄 Relationship to Other Folders

- **Main Directory**: Contains standardized process mining and analysis tools
- **`/discovery`**: Contains experimental process discovery and analysis tools
- **`/manage`**: Contains operational CRUD and workflow automation tools (this folder)

## 📋 Usage

Each tool follows the standard Fractalic pattern:
- JSON schema export via `--get-schema`
- Test mode via `--test`
- Robust stdin/stdout JSON I/O
- HubSpot API token integration
- Comprehensive error handling

Example:
```bash
python hubspot_contact_get_or_create.py --get-schema
python hubspot_contact_get_or_create.py --test
echo '{"email": "test@example.com", "hubspot_token": "your_token"}' | python hubspot_contact_get_or_create.py
```
