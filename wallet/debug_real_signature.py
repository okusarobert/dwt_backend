#!/usr/bin/env python3
"""
Debug the real signature verification with the correct signing key
"""

import hmac
import hashlib
import json
import base64

def debug_real_signature():
    # Real webhook data from user
    request_body = '{"webhookId": "wh_3jy2a58xredbdaso", "id": "whevt_kjhnv3azk5h2f1pp", "createdAt": "2025-08-08T20:08:52.623Z", "type": "ADDRESS_ACTIVITY", "event": {"transaction": [{"signature": "5q8ZbKic6r6bfr3HTEYxg2YWLw8PnxR13zhDgSokKLY2VstySBngb2Ry7u4tw5UUdtGVEbpiwYR4PyHWtVn4hUd4", "transaction": [{"signatures": ["5q8ZbKic6r6bfr3HTEYxg2YWLw8PnxR13zhDgSokKLY2VstySBngb2Ry7u4tw5UUdtGVEbpiwYR4PyHWtVn4hUd4"], "message": [{"header": [{"num_required_signatures": 1, "num_readonly_signed_accounts": 0, "num_readonly_unsigned_accounts": 1}], "instructions": [{"accounts": [0, 1], "data": "3Bxs4NN8M2Yn4TLb", "program_id_index": 2}], "versioned": false, "account_keys": ["5F1CseTyapzAJJN2JbySZbXyDPseh7naWaRGcURjA5yB", "8QK7uaVNAKPPbeHmoojpi9dffnmo5Q2vcqm9tLWscN26", "11111111111111111111111111111111"], "recent_blockhash": "2hefYRfVcesrNJrzCPp9ZJRPzEP9ixErQCWcYk5xJUnu"}]}], "meta": [{"fee": 5000, "pre_balances": [13000000000, 0, 1], "post_balances": [12989995000, 10000000, 1], "inner_instructions_none": false, "log_messages": ["Program 11111111111111111111111111111111 invoke [1]", "Program 11111111111111111111111111111111 success"], "log_messages_none": false, "return_data_none": true, "compute_units_consumed": 150}], "index": 22, "is_vote": false}], "slot": 399851707, "network": "SOLANA_DEVNET"}}'

    received_signature = 'c2cd8d9cee78213ee86b4ce4f07002abb30e2c9e407b9ffa30609f9f72e1436c'
    signing_key = 'whsec_Cr8A7jCSHJGPjE2A92l7gmbf'

    print('🔍 Debugging Real Signature Verification')
    print('=' * 50)
    print()
    
    # Test 1: Check request body details
    print('1. Request Body Analysis:')
    print(f'   Length: {len(request_body)} characters')
    print(f'   First 100 chars: {request_body[:100]}...')
    print(f'   Last 100 chars: ...{request_body[-100:]}')
    print()
    
    # Test 2: Check for hidden characters
    print('2. Checking for hidden characters:')
    print(f'   Raw bytes: {repr(request_body[:50])}')
    print(f'   UTF-8 bytes: {request_body.encode("utf-8")[:50]}')
    print()
    
    # Test 3: Try different approaches
    print('3. Testing different signature approaches:')
    
    # Standard approach
    digest1 = hmac.new(
        bytes(signing_key, 'utf-8'),
        msg=bytes(request_body, 'utf-8'),
        digestmod=hashlib.sha256
    ).hexdigest()
    print(f'   Standard: {digest1}')
    
    # Try with different line endings
    request_body_no_newlines = request_body.replace('\n', '').replace('\r', '')
    digest2 = hmac.new(
        bytes(signing_key, 'utf-8'),
        msg=bytes(request_body_no_newlines, 'utf-8'),
        digestmod=hashlib.sha256
    ).hexdigest()
    print(f'   No newlines: {digest2}')
    
    # Try with compact JSON
    try:
        parsed = json.loads(request_body)
        compact_json = json.dumps(parsed, separators=(',', ':'))
        digest3 = hmac.new(
            bytes(signing_key, 'utf-8'),
            msg=bytes(compact_json, 'utf-8'),
            digestmod=hashlib.sha256
        ).hexdigest()
        print(f'   Compact JSON: {digest3}')
    except:
        print('   Compact JSON: Error parsing')
    
    # Try with pretty JSON
    try:
        parsed = json.loads(request_body)
        pretty_json = json.dumps(parsed, indent=2)
        digest4 = hmac.new(
            bytes(signing_key, 'utf-8'),
            msg=bytes(pretty_json, 'utf-8'),
            digestmod=hashlib.sha256
        ).hexdigest()
        print(f'   Pretty JSON: {digest4}')
    except:
        print('   Pretty JSON: Error parsing')
    
    print(f'   Expected: {received_signature}')
    print()
    
    # Test 4: Check if any match
    matches = []
    if digest1 == received_signature:
        matches.append('Standard')
    if digest2 == received_signature:
        matches.append('No newlines')
    if 'digest3' in locals() and digest3 == received_signature:
        matches.append('Compact JSON')
    if 'digest4' in locals() and digest4 == received_signature:
        matches.append('Pretty JSON')
    
    if matches:
        print(f'   ✅ Match found with: {", ".join(matches)}')
    else:
        print('   ❌ No matches found')
    print()
    
    # Test 5: Try different signing key formats
    print('4. Testing different signing key formats:')
    key_variations = [
        signing_key,
        signing_key.encode('utf-8'),
        signing_key.encode('ascii'),
        signing_key.replace('whsec_', ''),
        base64.b64decode(signing_key + '==') if len(signing_key) % 4 == 0 else None,
    ]
    
    for i, key in enumerate(key_variations, 1):
        if key is None:
            continue
        try:
            if isinstance(key, bytes):
                digest = hmac.new(key, msg=bytes(request_body, 'utf-8'), digestmod=hashlib.sha256).hexdigest()
            else:
                digest = hmac.new(bytes(key, 'utf-8'), msg=bytes(request_body, 'utf-8'), digestmod=hashlib.sha256).hexdigest()
            
            is_match = digest == received_signature
            status = '✅ MATCH!' if is_match else '❌'
            print(f'   {i}. {key}: {digest[:20]}... {status}')
        except Exception as e:
            print(f'   {i}. {key}: Error - {e}')
    
    print()
    print('💡 If none of these match, the issue might be:')
    print('   - The request body was modified during transmission')
    print('   - The signing key is for a different webhook')
    print('   - Alchemy uses a different signing method for this webhook')
    print('   - There might be additional headers or metadata included')

if __name__ == '__main__':
    debug_real_signature()
