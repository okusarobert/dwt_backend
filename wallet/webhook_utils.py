"""
Webhook Utilities for Trading System
Provides utilities for webhook signature generation, validation, and testing
"""

import hmac
import hashlib
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from decouple import config

logger = logging.getLogger(__name__)

class WebhookUtils:
    """Utility class for webhook operations"""
    
    @staticmethod
    def generate_signature(payload: str, secret: str) -> str:
        """Generate HMAC-SHA256 signature for webhook payload"""
        return hmac.new(
            secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
    
    @staticmethod
    def verify_signature(payload: str, signature: str, secret: str) -> bool:
        """Verify webhook signature"""
        expected_signature = WebhookUtils.generate_signature(payload, secret)
        return hmac.compare_digest(signature, expected_signature)
    
    @staticmethod
    def create_buy_completion_webhook(
        trade_id: int,
        status: str,
        crypto_amount: float,
        transaction_hash: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create buy completion webhook payload"""
        payload = {
            "trade_id": trade_id,
            "status": status,
            "crypto_amount": crypto_amount,
            "timestamp": datetime.utcnow().isoformat(),
            "webhook_type": "buy_completion"
        }
        
        if transaction_hash:
            payload["transaction_hash"] = transaction_hash
        
        if error_message:
            payload["error_message"] = error_message
        
        return payload
    
    @staticmethod
    def create_sell_completion_webhook(
        trade_id: int,
        status: str,
        fiat_amount: float,
        payment_reference: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create sell completion webhook payload"""
        payload = {
            "trade_id": trade_id,
            "status": status,
            "fiat_amount": fiat_amount,
            "timestamp": datetime.utcnow().isoformat(),
            "webhook_type": "sell_completion"
        }
        
        if payment_reference:
            payload["payment_reference"] = payment_reference
        
        if error_message:
            payload["error_message"] = error_message
        
        return payload
    
    @staticmethod
    def create_trade_status_webhook(
        trade_id: int,
        status: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create trade status update webhook payload"""
        payload = {
            "trade_id": trade_id,
            "status": status,
            "timestamp": datetime.utcnow().isoformat(),
            "webhook_type": "trade_status"
        }
        
        if metadata:
            payload["metadata"] = metadata
        
        return payload

class WebhookTester:
    """Test utility for webhook operations"""
    
    @staticmethod
    def test_buy_completion_webhook(
        trade_id: int,
        crypto_amount: float = 0.001,
        transaction_hash: str = "0x1234567890abcdef",
        status: str = "completed"
    ):
        """Test buy completion webhook"""
        webhook_secret = config('BUY_WEBHOOK_SECRET', default='test-secret')
        
        payload = WebhookUtils.create_buy_completion_webhook(
            trade_id=trade_id,
            status=status,
            crypto_amount=crypto_amount,
            transaction_hash=transaction_hash
        )
        
        payload_str = json.dumps(payload)
        signature = WebhookUtils.generate_signature(payload_str, webhook_secret)
        
        return {
            "url": "/api/webhooks/buy-complete",
            "headers": {
                "Content-Type": "application/json",
                "X-Buy-Webhook-Signature": signature
            },
            "payload": payload
        }
    
    @staticmethod
    def test_sell_completion_webhook(
        trade_id: int,
        fiat_amount: float = 100.0,
        payment_reference: str = "PAY_REF_123456",
        status: str = "completed"
    ):
        """Test sell completion webhook"""
        webhook_secret = config('SELL_WEBHOOK_SECRET', default='test-secret')
        
        payload = WebhookUtils.create_sell_completion_webhook(
            trade_id=trade_id,
            status=status,
            fiat_amount=fiat_amount,
            payment_reference=payment_reference
        )
        
        payload_str = json.dumps(payload)
        signature = WebhookUtils.generate_signature(payload_str, webhook_secret)
        
        return {
            "url": "/api/webhooks/sell-complete",
            "headers": {
                "Content-Type": "application/json",
                "X-Sell-Webhook-Signature": signature
            },
            "payload": payload
        }
    
    @staticmethod
    def test_trade_status_webhook(
        trade_id: int,
        status: str = "processing",
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Test trade status webhook"""
        webhook_secret = config('TRADE_WEBHOOK_SECRET', default='test-secret')
        
        if metadata is None:
            metadata = {
                "processing_stage": "crypto_transfer",
                "estimated_completion": "5 minutes"
            }
        
        payload = WebhookUtils.create_trade_status_webhook(
            trade_id=trade_id,
            status=status,
            metadata=metadata
        )
        
        payload_str = json.dumps(payload)
        signature = WebhookUtils.generate_signature(payload_str, webhook_secret)
        
        return {
            "url": "/api/webhooks/trade-status",
            "headers": {
                "Content-Type": "application/json",
                "X-Trade-Webhook-Signature": signature
            },
            "payload": payload
        }

def generate_webhook_test_script():
    """Generate a test script for webhook testing"""
    script = """
# Webhook Test Script
# Use this script to test webhook endpoints

import requests
import json
from wallet.webhook_utils import WebhookTester

# Test configuration
BASE_URL = "http://localhost:8000"  # Update with your API URL

def test_buy_webhook():
    # Test buy completion webhook
    test_data = WebhookTester.test_buy_completion_webhook(
        trade_id=123,
        crypto_amount=0.001,
        transaction_hash="0x1234567890abcdef",
        status="completed"
    )
    
    response = requests.post(
        f"{BASE_URL}{test_data['url']}",
        headers=test_data['headers'],
        json=test_data['payload']
    )
    
    print(f"Buy Webhook Response: {response.status_code}")
    print(f"Response Body: {response.json()}")

def test_sell_webhook():
    # Test sell completion webhook
    test_data = WebhookTester.test_sell_completion_webhook(
        trade_id=124,
        fiat_amount=100.0,
        payment_reference="PAY_REF_123456",
        status="completed"
    )
    
    response = requests.post(
        f"{BASE_URL}{test_data['url']}",
        headers=test_data['headers'],
        json=test_data['payload']
    )
    
    print(f"Sell Webhook Response: {response.status_code}")
    print(f"Response Body: {response.json()}")

def test_status_webhook():
    # Test trade status webhook
    test_data = WebhookTester.test_trade_status_webhook(
        trade_id=125,
        status="processing",
        metadata={
            "processing_stage": "payment_verification",
            "estimated_completion": "2 minutes"
        }
    )
    
    response = requests.post(
        f"{BASE_URL}{test_data['url']}",
        headers=test_data['headers'],
        json=test_data['payload']
    )
    
    print(f"Status Webhook Response: {response.status_code}")
    print(f"Response Body: {response.json()}")

if __name__ == "__main__":
    print("Testing Buy Webhook...")
    test_buy_webhook()
    
    print("\\nTesting Sell Webhook...")
    test_sell_webhook()
    
    print("\\nTesting Status Webhook...")
    test_status_webhook()
"""
    
    return script

# Example usage functions
def example_webhook_usage():
    """Example usage of webhook utilities"""
    
    # Example 1: Generate buy completion webhook
    buy_payload = WebhookUtils.create_buy_completion_webhook(
        trade_id=123,
        status="completed",
        crypto_amount=0.001,
        transaction_hash="0x1234567890abcdef"
    )
    
    # Example 2: Generate sell completion webhook
    sell_payload = WebhookUtils.create_sell_completion_webhook(
        trade_id=124,
        status="completed",
        fiat_amount=100.0,
        payment_reference="PAY_REF_123456"
    )
    
    # Example 3: Generate trade status webhook
    status_payload = WebhookUtils.create_trade_status_webhook(
        trade_id=125,
        status="processing",
        metadata={
            "processing_stage": "crypto_transfer",
            "estimated_completion": "5 minutes"
        }
    )
    
    logger.info(f"Buy webhook payload: {buy_payload}")
    logger.info(f"Sell webhook payload: {sell_payload}")
    logger.info(f"Status webhook payload: {status_payload}")
    
    return {
        "buy": buy_payload,
        "sell": sell_payload,
        "status": status_payload
    }
