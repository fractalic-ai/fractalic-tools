#!/usr/bin/env python3
"""
Send emails via HubSpot - supports both template-based and plain email sending.
"""
from __future__ import annotations

import json
import sys
import time
from typing import Any, Dict


def process_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Send email via HubSpot using templates or plain content."""
    try:
        # Import dependencies inside the function to avoid top-level import issues
        from hubspot_hub_helpers import hs_client
        
        contact_id = data.get("contactId")
        template_name = data.get("templateName")
        subject = data.get("subject") 
        content = data.get("content")
        variables = data.get("variables", {})
        
        if not contact_id:
            return {"error": "contactId parameter is required"}
        
        # Either template_name OR (subject + content) is required
        if not template_name and not (subject and content):
            return {"error": "Either templateName OR both subject and content are required"}
        
        cli = hs_client()
        
        # Check email configuration capabilities before proceeding
        try:
            # Try to get account info to check email capabilities
            account_info = cli.settings.users.users_api.get_current()
            
            # Note: This is a basic check - full email capability validation would require
            # checking Marketing Hub subscription, domain verification, etc.
            # For production use, consider adding more comprehensive checks
            
        except Exception as check_err:
            # If we can't check account info, continue but warn user
            pass
        
        try:
            # Get contact details for email address
            contact = cli.crm.contacts.basic_api.get_by_id(contact_id=str(contact_id))
            contact_email = contact.properties.get("email")
            
            if not contact_email:
                return {"error": f"Contact {contact_id} does not have an email address"}
            
            if template_name:
                # Template-based email
                try:
                    # First, discover available templates
                    templates = cli.marketing.transactional.templates.get_all()
                    
                    # Find the template by name
                    template_id = None
                    for template in templates.results:
                        if template.name.lower() == template_name.lower():
                            template_id = template.id
                            break
                    
                    if not template_id:
                        available_templates = [t.name for t in templates.results]
                        return {
                            "error": f"Template '{template_name}' not found",
                            "available_templates": available_templates
                        }
                    
                    # Send template email
                    email_request = {
                        "emailId": template_id,
                        "message": {
                            "to": contact_email,
                            "sendId": f"deal-email-{contact_id}"
                        },
                        "contactProperties": variables
                    }
                    
                    response = cli.marketing.transactional.single_send_api.send_email(email_request)
                    
                    return {
                        "status": "success",
                        "emailType": "template",
                        "templateName": template_name,
                        "templateId": template_id,
                        "contactId": contact_id,
                        "recipientEmail": contact_email,
                        "variables": variables,
                        "response": response
                    }
                    
                except Exception as err:
                    return {"error": f"Template email failed: {str(err)}"}
            
            else:
                # Plain email - Try actual sending first, fallback to activity logging
                
                # ATTEMPT 1: Try transactional email sending (actual delivery)
                actual_send_attempted = False
                actual_send_successful = False
                
                try:
                    if hasattr(cli, 'marketing') and hasattr(cli.marketing, 'transactional'):
                        actual_send_attempted = True
                        
                        # Try to send via transactional email API
                        email_send_request = {
                            "emailId": None,  # We'll use custom content
                            "message": {
                                "to": contact_email,
                                "subject": subject,
                                "htmlBody": f"<html><body>{content}</body></html>",
                                "textBody": content
                            },
                            "contactProperties": {},
                            "customProperties": {}
                        }
                        
                        # This would be the actual sending method
                        if hasattr(cli.marketing.transactional, 'single_send') and hasattr(cli.marketing.transactional.single_send, 'send'):
                            send_result = cli.marketing.transactional.single_send.send(email_send_request)
                            actual_send_successful = True
                            
                            return {
                                "status": "sent",
                                "emailType": "transactional",
                                "delivery": "actual_email_sent",
                                "subject": subject,
                                "contactId": contact_id,
                                "recipientEmail": contact_email,
                                "sendId": getattr(send_result, 'id', 'unknown'),
                                "note": "Email successfully sent to recipient's inbox via HubSpot Transactional API"
                            }
                        
                except Exception as send_err:
                    # Transactional sending failed - will fallback to activity logging
                    pass
                
                # ATTEMPT 2: Fallback to email activity logging (what we know works)
                try:
                    # Generate current timestamp in milliseconds (required by HubSpot)
                    current_timestamp = int(time.time() * 1000)
                    
                    email_data = {
                        "properties": {
                            "hs_email_subject": subject,
                            "hs_email_text": content,
                            "hs_email_html": f"<html><body>{content}</body></html>",
                            "hs_email_direction": "EMAIL",
                            "hs_email_status": "SENT",
                            "hs_timestamp": current_timestamp
                        },
                        "associations": [
                            {
                                "to": {"id": str(contact_id)},
                                "types": [{"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": 198}]
                            }
                        ]
                    }
                    
                    # Create email activity record
                    email_response = cli.crm.objects.emails.basic_api.create(email_data)
                    
                    # Provide clear feedback about what actually happened
                    delivery_status = "activity_logged"
                    note = "Email activity logged in HubSpot contact timeline. "
                    
                    if actual_send_attempted:
                        note += "Attempted actual email sending but failed - likely due to missing permissions or domain verification. "
                    
                    note += "For actual email delivery, ensure: (1) Marketing Hub subscription, (2) Verified sending domain, (3) Proper email permissions."
                    
                    return {
                        "status": "logged",
                        "emailType": "activity",
                        "delivery": delivery_status,
                        "subject": subject,
                        "contactId": contact_id,
                        "recipientEmail": contact_email,
                        "emailId": email_response.id,
                        "actualSendAttempted": actual_send_attempted,
                        "actualSendSuccessful": actual_send_successful,
                        "note": note
                    }
                    
                except Exception as err:
                    return {"error": f"Both email sending and activity logging failed: {str(err)}"}
            
        except Exception as err:
            return {"error": f"Contact lookup failed: {str(err)}"}
    
    except Exception as e:
        return {"error": f"Email operation failed: {str(e)}"}


def main() -> None:
    # Test mode for autodiscovery (REQUIRED)
    if len(sys.argv) == 2 and sys.argv[1] == '{"__test__": true}':
        print(json.dumps({"success": True, "_simple": True}))
        return
    
    # Optional: Rich schema for better LLM integration
    if len(sys.argv) == 2 and sys.argv[1] == "--fractalic-dump-schema":
        schema = {
            "description": "Send emails via HubSpot using templates or plain content. Supports both automated template emails (Commercial offer, Need STL/STEP file) and custom plain emails.",
            "parameters": {
                "type": "object",
                "properties": {
                    "contactId": {
                        "type": ["integer", "string"],
                        "description": "ID of the contact to send email to (required)"
                    },
                    "templateName": {
                        "type": "string",
                        "description": "Name of HubSpot email template (e.g., 'Commercial offer', 'Need STL/STEP file') - use this OR subject+content"
                    },
                    "subject": {
                        "type": "string",
                        "description": "Email subject (required when not using templateName)"
                    },
                    "content": {
                        "type": "string", 
                        "description": "Email content/body (required when not using templateName)"
                    },
                    "variables": {
                        "type": "object",
                        "description": "Template variables for personalization (e.g., {'quote_amount': '$1,500', 'part_description': 'TIE Fighter figurine'})",
                        "additionalProperties": True
                    }
                },
                "required": ["contactId"],
                "additionalProperties": False
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
        print(json.dumps(result, ensure_ascii=False))
        
    except Exception as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    main()
