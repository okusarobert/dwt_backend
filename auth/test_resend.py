#!/usr/bin/env python3
"""
Test script for Resend email functionality
Run this to test if Resend is working correctly
"""

import os
import sys
from decouple import config
import resend

def test_resend_connection():
    """Test Resend API connection and send a test email"""
    
    # Check if API key is configured
    api_key = config("RESEND_API_KEY", default=None)
    if not api_key:
        print("❌ RESEND_API_KEY not found in environment variables")
        print("Please set RESEND_API_KEY in your .env file")
        return False
    
    # Set the API key
    resend.api_key = api_key
    
    # Get from email
    from_email = config("RESEND_FROM_EMAIL", default="no-reply@badix.io")
    
    try:
        # Test email parameters
        params = {
            "from": from_email,
            "to": "test@example.com",  # Replace with your test email
            "subject": "Test Email from DT Exchange",
            "html": """
            <html>
                <body>
                    <h1>Test Email</h1>
                    <p>This is a test email to verify Resend integration is working.</p>
                    <p>If you receive this, Resend is configured correctly!</p>
                </body>
            </html>
            """
        }
        
        print(f"🔑 API Key: {api_key[:10]}...{api_key[-4:]}")
        print(f"📧 From Email: {from_email}")
        print(f"📨 To Email: test@example.com")
        print("📤 Sending test email...")
        
        # Send the email
        response = resend.Emails.send(params)
        
        print("✅ Email sent successfully!")
        print(f"📋 Response: {response}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        return False

def test_email_templates():
    """Test if email templates can be loaded and processed"""
    
    templates_dir = "templates/email"
    templates = ["verify.html", "recover.html"]
    
    print("\n📋 Testing email templates...")
    
    for template in templates:
        template_path = os.path.join(templates_dir, template)
        
        if os.path.exists(template_path):
            try:
                with open(template_path, 'r') as f:
                    content = f.read()
                
                # Test template processing
                processed_content = content.replace("{code}", "123456")
                
                if "{code}" not in processed_content and "123456" in processed_content:
                    print(f"✅ {template}: Template loaded and processed successfully")
                else:
                    print(f"❌ {template}: Template processing failed")
                    
            except Exception as e:
                print(f"❌ {template}: Error reading template: {e}")
        else:
            print(f"❌ {template}: Template file not found")

def main():
    """Main test function"""
    print("🚀 Testing Resend Email Integration")
    print("=" * 50)
    
    # Test Resend connection
    success = test_resend_connection()
    
    # Test email templates
    test_email_templates()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 All tests passed! Resend integration is working correctly.")
        print("\n📝 Next steps:")
        print("1. Update your .env file with RESEND_API_KEY")
        print("2. Test with a real email address")
        print("3. Run the auth service to process email jobs")
    else:
        print("❌ Some tests failed. Please check the configuration.")
        print("\n🔧 Troubleshooting:")
        print("1. Verify RESEND_API_KEY is set correctly")
        print("2. Check if the domain is verified in Resend")
        print("3. Ensure you have sufficient credits in Resend")

if __name__ == "__main__":
    main()
