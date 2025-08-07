#!/usr/bin/env python3
"""
Test script for BlockCypher webhook endpoint.
This script simulates a BlockCypher webhook request to test the endpoint.
"""

import requests
import json
import base64
import hashlib
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import load_pem_private_key

# Test configuration
WEBHOOK_URL = "http://localhost:3000/api/v1/wallet/btc/callbacks/address-webhook"
BLOCKCYPHER_PUBLIC_KEY = """-----BEGIN PUBLIC KEY-----
MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAEflgGqpIAC9k65JicOPBgXZUExen4
rWLq05KwYmZHphTU/fmi3Oe/ckyxo2w3Ayo/SCO/rU2NB90jtCJfz9i1ow==
-----END PUBLIC KEY-----"""

def create_test_signature(payload: str) -> str:
    """Create a test signature for the payload."""
    try:
        # Load the public key
        public_key = load_pem_private_key(
            BLOCKCYPHER_PUBLIC_KEY.encode(),
            password=None
        )
        
        # Create hash of the payload
        hash_obj = hashlib.sha256()
        hash_obj.update(payload.encode())
        message_hash = hash_obj.digest()
        
        # Sign the hash (this is just for testing - in real scenario BlockCypher signs)
        signature = public_key.sign(
            message_hash,
            ec.ECDSA(hashes.SHA256())
        )
        
        return base64.b64encode(signature).decode()
    except Exception as e:
        print(f"Error creating signature: {e}")
        return ""

def test_webhook_endpoint():
    """Test the webhook endpoint with different event types."""
    
    # Test payloads for different event types
    test_payloads = [
        {
            "event": "unconfirmed-tx",
            "hash": "2b17f5589528f97436b5d563635b4b27ca8980aa20c300abdc538f2a8bfa871b",
            "address": "mt4Vd5HFw2C8BZDbEGDxdhAGYYdsJCazoh",
            "confirmations": 0,
            "confidence": 0.95
        },
        {
            "event": "confirmed-tx",
            "hash": "2b17f5589528f97436b5d563635b4b27ca8980aa20c300abdc538f2a8bfa871b",
            "address": "mt4Vd5HFw2C8BZDbEGDxdhAGYYdsJCazoh",
            "confirmations": 1,
            "confidence": 1.0
        },
        {
            "event": "tx-confirmation",
            "hash": "2b17f5589528f97436b5d563635b4b27ca8980aa20c300abdc538f2a8bfa871b",
            "address": "mt4Vd5HFw2C8BZDbEGDxdhAGYYdsJCazoh",
            "confirmations": 3,
            "confidence": 1.0
        }
    ]
    
    for i, payload in enumerate(test_payloads):
        print(f"\n--- Test {i+1}: {payload['event']} ---")
        
        # Convert payload to JSON string
        payload_str = json.dumps(payload)
        
        # Create signature (for testing purposes)
        signature = create_test_signature(payload_str)
        
        # Prepare headers
        headers = {
            'Content-Type': 'application/json',
            'X-BlockCypher-Signature': f'keyId="test",algorithm="sha256-ecdsa",signature="{signature}"'
        }
        
        try:
            # Send POST request to webhook endpoint
            response = requests.post(
                WEBHOOK_URL,
                json=payload,
                headers=headers,
                timeout=10
            )
            
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.text}")
            
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
        except Exception as e:
            print(f"Error: {e}")

def test_without_signature():
    """Test webhook without signature (should work if signature verification is disabled)."""
    print("\n--- Test without signature ---")
    
    payload = {
        "event": "unconfirmed-tx",
        "hash": "test_hash_123",
        "address": "mt4Vd5HFw2C8BZDbEGDxdhAGYYdsJCazoh",
        "confirmations": 0
    }
    
    headers = {'Content-Type': 'application/json'}
    
    try:
        response = requests.post(
            WEBHOOK_URL,
            json=payload,
            headers=headers,
            timeout=10
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    print("Testing BlockCypher webhook endpoint...")
    print(f"Webhook URL: {WEBHOOK_URL}")
    
    # Test with signature
    test_webhook_endpoint()
    
    # Test without signature
    test_without_signature()
    
    print("\nTest completed!") 