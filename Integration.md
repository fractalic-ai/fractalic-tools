# Fractalic Tools Integration Guide

## Overview

This document describes the data model and parsing logic for the README.md file to enable deterministic extraction of tool information for marketplace integration and one-click installation from the remote GitHub repository.

## README.md Data Model

### Structure Hierarchy

The README.md follows a strict hierarchical structure:

```
# Fractalic Tools Marketplace
## Tool Categories
### 🔧 Category Name (N tools)
#### Subcategory Name (N tools)
- **[Tool Name](./path/to/tool.py)** - Description
```

### Data Elements

#### Category Header
- **Pattern**: `### {emoji} {category_name} ({count} tool{s})`  
- **Purpose**: Defines tool categories with visual icons and counts
- **Example**: `### 🔧 Core (2 tools)`

#### Subcategory Header (Optional)
- **Pattern**: `#### {subcategory_name} ({count} tool{s})`
- **Purpose**: Groups related tools within categories
- **Example**: `#### File Operations (5 tools)`

#### Tool Entry
- **Pattern**: `- **[{tool_name}](./{relative_path}){suffix}** - {description}`
- **Components**:
  - `tool_name`: Display name for the tool
  - `relative_path`: Path from repository root (starts with `./`)
  - `description`: Brief functional description
- **Example**: `- **[Read](./development/file-ops/read.py)** - File reading with image support`

## Parsing Logic

### Regular Expressions

#### Category Detection
```regex
^### (.+?) \((\d+) tools?\)$
```
**Captures**: `[full_title, count]`
**Title Format**: `{emoji} {category_name}`

#### Subcategory Detection  
```regex
^#### (.+?) \((\d+) tools?\)$
```
**Captures**: `[subcategory_name, count]`

#### Tool Detection
```regex
^- \*\*\[(.+?)\]\((.+?)\)\*\* - (.+)$
```
**Captures**: `[tool_name, path, description]`

### Parsing Algorithm

1. **Line-by-line processing** of README.md content
2. **State tracking** for current category and subcategory context
3. **Pattern matching** using regular expressions for each line type
4. **Path normalization** from relative (`./path`) to absolute GitHub URLs
5. **Hierarchical grouping** of tools under categories and subcategories

### Data Structure Model

#### Tool Object
```json
{
  "name": "string",
  "path": "string (relative, starts with ./)",
  "description": "string", 
  "category": "string",
  "subcategory": "string (optional)",
  "githubUrl": "string (constructed)"
}
```

#### Category Object
```json
{
  "name": "string",
  "icon": "string (emoji)",
  "toolCount": "number",
  "subcategories": "CategoryObject[] (optional)",
  "tools": "ToolObject[]"
}
```

#### Root Structure
```json
{
  "totalTools": "number",
  "categories": "CategoryObject[]"
}
```

## URL Construction

### GitHub Raw URL Pattern
```
https://raw.githubusercontent.com/{owner}/{repo}/main/{path_without_dot_slash}
```

### Path Transformation
- **Input**: `./category/subcategory/tool.py`
- **Output**: `https://raw.githubusercontent.com/{owner}/{repo}/main/category/subcategory/tool.py`

## Validation Rules

### Structure Validation
1. **Tool count accuracy**: Category headers must match actual tool entries
2. **Path validity**: All relative paths must start with `./` and end with `.py`
3. **Hierarchy consistency**: Tools must appear under appropriate category/subcategory headers
4. **Unique paths**: No duplicate tool paths within the repository

### Content Validation
1. **Required sections**: Must contain "## Tool Categories" section
2. **Tool statistics**: Must contain "## Tool Statistics" with total count
3. **Format compliance**: All tool entries must follow the exact markdown format
4. **Description presence**: Every tool must have a non-empty description

## Integration Requirements

### Frontend Responsibilities
1. **README.md fetching** from GitHub repository
2. **Content parsing** using the defined regular expressions
3. **URL construction** for individual tool installation
4. **Validation** against the defined rules
5. **Error handling** for malformed entries

### Installation Process
1. **Tool selection** from parsed marketplace data
2. **URL resolution** to GitHub raw content
3. **Content download** and local installation
4. **Dependency resolution** (requirements.txt, shared utilities)
5. **Autodiscovery verification** via test execution

## Error Handling

### Parsing Errors
- **Malformed headers**: Skip and log invalid category/subcategory entries
- **Invalid tool entries**: Skip tools that don't match the required pattern
- **Count mismatches**: Log warnings but continue processing
- **Missing descriptions**: Treat as validation warnings

### Integration Errors
- **Network failures**: Retry with exponential backoff
- **Invalid URLs**: Skip tools with malformed paths
- **Installation failures**: Provide user feedback and rollback options
- **Validation failures**: Report tools that fail autodiscovery tests

This data model ensures reliable, deterministic parsing of the README.md for marketplace integration while maintaining flexibility for future tool additions and category expansions.