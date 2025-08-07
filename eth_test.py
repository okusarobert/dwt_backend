#!/usr/bin/env python3
"""
Ethereum API Test Script using Alchemy
Tests various Ethereum blockchain operations via Alchemy's API
Includes WebSocket support for real-time data
"""

import os
import json
import requests
import time
import threading
import ssl
import socket
from typing import Dict, Optional

# Configure logging
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AlchemyEthereumClient:
    """Ethereum client using Alchemy API"""
    
    def __init__(self, api_key: str = None, network: str = "mainnet"):
        """
        Initialize Alchemy client
        
        Args:
            api_key: Alchemy API key (optional, can be set via env var)
            network: Network to connect to (mainnet, sepolia, holesky)
        """
        self.api_key = api_key or os.getenv('ALCHEMY_API_KEY')
        self.network = network
        
        if not self.api_key:
            logger.warning("⚠️ No Alchemy API key provided. Set ALCHEMY_API_KEY environment variable or pass api_key parameter.")
            logger.info("📝 Get your free API key at: https://www.alchemy.com/")
            self.api_key = "demo"  # Use demo key for testing
        
        # Set up API URLs based on network
        if network == "mainnet":
            self.base_url = f"https://eth-mainnet.g.alchemy.com/v2/{self.api_key}"
            self.ws_url = f"wss://eth-mainnet.g.alchemy.com/v2/{self.api_key}"
        elif network == "sepolia":
            self.base_url = f"https://eth-sepolia.g.alchemy.com/v2/{self.api_key}"
            self.ws_url = f"wss://eth-sepolia.g.alchemy.com/v2/{self.api_key}"
        elif network == "holesky":
            self.base_url = f"https://eth-holesky.g.alchemy.com/v2/{self.api_key}"
            self.ws_url = f"wss://eth-holesky.g.alchemy.com/v2/{self.api_key}"
        else:
            raise ValueError(f"Unsupported network: {network}")
        
        logger.info(f"🔧 Initialized Alchemy client for {network}")
        logger.info(f"📡 HTTP API URL: {self.base_url}")
        logger.info(f"🔌 WebSocket URL: {self.ws_url}")
    
    def make_request(self, method: str, params: list = None) -> Optional[Dict]:
        """Make a JSON-RPC request to Alchemy API"""
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params or []
        }
        
        try:
            response = requests.post(
                self.base_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Request failed: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Unexpected error: {e}")
            return None
    
    def get_latest_block_number(self) -> Optional[int]:
        """Get the latest block number"""
        logger.info("🔍 Getting latest block number...")
        result = self.make_request("eth_blockNumber")
        
        if result and "result" in result:
            block_number = int(result["result"], 16)
            logger.info(f"✅ Latest block number: {block_number}")
            return block_number
        else:
            logger.error("❌ Failed to get latest block number")
            return None
    
    def get_block_by_number(self, block_number: int, full_transactions: bool = False) -> Optional[Dict]:
        """Get block information by number"""
        logger.info(f"🔍 Getting block {block_number}...")
        result = self.make_request(
            "eth_getBlockByNumber",
            [hex(block_number), full_transactions]
        )
        
        if result and "result" in result and result["result"]:
            block_data = result["result"]
            logger.info(f"✅ Retrieved block {block_number}")
            logger.info(f"   Hash: {block_data.get('hash', 'N/A')}")
            logger.info(f"   Timestamp: {int(block_data.get('timestamp', '0'), 16)}")
            logger.info(f"   Transactions: {len(block_data.get('transactions', []))}")
            return block_data
        else:
            logger.error(f"❌ Failed to get block {block_number}")
            return None
    
    def get_block_by_hash(self, block_hash: str, full_transactions: bool = False) -> Optional[Dict]:
        """Get block information by hash"""
        logger.info(f"🔍 Getting block with hash {block_hash}...")
        result = self.make_request(
            "eth_getBlockByHash",
            [block_hash, full_transactions]
        )
        
        if result and "result" in result and result["result"]:
            block_data = result["result"]
            logger.info(f"✅ Retrieved block by hash")
            logger.info(f"   Number: {int(block_data.get('number', '0'), 16)}")
            logger.info(f"   Timestamp: {int(block_data.get('timestamp', '0'), 16)}")
            return block_data
        else:
            logger.error(f"❌ Failed to get block by hash {block_hash}")
            return None
    
    def get_balance(self, address: str) -> Optional[Dict]:
        """Get account balance"""
        logger.info(f"💰 Getting balance for {address}...")
        result = self.make_request("eth_getBalance", [address, "latest"])
        
        if result and "result" in result:
            balance_wei = int(result["result"], 16)
            balance_eth = balance_wei / (10 ** 18)
            logger.info(f"✅ Balance: {balance_wei} wei ({balance_eth:.6f} ETH)")
            return {
                "address": address,
                "balance_wei": balance_wei,
                "balance_eth": balance_eth
            }
        else:
            logger.error(f"❌ Failed to get balance for {address}")
            return None
    
    def get_gas_price(self) -> Optional[Dict]:
        """Get current gas price"""
        logger.info("⛽ Getting current gas price...")
        result = self.make_request("eth_gasPrice")
        
        if result and "result" in result:
            gas_price_wei = int(result["result"], 16)
            gas_price_gwei = gas_price_wei / (10 ** 9)
            logger.info(f"✅ Gas price: {gas_price_wei} wei ({gas_price_gwei:.2f} gwei)")
            return {
                "gas_price_wei": gas_price_wei,
                "gas_price_gwei": gas_price_gwei
            }
        else:
            logger.error("❌ Failed to get gas price")
            return None
    
    def get_transaction(self, tx_hash: str) -> Optional[Dict]:
        """Get transaction details"""
        logger.info(f"🔍 Getting transaction {tx_hash}...")
        result = self.make_request("eth_getTransactionByHash", [tx_hash])
        
        if result and "result" in result and result["result"]:
            tx_data = result["result"]
            logger.info(f"✅ Retrieved transaction")
            logger.info(f"   From: {tx_data.get('from', 'N/A')}")
            logger.info(f"   To: {tx_data.get('to', 'N/A')}")
            logger.info(f"   Value: {int(tx_data.get('value', '0'), 16)} wei")
            return tx_data
        else:
            logger.error(f"❌ Failed to get transaction {tx_hash}")
            return None
    
    def get_transaction_receipt(self, tx_hash: str) -> Optional[Dict]:
        """Get transaction receipt"""
        logger.info(f"🔍 Getting transaction receipt for {tx_hash}...")
        result = self.make_request("eth_getTransactionReceipt", [tx_hash])
        
        if result and "result" in result and result["result"]:
            receipt = result["result"]
            logger.info(f"✅ Retrieved transaction receipt")
            logger.info(f"   Status: {receipt.get('status', 'N/A')}")
            logger.info(f"   Gas used: {int(receipt.get('gasUsed', '0'), 16)}")
            return receipt
        else:
            logger.error(f"❌ Failed to get transaction receipt for {tx_hash}")
            return None
    
    def get_recent_blocks(self, count: int = 5) -> list:
        """Get information about recent blocks"""
        logger.info(f"📋 Getting {count} recent blocks...")
        blocks = []
        
        latest_block = self.get_latest_block_number()
        if latest_block is None:
            return blocks
        
        for i in range(count):
            block_number = latest_block - i
            if block_number >= 0:
                block_data = self.get_block_by_number(block_number)
                if block_data:
                    # Extract key information
                    block_info = {
                        "number": int(block_data.get("number", "0"), 16),
                        "hash": block_data.get("hash"),
                        "timestamp": int(block_data.get("timestamp", "0"), 16),
                        "transactions_count": len(block_data.get("transactions", [])),
                        "gas_used": int(block_data.get("gasUsed", "0"), 16),
                        "gas_limit": int(block_data.get("gasLimit", "0"), 16)
                    }
                    blocks.append(block_info)
        
        logger.info(f"✅ Retrieved {len(blocks)} recent blocks")
        return blocks
    
    def test_connection(self) -> bool:
        """Test the connection to Alchemy API"""
        logger.info("🧪 Testing Alchemy API connection...")
        
        # Test with a simple request
        result = self.make_request("eth_blockNumber")
        
        if result and "result" in result:
            logger.info("✅ Connection test successful!")
            return True
        else:
            logger.error("❌ Connection test failed!")
            return False

class SimpleWebSocketClient:
    """Simple WebSocket client for testing"""
    
    def __init__(self, api_key: str = None, network: str = "mainnet"):
        """Initialize simple WebSocket client"""
        self.api_key = api_key or os.getenv('ALCHEMY_API_KEY')
        self.network = network
        
        if not self.api_key:
            logger.warning("⚠️ No Alchemy API key provided for WebSocket")
            self.api_key = "demo"
        
        # Set up WebSocket URL
        if network == "mainnet":
            self.ws_url = f"wss://eth-mainnet.g.alchemy.com/v2/{self.api_key}"
        elif network == "sepolia":
            self.ws_url = f"wss://eth-sepolia.g.alchemy.com/v2/{self.api_key}"
        elif network == "holesky":
            self.ws_url = f"wss://eth-holesky.g.alchemy.com/v2/{self.api_key}"
        else:
            raise ValueError(f"Unsupported network: {network}")
        
        logger.info(f"🔌 Initialized Simple WebSocket client for {network}")
        logger.info(f"📡 WebSocket URL: {self.ws_url}")
    
    def test_websocket_connection(self):
        """Test WebSocket connection (simplified)"""
        logger.info("🔌 Testing WebSocket connection...")
        
        try:
            # Parse WebSocket URL
            if self.ws_url.startswith("wss://"):
                host = self.ws_url[6:].split("/")[0]
                path = "/" + "/".join(self.ws_url[6:].split("/")[1:])
                port = 443
                use_ssl = True
            else:
                host = self.ws_url[5:].split("/")[0]
                path = "/" + "/".join(self.ws_url[5:].split("/")[1:])
                port = 80
                use_ssl = False
            
            logger.info(f"🔍 Connecting to {host}:{port}{path}")
            
            # Create socket connection
            if use_ssl:
                context = ssl.create_default_context()
                context.check_hostname = False  # Disable hostname verification for testing
                context.verify_mode = ssl.CERT_NONE  # Disable certificate verification for testing
                sock = context.wrap_socket(socket.socket(socket.AF_INET, socket.SOCK_STREAM), server_hostname=host)
            else:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            
            sock.connect((host, port))
            logger.info("✅ Socket connection established!")
            
            # Send WebSocket handshake
            handshake = (
                f"GET {path} HTTP/1.1\r\n"
                f"Host: {host}\r\n"
                f"Upgrade: websocket\r\n"
                f"Connection: Upgrade\r\n"
                f"Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==\r\n"
                f"Sec-WebSocket-Version: 13\r\n"
                f"\r\n"
            )
            
            sock.send(handshake.encode())
            response = sock.recv(1024).decode()
            
            if "101 Switching Protocols" in response:
                logger.info("✅ WebSocket handshake successful!")
                logger.info("📡 WebSocket connection test passed")
                return True
            else:
                logger.error(f"❌ WebSocket handshake failed: {response}")
                return False
                
        except Exception as e:
            logger.error(f"❌ WebSocket connection test failed: {e}")
            return False
        finally:
            try:
                sock.close()
            except:
                pass

def run_ethereum_tests():
    """Run comprehensive Ethereum API tests"""
    logger.info("🚀 Starting Ethereum API tests with Alchemy...")
    
    # Initialize client (you can change network to "sepolia" for testnet)
    client = AlchemyEthereumClient(
        network="sepolia",  
        api_key="EbcNdRQag_4Ep75VtLuPLV3-MMfLKMvH")
    
    # Test connection
    if not client.test_connection():
        logger.error("❌ Cannot proceed without API connection")
        return
    
    logger.info("\n" + "="*50)
    logger.info("📊 ETHEREUM API TEST RESULTS")
    logger.info("="*50)
    
    # Test 1: Get latest block number
    logger.info("\n🔍 Test 1: Getting latest block number")
    latest_block = client.get_latest_block_number()
    
    if latest_block:
        # Test 2: Get recent blocks
        logger.info("\n🔍 Test 2: Getting recent blocks")
        recent_blocks = client.get_recent_blocks(3)
        
        # Test 3: Get specific block details
        if recent_blocks:
            logger.info("\n🔍 Test 3: Getting specific block details")
            test_block = recent_blocks[0]
            block_details = client.get_block_by_number(test_block["number"])
            
            # Test 4: Get block by hash
            if block_details and "hash" in block_details:
                logger.info("\n🔍 Test 4: Getting block by hash")
                client.get_block_by_hash(block_details["hash"])
    
    # Test 5: Get gas price
    logger.info("\n🔍 Test 5: Getting current gas price")
    gas_price = client.get_gas_price()
    
    # Test 6: Get balance for a known address (Vitalik's address)
    logger.info("\n🔍 Test 6: Getting balance for a known address")
    vitalik_address = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"  # Vitalik's address
    balance = client.get_balance(vitalik_address)
    
    # Test 7: Get a recent transaction (if we have block data)
    if recent_blocks and recent_blocks[0]["transactions_count"] > 0:
        logger.info("\n🔍 Test 7: Getting recent transaction")
        block_with_txs = client.get_block_by_number(recent_blocks[0]["number"], full_transactions=True)
        if block_with_txs and "transactions" in block_with_txs and block_with_txs["transactions"]:
            # Get the first transaction
            first_tx = block_with_txs["transactions"][0]
            if isinstance(first_tx, dict) and "hash" in first_tx:
                tx_hash = first_tx["hash"]
                client.get_transaction(tx_hash)
                client.get_transaction_receipt(tx_hash)
    
    logger.info("\n" + "="*50)
    logger.info("✅ All HTTP API tests completed!")
    logger.info("="*50)

def run_websocket_tests():
    """Run WebSocket tests for real-time data"""
    logger.info("\n🚀 Starting WebSocket tests...")
    
    # Initialize WebSocket client
    ws_client = SimpleWebSocketClient(
        network="sepolia",
        api_key="EbcNdRQag_4Ep75VtLuPLV3-MMfLKMvH")
    
    # Test WebSocket connection
    ws_client.test_websocket_connection()
    
    logger.info("✅ WebSocket tests completed!")

def main():
    """Main function"""
    print("🔧 Ethereum API Test Script")
    print("📡 Using Alchemy API with WebSocket support")
    print("=" * 50)
    
    # Check if API key is set
    api_key = os.getenv('ALCHEMY_API_KEY')
    if not api_key:
        print("⚠️  No ALCHEMY_API_KEY environment variable found.")
        print("📝 Get your free API key at: https://www.alchemy.com/")
        print("💡 Using provided API key for testing.")
        print()
    
    # Run HTTP API tests
    run_ethereum_tests()
    
    # Run WebSocket tests
    run_websocket_tests()

if __name__ == "__main__":
    main() 