# Fractalic Tools Integration Guide

## Overview

This document describes how Fractalic frontend can deterministically parse the README.md to extract tool information for marketplace integration and one-click installation from the remote GitHub repository.

## Parsing Logic

### README.md Structure

The README.md follows a strict hierarchical structure that enables reliable parsing:

```
# Fractalic Tools Marketplace
## Tool Categories
### 🔧 Category Name (N tools)
- **[Tool Name](./path/to/tool.py)** - Description
```

### Parsing Algorithm

1. **Category Detection**: Lines starting with `### ` followed by emoji, category name, and tool count in parentheses
2. **Tool Detection**: Lines starting with `- **[` containing tool name, path, and description
3. **Path Extraction**: Tool paths are in format `(./relative/path/to/tool.py)`

### Regular Expressions

```javascript
// Category pattern
const categoryPattern = /^### (.+) \((\d+) tools?\)$/;

// Tool pattern  
const toolPattern = /^- \*\*\[(.+?)\]\((.+?)\)\*\* - (.+)$/;
```

## Data Structure

### Tool Object
```json
{
  "name": "Tool Name",
  "path": "./category/subcategory/tool.py",
  "description": "Tool description",
  "category": "Category Name",
  "categoryIcon": "🔧",
  "fullGitHubPath": "https://raw.githubusercontent.com/USER/REPO/main/category/subcategory/tool.py"
}
```

### Category Object
```json
{
  "name": "Category Name", 
  "icon": "🔧",
  "toolCount": 5,
  "tools": [/* Tool objects */]
}
```

## Complete Tool List

Based on current README.md structure, here are all 61 tools with their exact paths:

### Core (2 tools)
- `./core/fractalic-opgen/fractalic_opgen.py`
- `./core/workflow-utilities/anchor_window_patch.py`

### CRM (47 tools)
#### Management (16 tools)
- `./crm/hubspot-suite/manage/hubspot_contact_get_or_create.py`
- `./crm/hubspot-suite/manage/hubspot_contact_update.py`
- `./crm/hubspot-suite/manage/hubspot_deal_create_standalone.py`
- `./crm/hubspot-suite/manage/hubspot_deal_search.py`
- `./crm/hubspot-suite/manage/hubspot_deal_update.py`
- `./crm/hubspot-suite/manage/hubspot_deal_update_stage.py`
- `./crm/hubspot-suite/manage/hubspot_ticket_create_smart.py`
- `./crm/hubspot-suite/manage/hubspot_ticket_update.py`
- `./crm/hubspot-suite/manage/hubspot_task_create_advanced.py`
- `./crm/hubspot-suite/manage/hubspot_email_send.py`
- `./crm/hubspot-suite/manage/hubspot_associate.py`
- `./crm/hubspot-suite/manage/hubspot_bulk_update.py`
- `./crm/hubspot-suite/manage/hubspot_intelligent_batch.py`
- `./crm/hubspot-suite/manage/hubspot_owner_round_robin.py`
- `./crm/hubspot-suite/manage/hubspot_schema_cache.py`
- `./crm/hubspot-suite/manage/hubspot_smart_validator.py`

#### Discovery & Process Mining (19 tools)  
- `./crm/hubspot-suite/discovery/tools/hubspot_properties_discover.py`
- `./crm/hubspot-suite/discovery/tools/hubspot_pipelines_discover.py`
- `./crm/hubspot-suite/discovery/tools/hubspot_universal_enumerator.py`
- `./crm/hubspot-suite/discovery/tools/process_mining_analysis.py`
- `./crm/hubspot-suite/discovery/tools/run_full_process_mining.py`
- `./crm/hubspot-suite/discovery/tools/hubspot_activity_pattern_miner.py`
- `./crm/hubspot-suite/discovery/tools/hubspot_bottleneck_identifier.py`
- `./crm/hubspot-suite/discovery/tools/hubspot_customer_journey_mapper.py`
- `./crm/hubspot-suite/discovery/tools/hubspot_deal_timeline_extractor.py`
- `./crm/hubspot-suite/discovery/tools/hubspot_process_flow_analyzer.py`
- `./crm/hubspot-suite/discovery/tools/hubspot_account_discovery.py`
- `./crm/hubspot-suite/discovery/tools/hubspot_automation_recommender.py`
- `./crm/hubspot-suite/discovery/tools/hubspot_connection_tracer.py`
- `./crm/hubspot-suite/discovery/tools/hubspot_data_relationship_mapper.py`
- `./crm/hubspot-suite/discovery/tools/hubspot_detailed_process_extractor.py`
- `./crm/hubspot-suite/discovery/tools/hubspot_graph_process_miner.py`
- `./crm/hubspot-suite/discovery/tools/hubspot_graph_visualizer.py`
- `./crm/hubspot-suite/discovery/tools/hubspot_integration_gap_finder.py`
- `./crm/hubspot-suite/discovery/tools/hubspot_object_association_analyzer.py`

#### Additional Tools (12 tools)
- `./crm/hubspot-suite/discovery/tools/hubspot_object_audit_trail.py`
- `./crm/hubspot-suite/discovery/tools/hubspot_organization_analyzer.py`
- `./crm/hubspot-suite/discovery/tools/hubspot_process_sequence_detector.py`
- `./crm/hubspot-suite/discovery/tools/hubspot_property_usage_analyzer.py`
- `./crm/hubspot-suite/discovery/tools/hubspot_workflow_optimizer.py`
- `./crm/hubspot-suite/hubspot_hub_helpers.py`
- `./crm/hubspot-suite/manage/hubspot_hub_helpers.py`
- `./crm/hubspot-suite/discovery/tools/hubspot_hub_helpers.py`

