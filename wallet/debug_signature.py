#!/usr/bin/env python3
"""
Debug script to identify signature verification issues
"""

import hmac
import hashlib
import json

def debug_signature_verification():
    # Real webhook data from user
    request_body = '{"webhookId": "wh_3jy2a58xredbdaso", "id": "whevt_kjhnv3azk5h2f1pp", "createdAt": "2025-08-08T20:08:52.623Z", "type": "ADDRESS_ACTIVITY", "event": {"transaction": [{"signature": "5q8ZbKic6r6bfr3HTEYxg2YWLw8PnxR13zhDgSokKLY2VstySBngb2Ry7u4tw5UUdtGVEbpiwYR4PyHWtVn4hUd4", "transaction": [{"signatures": ["5q8ZbKic6r6bfr3HTEYxg2YWLw8PnxR13zhDgSokKLY2VstySBngb2Ry7u4tw5UUdtGVEbpiwYR4PyHWtVn4hUd4"], "message": [{"header": [{"num_required_signatures": 1, "num_readonly_signed_accounts": 0, "num_readonly_unsigned_accounts": 1}], "instructions": [{"accounts": [0, 1], "data": "3Bxs4NN8M2Yn4TLb", "program_id_index": 2}], "versioned": false, "account_keys": ["5F1CseTyapzAJJN2JbySZbXyDPseh7naWaRGcURjA5yB", "8QK7uaVNAKPPbeHmoojpi9dffnmo5Q2vcqm9tLWscN26", "11111111111111111111111111111111"], "recent_blockhash": "2hefYRfVcesrNJrzCPp9ZJRPzEP9ixErQCWcYk5xJUnu"}]}], "meta": [{"fee": 5000, "pre_balances": [13000000000, 0, 1], "post_balances": [12989995000, 10000000, 1], "inner_instructions_none": false, "log_messages": ["Program 11111111111111111111111111111111 invoke [1]", "Program 11111111111111111111111111111111 success"], "log_messages_none": false, "return_data_none": true, "compute_units_consumed": 150}], "index": 22, "is_vote": false}], "slot": 399851707, "network": "SOLANA_DEVNET"}}'

    received_signature = 'c2cd8d9cee78213ee86b4ce4f07002abb30e2c9e407b9ffa30609f9f72e1436c'
    signing_key = 'whsec_Cr8A7jCSHJGPjE2A92l7gmbf'

    print('🔍 Debugging Signature Verification')
    print('=' * 50)
    print()
    
    # Test 1: Check if request body is valid JSON
    print('1. Checking if request body is valid JSON:')
    try:
        parsed_json = json.loads(request_body)
        print('   ✅ Request body is valid JSON')
        print(f'   Webhook ID: {parsed_json.get("webhookId")}')
        print(f'   Event Type: {parsed_json.get("type")}')
    except json.JSONDecodeError as e:
        print(f'   ❌ Invalid JSON: {e}')
    print()
    
    # Test 2: Check different encoding approaches
    print('2. Testing different encoding approaches:')
    
    # Approach 1: UTF-8 encoding
    digest1 = hmac.new(
        bytes(signing_key, 'utf-8'),
        msg=bytes(request_body, 'utf-8'),
        digestmod=hashlib.sha256
    ).hexdigest()
    print(f'   UTF-8 encoding: {digest1}')
    
    # Approach 2: Raw bytes
    digest2 = hmac.new(
        signing_key.encode('utf-8'),
        msg=request_body.encode('utf-8'),
        digestmod=hashlib.sha256
    ).hexdigest()
    print(f'   Raw bytes: {digest2}')
    
    # Approach 3: ASCII encoding
    digest3 = hmac.new(
        bytes(signing_key, 'ascii'),
        msg=bytes(request_body, 'ascii'),
        digestmod=hashlib.sha256
    ).hexdigest()
    print(f'   ASCII encoding: {digest3}')
    
    print(f'   Expected: {received_signature}')
    print()
    
    # Test 3: Check if any match
    matches = []
    if digest1 == received_signature:
        matches.append('UTF-8 encoding')
    if digest2 == received_signature:
        matches.append('Raw bytes')
    if digest3 == received_signature:
        matches.append('ASCII encoding')
    
    if matches:
        print(f'   ✅ Match found with: {", ".join(matches)}')
    else:
        print('   ❌ No matches found')
    print()
    
    # Test 4: Try different signing key variations
    print('3. Testing different signing key variations:')
    variations = [
        signing_key,
        signing_key.replace('whsec_', ''),
        signing_key + '=',
        signing_key + '==',
        signing_key.replace('whsec_', 'whsec_')  # Same but explicit
    ]
    
    for i, key in enumerate(variations, 1):
        digest = hmac.new(
            bytes(key, 'utf-8'),
            msg=bytes(request_body, 'utf-8'),
            digestmod=hashlib.sha256
        ).hexdigest()
        
        is_match = digest == received_signature
        status = '✅ MATCH!' if is_match else '❌'
        print(f'   {i}. {key}: {digest[:20]}... {status}')
    
    print()
    print('💡 Possible issues:')
    print('   - The signing key might be for a different webhook')
    print('   - The request body might have been modified during transmission')
    print('   - There might be a different encoding used by Alchemy')
    print('   - The webhook might use a different signing method')

if __name__ == '__main__':
    debug_signature_verification()
