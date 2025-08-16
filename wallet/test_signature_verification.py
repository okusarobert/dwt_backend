#!/usr/bin/env python3
"""
Test script to verify Alchemy webhook signature
"""

import hmac
import hashlib
import json

def verify_alchemy_signature(request_body, received_signature, signing_key):
    """
    Verify Alchemy webhook signature using the correct HMAC approach
    """
    # Calculate HMAC using the correct approach (as per official Alchemy docs)
    digest = hmac.new(
        bytes(signing_key, 'utf-8'),
        msg=bytes(request_body, 'utf-8'),
        digestmod=hashlib.sha256
    ).hexdigest()
    
    is_valid = digest == received_signature
    return is_valid, digest

def main():
    # Real webhook data from user
    request_body = '{"webhookId": "wh_3jy2a58xredbdaso", "id": "whevt_kjhnv3azk5h2f1pp", "createdAt": "2025-08-08T20:08:52.623Z", "type": "ADDRESS_ACTIVITY", "event": {"transaction": [{"signature": "5q8ZbKic6r6bfr3HTEYxg2YWLw8PnxR13zhDgSokKLY2VstySBngb2Ry7u4tw5UUdtGVEbpiwYR4PyHWtVn4hUd4", "transaction": [{"signatures": ["5q8ZbKic6r6bfr3HTEYxg2YWLw8PnxR13zhDgSokKLY2VstySBngb2Ry7u4tw5UUdtGVEbpiwYR4PyHWtVn4hUd4"], "message": [{"header": [{"num_required_signatures": 1, "num_readonly_signed_accounts": 0, "num_readonly_unsigned_accounts": 1}], "instructions": [{"accounts": [0, 1], "data": "3Bxs4NN8M2Yn4TLb", "program_id_index": 2}], "versioned": false, "account_keys": ["5F1CseTyapzAJJN2JbySZbXyDPseh7naWaRGcURjA5yB", "8QK7uaVNAKPPbeHmoojpi9dffnmo5Q2vcqm9tLWscN26", "11111111111111111111111111111111"], "recent_blockhash": "2hefYRfVcesrNJrzCPp9ZJRPzEP9ixErQCWcYk5xJUnu"}]}], "meta": [{"fee": 5000, "pre_balances": [13000000000, 0, 1], "post_balances": [12989995000, 10000000, 1], "inner_instructions_none": false, "log_messages": ["Program 11111111111111111111111111111111 invoke [1]", "Program 11111111111111111111111111111111 success"], "log_messages_none": false, "return_data_none": true, "compute_units_consumed": 150}], "index": 22, "is_vote": false}], "slot": 399851707, "network": "SOLANA_DEVNET"}}'

    received_signature = 'c2cd8d9cee78213ee86b4ce4f07002abb30e2c9e407b9ffa30609f9f72e1436c'
    webhook_id = 'wh_3jy2a58xredbdaso'
    
    # Real signing key from user
    real_signing_key = 'whsec_Cr8A7jCSHJGPjE2A92l7gmbf'

    print('🔍 Testing Alchemy Webhook Signature Verification')
    print('=' * 60)
    print(f'Webhook ID: {webhook_id}')
    print(f'Received Signature: {received_signature}')
    print(f'Request Body Length: {len(request_body)} characters')
    print(f'Real Signing Key: {real_signing_key}')
    print()

    # Test with the real signing key
    print('🔑 Testing with real signing key:')
    print()
    
    is_valid, calculated_digest = verify_alchemy_signature(
        request_body, received_signature, real_signing_key
    )
    
    status = '✅ MATCH!' if is_valid else '❌ No match'
    
    print(f'Signing Key: {real_signing_key}')
    print(f'Calculated: {calculated_digest}')
    print(f'Expected:   {received_signature}')
    print(f'Result:     {status}')
    print()
    
    if is_valid:
        print('🎉 SUCCESS! Signature verification works correctly!')
        print('✅ The HMAC implementation is correct.')
        print('✅ The webhook verification will work in production.')
    else:
        print('❌ Signature verification failed.')
        print('💡 This might indicate:')
        print('   - The signing key might be different')
        print('   - The request body might have been modified')
        print('   - There might be encoding issues')

if __name__ == '__main__':
    main()