### Communication (1 tool)
- `./communication/telegram/telegram_automation_simple.py`

### Development (12 tools)
#### File Operations (5 tools)
- `./development/file-ops/read.py`
- `./development/file-ops/write.py`
- `./development/file-ops/edit.py`
- `./development/file-ops/multiedit.py`
- `./development/file-ops/glob.py`

#### Shell Operations (2 tools)
- `./development/shell/bash.py`
- `./development/shell/shell_tool.py`

#### Search & Navigation (2 tools)
- `./development/search/grep.py`
- `./development/search/ls.py`

#### Workflow (1 tool)
- `./development/workflow/exitplanmode.py`

### Web (3 tools)
#### Scraping (2 tools)
- `./web/scraping/webfetch.py`
- `./web/scraping/get_web_markdown.py`

#### Search (1 tool)
- `./web/search/tavily_search.py`

### Productivity (1 tool)
- `./productivity/tasks/todowrite.py`

### System (1 tool)
- `./system/ui/ui_server.py`

## Implementation Example

### JavaScript Parser
```javascript
async function parseToolsFromReadme(repoUrl) {
  const readmeUrl = `${repoUrl}/raw/main/README.md`;
  const response = await fetch(readmeUrl);
  const content = await response.text();
  
  const lines = content.split('\n');
  const categories = [];
  let currentCategory = null;
  
  for (const line of lines) {
    // Match category header
    const categoryMatch = line.match(/^### (.+) \((\d+) tools?\)$/);
    if (categoryMatch) {
      const [, fullName, count] = categoryMatch;
      const iconMatch = fullName.match(/^(.+?) (.+)$/);
      
      currentCategory = {
        name: iconMatch ? iconMatch[2] : fullName,
        icon: iconMatch ? iconMatch[1] : '',
        toolCount: parseInt(count),
        tools: []
      };
      categories.push(currentCategory);
      continue;
    }
    
    // Match tool entry
    const toolMatch = line.match(/^- \*\*\[(.+?)\]\((.+?)\)\*\* - (.+)$/);
    if (toolMatch && currentCategory) {
      const [, name, path, description] = toolMatch;
      
      currentCategory.tools.push({
        name,
        path,
        description,
        category: currentCategory.name,
        categoryIcon: currentCategory.icon,
        fullGitHubPath: `${repoUrl}/raw/main/${path.substring(2)}` // Remove ./
      });
    }
  }
  
  return categories;
}
```

### Python Parser
```python
import re
import requests

def parse_tools_from_readme(repo_url):
    readme_url = f"{repo_url}/raw/main/README.md"
    response = requests.get(readme_url)
    content = response.text
    
    lines = content.split('\n')
    categories = []
    current_category = None
    
    category_pattern = re.compile(r'^### (.+) \((\d+) tools?\)$')
    tool_pattern = re.compile(r'^- \*\*\[(.+?)\]\((.+?)\)\*\* - (.+)$')
    
    for line in lines:
        # Match category
        category_match = category_pattern.match(line)
        if category_match:
            full_name, count = category_match.groups()
            icon_match = re.match(r'^(.+?) (.+)$', full_name)
            
            current_category = {
                'name': icon_match.group(2) if icon_match else full_name,
                'icon': icon_match.group(1) if icon_match else '',
                'toolCount': int(count),
                'tools': []
            }
            categories.append(current_category)
            continue
            
        # Match tool
        tool_match = tool_pattern.match(line)
        if tool_match and current_category:
            name, path, description = tool_match.groups()
            
            current_category['tools'].append({
                'name': name,
                'path': path,
                'description': description,
                'category': current_category['name'],
                'categoryIcon': current_category['icon'],
                'fullGitHubPath': f"{repo_url}/raw/main/{path[2:]}"  # Remove ./
            })
    
    return categories
```

## One-Click Installation

### Installation Process
1. **Tool Selection**: User selects tool from marketplace UI
2. **Path Resolution**: Convert relative path to full GitHub raw URL
3. **Download**: Fetch tool content from GitHub
4. **Local Installation**: Save to user's local tools directory
5. **Dependency Check**: Check for additional files (requirements.txt, etc.)
6. **Verification**: Run autodiscovery test to confirm installation

### Dependencies Handling
- **HubSpot tools**: Require `HUBSPOT_TOKEN` environment variable
- **Telegram tools**: Include `telegram_requirements.txt` in same directory
- **Core tools**: No external dependencies

### Installation URLs
Base repository: `https://github.com/USER/REPO`

Tool URLs follow pattern:  
`https://raw.githubusercontent.com/USER/REPO/main/{path_without_dot_slash}`

Example:  
`./core/fractalic-opgen/fractalic_opgen.py` →  
`https://raw.githubusercontent.com/USER/REPO/main/core/fractalic-opgen/fractalic_opgen.py`

## Validation

The parsing logic can be validated by ensuring:
1. Total tool count matches: **61 tools**
2. Category counts match README headers
3. All paths are valid and point to existing Python files
4. All tools pass autodiscovery test: `python tool.py '{"__test__": true}'`

This deterministic structure enables reliable marketplace integration with one-click tool installation from the remote repository.