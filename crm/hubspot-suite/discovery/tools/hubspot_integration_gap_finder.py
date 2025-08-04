#!/usr/bin/env python3
"""
HubSpot Integration Gap Finder

This tool identifies potential integration gaps, data silos, and missing connections
in HubSpot CRM by analyzing data flow patterns, orphaned records, and relationship integrity.
Part of the Fractalic Process Mining Intelligence Suite.
"""

from typing import Dict, Any, List, Tuple, Optional
import json
import sys
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import statistics

def process_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Identify integration gaps and data silos in HubSpot CRM.
    
    Args:
        data: Dictionary containing analysis parameters
    
    Returns:
        Dictionary containing integration gap analysis results
    """
    try:
        from hubspot_hub_helpers import hs_client
        from hubspot.crm.contacts import ApiException as ContactsApiException
        from hubspot.crm.deals import ApiException as DealsApiException
        from hubspot.crm.companies import ApiException as CompaniesApiException
        from hubspot.crm.associations import BatchApi as AssociationsApi
        
        # Get the HubSpot client instance
        client = hs_client()
        
        # Extract parameters
        scope = data.get('scope', 'comprehensive')
        include_recommendations = data.get('include_recommendations', True)
        sample_size = data.get('sample_size', 100)
        check_associations = data.get('check_associations', True)
        analyze_data_sources = data.get('analyze_data_sources', True)
        check_activity_gaps = data.get('check_activity_gaps', True)
        days_back = data.get('days_back', 90)
        
        print(f"🔍 Analyzing integration gaps and data silos...", file=sys.stderr)
        
        # Initialize analysis containers
        gap_analysis = {
            'orphaned_records': defaultdict(list),
            'missing_associations': defaultdict(int),
            'data_source_analysis': defaultdict(dict),
            'activity_gaps': defaultdict(list),
            'relationship_issues': [],
            'integration_opportunities': []
        }
        
        metrics = {
            'total_records_analyzed': 0,
            'orphaned_contacts': 0,
            'orphaned_deals': 0,
            'orphaned_companies': 0,
            'missing_associations_count': 0,
            'data_sources_identified': 0,
            'activity_gaps_found': 0
        }
        
        cutoff_date = datetime.now() - timedelta(days=days_back)
        cutoff_timestamp = int(cutoff_date.timestamp() * 1000)
        
        # 1. Analyze orphaned contacts (contacts without company associations)
        print("👤 Analyzing orphaned contacts...")
        try:
            contacts_response = client.crm.contacts.basic_api.get_page(
                limit=sample_size,
                properties=['firstname', 'lastname', 'email', 'company', 'associatedcompanyid', 
                           'hs_analytics_source', 'createdate', 'lastmodifieddate'],
                archived=False
            )
            
            contacts = contacts_response.results if contacts_response.results else []
            metrics['total_records_analyzed'] += len(contacts)
            
            for contact in contacts:
                contact_props = contact.properties
                
                # Check for orphaned contacts (no company association)
                company_id = contact_props.get('associatedcompanyid')
                company_name = contact_props.get('company')
                
                if not company_id and not company_name:
                    gap_analysis['orphaned_records']['contacts'].append({
                        'id': contact.id,
                        'name': f"{contact_props.get('firstname', '')} {contact_props.get('lastname', '')}".strip(),
                        'email': contact_props.get('email'),
                        'created_date': contact_props.get('createdate'),
                        'issue': 'No company association'
                    })
                    metrics['orphaned_contacts'] += 1
                
                # Analyze data sources
                if analyze_data_sources:
                    source = contact_props.get('hs_analytics_source', 'unknown')
                    if source not in gap_analysis['data_source_analysis']:
                        gap_analysis['data_source_analysis'][source] = {
                            'contact_count': 0,
                            'has_company_association': 0,
                            'missing_email': 0
                        }
                    
                    gap_analysis['data_source_analysis'][source]['contact_count'] += 1
                    
                    if company_id or company_name:
                        gap_analysis['data_source_analysis'][source]['has_company_association'] += 1
                    
                    if not contact_props.get('email'):
                        gap_analysis['data_source_analysis'][source]['missing_email'] += 1
            
        except ContactsApiException as e:
            print(f"⚠️ Error analyzing contacts: {e}")
        
        # 2. Analyze orphaned deals (deals without contact or company associations)
        print("💼 Analyzing orphaned deals...")
        try:
            deals_response = client.crm.deals.basic_api.get_page(
                limit=sample_size,
                properties=['dealname', 'dealstage', 'amount', 'pipeline', 'createdate', 
                           'closedate', 'hubspot_owner_id'],
                archived=False
            )
            
            deals = deals_response.results if deals_response.results else []
            metrics['total_records_analyzed'] += len(deals)
            
            for deal in deals:
                deal_props = deal.properties
                
                # Check for deals without proper associations (simplified check)
                if not deal_props.get('hubspot_owner_id'):
                    gap_analysis['orphaned_records']['deals'].append({
                        'id': deal.id,
                        'name': deal_props.get('dealname', 'Unnamed Deal'),
                        'stage': deal_props.get('dealstage'),
                        'amount': deal_props.get('amount'),
                        'created_date': deal_props.get('createdate'),
                        'issue': 'No owner assigned'
                    })
                    metrics['orphaned_deals'] += 1
            
        except DealsApiException as e:
            print(f"⚠️ Error analyzing deals: {e}")
        
        # 3. Analyze companies for missing contact associations
        print("🏢 Analyzing company associations...")
        try:
            companies_response = client.crm.companies.basic_api.get_page(
                limit=sample_size,
                properties=['name', 'domain', 'city', 'state', 'country', 'industry', 
                           'createdate', 'num_associated_contacts'],
                archived=False
            )
            
            companies = companies_response.results if companies_response.results else []
            metrics['total_records_analyzed'] += len(companies)
            
            for company in companies:
                company_props = company.properties
                
                # Check for companies without contacts
                num_contacts = company_props.get('num_associated_contacts', '0')
                try:
                    contact_count = int(num_contacts)
                    if contact_count == 0:
                        gap_analysis['orphaned_records']['companies'].append({
                            'id': company.id,
                            'name': company_props.get('name', 'Unnamed Company'),
                            'domain': company_props.get('domain'),
                            'industry': company_props.get('industry'),
                            'created_date': company_props.get('createdate'),
                            'issue': 'No associated contacts'
                        })
                        metrics['orphaned_companies'] += 1
                except (ValueError, TypeError):
                    pass
            
        except CompaniesApiException as e:
            print(f"⚠️ Error analyzing companies: {e}")
        
        # 4. Check for activity gaps
        if check_activity_gaps:
            print("📅 Analyzing activity gaps...")
            try:
                # Get recent activities - simplified check for contacts without recent activity
                recent_threshold = datetime.now() - timedelta(days=30)
                recent_timestamp = int(recent_threshold.timestamp() * 1000)
                
                # Check contacts for recent activity (using last modified date as proxy)
                for contact in contacts[:20]:  # Sample subset
                    contact_props = contact.properties
                    last_modified = contact_props.get('lastmodifieddate')
                    
                    if last_modified:
                        try:
                            last_modified_date = datetime.fromtimestamp(int(last_modified) / 1000)
                            if last_modified_date < recent_threshold:
                                gap_analysis['activity_gaps']['stale_contacts'].append({
                                    'id': contact.id,
                                    'name': f"{contact_props.get('firstname', '')} {contact_props.get('lastname', '')}".strip(),
                                    'email': contact_props.get('email'),
                                    'last_activity': last_modified_date.isoformat(),
                                    'days_inactive': (datetime.now() - last_modified_date).days
                                })
                                metrics['activity_gaps_found'] += 1
                        except (ValueError, TypeError):
                            pass
                
            except Exception as e:
                print(f"⚠️ Error analyzing activity gaps: {e}")
        
        # 5. Identify relationship integrity issues
        print("🔗 Analyzing relationship integrity...")
        
        # Check for data consistency issues
        relationship_issues = []
        
        # Example: Contacts with company name but no company ID
        for contact in contacts[:10]:  # Sample subset
            contact_props = contact.properties
            company_name = contact_props.get('company')
            company_id = contact_props.get('associatedcompanyid')
            
            if company_name and not company_id:
                relationship_issues.append({
                    'type': 'missing_company_association',
                    'contact_id': contact.id,
                    'issue': f"Contact has company name '{company_name}' but no company ID association",
                    'severity': 'medium'
                })
        
        gap_analysis['relationship_issues'] = relationship_issues
        
        # 6. Generate integration opportunities
        integration_opportunities = []
        
        # Suggest opportunities based on findings
        if metrics['orphaned_contacts'] > 0:
            integration_opportunities.append({
                'type': 'contact_company_matching',
                'description': f"Match {metrics['orphaned_contacts']} orphaned contacts to companies",
                'impact': 'high',
                'effort': 'medium'
            })
        
        if metrics['orphaned_companies'] > 0:
            integration_opportunities.append({
                'type': 'company_contact_discovery',
                'description': f"Find contacts for {metrics['orphaned_companies']} companies without contacts",
                'impact': 'high',
                'effort': 'medium'
            })
        
        if metrics['activity_gaps_found'] > 0:
            integration_opportunities.append({
                'type': 'activity_automation',
                'description': f"Set up automated nurturing for {metrics['activity_gaps_found']} inactive contacts",
                'impact': 'medium',
                'effort': 'low'
            })
        
        # Data source optimization opportunities
        if gap_analysis['data_source_analysis']:
            for source, stats in gap_analysis['data_source_analysis'].items():
                if stats['contact_count'] > 10:  # Significant source
                    association_rate = (stats['has_company_association'] / stats['contact_count']) * 100
                    if association_rate < 50:  # Low association rate
                        integration_opportunities.append({
                            'type': 'source_optimization',
                            'description': f"Improve data quality for {source} source (only {association_rate:.1f}% have company associations)",
                            'impact': 'medium',
                            'effort': 'low'
                        })
        
        gap_analysis['integration_opportunities'] = integration_opportunities
        metrics['data_sources_identified'] = len(gap_analysis['data_source_analysis'])
        
        # Generate insights and recommendations
        insights = []
        recommendations = []
        
        insights.append(f"Analyzed {metrics['total_records_analyzed']} records across contacts, deals, and companies")
        
        total_orphaned = metrics['orphaned_contacts'] + metrics['orphaned_deals'] + metrics['orphaned_companies']
        if total_orphaned > 0:
            insights.append(f"Found {total_orphaned} orphaned records requiring attention")
        
        if gap_analysis['data_source_analysis']:
            insights.append(f"Identified {len(gap_analysis['data_source_analysis'])} different data sources")
        
        if relationship_issues:
            insights.append(f"Detected {len(relationship_issues)} relationship integrity issues")
        
        # Generate specific recommendations
        recommendations.extend([
            "Implement automated company matching for orphaned contacts",
            "Set up data validation rules to prevent orphaned records",
            "Create workflows to maintain data association integrity",
            "Establish data governance policies for new integrations"
        ])
        
        if metrics['activity_gaps_found'] > 0:
            recommendations.append("Implement automated nurturing sequences for inactive contacts")
        
        if gap_analysis['data_source_analysis']:
            recommendations.append("Standardize data quality requirements across all sources")
        
        recommendations.extend([
            "Regular data integrity audits and cleanup processes",
            "Integration testing protocols for new data sources",
            "Automated monitoring for data association completeness"
        ])
        
        return {
            "success": True,
            "analysis_type": "integration_gap_analysis",
            "timestamp": datetime.now().isoformat(),
            "parameters": {
                "sample_size": sample_size,
                "check_associations": check_associations,
                "analyze_data_sources": analyze_data_sources,
                "check_activity_gaps": check_activity_gaps,
                "days_back": days_back
            },
            "metrics": metrics,
            "gap_analysis": {
                "orphaned_records": dict(gap_analysis['orphaned_records']),
                "data_source_analysis": dict(gap_analysis['data_source_analysis']),
                "activity_gaps": dict(gap_analysis['activity_gaps']),
                "relationship_issues": gap_analysis['relationship_issues'],
                "integration_opportunities": gap_analysis['integration_opportunities']
            },
            "insights": insights,
            "recommendations": recommendations,
            "summary": {
                "total_gaps_identified": total_orphaned + len(relationship_issues),
                "high_priority_issues": len([opp for opp in integration_opportunities if opp.get('impact') == 'high']),
                "data_sources_analyzed": len(gap_analysis['data_source_analysis']),
                "improvement_opportunities": len(integration_opportunities)
            }
        }
    
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "analysis_type": "integration_gap_analysis",
            "timestamp": datetime.now().isoformat()
        }

def get_schema() -> Dict[str, Any]:
    """Return the JSON schema for this tool's input parameters."""
    return {
        "type": "object",
        "properties": {
            "sample_size": {
                "type": "integer",
                "description": "Number of records to sample for analysis",
                "default": 100,
                "minimum": 10,
                "maximum": 1000
            },
            "check_associations": {
                "type": "boolean",
                "description": "Whether to check for missing associations between objects",
                "default": True
            },
            "analyze_data_sources": {
                "type": "boolean", 
                "description": "Whether to analyze data source patterns",
                "default": True
            },
            "check_activity_gaps": {
                "type": "boolean",
                "description": "Whether to check for activity gaps",
                "default": True
            },
            "days_back": {
                "type": "integer",
                "description": "Number of days back to analyze",
                "default": 90,
                "minimum": 1,
                "maximum": 365
            },
            "hubspot_token": {
                "type": "string",
                "description": "HubSpot API token (required for live analysis)"
            }
        },
        "required": []
    }


def main():
    """Main function to handle CLI arguments and process data"""
    import sys
    
    # Test mode for autodiscovery (REQUIRED)
    if len(sys.argv) == 2 and sys.argv[1] == '{"__test__": true}':
        print(json.dumps({"success": True, "_simple": True}))
        return
    
    # Handle command line arguments for schema export
    if len(sys.argv) == 2 and sys.argv[1] == "--fractalic-dump-schema":
        print(json.dumps(get_schema(), ensure_ascii=False))
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
