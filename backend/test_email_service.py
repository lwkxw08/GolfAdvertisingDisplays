#!/usr/bin/env python3
"""
Test script for email notification system
"""

import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from app.database import get_db, EmailTemplate
from app.services.email_service import email_service

def test_email_service():
    """Test email service functionality"""
    print("🧪 Testing Golf CMS Email Service")
    print("=" * 40)
    
    print(f"📧 Email Provider: {email_service.email_provider}")
    print(f"📧 From Email: {email_service.from_email}")
    print(f"📧 SendGrid API Key: {'✅ Configured' if email_service.sendgrid_api_key else '❌ Missing'}")
    
    db = next(get_db())
    
    templates = db.query(EmailTemplate).all()
    print(f"📧 Email Templates: {len(templates)} found")
    
    for template in templates:
        print(f"   - {template.name}: {'✅ Active' if template.is_active else '❌ Inactive'}")
    
    if templates:
        print("\n🧪 Testing email sending (dry run)...")
        test_template = templates[0]
        
        variables = {
            "course_name": "Test Golf Course",
            "owner_name": "Test Owner",
            "login_url": "https://web-app-fpcoy3i7.devinapps.com"
        }
        
        subject = email_service._replace_variables(test_template.subject, variables)
        html_content = email_service._replace_variables(test_template.html_content, variables)
        
        print(f"✅ Template processing successful")
        print(f"   Subject: {subject}")
        print(f"   Content length: {len(html_content)} characters")
    
    print("\n🎉 Email service test completed!")

if __name__ == "__main__":
    test_email_service()
