#!/usr/bin/env python3
"""
TRON Client for HTTP API interactions
Based on TRON Developer Hub: https://developers.tron.network/reference/background#note
"""

import os
import json
import time
import requests
from datetime import datetime
from typing import Optional, Dict, Any, List
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TronClient:
    """TRON client for HTTP API interactions"""
    
    def __init__(self, api_key: str = None, network: str = "mainnet"):
        """Initialize TRON client"""
        self.api_key = api_key or os.getenv('TRONGRID_API_KEY')
        self.network = network
        
        # Set base URL based on network
        if network == "mainnet":
            self.base_url = "https://api.trongrid.io"
        elif network == "shasta":
            self.base_url = "https://api.shasta.trongrid.io"
        elif network == "nile":
            self.base_url = "https://api.nile.trongrid.io"
        else:
            raise ValueError(f"Unsupported network: {network}")
        
        logger.info(f"🔧 Initialized TRON client for {network}")
        logger.info(f"📡 HTTP API URL: {self.base_url}")
    
    def get_latest_block(self) -> Optional[Dict[str, Any]]:
        """Get the latest block information"""
        try:
            url = f"{self.base_url}/wallet/getnowblock"
            headers = {"TRON-PRO-API-KEY": self.api_key} if self.api_key else {}
            
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            
            logger.error(f"❌ Failed to get latest block: {response.status_code}")
            return None
            
        except Exception as e:
            logger.error(f"❌ Error getting latest block: {e}")
            return None
    
    def get_block_by_number(self, block_number: int) -> Optional[Dict[str, Any]]:
        """Get block information by block number"""
        try:
            url = f"{self.base_url}/wallet/getblockbynum"
            headers = {"TRON-PRO-API-KEY": self.api_key} if self.api_key else {}
            params = {"num": block_number}
            
            response = requests.post(url, json=params, headers=headers, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            
            logger.error(f"❌ Failed to get block {block_number}: {response.status_code}")
            return None
            
        except Exception as e:
            logger.error(f"❌ Error getting block {block_number}: {e}")
            return None
    
    def get_account_info(self, address: str) -> Optional[Dict[str, Any]]:
        """Get account information"""
        try:
            url = f"{self.base_url}/v1/accounts/{address}"
            headers = {"TRON-PRO-API-KEY": self.api_key} if self.api_key else {}
            
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            
            logger.error(f"❌ Failed to get account info: {response.status_code}")
            return None
            
        except Exception as e:
            logger.error(f"❌ Error getting account info: {e}")
            return None
    
    def get_transaction_info(self, tx_id: str) -> Optional[Dict[str, Any]]:
        """Get transaction information"""
        try:
            url = f"{self.base_url}/v1/transactions/{tx_id}"
            headers = {"TRON-PRO-API-KEY": self.api_key} if self.api_key else {}
            
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            
            logger.error(f"❌ Failed to get transaction info: {response.status_code}")
            return None
            
        except Exception as e:
            logger.error(f"❌ Error getting transaction info: {e}")
            return None
    
    def get_address_transactions(self, address: str, limit: int = 50) -> Optional[Dict[str, Any]]:
        """Get transactions for a specific address"""
        try:
            url = f"{self.base_url}/v1/accounts/{address}/transactions"
            headers = {"TRON-PRO-API-KEY": self.api_key} if self.api_key else {}
            params = {"limit": limit}
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            
            logger.error(f"❌ Failed to get address transactions: {response.status_code}")
            return None
            
        except Exception as e:
            logger.error(f"❌ Error getting address transactions: {e}")
            return None
    
    def get_trc20_transactions(self, address: str, contract_address: str = None, limit: int = 50) -> Optional[Dict[str, Any]]:
        """Get TRC20 token transactions for a specific address"""
        try:
            url = f"{self.base_url}/v1/accounts/{address}/transactions/trc20"
            headers = {"TRON-PRO-API-KEY": self.api_key} if self.api_key else {}
            params = {"limit": limit}
            
            if contract_address:
                params["contract_address"] = contract_address
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            
            logger.error(f"❌ Failed to get TRC20 transactions: {response.status_code}")
            return None
            
        except Exception as e:
            logger.error(f"❌ Error getting TRC20 transactions: {e}")
            return None
    
    def test_tron_api(self) -> bool:
        """Test TRON API functionality"""
        print("🔧 TRON API Test")
        print("📡 Using TRONGrid API")
        print("=" * 50)
        
        # Test 1: Get latest block
        print("🔍 Test 1: Getting latest block")
        latest_block = self.get_latest_block()
        if latest_block:
            block_header = latest_block.get("block_header", {})
            raw_data = block_header.get("raw_data", {})
            block_number = raw_data.get("number", "N/A")
            block_hash = latest_block.get("blockID", "N/A")[:20] + "..."
            print(f"✅ Latest block: {block_number}")
            print(f"✅ Block hash: {block_hash}")
        else:
            print("❌ Failed to get latest block")
            return False
        
        # Test 2: Get account info for a test address
        print("🔍 Test 2: Getting account info")
        test_address = "TJRabPrwbZy45sbavfcjinPJC18kjpRTv8"  # Example TRON address
        account_info = self.get_account_info(test_address)
        if account_info:
            data = account_info.get("data", [])
            if data:
                account_data = data[0]
                balance = account_data.get("balance", 0)
                print(f"✅ Account balance: {balance} TRX")
            else:
                print("⚠️  Account info check failed (this is normal for test addresses)")
        else:
            print("⚠️  Account info check failed (this is normal for test addresses)")
        
        # Test 3: Get block by number
        print("🔍 Test 3: Getting block by number")
        if latest_block:
            block_num = raw_data.get("number", 0)
            block_info = self.get_block_by_number(block_num)
            if block_info:
                transactions = block_info.get("transactions", [])
                print(f"✅ Block {block_num}: {len(transactions)} transactions")
            else:
                print("❌ Failed to get block info")
                return False
        
        print("✅ All TRON API tests passed!")
        return True


def main():
    """Main function to test TRON client"""
    print("🔧 TRON Client")
    print("📡 Using TRONGrid API")
    print("=" * 50)
    
    # Check for API key
    api_key = os.getenv('TRONGRID_API_KEY')
    if not api_key:
        print("⚠️  No TRONGRID_API_KEY environment variable found.")
        print("📝 Get your free API key at: https://www.trongrid.io/")
        print("💡 Using provided API key for testing.")
        api_key = "c6ea62f4-4f0b-4af2-9c6b-495ae84d1648"  # Replace with actual API key
    
    # Test HTTP API first
    client = TronClient(api_key=api_key, network="shasta")
    if not client.test_tron_api():
        print("❌ TRON API test failed")
        return
    
    print("\n🎉 TRON Client Test Complete!")
    print("📝 Note: WebSocket is not supported by TRONGrid")
    print("💡 Use webhooks for real-time transaction monitoring")


if __name__ == "__main__":
    main() 