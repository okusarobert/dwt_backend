#!/usr/bin/env python3
"""
Check transaction status using our ETH client
"""

import sys
sys.path.append('/app')

from shared.crypto.clients.eth import ETHWallet, EthereumConfig
from db.connection import get_session
import os

def check_transaction():
    """Check the transaction status"""
    
    tx_hash = "0x37cc5af0fa25e1fc834992ac2cf04f57780faf41e2fe3cf58826f447182b38ed"
    
    print(f"🔍 Checking transaction: {tx_hash}")
    
    try:
        # Get session
        session = get_session()
        
        # Get API key
        api_key = os.getenv('ALCHEMY_API_KEY', '')
        if not api_key:
            print("❌ ALCHEMY_API_KEY not set")
            return
        
        # Create ETH client
        eth_config = EthereumConfig.testnet(api_key)
        eth_wallet = ETHWallet(
            user_id=14,  # Test user
            eth_config=eth_config,
            session=session
        )
        
        # Check transaction status
        print("📡 Checking transaction status...")
        status = eth_wallet.get_transaction_status(tx_hash)
        
        if status:
            print(f"✅ Transaction Status: {status.get('status')}")
            print(f"   Gas Used: {status.get('gas_used', 'N/A')}")
            print(f"   Block Number: {status.get('block_number', 'N/A')}")
            
            if status.get('receipt'):
                receipt = status['receipt']
                print(f"   Status Code: {receipt.get('status')}")
                print(f"   Cumulative Gas Used: {receipt.get('cumulativeGasUsed')}")
        else:
            print("❌ Transaction not found or pending")
            
        # Also check the raw transaction
        print("\n📡 Checking raw transaction...")
        tx = eth_wallet.get_transaction(tx_hash)
        
        if tx:
            print(f"✅ Transaction found!")
            print(f"   From: {tx.get('from')}")
            print(f"   To: {tx.get('to')}")
            print(f"   Value: {tx.get('value')} wei")
            print(f"   Gas Price: {tx.get('gasPrice')} wei")
            print(f"   Nonce: {tx.get('nonce')}")
            print(f"   Block Number: {tx.get('blockNumber', 'Pending')}")
        else:
            print("❌ Raw transaction not found")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_transaction() 