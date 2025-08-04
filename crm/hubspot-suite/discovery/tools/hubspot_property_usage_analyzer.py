#!/usr/bin/env python3
"""
HubSpot Property Usage Analyzer

This tool analyzes property usage patterns across HubSpot objects to identify
underutilized fields, data quality issues, and optimization opportunities.
Part of the Fractalic Process Mining Intelligence Suite.
"""

import os
from typing import Dict, Any, List, Tuple, Optional
import json
import sys
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import statistics

def process_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze property usage patterns across HubSpot objects.
    
    Args:
        data: Dictionary containing analysis parameters
    
    Returns:
        Dictionary containing property usage analysis results
    """
    try:
        from hubspot_hub_helpers import hs_client
        from hubspot.crm.properties import ApiException as PropertiesApiException
        from hubspot.crm.contacts import ApiException as ContactsApiException
        from hubspot.crm.deals import ApiException as DealsApiException
        from hubspot.crm.companies import ApiException as CompaniesApiException
        
        # Get the HubSpot client instance
        client = hs_client()
        
        # Extract parameters
        object_types = data.get('object_types', ['contacts', 'deals', 'companies'])
        sample_size = data.get('sample_size', 100)
        include_custom_only = data.get('include_custom_only', False)
        analyze_data_quality = data.get('analyze_data_quality', True)
        include_detailed_analysis = data.get('include_detailed_analysis', False)
        
        print(f"🔍 Analyzing property usage for objects: {', '.join(object_types)}", file=sys.stderr)
        
        # Initialize analysis containers
        property_analysis = {}
        usage_stats = defaultdict(dict)
        data_quality_issues = defaultdict(list)
        optimization_opportunities = []
        
        # Object type mapping
        object_apis = {
            'contacts': {
                'properties_api': client.crm.properties.core_api,
                'basic_api': client.crm.contacts.basic_api,
                'object_type': 'contact'
            },
            'deals': {
                'properties_api': client.crm.properties.core_api,
                'basic_api': client.crm.deals.basic_api,
                'object_type': 'deal'
            },
            'companies': {
                'properties_api': client.crm.properties.core_api,
                'basic_api': client.crm.companies.basic_api,
                'object_type': 'company'
            }
        }
        
        total_objects_analyzed = 0
        
        for obj_type in object_types:
            if obj_type not in object_apis:
                print(f"⚠️ Unsupported object type: {obj_type}", file=sys.stderr)
                continue
                
            print(f"\n📊 Analyzing {obj_type} properties...", file=sys.stderr)
            
            try:
                # Get properties for this object type
                properties_response = object_apis[obj_type]['properties_api'].get_all(
                    object_type=object_apis[obj_type]['object_type']
                )
                
                if not properties_response or not properties_response.results:
                    print(f"⚠️ No properties found for {obj_type}", file=sys.stderr)
                    continue
                
                properties = properties_response.results
                
                # Filter to custom properties if requested
                if include_custom_only:
                    properties = [prop for prop in properties if hasattr(prop, 'hub_spot_defined') and not prop.hub_spot_defined]
                
                print(f"Found {len(properties)} properties for {obj_type}", file=sys.stderr)
                
                # Get sample objects to analyze property usage
                # Limit properties to avoid API limits and use only standard properties for sampling
                sample_properties = [prop.name for prop in properties[:20] if hasattr(prop, 'hub_spot_defined') and prop.hub_spot_defined]
                if not sample_properties:
                    # Fallback to first 10 properties if no standard ones found
                    sample_properties = [prop.name for prop in properties[:10]]
                
                objects_response = object_apis[obj_type]['basic_api'].get_page(
                    limit=min(sample_size, 100),  # Ensure we don't exceed API limits
                    properties=sample_properties,
                    archived=False
                )
                
                objects = objects_response.results if objects_response.results else []
                total_objects_analyzed += len(objects)
                
                print(f"Analyzing {len(objects)} {obj_type} records...", file=sys.stderr)
                
                # Initialize property usage tracking
                property_stats = {}
                for prop in properties:
                    property_stats[prop.name] = {
                        'property_info': {
                            'label': prop.label,
                            'type': prop.type,
                            'field_type': prop.field_type,
                            'description': prop.description,
                            'hub_spot_defined': getattr(prop, 'hub_spot_defined', True),
                            'calculated': getattr(prop, 'calculated', False),
                            'options': []
                        },
                        'usage_metrics': {
                            'total_objects': len(objects),
                            'populated_count': 0,
                            'empty_count': 0,
                            'unique_values': set(),
                            'null_count': 0,
                            'usage_percentage': 0.0
                        },
                        'data_quality': {
                            'has_duplicates': False,
                            'inconsistent_format': False,
                            'potential_issues': []
                        }
                    }
                    
                    # Add options for enumeration fields
                    if hasattr(prop, 'options') and prop.options:
                        property_stats[prop.name]['property_info']['options'] = [
                            {'label': opt.label, 'value': opt.value} for opt in prop.options
                        ]
                
                # Analyze each object's property values
                for obj in objects:
                    if not obj.properties:
                        continue
                        
                    for prop_name, prop_stats in property_stats.items():
                        if prop_name in obj.properties:
                            value = obj.properties[prop_name]
                            
                            if value is None or value == '' or value == 'null':
                                prop_stats['usage_metrics']['null_count'] += 1
                                prop_stats['usage_metrics']['empty_count'] += 1
                            else:
                                prop_stats['usage_metrics']['populated_count'] += 1
                                prop_stats['usage_metrics']['unique_values'].add(str(value))
                                
                                # Data quality checks
                                if analyze_data_quality:
                                    # Check for common data quality issues
                                    str_value = str(value).strip()
                                    
                                    # Check for placeholder values
                                    placeholder_patterns = ['test', 'temp', 'tbd', 'n/a', 'none', 'unknown']
                                    if str_value.lower() in placeholder_patterns:
                                        prop_stats['data_quality']['potential_issues'].append(
                                            f"Placeholder value detected: {str_value}"
                                        )
                                    
                                    # Check email format for email fields
                                    if 'email' in prop_name.lower() and '@' not in str_value:
                                        prop_stats['data_quality']['potential_issues'].append(
                                            "Invalid email format"
                                        )
                                    
                                    # Check phone format for phone fields
                                    if 'phone' in prop_name.lower():
                                        # Simple phone validation
                                        digits_only = ''.join(filter(str.isdigit, str_value))
                                        if len(digits_only) < 10:
                                            prop_stats['data_quality']['potential_issues'].append(
                                                "Potentially invalid phone number"
                                            )
                        else:
                            prop_stats['usage_metrics']['empty_count'] += 1
                
                # Calculate final statistics
                for prop_name, prop_stats in property_stats.items():
                    total_objects = prop_stats['usage_metrics']['total_objects']
                    populated_count = prop_stats['usage_metrics']['populated_count']
                    
                    if total_objects > 0:
                        prop_stats['usage_metrics']['usage_percentage'] = (populated_count / total_objects) * 100
                    
                    # Convert set to count for JSON serialization
                    prop_stats['usage_metrics']['unique_value_count'] = len(prop_stats['usage_metrics']['unique_values'])
                    del prop_stats['usage_metrics']['unique_values']  # Remove set for JSON compatibility
                    
                    # Check for duplicates (simplified)
                    if prop_stats['usage_metrics']['unique_value_count'] < populated_count:
                        prop_stats['data_quality']['has_duplicates'] = True
                    
                    # Flag potential data quality issues
                    if len(prop_stats['data_quality']['potential_issues']) > 0:
                        data_quality_issues[obj_type].append({
                            'property': prop_name,
                            'issues': prop_stats['data_quality']['potential_issues'],
                            'affected_records': len(prop_stats['data_quality']['potential_issues'])
                        })
                
                property_analysis[obj_type] = property_stats
                
            except Exception as e:
                print(f"⚠️ Error analyzing {obj_type}: {str(e)}", file=sys.stderr)
                property_analysis[obj_type] = {'error': str(e)}
                continue
        
        # Generate insights and optimization opportunities
        insights = []
        recommendations = []
        
        # Analyze usage patterns across all object types
        underutilized_properties = []
        highly_utilized_properties = []
        custom_property_usage = []
        
        for obj_type, properties in property_analysis.items():
            if 'error' in properties:
                continue
                
            for prop_name, prop_stats in properties.items():
                usage_pct = prop_stats['usage_metrics']['usage_percentage']
                is_custom = not prop_stats['property_info']['hub_spot_defined']
                
                prop_summary = {
                    'object_type': obj_type,
                    'property': prop_name,
                    'label': prop_stats['property_info']['label'],
                    'usage_percentage': usage_pct,
                    'is_custom': is_custom,
                    'type': prop_stats['property_info']['type']
                }
                
                if usage_pct < 10:  # Underutilized threshold
                    underutilized_properties.append(prop_summary)
                elif usage_pct > 80:  # Highly utilized threshold
                    highly_utilized_properties.append(prop_summary)
                
                if is_custom:
                    custom_property_usage.append(prop_summary)
        
        # Sort by usage percentage
        underutilized_properties.sort(key=lambda x: x['usage_percentage'])
        highly_utilized_properties.sort(key=lambda x: x['usage_percentage'], reverse=True)
        custom_property_usage.sort(key=lambda x: x['usage_percentage'], reverse=True)
        
        # Generate insights
        insights.append(f"Analyzed {total_objects_analyzed} objects across {len(object_types)} object types")
        
        if underutilized_properties:
            insights.append(f"Found {len(underutilized_properties)} underutilized properties (<10% usage)")
            
        if highly_utilized_properties:
            insights.append(f"Identified {len(highly_utilized_properties)} highly utilized properties (>80% usage)")
        
        if custom_property_usage:
            avg_custom_usage = statistics.mean([p['usage_percentage'] for p in custom_property_usage])
            insights.append(f"Custom properties average usage: {avg_custom_usage:.1f}%")
        
        # Generate recommendations
        if underutilized_properties:
            recommendations.extend([
                "Review underutilized properties for potential removal or consolidation",
                "Train users on the purpose and importance of low-usage properties",
                "Consider making underutilized properties required if they're business-critical"
            ])
        
        if len(data_quality_issues) > 0:
            recommendations.extend([
                "Implement data validation rules for properties with quality issues",
                "Set up automated data cleansing workflows",
                "Create data entry guidelines and training for users"
            ])
        
        recommendations.extend([
            "Establish property governance policies for new custom properties",
            "Regular property usage audits to maintain data hygiene",
            "Consider property field dependencies and conditional logic",
            "Implement property usage analytics dashboards"
        ])
        
        result = {
            "status": "success",
            "analysis_type": "property_usage_analysis",
            "timestamp": datetime.now().isoformat(),
            "parameters": {
                "object_types": object_types,
                "sample_size": sample_size,
                "include_custom_only": include_custom_only,
                "analyze_data_quality": analyze_data_quality
            },
            "summary_metrics": {
                "total_objects_analyzed": total_objects_analyzed,
                "underutilized_properties": len(underutilized_properties),
                "highly_utilized_properties": len(highly_utilized_properties),
                "custom_properties_analyzed": len(custom_property_usage),
                "data_quality_issues_found": sum(len(issues) for issues in data_quality_issues.values())
            },
            "optimization_opportunities": {
                "underutilized_properties": underutilized_properties[:10],  # Top 10
                "highly_utilized_properties": highly_utilized_properties[:10],  # Top 10
                "custom_property_usage": custom_property_usage
            },
            "data_quality_issues": dict(data_quality_issues),
            "insights": insights,
            "recommendations": recommendations
        }

        # Add detailed analysis only if specifically requested
        if include_detailed_analysis:
            result["detailed_analysis"] = property_analysis
            
        return result
    
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "analysis_type": "property_usage_analysis",
            "timestamp": datetime.now().isoformat()
        }


def main() -> None:
    # Test mode for autodiscovery (REQUIRED)
    if len(sys.argv) == 2 and sys.argv[1] == '{"__test__": true}':
        print(json.dumps({"success": True, "_simple": True}))
        return
    
    # Optional: Rich schema for better LLM integration
    if len(sys.argv) == 2 and sys.argv[1] == "--fractalic-dump-schema":
        schema = {
            "description": "Get high-level property usage summary across HubSpot objects to identify optimization opportunities. Returns concise insights and recommendations, not full property details unless specifically requested.",
            "parameters": {
                "type": "object",
                "properties": {
                    "object_types": {
                        "type": "array",
                        "items": {"type": "string", "enum": ["contacts", "deals", "companies", "tickets"]},
                        "description": "List of HubSpot object types to analyze",
                        "default": ["contacts", "deals", "companies"]
                    },
                    "sample_size": {
                        "type": "integer",
                        "minimum": 10,
                        "maximum": 1000,
                        "description": "Number of objects to analyze per type",
                        "default": 100
                    },
                    "include_custom_only": {
                        "type": "boolean",
                        "description": "Whether to analyze only custom properties",
                        "default": False
                    },
                    "analyze_data_quality": {
                        "type": "boolean",
                        "description": "Whether to perform data quality analysis",
                        "default": True
                    },
                    "include_detailed_analysis": {
                        "type": "boolean",
                        "description": "Whether to include detailed property-by-property analysis (warning: creates very large output)",
                        "default": False
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
