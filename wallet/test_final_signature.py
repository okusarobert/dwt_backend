#!/usr/bin/env python3
"""
Final test of signature verification with the updated implementation
"""

import hmac
import hashlib
import json

def test_final_signature():
    # Real webhook data from user
    request_body = '{"webhookId": "wh_3jy2a58xredbdaso", "id": "whevt_kjhnv3azk5h2f1pp", "createdAt": "2025-08-08T20:08:52.623Z", "type": "ADDRESS_ACTIVITY", "event": {"transaction": [{"signature": "5q8ZbKic6r6bfr3HTEYxg2YWLw8PnxR13zhDgSokKLY2VstySBngb2Ry7u4tw5UUdtGVEbpiwYR4PyHWtVn4hUd4", "transaction": [{"signatures": ["5q8ZbKic6r6bfr3HTEYxg2YWLw8PnxR13zhDgSokKLY2VstySBngb2Ry7u4tw5UUdtGVEbpiwYR4PyHWtVn4hUd4"], "message": [{"header": [{"num_required_signatures": 1, "num_readonly_signed_accounts": 0, "num_readonly_unsigned_accounts": 1}], "instructions": [{"accounts": [0, 1], "data": "3Bxs4NN8M2Yn4TLb", "program_id_index": 2}], "versioned": false, "account_keys": ["5F1CseTyapzAJJN2JbySZbXyDPseh7naWaRGcURjA5yB", "8QK7uaVNAKPPbeHmoojpi9dffnmo5Q2vcqm9tLWscN26", "11111111111111111111111111111111"], "recent_blockhash": "2hefYRfVcesrNJrzCPp9ZJRPzEP9ixErQCWcYk5xJUnu"}]}], "meta": [{"fee": 5000, "pre_balances": [13000000000, 0, 1], "post_balances": [12989995000, 10000000, 1], "inner_instructions_none": false, "log_messages": ["Program 11111111111111111111111111111111 invoke [1]", "Program 11111111111111111111111111111111 success"], "log_messages_none": false, "return_data_none": true, "compute_units_consumed": 150}], "index": 22, "is_vote": false}], "slot": 399851707, "network": "SOLANA_DEVNET"}}'

    received_signature = 'c2cd8d9cee78213ee86b4ce4f07002abb30e2c9e407b9ffa30609f9f72e1436c'
    signing_key = 'whsec_Cr8A7jCSHJGPjE2A92l7gmbf'

    print('🎯 Final Signature Verification Test')
    print('=' * 40)
    print()
    
    # Simulate the updated verification logic
    try:
        # Parse the request body and re-serialize as compact JSON
        parsed_json = json.loads(request_body)
        compact_json = json.dumps(parsed_json, separators=(',', ':'))
        
        # Calculate signature using compact JSON
        digest = hmac.new(
            bytes(signing_key, 'utf-8'),
            msg=bytes(compact_json, 'utf-8'),
            digestmod=hashlib.sha256
        ).hexdigest()
        
        is_valid = digest == received_signature
        
        print(f'Signing Key: {signing_key}')
        print(f'Original Body Length: {len(request_body)} characters')
        print(f'Compact JSON Length: {len(compact_json)} characters')
        print(f'Calculated Signature: {digest}')
        print(f'Expected Signature: {received_signature}')
        print(f'Match: {is_valid}')
        print()
        
        if is_valid:
            print('🎉 SUCCESS! Signature verification works correctly!')
            print('✅ The updated implementation will work with real Alchemy webhooks.')
            print('✅ The webhook verification is now ready for production.')
        else:
            print('❌ Signature verification still failed.')
            print('💡 This might indicate a different issue.')
            
    except Exception as e:
        print(f'❌ Error during signature verification: {e}')

if __name__ == '__main__':
    test_final_signature()
