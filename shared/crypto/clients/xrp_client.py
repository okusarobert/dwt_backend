"""
XRP Client for DWT Backend
Connects to XRPL via public APIs (testnet and mainnet)
"""
import json
import requests
import os
import asyncio
import websockets
from decimal import Decimal
from typing import Dict, List, Optional, Any, Union
import logging
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class XRPTransaction:
    """XRP transaction data structure"""
    hash: str
    account: str
    destination: str
    amount: Union[str, Dict[str, str]]  # XRP amount as string, or token object
    fee: str
    sequence: int
    destination_tag: Optional[int] = None
    source_tag: Optional[int] = None
    transaction_type: str = "Payment"
    ledger_index: Optional[int] = None
    date: Optional[int] = None  # Ripple timestamp
    validated: bool = False

class XRPClient:
    """XRP Client for XRPL operations via public APIs"""
    
    def __init__(self, api_url: str, websocket_url: str = None, testnet: bool = True):
        self.api_url = api_url.rstrip('/')
        self.websocket_url = websocket_url
        self.testnet = testnet
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'DWT-Backend-XRP-Client/1.0'
        })
        
    def _api_request(self, method: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Make API request to XRPL"""
        if params is None:
            params = {}
            
        payload = {
            "method": method,
            "params": [params]
        }
        
        try:
            response = self.session.post(self.api_url, json=payload)
            response.raise_for_status()
            
            result = response.json()
            if result.get('result', {}).get('status') != 'success':
                error = result.get('result', {}).get('error', 'Unknown error')
                raise Exception(f"XRPL API error: {error}")
                
            return result.get('result', {})
            
        except requests.exceptions.RequestException as e:
            logger.error(f"XRPL API connection error: {e}")
            raise Exception(f"Failed to connect to XRPL: {e}")
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON response from XRPL: {e}")
            raise Exception(f"Invalid response from XRPL: {e}")
    
    def get_server_info(self) -> Dict[str, Any]:
        """Get server information"""
        return self._api_request("server_info")
    
    def get_ledger(self, ledger_index: str = "validated") -> Dict[str, Any]:
        """Get ledger information"""
        return self._api_request("ledger", {"ledger_index": ledger_index})
    
    def get_account_info(self, account: str) -> Dict[str, Any]:
        """Get account information"""
        return self._api_request("account_info", {"account": account})
    
    def get_account_balance(self, account: str) -> Decimal:
        """Get account XRP balance in XRP (not drops)"""
        try:
            info = self.get_account_info(account)
            balance_drops = info.get('account_data', {}).get('Balance', '0')
            return self.drops_to_xrp(int(balance_drops))
        except Exception as e:
            logger.error(f"Failed to get balance for {account}: {e}")
            return Decimal('0')
    
    def get_account_transactions(self, account: str, limit: int = 10, 
                               marker: str = None) -> Dict[str, Any]:
        """Get account transaction history"""
        params = {
            "account": account,
            "limit": limit
        }
        if marker:
            params["marker"] = marker
            
        return self._api_request("account_tx", params)
    
    def get_transaction(self, tx_hash: str) -> Dict[str, Any]:
        """Get specific transaction details"""
        return self._api_request("tx", {"transaction": tx_hash})
    
    def submit_transaction(self, tx_blob: str) -> Dict[str, Any]:
        """Submit signed transaction"""
        return self._api_request("submit", {"tx_blob": tx_blob})
    
    def get_fee(self) -> Dict[str, Any]:
        """Get current base fee and reserve amounts"""
        return self._api_request("server_state")
    
    def validate_address(self, address: str) -> bool:
        """Validate XRP address format"""
        try:
            # Basic validation - XRP addresses start with 'r' and are 25-34 characters
            if not address.startswith('r'):
                return False
            if len(address) < 25 or len(address) > 34:
                return False
            # Could add more sophisticated validation using xrpl-py library
            return True
        except Exception:
            return False
    
    def get_account_lines(self, account: str) -> Dict[str, Any]:
        """Get account trust lines (for tokens, not needed for XRP)"""
        return self._api_request("account_lines", {"account": account})
    
    def get_account_offers(self, account: str) -> Dict[str, Any]:
        """Get account offers on the DEX"""
        return self._api_request("account_offers", {"account": account})
    
    def get_book_offers(self, taker_gets: Dict[str, str], 
                       taker_pays: Dict[str, str], limit: int = 10) -> Dict[str, Any]:
        """Get order book offers"""
        return self._api_request("book_offers", {
            "taker_gets": taker_gets,
            "taker_pays": taker_pays,
            "limit": limit
        })
    
    def get_path_find(self, source_account: str, destination_account: str,
                     destination_amount: Union[str, Dict[str, str]]) -> Dict[str, Any]:
        """Find payment paths"""
        return self._api_request("ripple_path_find", {
            "source_account": source_account,
            "destination_account": destination_account,
            "destination_amount": destination_amount
        })
    
    def drops_to_xrp(self, drops: int) -> Decimal:
        """Convert drops to XRP (1 XRP = 1,000,000 drops)"""
        return Decimal(drops) / Decimal('1000000')
    
    def xrp_to_drops(self, xrp: Decimal) -> int:
        """Convert XRP to drops"""
        return int(xrp * Decimal('1000000'))
    
    def format_amount(self, amount: Union[str, Dict[str, str]]) -> str:
        """Format amount for display"""
        if isinstance(amount, str):
            # XRP amount in drops
            xrp_amount = self.drops_to_xrp(int(amount))
            return f"{xrp_amount} XRP"
        else:
            # Token amount
            return f"{amount['value']} {amount['currency']}"
    
    def is_account_funded(self, account: str) -> bool:
        """Check if account exists and is funded"""
        try:
            self.get_account_info(account)
            return True
        except Exception:
            return False
    
    def get_reserve_requirements(self) -> Dict[str, Decimal]:
        """Get current reserve requirements"""
        try:
            server_state = self.get_fee()
            state = server_state.get('state', {})
            
            base_reserve_drops = state.get('reserve_base_xrp', 10000000)  # Default 10 XRP
            owner_reserve_drops = state.get('reserve_inc_xrp', 2000000)   # Default 2 XRP
            
            return {
                'base_reserve': self.drops_to_xrp(base_reserve_drops),
                'owner_reserve': self.drops_to_xrp(owner_reserve_drops)
            }
        except Exception as e:
            logger.error(f"Failed to get reserve requirements: {e}")
            # Return defaults
            return {
                'base_reserve': Decimal('10'),
                'owner_reserve': Decimal('2')
            }
    
    def calculate_available_balance(self, account: str) -> Decimal:
        """Calculate available balance (total - reserves)"""
        try:
            info = self.get_account_info(account)
            account_data = info.get('account_data', {})
            
            total_balance = self.drops_to_xrp(int(account_data.get('Balance', '0')))
            owner_count = account_data.get('OwnerCount', 0)
            
            reserves = self.get_reserve_requirements()
            total_reserve = reserves['base_reserve'] + (reserves['owner_reserve'] * owner_count)
            
            available = total_balance - total_reserve
            return max(available, Decimal('0'))
            
        except Exception as e:
            logger.error(f"Failed to calculate available balance for {account}: {e}")
            return Decimal('0')
    
    async def subscribe_to_account(self, account: str, callback=None):
        """Subscribe to account transactions via WebSocket"""
        if not self.websocket_url:
            raise Exception("WebSocket URL not configured")
            
        try:
            async with websockets.connect(self.websocket_url) as websocket:
                # Subscribe to account
                subscribe_msg = {
                    "command": "subscribe",
                    "accounts": [account]
                }
                
                await websocket.send(json.dumps(subscribe_msg))
                
                # Listen for messages
                async for message in websocket:
                    data = json.loads(message)
                    
                    if callback:
                        await callback(data)
                    else:
                        logger.info(f"Account {account} transaction: {data}")
                        
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
            raise
    
    def parse_transaction(self, tx_data: Dict[str, Any]) -> XRPTransaction:
        """Parse transaction data into XRPTransaction object"""
        tx = tx_data.get('transaction', tx_data)
        
        return XRPTransaction(
            hash=tx.get('hash', ''),
            account=tx.get('Account', ''),
            destination=tx.get('Destination', ''),
            amount=tx.get('Amount', '0'),
            fee=tx.get('Fee', '0'),
            sequence=tx.get('Sequence', 0),
            destination_tag=tx.get('DestinationTag'),
            source_tag=tx.get('SourceTag'),
            transaction_type=tx.get('TransactionType', 'Payment'),
            ledger_index=tx.get('ledger_index'),
            date=tx.get('date'),
            validated=tx_data.get('validated', False)
        )

# Factory functions for easy client creation
def create_xrp_testnet_client() -> XRPClient:
    """Create XRP client for testnet"""
    api_url = os.getenv('XRP_TESTNET_API_URL', 'http://104.248.77.43:5005')
    ws_url = os.getenv('XRP_TESTNET_WS_URL', 'ws://104.248.77.43:6006')
    return XRPClient(api_url, ws_url, testnet=True)

def create_xrp_mainnet_client() -> XRPClient:
    """Create XRP client for mainnet"""
    api_url = os.getenv('XRP_MAINNET_API_URL', 'https://xrplcluster.com')
    ws_url = os.getenv('XRP_MAINNET_WS_URL', 'wss://xrplcluster.com')
    return XRPClient(api_url, ws_url, testnet=False)

def create_xrp_client(testnet: bool = True) -> XRPClient:
    """Create XRP client based on environment"""
    if testnet:
        return create_xrp_testnet_client()
    else:
        return create_xrp_mainnet_client()

# Example usage
if __name__ == "__main__":
    # Test the client
    client = create_xrp_testnet_client()
    
    try:
        # Test connection
        server_info = client.get_server_info()
        print(f"Connected to XRPL server")
        print(f"Server version: {server_info.get('info', {}).get('build_version', 'unknown')}")
        
        # Get ledger info
        ledger = client.get_ledger()
        print(f"Current ledger: {ledger.get('ledger', {}).get('ledger_index', 'unknown')}")
        
        # Get reserve requirements
        reserves = client.get_reserve_requirements()
        print(f"Base reserve: {reserves['base_reserve']} XRP")
        print(f"Owner reserve: {reserves['owner_reserve']} XRP")
        
        # Test address validation
        test_address = "rN7n7otQDd6FczFgLdSqtcsAUxDkw6fzRH"
        is_valid = client.validate_address(test_address)
        print(f"Address {test_address} is valid: {is_valid}")
        
    except Exception as e:
        print(f"Error: {e}")
