#!/usr/bin/env python3
"""
Solana Test Script
Tests address balances and real-time block monitoring
"""

import os
import json
import time
import requests
from datetime import datetime

# Configure logging
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SolanaTestClient:
    """Solana test client using Alchemy API"""
    
    def __init__(self, api_key: str = None, network: str = "mainnet"):
        """Initialize Solana test client"""
        self.api_key = api_key or os.getenv('ALCHEMY_SOLANA_API_KEY')
        self.network = network
        
        if not self.api_key:
            logger.error("❌ No Alchemy Solana API key provided")
            raise ValueError("API key is required")
        
        # Set up API URL
        if network == "mainnet":
            self.http_url = f"https://solana-mainnet.g.alchemy.com/v2/{self.api_key}"
        elif network == "devnet":
            self.http_url = f"https://solana-devnet.g.alchemy.com/v2/{self.api_key}"
        else:
            raise ValueError(f"Unsupported network: {network}")
        
        logger.info(f"🔧 Initialized Solana test client for {network}")
        logger.info(f"📡 HTTP API URL: {self.http_url}")
    
    def make_request(self, method: str, params: list = None) -> dict:
        """Make an RPC request to Solana API"""
        headers = {'Content-Type': 'application/json'}
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params if params is not None else [],
            "id": 1
        }
        try:
            response = requests.post(self.http_url, headers=headers, data=json.dumps(payload), timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Request failed: {e}")
            return {"error": str(e)}
    
    def get_latest_slot(self) -> int:
        """Get the latest slot number"""
        response = self.make_request("getSlot")
        if response and 'result' in response:
            return response['result']
        return None
    
    def get_balance(self, address: str) -> dict:
        """Get balance for a specific address"""
        try:
            logger.info(f"💰 Getting balance for {address}")
            
            response = self.make_request("getBalance", [address])
            if response and 'result' in response:
                balance_data = response['result']
                
                # Convert lamports to SOL (1 SOL = 1,000,000,000 lamports)
                lamports = balance_data.get('value', 0)
                sol_balance = lamports / 1_000_000_000
                
                result = {
                    "address": address,
                    "lamports": lamports,
                    "sol_balance": sol_balance,
                    "confirmed": True,
                    "network": self.network
                }
                
                logger.info(f"✅ Balance for {address}: {sol_balance:.9f} SOL ({lamports} lamports)")
                return result
            else:
                logger.error(f"❌ Failed to get balance for {address}")
                return {"error": "Failed to get balance"}
                
        except Exception as e:
            logger.error(f"❌ Error getting balance for {address}: {e}")
            return {"error": str(e)}
    
    def get_account_info(self, address: str) -> dict:
        """Get account information"""
        try:
            logger.info(f"📋 Getting account info for {address}")
            
            response = self.make_request("getAccountInfo", [address, {"encoding": "jsonParsed"}])
            if response and 'result' in response:
                account_data = response['result']
                
                if account_data and 'value' in account_data:
                    account_info = account_data['value']
                    
                    result = {
                        "address": address,
                        "lamports": account_info.get('lamports', 0),
                        "sol_balance": account_info.get('lamports', 0) / 1_000_000_000,
                        "owner": account_info.get('owner'),
                        "executable": account_info.get('executable', False),
                        "rent_epoch": account_info.get('rentEpoch'),
                        "network": self.network
                    }
                    
                    logger.info(f"✅ Account info retrieved for {address}")
                    return result
                else:
                    logger.warning(f"⚠️ Account {address} not found or has no data")
                    return {"error": "Account not found"}
            else:
                logger.error(f"❌ Failed to get account info for {address}")
                return {"error": "Failed to get account info"}
                
        except Exception as e:
            logger.error(f"❌ Error getting account info for {address}: {e}")
            return {"error": str(e)}
    
    def get_token_accounts(self, address: str) -> dict:
        """Get token accounts for an address"""
        try:
            logger.info(f"🪙 Getting token accounts for {address}")
            
            response = self.make_request("getTokenAccountsByOwner", [
                address,
                {"programId": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"},
                {"encoding": "jsonParsed"}
            ])
            
            if response and 'result' in response:
                token_accounts = response['result'].get('value', [])
                
                parsed_accounts = []
                for account in token_accounts:
                    account_data = account.get('account', {}).get('data', {}).get('parsed', {})
                    info = account_data.get('info', {})
                    
                    parsed_accounts.append({
                        "pubkey": account.get('pubkey'),
                        "mint": info.get('mint'),
                        "owner": info.get('owner'),
                        "token_amount": info.get('tokenAmount', {}),
                        "state": info.get('state'),
                        "is_native": info.get('isNative')
                    })
                
                logger.info(f"✅ Found {len(parsed_accounts)} token accounts for {address}")
                return {
                    "address": address,
                    "token_accounts": parsed_accounts,
                    "count": len(parsed_accounts),
                    "network": self.network
                }
            else:
                logger.error(f"❌ Failed to get token accounts for {address}")
                return {"error": "Failed to get token accounts"}
                
        except Exception as e:
            logger.error(f"❌ Error getting token accounts for {address}: {e}")
            return {"error": str(e)}

def test_solana_addresses():
    """Test multiple Solana addresses"""
    print("🔧 Solana Address Balance Test")
    print("📡 Using Alchemy Solana API")
    print("=" * 60)
    
    # Initialize client
    client = SolanaTestClient(
        network="devnet",
        api_key="EbcNdRQag_4Ep75VtLuPLV3-MMfLKMvH"
    )
    
    # Test addresses (known Solana addresses)
    test_addresses = [
        {
            "name": "Solana Foundation",
            "address": "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM"
        },
        {
            "name": "Solana Labs",
            "address": "8FE27B99A5A9E6C8E2VzE8NHB67HkD5W1Z1E2X3Y4Z5A6B"
        },
        {
            "name": "USDC Treasury",
            "address": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
        },
        {
            "name": "Raydium Protocol",
            "address": "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8"
        },
        {
            "name": "Serum DEX",
            "address": "9xQeWvG816bUx9EPjHmaT23yvVM2ZWbrrpZb9PusVFin"
        }
    ]
    
    # Get latest slot
    print("\n🔍 Getting latest slot...")
    latest_slot = client.get_latest_slot()
    if latest_slot:
        print(f"✅ Latest slot: {latest_slot:,}")
    else:
        print("❌ Failed to get latest slot")
    
    # Test each address
    print("\n" + "="*80)
    print("💰 ADDRESS BALANCE TEST RESULTS")
    print("="*80)
    
    for i, test_addr in enumerate(test_addresses, 1):
        print(f"\n🔍 Test {i}: {test_addr['name']}")
        print(f"📍 Address: {test_addr['address']}")
        
        # Get balance
        balance = client.get_balance(test_addr['address'])
        if 'error' not in balance:
            print(f"✅ Balance: {balance['sol_balance']:.9f} SOL")
            print(f"💰 Lamports: {balance['lamports']:,}")
        else:
            print(f"❌ Balance error: {balance['error']}")
        
        # Get account info
        account_info = client.get_account_info(test_addr['address'])
        if 'error' not in account_info:
            print(f"📋 Owner: {account_info['owner']}")
            print(f"🔧 Executable: {account_info['executable']}")
        else:
            print(f"❌ Account info error: {account_info['error']}")
        
        # Get token accounts (only for first 2 addresses to avoid rate limits)
        if i <= 2:
            token_accounts = client.get_token_accounts(test_addr['address'])
            if 'error' not in token_accounts:
                print(f"🪙 Token accounts: {token_accounts['count']}")
                if token_accounts['count'] > 0:
                    print(f"   Sample tokens:")
                    for j, token in enumerate(token_accounts['token_accounts'][:3]):
                        mint = token.get('mint', 'Unknown')
                        amount = token.get('token_amount', {}).get('uiAmount', 0)
                        print(f"     {j+1}. {mint[:8]}... ({amount})")
            else:
                print(f"❌ Token accounts error: {token_accounts['error']}")
        
        print("-" * 60)
    
    print("\n" + "="*80)
    print("✅ SOLANA ADDRESS TEST COMPLETED")
    print("="*80)

def main():
    """Main function"""
    print("🔧 Solana Address Balance Test")
    print("📡 Using Alchemy Solana API")
    print("=" * 60)
    
    # Check if API key is set
    api_key = os.getenv('ALCHEMY_SOLANA_API_KEY')
    if not api_key:
        print("⚠️  No ALCHEMY_SOLANA_API_KEY environment variable found.")
        print("📝 Get your free API key at: https://www.alchemy.com/")
        print("💡 Using provided API key for testing.")
        print()
    
    # Test Solana addresses
    test_solana_addresses()

if __name__ == "__main__":
    main() 