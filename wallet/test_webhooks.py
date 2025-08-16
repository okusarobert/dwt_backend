#!/usr/bin/env python3
"""
Test script for trading webhooks
Demonstrates how to use the webhook system for buy and sell operations
"""

import requests
import json
import hmac
import hashlib
from datetime import datetime
from decouple import config

# Configuration
BASE_URL = "http://localhost:8000"  # Update with your API URL
API_GATEWAY_URL = "http://localhost:8000/api/v1"  # API gateway URL

# Webhook secrets (should be in environment variables)
BUY_WEBHOOK_SECRET = config('BUY_WEBHOOK_SECRET', default='test-buy-secret')
SELL_WEBHOOK_SECRET = config('SELL_WEBHOOK_SECRET', default='test-sell-secret')
TRADE_WEBHOOK_SECRET = config('TRADE_WEBHOOK_SECRET', default='test-trade-secret')

def generate_signature(payload: str, secret: str) -> str:
    """Generate HMAC-SHA256 signature for webhook payload"""
    return hmac.new(
        secret.encode('utf-8'),
        payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

def test_buy_completion_webhook(trade_id: int = 123):
    """Test buy completion webhook"""
    print(f"\n🧪 Testing Buy Completion Webhook for Trade {trade_id}")
    
    payload = {
        "trade_id": trade_id,
        "status": "completed",
        "crypto_amount": 0.001,
        "transaction_hash": "0x1234567890abcdef1234567890abcdef12345678",
        "timestamp": datetime.utcnow().isoformat(),
        "webhook_type": "buy_completion"
    }
    
    payload_str = json.dumps(payload)
    signature = generate_signature(payload_str, BUY_WEBHOOK_SECRET)
    
    headers = {
        "Content-Type": "application/json",
        "X-Buy-Webhook-Signature": signature
    }
    
    try:
        # Test direct wallet service endpoint
        response = requests.post(
            f"{BASE_URL}/api/webhooks/buy-complete",
            headers=headers,
            json=payload,
            timeout=10
        )
        
        print(f"✅ Direct Wallet Service Response: {response.status_code}")
        print(f"Response Body: {response.json()}")
        
        # Test API gateway endpoint
        response = requests.post(
            f"{API_GATEWAY_URL}/webhooks/buy-complete",
            headers=headers,
            json=payload,
            timeout=10
        )
        
        print(f"✅ API Gateway Response: {response.status_code}")
        print(f"Response Body: {response.json()}")
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error: {e}")

def test_sell_completion_webhook(trade_id: int = 124):
    """Test sell completion webhook"""
    print(f"\n🧪 Testing Sell Completion Webhook for Trade {trade_id}")
    
    payload = {
        "trade_id": trade_id,
        "status": "completed",
        "fiat_amount": 100.0,
        "payment_reference": "PAY_REF_123456789",
        "timestamp": datetime.utcnow().isoformat(),
        "webhook_type": "sell_completion"
    }
    
    payload_str = json.dumps(payload)
    signature = generate_signature(payload_str, SELL_WEBHOOK_SECRET)
    
    headers = {
        "Content-Type": "application/json",
        "X-Sell-Webhook-Signature": signature
    }
    
    try:
        # Test direct wallet service endpoint
        response = requests.post(
            f"{BASE_URL}/api/webhooks/sell-complete",
            headers=headers,
            json=payload,
            timeout=10
        )
        
        print(f"✅ Direct Wallet Service Response: {response.status_code}")
        print(f"Response Body: {response.json()}")
        
        # Test API gateway endpoint
        response = requests.post(
            f"{API_GATEWAY_URL}/webhooks/sell-complete",
            headers=headers,
            json=payload,
            timeout=10
        )
        
        print(f"✅ API Gateway Response: {response.status_code}")
        print(f"Response Body: {response.json()}")
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error: {e}")

def test_trade_status_webhook(trade_id: int = 125):
    """Test trade status webhook"""
    print(f"\n🧪 Testing Trade Status Webhook for Trade {trade_id}")
    
    payload = {
        "trade_id": trade_id,
        "status": "processing",
        "metadata": {
            "processing_stage": "crypto_transfer",
            "estimated_completion": "5 minutes",
            "block_height": 12345678
        },
        "timestamp": datetime.utcnow().isoformat(),
        "webhook_type": "trade_status"
    }
    
    payload_str = json.dumps(payload)
    signature = generate_signature(payload_str, TRADE_WEBHOOK_SECRET)
    
    headers = {
        "Content-Type": "application/json",
        "X-Trade-Webhook-Signature": signature
    }
    
    try:
        # Test direct wallet service endpoint
        response = requests.post(
            f"{BASE_URL}/api/webhooks/trade-status",
            headers=headers,
            json=payload,
            timeout=10
        )
        
        print(f"✅ Direct Wallet Service Response: {response.status_code}")
        print(f"Response Body: {response.json()}")
        
        # Test API gateway endpoint
        response = requests.post(
            f"{API_GATEWAY_URL}/webhooks/trade-status",
            headers=headers,
            json=payload,
            timeout=10
        )
        
        print(f"✅ API Gateway Response: {response.status_code}")
        print(f"Response Body: {response.json()}")
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error: {e}")

def test_invalid_signature():
    """Test webhook with invalid signature"""
    print(f"\n🧪 Testing Invalid Signature")
    
    payload = {
        "trade_id": 999,
        "status": "completed",
        "crypto_amount": 0.001
    }
    
    # Use wrong secret to generate invalid signature
    payload_str = json.dumps(payload)
    signature = generate_signature(payload_str, "wrong-secret")
    
    headers = {
        "Content-Type": "application/json",
        "X-Buy-Webhook-Signature": signature
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/webhooks/buy-complete",
            headers=headers,
            json=payload,
            timeout=10
        )
        
        print(f"✅ Expected 401 Response: {response.status_code}")
        print(f"Response Body: {response.json()}")
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error: {e}")

def test_missing_fields():
    """Test webhook with missing required fields"""
    print(f"\n🧪 Testing Missing Required Fields")
    
    payload = {
        "trade_id": 999
        # Missing status field
    }
    
    payload_str = json.dumps(payload)
    signature = generate_signature(payload_str, BUY_WEBHOOK_SECRET)
    
    headers = {
        "Content-Type": "application/json",
        "X-Buy-Webhook-Signature": signature
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/webhooks/buy-complete",
            headers=headers,
            json=payload,
            timeout=10
        )
        
        print(f"✅ Expected 400 Response: {response.status_code}")
        print(f"Response Body: {response.json()}")
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error: {e}")

def test_failed_trade():
    """Test webhook for failed trade"""
    print(f"\n🧪 Testing Failed Trade Webhook")
    
    payload = {
        "trade_id": 126,
        "status": "failed",
        "error_message": "Insufficient funds in reserve account",
        "timestamp": datetime.utcnow().isoformat(),
        "webhook_type": "buy_completion"
    }
    
    payload_str = json.dumps(payload)
    signature = generate_signature(payload_str, BUY_WEBHOOK_SECRET)
    
    headers = {
        "Content-Type": "application/json",
        "X-Buy-Webhook-Signature": signature
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/webhooks/buy-complete",
            headers=headers,
            json=payload,
            timeout=10
        )
        
        print(f"✅ Failed Trade Response: {response.status_code}")
        print(f"Response Body: {response.json()}")
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error: {e}")

def main():
    """Run all webhook tests"""
    print("🚀 Starting Trading Webhook Tests")
    print("=" * 50)
    
    # Test successful webhooks
    test_buy_completion_webhook()
    test_sell_completion_webhook()
    test_trade_status_webhook()
    
    # Test error scenarios
    test_invalid_signature()
    test_missing_fields()
    test_failed_trade()
    
    print("\n" + "=" * 50)
    print("✅ All webhook tests completed!")

if __name__ == "__main__":
    main()
