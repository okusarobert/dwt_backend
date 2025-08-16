#!/usr/bin/env python3
"""
Migration script to handle Solana private key format changes.
This script checks for existing Solana addresses with 32-byte private keys
and provides information about them.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.crypto.clients.sol import SOLWallet, SolanaConfig
from shared.logger import setup_logging
from db.connection import session
from db.wallet import CryptoAddress
from decouple import config
import base58

def check_solana_addresses():
    """Check existing Solana addresses for private key format issues"""
    try:
        # Get all SOL addresses
        sol_addresses = session.query(CryptoAddress).filter_by(
            currency_code="SOL",
            is_active=True
        ).all()
        
        print(f"Found {len(sol_addresses)} active SOL addresses")
        
        issues_found = []
        valid_addresses = []
        
        for addr in sol_addresses:
            try:
                # Decode the private key
                private_key_bytes = base58.b58decode(addr.private_key)
                
                if len(private_key_bytes) == 32:
                    issues_found.append({
                        "address": addr.address,
                        "id": addr.id,
                        "issue": "32-byte private key (old format)",
                        "private_key_length": len(private_key_bytes)
                    })
                elif len(private_key_bytes) == 64:
                    valid_addresses.append({
                        "address": addr.address,
                        "id": addr.id,
                        "format": "64-byte keypair (correct format)",
                        "private_key_length": len(private_key_bytes)
                    })
                else:
                    issues_found.append({
                        "address": addr.address,
                        "id": addr.id,
                        "issue": f"Unexpected length: {len(private_key_bytes)} bytes",
                        "private_key_length": len(private_key_bytes)
                    })
                    
            except Exception as e:
                issues_found.append({
                    "address": addr.address,
                    "id": addr.id,
                    "issue": f"Decoding error: {str(e)}",
                    "private_key_length": "unknown"
                })
        
        print(f"\n✅ Valid addresses ({len(valid_addresses)}):")
        for addr in valid_addresses:
            print(f"  - {addr['address']} (ID: {addr['id']}) - {addr['format']}")
        
        print(f"\n⚠️  Issues found ({len(issues_found)}):")
        for addr in issues_found:
            print(f"  - {addr['address']} (ID: {addr['id']}) - {addr['issue']}")
        
        if issues_found:
            print(f"\n❌ Found {len(issues_found)} addresses with issues.")
            print("These addresses will need to be regenerated with the new 64-byte format.")
            print("You can either:")
            print("1. Delete these addresses and create new ones")
            print("2. Manually update the private keys (not recommended for security)")
            return False
        else:
            print(f"\n✅ All {len(valid_addresses)} addresses are using the correct format!")
            return True
            
    except Exception as e:
        print(f"❌ Error checking addresses: {e}")
        return False

def test_new_address_creation():
    """Test creating a new address with the correct format"""
    try:
        api_key = config('ALCHEMY_API_KEY', default='test_key')
        sol_config = SolanaConfig.testnet(api_key)
        wallet = SOLWallet(user_id=999, sol_config=sol_config, session=session, logger=setup_logging())
        
        print("\n🧪 Testing new address creation...")
        
        # Create a test account first
        from db.wallet import Account, AccountType
        test_account = Account(
            user_id=999,
            balance=0,
            locked_amount=0,
            currency="SOL",
            account_type=AccountType.CRYPTO,
            account_number="TEST999",
            label="Test SOL Account"
        )
        session.add(test_account)
        session.flush()
        
        wallet.account_id = test_account.id
        wallet.symbol = "SOL"
        wallet.label = "Test SOL"
        
        # Generate new address
        result = wallet.generate_new_address()
        
        if result:
            print(f"✅ New address created: {result['address']}")
            
            # Check the private key format
            crypto_addr = session.query(CryptoAddress).filter_by(
                address=result['address'],
                currency_code="SOL"
            ).first()
            
            if crypto_addr:
                private_key_bytes = base58.b58decode(crypto_addr.private_key)
                print(f"Private key length: {len(private_key_bytes)} bytes")
                
                if len(private_key_bytes) == 64:
                    print("✅ Private key is in correct 64-byte format")
                else:
                    print(f"❌ Private key is in wrong format: {len(private_key_bytes)} bytes")
            
            # Clean up test account
            session.delete(test_account)
            session.commit()
            
        else:
            print("❌ Failed to create new address")
            
    except Exception as e:
        print(f"❌ Error testing address creation: {e}")

if __name__ == "__main__":
    print("🔍 Checking Solana address private key formats...")
    
    # Check existing addresses
    all_valid = check_solana_addresses()
    
    # Test new address creation
    test_new_address_creation()
    
    if all_valid:
        print("\n✅ All addresses are using the correct format!")
    else:
        print("\n⚠️  Some addresses need to be updated to the new format.")
        print("New addresses will use the correct 64-byte format automatically.")
