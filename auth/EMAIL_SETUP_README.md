# Email Verification Setup with Resend

This document explains how to set up email verification functionality using Resend for the DT Exchange platform.

## 🚀 Features

- **6-digit OTP codes** for email verification
- **Beautiful PayPal-style email templates** with responsive design
- **Resend API integration** for reliable email delivery
- **SMTP fallback** for backup email delivery
- **Automatic code expiration** (10 minutes)
- **Rate limiting** and security features

## 📋 Prerequisites

1. **Resend Account**: Sign up at [resend.com](https://resend.com)
2. **Domain Verification**: Verify your domain in Resend
3. **API Key**: Get your Resend API key from the dashboard

## 🔧 Configuration

### Environment Variables

Add these to your `.env` file:

```bash
# Resend Configuration
RESEND_API_KEY=re_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
RESEND_FROM_EMAIL=no-reply@badix.io

# SMTP Fallback (Optional)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
EMAIL_ADDRESS=your-email@gmail.com
EMAIL_PASSWORD=your-app-password
```

### Dependencies

Install the required packages:

```bash
pip install resend>=0.8.0
```

Or add to your `requirements.txt`:

```
resend>=0.8.0
```

## 📧 Email Templates

### Verification Email (`templates/email/verify.html`)
- Beautiful PayPal-style design
- 6-digit OTP code display
- Security information and disclaimers
- Mobile-responsive layout

### Password Reset Email (`templates/email/recover.html`)
- Professional password reset flow
- Security notices and tips
- Clear call-to-action

## 🔄 How It Works

### 1. User Registration
1. User signs up with email
2. System generates 6-digit OTP
3. OTP stored in database with 10-minute expiration
4. Beautiful email sent via Resend

### 2. Email Verification
1. User receives email with OTP
2. User enters OTP in frontend form
3. Frontend validates OTP with backend
4. Backend marks email as verified

### 3. Password Reset
1. User requests password reset
2. System generates new OTP
3. Email sent with reset instructions
4. User enters OTP to reset password

## 🧪 Testing

### Test Resend Integration

```bash
cd auth
python test_resend.py
```

This will:
- Verify API key configuration
- Test email sending
- Validate email templates
- Provide troubleshooting guidance

### Test Email Templates

The test script also validates that:
- Templates can be loaded
- Code replacement works correctly
- HTML is properly formatted

## 📊 Database Schema

### EmailVerify Table

```sql
CREATE TABLE email_verifications (
    id SERIAL PRIMARY KEY,
    code VARCHAR(16) NOT NULL,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Status Values
- `pending`: Code generated, not yet used
- `used`: Code successfully used for verification
- `expired`: Code expired (10 minutes)

## 🚨 Security Features

### Code Generation
- 6-digit random numbers
- No sequential patterns
- Cryptographically secure

### Expiration
- 10-minute automatic expiration
- Prevents code reuse
- Automatic cleanup of expired codes

### Rate Limiting
- One active code per user
- Prevents spam and abuse
- Automatic code replacement

## 🔍 Troubleshooting

### Common Issues

#### 1. "RESEND_API_KEY not found"
- Check your `.env` file
- Ensure the variable name is correct
- Restart your application after changes

#### 2. "Domain not verified"
- Verify your domain in Resend dashboard
- Check DNS records
- Wait for verification to complete

#### 3. "Insufficient credits"
- Check your Resend account balance
- Upgrade your plan if needed
- Monitor usage in dashboard

#### 4. "Template not found"
- Verify template files exist
- Check file permissions
- Ensure correct file paths

### Debug Mode

Enable detailed logging in your application:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 📈 Monitoring

### Email Delivery Metrics
- Track delivery rates in Resend dashboard
- Monitor bounce rates and spam reports
- Set up webhooks for real-time updates

### Application Logs
- Monitor OTP generation and verification
- Track email sending success/failure
- Watch for rate limiting events

## 🔄 Fallback Strategy

### Primary: Resend API
- Fast and reliable delivery
- Professional email infrastructure
- Built-in analytics and monitoring

### Secondary: SMTP
- Backup delivery method
- Works when Resend is unavailable
- Configurable with any SMTP provider

## 🎨 Customization

### Branding
- Update logo and colors in templates
- Modify company name and contact info
- Customize email subjects and content

### Styling
- Modify CSS in email templates
- Adjust layout and spacing
- Add custom fonts and images

### Content
- Update verification messages
- Modify security notices
- Add company-specific information

## 📚 API Reference

### Resend API
- [Official Documentation](https://resend.com/docs)
- [Python SDK](https://github.com/resendlabs/resend-python)
- [Webhook Events](https://resend.com/docs/webhooks)

### Email Templates
- HTML5 compliant
- CSS3 support
- Mobile-responsive design
- Dark mode support

## 🤝 Support

### Resend Support
- [Help Center](https://resend.com/help)
- [Community Forum](https://community.resend.com)
- [Email Support](mailto:support@resend.com)

### DT Exchange Support
- [Documentation](https://docs.dtexchange.com)
- [GitHub Issues](https://github.com/dtexchange/issues)
- [Email Support](mailto:support@badix.io)

## 📝 Changelog

### v1.0.0 (Current)
- Initial Resend integration
- PayPal-style email templates
- 6-digit OTP system
- SMTP fallback support
- Comprehensive testing suite

### Future Enhancements
- Email analytics dashboard
- A/B testing for templates
- Advanced rate limiting
- Multi-language support
- Email preference management

---

**Note**: This system is designed for production use with proper security measures. Always test thoroughly in development before deploying to production.
