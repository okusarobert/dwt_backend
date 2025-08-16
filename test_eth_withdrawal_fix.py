#!/usr/bin/env python3
"""
Test script to verify that Ethereum withdrawal works with the new smallest unit fields
"""

import requests
import json
from decouple import config

def test_eth_withdrawal():
    """Test Ethereum withdrawal with the new smallest unit fields"""
    
    # API endpoint
    api_url = "http://localhost:8000/api/v1/wallet/withdraw/ethereum"
    
    # Test data
    test_data = {
        "to_address": "0x153fEEe2FD50018f2d9DD643174F7C244aA77C95",
        "amount": 0.0001,  # Very small amount for testing
        "reference_id": "test_withdrawal_fix_123",
        "description": "Test withdrawal with smallest unit fix",
        "gas_limit": 21000
    }
    
    # Headers (you'll need to get a valid token)
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer YOUR_TOKEN_HERE"  # Replace with actual token
    }
    
    print("Testing Ethereum Withdrawal with Smallest Unit Fix")
    print("=" * 55)
    print(f"API URL: {api_url}")
    print(f"Test Data: {json.dumps(test_data, indent=2)}")
    print()
    
    try:
        # Make the request
        response = requests.post(api_url, json=test_data, headers=headers)
        
        print(f"Response Status: {response.status_code}")
        print(f"Response Body: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 201:
            print("✅ Ethereum withdrawal created successfully!")
            print("   The smallest unit fields should now be properly set")
        else:
            print("❌ Ethereum withdrawal failed")
            print("   Check the error message above")
            
    except Exception as e:
        print(f"❌ Error testing Ethereum withdrawal: {e}")

def test_database_verification():
    """Test script to verify the transaction was created with proper fields"""
    print("\n" + "=" * 55)
    print("Database Verification Test")
    print("=" * 55)
    
    print("To verify the transaction was created correctly, run:")
    print("docker exec -it dwt_backend-wallet-1 python -c \\")
    print("  \"from db.connection import get_session; from db.wallet import Transaction; session = get_session(); tx = session.query(Transaction).filter_by(reference_id='test_withdrawal_fix_123').first(); print(f'Transaction: {tx.reference_id}' if tx else 'Transaction not found'); print(f'Amount: {tx.amount}' if tx else ''); print(f'Amount Smallest Unit: {tx.amount_smallest_unit}' if tx else ''); print(f'Precision Config: {tx.precision_config}' if tx else '')\"")

if __name__ == "__main__":
    test_eth_withdrawal()
    test_database_verification() 