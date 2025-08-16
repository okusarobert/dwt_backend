"""
Trade Notification Service
Sends email notifications for successful trades
"""

import logging
import json
from datetime import datetime
from typing import Dict, Any
from decouple import config
import resend
from db.connection import get_session
from db.models import User
from db.wallet import Trade, TradeType, TradeStatus

logger = logging.getLogger(__name__)

class TradeNotificationService:
    def __init__(self):
        self.resend_api_key = config("RESEND_API_KEY", default=None)
        self.from_email = config("RESEND_FROM_EMAIL", default="no-reply@badix.io")
        
        if self.resend_api_key:
            resend.api_key = self.resend_api_key
            logger.info("Resend client initialized for trade notifications")
        else:
            logger.warning("RESEND_API_KEY not configured - email notifications disabled")
    
    def send_trade_completion_email(self, trade: Trade) -> bool:
        """Send email notification for completed trade"""
        try:
            session = get_session()
            user = session.query(User).filter(User.id == trade.user_id).first()
            
            if not user:
                logger.error(f"User not found for trade {trade.id}")
                return False
            
            # Generate email content based on trade type
            if trade.trade_type == TradeType.BUY:
                subject, html_content = self._generate_buy_completion_email(trade, user)
            else:
                subject, html_content = self._generate_sell_completion_email(trade, user)
            
            # Send email
            success = self._send_email(user.email, subject, html_content, user.first_name)
            
            if success:
                logger.info(f"Trade completion email sent to user {user.id} for trade {trade.id}")
            else:
                logger.error(f"Failed to send trade completion email for trade {trade.id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending trade completion email: {e}")
            return False
        finally:
            session.close()
    
    def send_trade_failed_email(self, trade: Trade, error_message: str) -> bool:
        """Send email notification for failed trade"""
        try:
            session = get_session()
            user = session.query(User).filter(User.id == trade.user_id).first()
            
            if not user:
                logger.error(f"User not found for trade {trade.id}")
                return False
            
            subject, html_content = self._generate_trade_failed_email(trade, user, error_message)
            
            # Send email
            success = self._send_email(user.email, subject, html_content, user.first_name)
            
            if success:
                logger.info(f"Trade failed email sent to user {user.id} for trade {trade.id}")
            else:
                logger.error(f"Failed to send trade failed email for trade {trade.id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending trade failed email: {e}")
            return False
        finally:
            session.close()
    
    def _generate_buy_completion_email(self, trade: Trade, user: User) -> tuple[str, str]:
        """Generate buy completion email content"""
        subject = f"✅ Trade Completed - {trade.crypto_amount:.8f} {trade.crypto_currency} Purchased"
        
        html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Trade Completed - DT Exchange</title>
            <style>
                body {{
                    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    background-color: #f7f9fa;
                    color: #2c2e2f;
                    line-height: 1.6;
                    margin: 0;
                    padding: 0;
                }}
                .container {{
                    max-width: 600px;
                    margin: 0 auto;
                    background-color: #ffffff;
                    border-radius: 16px;
                    overflow: hidden;
                    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
                }}
                .header {{
                    background: linear-gradient(135deg, #0070ba 0%, #1546a0 100%);
                    padding: 40px 30px;
                    text-align: center;
                    color: white;
                }}
                .logo {{
                    font-size: 28px;
                    font-weight: 700;
                    margin-bottom: 10px;
                    letter-spacing: -0.5px;
                }}
                .subtitle {{
                    font-size: 16px;
                    opacity: 0.9;
                    font-weight: 400;
                }}
                .content {{
                    padding: 40px 30px;
                    text-align: center;
                }}
                .success-icon {{
                    width: 80px;
                    height: 80px;
                    background: linear-gradient(135deg, #10b981 0%, #059669 100%);
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    margin: 0 auto 24px;
                }}
                .title {{
                    font-size: 24px;
                    font-weight: 600;
                    color: #2c2e2f;
                    margin-bottom: 16px;
                    letter-spacing: -0.3px;
                }}
                .description {{
                    font-size: 16px;
                    color: #6b7c93;
                    margin-bottom: 32px;
                    line-height: 1.6;
                }}
                .trade-summary {{
                    background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
                    border: 2px solid #e2e8f0;
                    border-radius: 12px;
                    padding: 24px;
                    margin: 32px 0;
                    text-align: left;
                }}
                .trade-row {{
                    display: flex;
                    justify-content: space-between;
                    margin-bottom: 12px;
                    padding-bottom: 8px;
                    border-bottom: 1px solid #e2e8f0;
                }}
                .trade-row:last-child {{
                    border-bottom: none;
                    margin-bottom: 0;
                }}
                .trade-label {{
                    color: #6b7c93;
                    font-weight: 500;
                }}
                .trade-value {{
                    color: #2c2e2f;
                    font-weight: 600;
                }}
                .crypto-amount {{
                    color: #0070ba;
                    font-size: 18px;
                    font-weight: 700;
                }}
                .footer {{
                    background-color: #f8fafc;
                    padding: 24px 30px;
                    text-align: center;
                    border-top: 1px solid #e2e8f0;
                }}
                .footer-text {{
                    color: #94a3b8;
                    font-size: 12px;
                    line-height: 1.5;
                }}
                .support-link {{
                    color: #0070ba;
                    text-decoration: none;
                    font-weight: 500;
                }}
                .support-link:hover {{
                    text-decoration: underline;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="logo">DT Exchange</div>
                    <div class="subtitle">Secure Crypto Trading Platform</div>
                </div>
                
                <div class="content">
                    <div class="success-icon">
                        <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M20 6L9 17l-5-5"/>
                        </svg>
                    </div>
                    
                    <h1 class="title">Trade Completed Successfully!</h1>
                    <p class="description">
                        Your cryptocurrency purchase has been completed. The {trade.crypto_currency} has been added to your wallet.
                    </p>
                    
                    <div class="trade-summary">
                        <div class="trade-row">
                            <span class="trade-label">Trade ID:</span>
                            <span class="trade-value">#{trade.id}</span>
                        </div>
                        <div class="trade-row">
                            <span class="trade-label">Cryptocurrency:</span>
                            <span class="trade-value">{trade.crypto_currency}</span>
                        </div>
                        <div class="trade-row">
                            <span class="trade-label">Amount Purchased:</span>
                            <span class="trade-value crypto-amount">{trade.crypto_amount:.8f} {trade.crypto_currency}</span>
                        </div>
                        <div class="trade-row">
                            <span class="trade-label">Amount Paid:</span>
                            <span class="trade-value">{trade.fiat_currency} {trade.fiat_amount:,.2f}</span>
                        </div>
                        <div class="trade-row">
                            <span class="trade-label">Exchange Rate:</span>
                            <span class="trade-value">{trade.fiat_currency} {trade.exchange_rate:,.2f}</span>
                        </div>
                        <div class="trade-row">
                            <span class="trade-label">Fee:</span>
                            <span class="trade-value">{trade.fiat_currency} {trade.fee_amount:,.2f}</span>
                        </div>
                        <div class="trade-row">
                            <span class="trade-label">Payment Method:</span>
                            <span class="trade-value">{trade.payment_method.replace('_', ' ').title()}</span>
                        </div>
                        <div class="trade-row">
                            <span class="trade-label">Completed At:</span>
                            <span class="trade-value">{trade.completed_at.strftime('%B %d, %Y at %I:%M %p') if trade.completed_at else 'N/A'}</span>
                        </div>
                    </div>
                    
                    <p style="color: #6b7c93; font-size: 14px; margin-top: 24px;">
                        Your {trade.crypto_currency} is now available in your DT Exchange wallet. 
                        You can view your balance and transaction history in your dashboard.
                    </p>
                </div>
                
                <div class="footer">
                    <p class="footer-text">
                        Thank you for trading with DT Exchange!<br>
                        Need help? Contact our support team at 
                        <a href="mailto:support@badix.io" class="support-link">support@badix.io</a>
                    </p>
                    <p class="footer-text" style="margin-top: 16px;">
                        © 2024 DT Exchange. All rights reserved.
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return subject, html_content
    
    def _generate_sell_completion_email(self, trade: Trade, user: User) -> tuple[str, str]:
        """Generate sell completion email content"""
        subject = f"✅ Trade Completed - {trade.crypto_amount:.8f} {trade.crypto_currency} Sold"
        
        html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Trade Completed - DT Exchange</title>
            <style>
                body {{
                    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    background-color: #f7f9fa;
                    color: #2c2e2f;
                    line-height: 1.6;
                    margin: 0;
                    padding: 0;
                }}
                .container {{
                    max-width: 600px;
                    margin: 0 auto;
                    background-color: #ffffff;
                    border-radius: 16px;
                    overflow: hidden;
                    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
                }}
                .header {{
                    background: linear-gradient(135deg, #0070ba 0%, #1546a0 100%);
                    padding: 40px 30px;
                    text-align: center;
                    color: white;
                }}
                .logo {{
                    font-size: 28px;
                    font-weight: 700;
                    margin-bottom: 10px;
                    letter-spacing: -0.5px;
                }}
                .subtitle {{
                    font-size: 16px;
                    opacity: 0.9;
                    font-weight: 400;
                }}
                .content {{
                    padding: 40px 30px;
                    text-align: center;
                }}
                .success-icon {{
                    width: 80px;
                    height: 80px;
                    background: linear-gradient(135deg, #10b981 0%, #059669 100%);
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    margin: 0 auto 24px;
                }}
                .title {{
                    font-size: 24px;
                    font-weight: 600;
                    color: #2c2e2f;
                    margin-bottom: 16px;
                    letter-spacing: -0.3px;
                }}
                .description {{
                    font-size: 16px;
                    color: #6b7c93;
                    margin-bottom: 32px;
                    line-height: 1.6;
                }}
                .trade-summary {{
                    background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
                    border: 2px solid #e2e8f0;
                    border-radius: 12px;
                    padding: 24px;
                    margin: 32px 0;
                    text-align: left;
                }}
                .trade-row {{
                    display: flex;
                    justify-content: space-between;
                    margin-bottom: 12px;
                    padding-bottom: 8px;
                    border-bottom: 1px solid #e2e8f0;
                }}
                .trade-row:last-child {{
                    border-bottom: none;
                    margin-bottom: 0;
                }}
                .trade-label {{
                    color: #6b7c93;
                    font-weight: 500;
                }}
                .trade-value {{
                    color: #2c2e2f;
                    font-weight: 600;
                }}
                .fiat-amount {{
                    color: #0070ba;
                    font-size: 18px;
                    font-weight: 700;
                }}
                .footer {{
                    background-color: #f8fafc;
                    padding: 24px 30px;
                    text-align: center;
                    border-top: 1px solid #e2e8f0;
                }}
                .footer-text {{
                    color: #94a3b8;
                    font-size: 12px;
                    line-height: 1.5;
                }}
                .support-link {{
                    color: #0070ba;
                    text-decoration: none;
                    font-weight: 500;
                }}
                .support-link:hover {{
                    text-decoration: underline;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="logo">DT Exchange</div>
                    <div class="subtitle">Secure Crypto Trading Platform</div>
                </div>
                
                <div class="content">
                    <div class="success-icon">
                        <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M20 6L9 17l-5-5"/>
                        </svg>
                    </div>
                    
                    <h1 class="title">Trade Completed Successfully!</h1>
                    <p class="description">
                        Your cryptocurrency sale has been completed. The {trade.fiat_currency} has been added to your account.
                    </p>
                    
                    <div class="trade-summary">
                        <div class="trade-row">
                            <span class="trade-label">Trade ID:</span>
                            <span class="trade-value">#{trade.id}</span>
                        </div>
                        <div class="trade-row">
                            <span class="trade-label">Cryptocurrency:</span>
                            <span class="trade-value">{trade.crypto_currency}</span>
                        </div>
                        <div class="trade-row">
                            <span class="trade-label">Amount Sold:</span>
                            <span class="trade-value">{trade.crypto_amount:.8f} {trade.crypto_currency}</span>
                        </div>
                        <div class="trade-row">
                            <span class="trade-label">Amount Received:</span>
                            <span class="trade-value fiat-amount">{trade.fiat_currency} {trade.fiat_amount:,.2f}</span>
                        </div>
                        <div class="trade-row">
                            <span class="trade-label">Exchange Rate:</span>
                            <span class="trade-value">{trade.fiat_currency} {trade.exchange_rate:,.2f}</span>
                        </div>
                        <div class="trade-row">
                            <span class="trade-label">Fee:</span>
                            <span class="trade-value">{trade.fiat_currency} {trade.fee_amount:,.2f}</span>
                        </div>
                        <div class="trade-row">
                            <span class="trade-label">Payment Method:</span>
                            <span class="trade-value">{trade.payment_method.replace('_', ' ').title()}</span>
                        </div>
                        <div class="trade-row">
                            <span class="trade-label">Completed At:</span>
                            <span class="trade-value">{trade.completed_at.strftime('%B %d, %Y at %I:%M %p') if trade.completed_at else 'N/A'}</span>
                        </div>
                    </div>
                    
                    <p style="color: #6b7c93; font-size: 14px; margin-top: 24px;">
                        Your {trade.fiat_currency} is now available in your DT Exchange account. 
                        You can withdraw it to your bank account or use it for future trades.
                    </p>
                </div>
                
                <div class="footer">
                    <p class="footer-text">
                        Thank you for trading with DT Exchange!<br>
                        Need help? Contact our support team at 
                        <a href="mailto:support@badix.io" class="support-link">support@badix.io</a>
                    </p>
                    <p class="footer-text" style="margin-top: 16px;">
                        © 2024 DT Exchange. All rights reserved.
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return subject, html_content
    
    def _generate_trade_failed_email(self, trade: Trade, user: User, error_message: str) -> tuple[str, str]:
        """Generate trade failed email content"""
        subject = f"❌ Trade Failed - {trade.trade_type.value.title()} {trade.crypto_currency}"
        
        html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Trade Failed - DT Exchange</title>
            <style>
                body {{
                    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    background-color: #f7f9fa;
                    color: #2c2e2f;
                    line-height: 1.6;
                    margin: 0;
                    padding: 0;
                }}
                .container {{
                    max-width: 600px;
                    margin: 0 auto;
                    background-color: #ffffff;
                    border-radius: 16px;
                    overflow: hidden;
                    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
                }}
                .header {{
                    background: linear-gradient(135deg, #dc2626 0%, #b91c1c 100%);
                    padding: 40px 30px;
                    text-align: center;
                    color: white;
                }}
                .logo {{
                    font-size: 28px;
                    font-weight: 700;
                    margin-bottom: 10px;
                    letter-spacing: -0.5px;
                }}
                .subtitle {{
                    font-size: 16px;
                    opacity: 0.9;
                    font-weight: 400;
                }}
                .content {{
                    padding: 40px 30px;
                    text-align: center;
                }}
                .error-icon {{
                    width: 80px;
                    height: 80px;
                    background: linear-gradient(135deg, #dc2626 0%, #b91c1c 100%);
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    margin: 0 auto 24px;
                }}
                .title {{
                    font-size: 24px;
                    font-weight: 600;
                    color: #2c2e2f;
                    margin-bottom: 16px;
                    letter-spacing: -0.3px;
                }}
                .description {{
                    font-size: 16px;
                    color: #6b7c93;
                    margin-bottom: 32px;
                    line-height: 1.6;
                }}
                .error-message {{
                    background: linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%);
                    border: 2px solid #fecaca;
                    border-radius: 12px;
                    padding: 20px;
                    margin: 24px 0;
                    text-align: left;
                }}
                .error-title {{
                    color: #dc2626;
                    font-weight: 600;
                    margin-bottom: 8px;
                }}
                .error-text {{
                    color: #7f1d1d;
                    font-size: 14px;
                }}
                .trade-summary {{
                    background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
                    border: 2px solid #e2e8f0;
                    border-radius: 12px;
                    padding: 24px;
                    margin: 32px 0;
                    text-align: left;
                }}
                .trade-row {{
                    display: flex;
                    justify-content: space-between;
                    margin-bottom: 12px;
                    padding-bottom: 8px;
                    border-bottom: 1px solid #e2e8f0;
                }}
                .trade-row:last-child {{
                    border-bottom: none;
                    margin-bottom: 0;
                }}
                .trade-label {{
                    color: #6b7c93;
                    font-weight: 500;
                }}
                .trade-value {{
                    color: #2c2e2f;
                    font-weight: 600;
                }}
                .footer {{
                    background-color: #f8fafc;
                    padding: 24px 30px;
                    text-align: center;
                    border-top: 1px solid #e2e8f0;
                }}
                .footer-text {{
                    color: #94a3b8;
                    font-size: 12px;
                    line-height: 1.5;
                }}
                .support-link {{
                    color: #0070ba;
                    text-decoration: none;
                    font-weight: 500;
                }}
                .support-link:hover {{
                    text-decoration: underline;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="logo">DT Exchange</div>
                    <div class="subtitle">Secure Crypto Trading Platform</div>
                </div>
                
                <div class="content">
                    <div class="error-icon">
                        <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M18 6L6 18M6 6l12 12"/>
                        </svg>
                    </div>
                    
                    <h1 class="title">Trade Failed</h1>
                    <p class="description">
                        Unfortunately, your {trade.trade_type.value} order for {trade.crypto_currency} could not be completed.
                    </p>
                    
                    <div class="error-message">
                        <div class="error-title">Error Details</div>
                        <div class="error-text">{error_message}</div>
                    </div>
                    
                    <div class="trade-summary">
                        <div class="trade-row">
                            <span class="trade-label">Trade ID:</span>
                            <span class="trade-value">#{trade.id}</span>
                        </div>
                        <div class="trade-row">
                            <span class="trade-label">Trade Type:</span>
                            <span class="trade-value">{trade.trade_type.value.title()}</span>
                        </div>
                        <div class="trade-row">
                            <span class="trade-label">Cryptocurrency:</span>
                            <span class="trade-value">{trade.crypto_currency}</span>
                        </div>
                        <div class="trade-row">
                            <span class="trade-label">Amount:</span>
                            <span class="trade-value">{trade.crypto_amount:.8f} {trade.crypto_currency}</span>
                        </div>
                        <div class="trade-row">
                            <span class="trade-label">Value:</span>
                            <span class="trade-value">{trade.fiat_currency} {trade.fiat_amount:,.2f}</span>
                        </div>
                        <div class="trade-row">
                            <span class="trade-label">Payment Method:</span>
                            <span class="trade-value">{trade.payment_method.replace('_', ' ').title()}</span>
                        </div>
                        <div class="trade-row">
                            <span class="trade-label">Created At:</span>
                            <span class="trade-value">{trade.created_at.strftime('%B %d, %Y at %I:%M %p')}</span>
                        </div>
                    </div>
                    
                    <p style="color: #6b7c93; font-size: 14px; margin-top: 24px;">
                        Please try again or contact our support team if the issue persists. 
                        Your funds have not been charged for this failed transaction.
                    </p>
                </div>
                
                <div class="footer">
                    <p class="footer-text">
                        Need help? Contact our support team at 
                        <a href="mailto:support@badix.io" class="support-link">support@badix.io</a>
                    </p>
                    <p class="footer-text" style="margin-top: 16px;">
                        © 2024 DT Exchange. All rights reserved.
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return subject, html_content
    
    def _send_email(self, to_email: str, subject: str, html_content: str, user_name: str = None) -> bool:
        """Send email using Resend"""
        if not self.resend_api_key:
            logger.warning("Resend API key not configured - skipping email send")
            return False
        
        try:
            params = {
                "from": self.from_email,
                "to": to_email,
                "subject": subject,
                "html": html_content
            }
            
            if user_name:
                params["reply_to"] = "support@badix.io"
            
            response = resend.Emails.send(params)
            logger.info(f"Trade notification email sent successfully: {response}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send trade notification email: {e}")
            return False

# Global instance
trade_notification_service = TradeNotificationService()
