#!/usr/bin/env python3
"""
Solana Client using Alchemy API
Supports address balance queries and real-time block monitoring
"""

import os
import json
import time
import threading
import socket
import ssl
import base64
import hashlib
import struct
import requests
from datetime import datetime
from typing import Dict, Optional, List

# Configure logging
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SolanaClient:
    """Solana client using Alchemy API"""
    
    def __init__(self, api_key: str = None, network: str = "mainnet"):
        """
        Initialize Solana client
        
        Args:
            api_key: Alchemy API key
            network: Network to connect to (mainnet, devnet)
        """
        self.api_key = api_key or os.getenv('ALCHEMY_SOLANA_API_KEY')
        self.network = network
        
        if not self.api_key:
            logger.error("❌ No Alchemy Solana API key provided")
            raise ValueError("API key is required")
        
        # Set up API URLs
        if network == "mainnet":
            self.http_url = f"https://solana-mainnet.g.alchemy.com/v2/{self.api_key}"
            self.ws_url = f"wss://solana-mainnet.g.alchemy.com/v2/{self.api_key}"
        elif network == "devnet":
            self.http_url = f"https://solana-devnet.g.alchemy.com/v2/{self.api_key}"
            self.ws_url = f"wss://solana-devnet.g.alchemy.com/v2/{self.api_key}"
        else:
            raise ValueError(f"Unsupported network: {network}")
        
        # WebSocket properties
        self.sock = None
        self.is_connected = False
        self.is_running = False
        self.block_count = 0
        self.start_time = None
        
        logger.info(f"🔧 Initialized Solana client for {network}")
        logger.info(f"📡 HTTP API URL: {self.http_url}")
        logger.info(f"🔌 WebSocket URL: {self.ws_url}")
    
    def make_request(self, method: str, params: list = None) -> Optional[Dict]:
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
            return None
    
    def get_latest_slot(self) -> Optional[int]:
        """Get the latest slot number"""
        response = self.make_request("getSlot")
        if response and 'result' in response:
            return response['result']
        return None
    
    def get_balance(self, address: str) -> Optional[Dict]:
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
                return None
                
        except Exception as e:
            logger.error(f"❌ Error getting balance for {address}: {e}")
            return None
    
    def get_account_info(self, address: str) -> Optional[Dict]:
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
                        "data": account_info.get('data'),
                        "network": self.network
                    }
                    
                    logger.info(f"✅ Account info retrieved for {address}")
                    return result
                else:
                    logger.warning(f"⚠️ Account {address} not found or has no data")
                    return None
            else:
                logger.error(f"❌ Failed to get account info for {address}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error getting account info for {address}: {e}")
            return None
    
    def get_token_accounts(self, address: str) -> Optional[List[Dict]]:
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
                        "delegate": info.get('delegate'),
                        "state": info.get('state'),
                        "is_native": info.get('isNative')
                    })
                
                logger.info(f"✅ Found {len(parsed_accounts)} token accounts for {address}")
                return parsed_accounts
            else:
                logger.error(f"❌ Failed to get token accounts for {address}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error getting token accounts for {address}: {e}")
            return None
    
    def get_recent_blocks(self, limit: int = 10) -> Optional[List[Dict]]:
        """Get recent blocks"""
        try:
            logger.info(f"📦 Getting {limit} recent blocks")
            
            # Get recent block hashes
            response = self.make_request("getRecentBlockhash")
            if not response or 'result' not in response:
                logger.error("❌ Failed to get recent blockhash")
                return None
            
            # Get recent slots
            slots_response = self.make_request("getRecentPerformanceSamples", [limit])
            if not slots_response or 'result' not in slots_response:
                logger.error("❌ Failed to get recent performance samples")
                return None
            
            slots = slots_response['result']
            blocks = []
            
            for slot_data in slots:
                block_info = {
                    "slot": slot_data.get('slot'),
                    "num_transactions": slot_data.get('numTransactions'),
                    "sample_period_secs": slot_data.get('samplePeriodSecs'),
                    "network": self.network
                }
                blocks.append(block_info)
            
            logger.info(f"✅ Retrieved {len(blocks)} recent blocks")
            return blocks
                
        except Exception as e:
            logger.error(f"❌ Error getting recent blocks: {e}")
            return None

class SolanaWebSocketClient:
    """Solana client using HTTP polling for real-time monitoring"""
    
    def __init__(self, api_key: str = None, network: str = "mainnet"):
        """Initialize Solana client"""
        self.api_key = api_key or os.getenv('ALCHEMY_SOLANA_API_KEY')
        self.network = network
        self.is_running = False
        self.block_count = 0
        self.start_time = None
        self.last_slot = None
        
        # Set up API URL
        if network == "mainnet":
            self.http_url = f"https://solana-mainnet.g.alchemy.com/v2/{self.api_key}"
        else:
            self.http_url = f"https://solana-devnet.g.alchemy.com/v2/{self.api_key}"
        
        logger.info(f"🔧 Initialized Solana HTTP polling client for {network}")
        logger.info(f"📡 HTTP API URL: {self.http_url}")
    
    def get_latest_slot(self):
        """Get the latest slot number"""
        try:
            response = requests.post(
                self.http_url,
                json={
                    "jsonrpc": "2.0",
                    "method": "getSlot",
                    "params": [],
                    "id": 1
                },
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            if "result" in data:
                return data["result"]
            else:
                logger.error(f"❌ Failed to get latest slot: {data}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error getting latest slot: {e}")
            return None
    
    def get_slot_info(self, slot):
        """Get detailed information about a specific slot"""
        try:
            response = requests.post(
                self.http_url,
                json={
                    "jsonrpc": "2.0",
                    "method": "getBlock",
                    "params": [slot, {"encoding": "json", "maxSupportedTransactionVersion": 0}],
                    "id": 1
                },
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            if "result" in data and data["result"]:
                return data["result"]
            else:
                return None
                
        except Exception as e:
            logger.error(f"❌ Error getting slot info for {slot}: {e}")
            return None
    
    def start_monitoring(self, duration: int = 120):
        """Start monitoring for new slots using HTTP polling"""
        logger.info("🚀 Starting real-time Solana slot monitoring...")
        
        print("=" * 80)
        print("🔧 REAL-TIME SOLANA SLOT MONITOR")
        print("=" * 80)
        print(f"📡 Network: {self.network}")
        print(f"🌐 HTTP API: {self.http_url}")
        print(f"⏰ Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"⏱️  Duration: {duration} seconds")
        print("=" * 80)
        print("⏳ Polling for new slots...")
        print("=" * 80)
        
        self.is_running = True
        self.start_time = time.time()
        self.last_slot = self.get_latest_slot()
        
        if self.last_slot:
            logger.info(f"📊 Starting from slot: {self.last_slot}")
        
        try:
            while self.is_running and (time.time() - self.start_time) < duration:
                current_slot = self.get_latest_slot()
                
                if current_slot and current_slot != self.last_slot:
                    # New slot detected
                    self.block_count += 1
                    self._handle_new_slot(current_slot)
                    self.last_slot = current_slot
                
                # Poll every 400ms (Solana's approximate block time)
                time.sleep(0.4)
                
        except KeyboardInterrupt:
            print("\n⏹️  Monitoring stopped by user")
        except Exception as e:
            logger.error(f"❌ Error during monitoring: {e}")
        finally:
            self.stop_monitoring()
    
    def _handle_new_slot(self, slot):
        """Handle new slot data"""
        try:
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Calculate slots per minute
            elapsed_time = time.time() - self.start_time
            slots_per_minute = (self.block_count / elapsed_time) * 60 if elapsed_time > 0 else 0
            
            print("=" * 80)
            print(f"🆕 NEW SOLANA SLOT #{slot}")
            print("=" * 80)
            print(f"📅 Time: {current_time}")
            print(f"📈 Total Slots Received: {self.block_count}")
            print(f"⏱️  Slots per minute: {slots_per_minute:.2f}")
            print("=" * 80)
            
            # Get detailed slot info (optional, can be slow)
            # slot_info = self.get_slot_info(slot)
            # if slot_info:
            #     tx_count = len(slot_info.get("transactions", []))
            #     print(f"📦 Transactions in slot: {tx_count}")
            
        except Exception as e:
            logger.error(f"❌ Error handling new slot {slot}: {e}")
    
    def stop_monitoring(self):
        """Stop monitoring"""
        self.is_running = False
        
        if self.start_time:
            total_time = time.time() - self.start_time
            avg_slots_per_minute = (self.block_count / total_time) * 60 if total_time > 0 else 0
            
            print("=" * 80)
            print("📊 MONITORING STATISTICS")
            print("=" * 80)
            print(f"📈 Total Slots Received: {self.block_count}")
            print(f"⏱️  Total Time: {total_time:.1f} seconds")
            print(f"📊 Average Slots per Minute: {avg_slots_per_minute:.2f}")
            print("=" * 80)
        
        logger.info("🔌 HTTP polling stopped")

def test_solana_api():
    """Test Solana API functionality"""
    print("🔧 Solana API Test")
    print("📡 Using Alchemy Solana API")
    print("=" * 50)
    
    # Initialize client
    client = SolanaClient(
        network="mainnet",
        api_key="EbcNdRQag_4Ep75VtLuPLV3-MMfLKMvH"  # Using the same API key for testing
    )
    
    # Test 1: Get latest slot
    print("\n🔍 Test 1: Getting latest slot")
    latest_slot = client.get_latest_slot()
    if latest_slot:
        print(f"✅ Latest slot: {latest_slot}")
    else:
        print("❌ Failed to get latest slot")
    
    # Test 2: Get balance for a known address (e.g., Solana Foundation)
    print("\n🔍 Test 2: Getting balance for Solana Foundation")
    foundation_address = "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM"
    balance = client.get_balance(foundation_address)
    if balance:
        print(f"✅ Balance: {balance['sol_balance']:.9f} SOL")
    else:
        print("❌ Failed to get balance")
    
    # Test 3: Get account info
    print("\n🔍 Test 3: Getting account info")
    account_info = client.get_account_info(foundation_address)
    if account_info:
        print(f"✅ Account owner: {account_info['owner']}")
        print(f"✅ Executable: {account_info['executable']}")
    else:
        print("❌ Failed to get account info")
    
    # Test 4: Get token accounts
    print("\n🔍 Test 4: Getting token accounts")
    token_accounts = client.get_token_accounts(foundation_address)
    if token_accounts:
        print(f"✅ Found {len(token_accounts)} token accounts")
        for i, account in enumerate(token_accounts[:3]):  # Show first 3
            print(f"   Token {i+1}: {account['mint']}")
    else:
        print("❌ Failed to get token accounts")
    
    # Test 5: Get recent blocks
    print("\n🔍 Test 5: Getting recent blocks")
    recent_blocks = client.get_recent_blocks(5)
    if recent_blocks:
        print(f"✅ Retrieved {len(recent_blocks)} recent blocks")
        for block in recent_blocks:
            print(f"   Slot {block['slot']}: {block['num_transactions']} transactions")
    else:
        print("❌ Failed to get recent blocks")

def main():
    """Main function"""
    print("🔧 Solana Client")
    print("📡 Using Alchemy Solana API")
    print("=" * 50)
    
    # Check if API key is set
    api_key = os.getenv('ALCHEMY_SOLANA_API_KEY')
    if not api_key:
        print("⚠️  No ALCHEMY_SOLANA_API_KEY environment variable found.")
        print("📝 Get your free API key at: https://www.alchemy.com/")
        print("💡 Using provided API key for testing.")
        print()
    
    # Test HTTP API functionality
    test_solana_api()
    
    print("\n" + "="*80)
    print("🚀 Starting real-time block monitoring...")
    print("="*80)
    
    # Initialize WebSocket client for real-time monitoring
    ws_client = SolanaWebSocketClient(
        network="mainnet",
        api_key="EbcNdRQag_4Ep75VtLuPLV3-MMfLKMvH"
    )
    
    # Start real-time monitoring (run for 2 minutes)
    ws_client.start_monitoring(duration=120)

if __name__ == "__main__":
    main() 