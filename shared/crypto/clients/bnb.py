import traceback
import logging
import os
import json
import requests
import time
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from pydantic import BaseModel

from db.utils import generate_unique_account_number
from shared.logger import setup_logging
from db.wallet import Account, AccountType, CryptoAddress
from sqlalchemy.orm import Session
from decouple import config
from ..HD import ETH  # BNB uses Ethereum addresses
from cryptography.fernet import Fernet
import base64


class AlchemyBNBConfig(BaseModel):
    """Pydantic model for Alchemy BNB configuration"""
    api_key: str
    network: str = "mainnet"
    base_url: str = ""
    ws_url: str = ""


@dataclass
class BNBConfig:
    """Configuration for BNB Smart Chain client"""
    api_key: str
    network: str = "mainnet"
    base_url: str = ""
    ws_url: str = ""
    timeout: int = 30

    @classmethod
    def testnet(cls, api_key: str) -> 'BNBConfig':
        return cls(
            api_key=api_key,
            network="testnet",
            base_url=f"https://bnb-testnet.g.alchemy.com/v2/{api_key}",
            ws_url=f"wss://bnb-testnet.g.alchemy.com/v2/{api_key}"
        )

    @classmethod
    def mainnet(cls, api_key: str) -> 'BNBConfig':
        return cls(
            api_key=api_key,
            network="mainnet",
            base_url=f"https://bnb-mainnet.g.alchemy.com/v2/{api_key}",
            ws_url=f"wss://bnb-mainnet.g.alchemy.com/v2/{api_key}"
        )


class BNBWallet:
    account_id = None

    def __init__(self, user_id: int, config: BNBConfig, session: Session, logger: logging.Logger = None):
        self.user_id = user_id
        self.label = "BNB Wallet"
        self.account_number = generate_unique_account_number(session=session, length=10)
        self.session = session
        self.logger = logger or setup_logging()
        self.symbol = "BNB"
        self.app_secret = config('APP_SECRET', default='your-app-secret-key')
        self.bnb_config = config
        self.session_request = requests.Session()
        self.session_request.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'BNBWallet/1.0'
        })
        
    def encrypt_private_key(self, private_key: str) -> str:
        """Encrypt private key using APP_SECRET."""
        try:
            # Create a key from APP_SECRET (32 bytes required for Fernet)
            key = base64.urlsafe_b64encode(self.app_secret.encode()[:32].ljust(32, b'0'))
            cipher = Fernet(key)
            encrypted_key = cipher.encrypt(private_key.encode())
            return encrypted_key.decode()
        except Exception as e:
            self.logger.error(f"Failed to encrypt private key: {e}")
            return private_key  # Return unencrypted as fallback
            
    def decrypt_private_key(self, encrypted_private_key: str) -> str:
        """Decrypt private key using APP_SECRET."""
        try:
            # Create a key from APP_SECRET (32 bytes required for Fernet)
            key = base64.urlsafe_b64encode(self.app_secret.encode()[:32].ljust(32, b'0'))
            cipher = Fernet(key)
            decrypted_key = cipher.decrypt(encrypted_private_key.encode())
            return decrypted_key.decode()
        except Exception as e:
            self.logger.error(f"Failed to decrypt private key: {e}")
            return encrypted_private_key  # Return encrypted as fallback
        
    def create_wallet(self):
        """Create a new BNB wallet account in the database."""
        try:
            crypto_account = Account(
                user_id=self.user_id,
                balance=0,
                locked_amount=0,
                currency=self.symbol,
                account_type=AccountType.CRYPTO,
                account_number=self.account_number,
                label=self.label
            )
            self.session.add(crypto_account)
            self.session.flush()  # Get the ID without committing
            self.account_id = crypto_account.id
            self.create_address()
            self.logger.info(
                f"[Wallet] Created {self.symbol} crypto account for user {self.user_id}")
        except Exception as e:
            self.logger.error(f"[BNB] Failed to create wallet for user {self.user_id}: {e!r}")
            self.logger.error(traceback.format_exc())
            raise  # Re-raise the exception so the wallet service can handle it

    def create_address(self):
        """Create a new BNB address for the wallet."""
        try:
            self.logger.info(f"Creating address for user {self.user_id}")
            mnemonic_key = f"{self.symbol}_MNEMONIC"
            mnemonic = config(mnemonic_key, default=None)
            if mnemonic:
                # BNB uses Ethereum addresses, so we use the ETH HD wallet
                eth_wallet = ETH()
                wallet = eth_wallet.from_mnemonic(mnemonic=mnemonic)
                
                # Create user's address
                user_address, priv_key, pub_key = wallet.new_address(index=self.account_id)
                
                # Encrypt private key before storing
                encrypted_private_key = self.encrypt_private_key(priv_key)
                
                # Create crypto address record for user's address
                crypto_address = CryptoAddress(
                    account_id=self.account_id,
                    address=user_address,
                    label=self.label,
                    is_active=True,
                    currency_code=self.symbol,
                    address_type="hd_wallet",
                    private_key=encrypted_private_key,
                    public_key=pub_key
                )
                self.session.add(crypto_address)
                
                self.logger.info(f"Created user address: {user_address}")
                    
        except Exception as e:
            self.logger.error(f"[BNB] Failed to create address for user {self.user_id}: {e!r}")
            self.logger.error(traceback.format_exc())
            raise  # Re-raise the exception so the wallet service can handle it
        finally:
            self.logger.info(f"Done creating address for user {self.user_id}")

    # ===== BNB API Methods =====
    
    def make_request(self, method: str, params: list = None) -> Optional[Dict]:
        """Make a JSON-RPC request to BNB API"""
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params or []
        }
        
        try:
            response = self.session_request.post(
                self.bnb_config.base_url,
                json=payload,
                timeout=self.bnb_config.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request failed: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
            return None

    def test_connection(self) -> bool:
        """Test the connection to BNB API"""
        self.logger.info("Testing BNB API connection...")
        result = self.make_request("eth_blockNumber")
        return result is not None and "result" in result

    def get_latest_block_number(self) -> Optional[int]:
        """Get the latest block number"""
        result = self.make_request("eth_blockNumber")
        if result and "result" in result:
            return int(result["result"], 16)
        return None

    def get_block_by_number(self, block_number: int, full_transactions: bool = False) -> Optional[Dict]:
        """Get block information by number"""
        result = self.make_request(
            "eth_getBlockByNumber",
            [hex(block_number), full_transactions]
        )
        return result.get("result") if result else None

    def get_block_by_hash(self, block_hash: str, full_transactions: bool = False) -> Optional[Dict]:
        """Get block information by hash"""
        result = self.make_request(
            "eth_getBlockByHash",
            [block_hash, full_transactions]
        )
        return result.get("result") if result else None

    def get_balance(self, address: str) -> Optional[Dict]:
        """Get account balance"""
        result = self.make_request("eth_getBalance", [address, "latest"])
        if result and "result" in result:
            balance_wei = int(result["result"], 16)
            balance_bnb = balance_wei / (10 ** 18)
            return {
                "address": address,
                "balance_wei": balance_wei,
                "balance_bnb": balance_bnb
            }
        return None

    def get_gas_price(self) -> Optional[Dict]:
        """Get current gas price"""
        result = self.make_request("eth_gasPrice")
        if result and "result" in result:
            gas_price_wei = int(result["result"], 16)
            gas_price_gwei = gas_price_wei / (10 ** 9)
            return {
                "gas_price_wei": gas_price_wei,
                "gas_price_gwei": gas_price_gwei
            }
        return None

    def get_transaction(self, tx_hash: str) -> Optional[Dict]:
        """Get transaction details"""
        result = self.make_request("eth_getTransactionByHash", [tx_hash])
        return result.get("result") if result else None

    def get_transaction_receipt(self, tx_hash: str) -> Optional[Dict]:
        """Get transaction receipt"""
        result = self.make_request("eth_getTransactionReceipt", [tx_hash])
        return result.get("result") if result else None

    def get_recent_blocks(self, count: int = 5) -> List[Dict]:
        """Get information about recent blocks"""
        blocks = []
        latest_block = self.get_latest_block_number()
        
        if latest_block is None:
            return blocks
        
        for i in range(count):
            block_number = latest_block - i
            if block_number >= 0:
                block_data = self.get_block_by_number(block_number)
                if block_data:
                    block_info = {
                        "number": int(block_data.get("number", "0"), 16),
                        "hash": block_data.get("hash"),
                        "timestamp": int(block_data.get("timestamp", "0"), 16),
                        "transactions_count": len(block_data.get("transactions", [])),
                        "gas_used": int(block_data.get("gasUsed", "0"), 16),
                        "gas_limit": int(block_data.get("gasLimit", "0"), 16)
                    }
                    blocks.append(block_info)
        
        return blocks

    def estimate_gas(self, from_address: str, to_address: str, value: str = "0x0", data: str = "0x") -> Optional[Dict]:
        """Estimate gas for a transaction"""
        params = [{
            "from": from_address,
            "to": to_address,
            "value": value,
            "data": data
        }, "latest"]
        
        result = self.make_request("eth_estimateGas", params)
        if result and "result" in result:
            gas_estimate = int(result["result"], 16)
            return {"gas_estimate": gas_estimate}
        return None

    def get_transaction_count(self, address: str) -> Optional[int]:
        """Get transaction count (nonce) for an address"""
        result = self.make_request("eth_getTransactionCount", [address, "latest"])
        if result and "result" in result:
            return int(result["result"], 16)
        return None

    def get_code(self, address: str) -> Optional[str]:
        """Get contract code at address"""
        result = self.make_request("eth_getCode", [address, "latest"])
        return result.get("result") if result else None

    def get_storage_at(self, address: str, position: str) -> Optional[str]:
        """Get storage at position for address"""
        result = self.make_request("eth_getStorageAt", [address, position, "latest"])
        return result.get("result") if result else None

    def get_logs(self, from_block: str = "latest", to_block: str = "latest", 
                 address: str = None, topics: List[str] = None) -> Optional[List[Dict]]:
        """Get logs matching criteria"""
        params = {
            "fromBlock": from_block,
            "toBlock": to_block
        }
        if address:
            params["address"] = address
        if topics:
            params["topics"] = topics
            
        result = self.make_request("eth_getLogs", [params])
        return result.get("result") if result else None

    # ===== BNB-specific methods =====

    def get_token_balance(self, token_address: str, wallet_address: str) -> Optional[Dict]:
        """Get BEP-20 token balance on BNB Smart Chain"""
        try:
            # BEP-20 balanceOf function signature
            balance_of_signature = "0x70a08231"  # balanceOf(address)
            data = balance_of_signature + "000000000000000000000000" + wallet_address[2:]  # Remove 0x prefix
            
            result = self.make_request("eth_call", [{
                "to": token_address,
                "data": data
            }, "latest"])
            
            if result and "result" in result:
                balance_hex = result["result"]
                if balance_hex == "0x":
                    return {"balance": 0, "token_address": token_address, "wallet_address": wallet_address}
                
                balance_wei = int(balance_hex, 16)
                return {
                    "balance": balance_wei,
                    "token_address": token_address,
                    "wallet_address": wallet_address
                }
            
            return None
        except Exception as e:
            self.logger.error(f"Error getting token balance: {e}")
            return None

    def get_account_info(self, address: str) -> Optional[Dict]:
        """Get comprehensive account information"""
        try:
            balance = self.get_balance(address)
            tx_count = self.get_transaction_count(address)
            code = self.get_code(address)
            
            return {
                "address": address,
                "balance": balance,
                "transaction_count": tx_count,
                "is_contract": code != "0x" if code else False,
                "code": code
            }
        except Exception as e:
            self.logger.error(f"Error getting account info: {e}")
            return None

    def get_network_info(self) -> Dict[str, Any]:
        """Get network information"""
        try:
            latest_block = self.get_latest_block_number()
            gas_price = self.get_gas_price()
            
            return {
                "network": self.bnb_config.network,
                "latest_block": latest_block,
                "gas_price": gas_price,
                "base_url": self.bnb_config.base_url,
                "ws_url": self.bnb_config.ws_url
            }
        except Exception as e:
            self.logger.error(f"Error getting network info: {e}")
            return {}

    def validate_address(self, address: str) -> bool:
        """Validate BNB address format (same as Ethereum)"""
        try:
            # BNB uses Ethereum addresses, so same validation
            if not address.startswith("0x"):
                return False
            if len(address) != 42:  # 0x + 40 hex chars
                return False
            # Check if it's a valid hex string
            int(address[2:], 16)
            return True
        except:
            return False

    def get_blockchain_info(self) -> Dict[str, Any]:
        """Get comprehensive blockchain information"""
        try:
            latest_block = self.get_latest_block_number()
            gas_price = self.get_gas_price()
            recent_blocks = self.get_recent_blocks(3)
            
            return {
                "network": self.bnb_config.network,
                "latest_block": latest_block,
                "gas_price": gas_price,
                "recent_blocks": recent_blocks,
                "connection_status": self.test_connection()
            }
        except Exception as e:
            self.logger.error(f"Error getting blockchain info: {e}")
            return {}

    def get_bnb_specific_info(self) -> Dict[str, Any]:
        """Get BNB-specific information"""
        try:
            # Get BNB specific information
            latest_block = self.get_latest_block_number()
            gas_price = self.get_gas_price()
            
            return {
                "network": "BNB Smart Chain",
                "chain_id": 56 if self.bnb_config.network == "mainnet" else 97,  # BNB mainnet/testnet
                "latest_block": latest_block,
                "gas_price": gas_price,
                "consensus": "Proof of Staked Authority (PoSA)",
                "block_time": "~3 seconds",
                "finality": "~3 seconds",
                "native_token": "BNB"
            }
        except Exception as e:
            self.logger.error(f"Error getting BNB-specific info: {e}")
            return {}

    def get_bep20_token_info(self, token_address: str) -> Optional[Dict]:
        """Get BEP-20 token information"""
        try:
            # Get token name, symbol, and decimals
            name_signature = "0x06fdde03"  # name()
            symbol_signature = "0x95d89b41"  # symbol()
            decimals_signature = "0x313ce567"  # decimals()
            
            # Get token name
            name_result = self.make_request("eth_call", [{
                "to": token_address,
                "data": name_signature
            }, "latest"])
            
            # Get token symbol
            symbol_result = self.make_request("eth_call", [{
                "to": token_address,
                "data": symbol_signature
            }, "latest"])
            
            # Get token decimals
            decimals_result = self.make_request("eth_call", [{
                "to": token_address,
                "data": decimals_signature
            }, "latest"])
            
            token_info = {
                "address": token_address,
                "name": None,
                "symbol": None,
                "decimals": None
            }
            
            if name_result and "result" in name_result:
                name_hex = name_result["result"]
                if name_hex != "0x":
                    # Decode hex to string
                    name_bytes = bytes.fromhex(name_hex[2:])
                    token_info["name"] = name_bytes.decode('utf-8').rstrip('\x00')
            
            if symbol_result and "result" in symbol_result:
                symbol_hex = symbol_result["result"]
                if symbol_hex != "0x":
                    # Decode hex to string
                    symbol_bytes = bytes.fromhex(symbol_hex[2:])
                    token_info["symbol"] = symbol_bytes.decode('utf-8').rstrip('\x00')
            
            if decimals_result and "result" in decimals_result:
                decimals_hex = decimals_result["result"]
                if decimals_hex != "0x":
                    token_info["decimals"] = int(decimals_hex, 16)
            
            return token_info
        except Exception as e:
            self.logger.error(f"Error getting BEP-20 token info: {e}")
            return None

    def get_bnb_features(self) -> Dict[str, Any]:
        """Get BNB-specific features"""
        try:
            return {
                "high_performance": True,
                "fast_finality": "~3 seconds",
                "low_fees": True,
                "bep20_tokens": True,
                "smart_contracts": True,
                "cross_chain": True,
                "binance_ecosystem": True
            }
        except Exception as e:
            self.logger.error(f"Error getting BNB features: {e}")
            return {}

    def monitor_address_transactions(self, address: str, from_block: int = None, to_block: int = None) -> List[Dict]:
        """Monitor transactions for a specific address"""
        try:
            if from_block is None:
                # Get recent blocks if no from_block specified
                latest_block = self.get_latest_block_number()
                if latest_block:
                    from_block = max(0, latest_block - 100)  # Last 100 blocks
                else:
                    return []
            
            if to_block is None:
                to_block = "latest"
            
            # Get logs for the address
            logs = self.get_logs(
                from_block=hex(from_block),
                to_block=to_block,
                address=address
            )
            
            transactions = []
            if logs:
                for log in logs:
                    transaction_info = {
                        "address": address,
                        "block_number": int(log.get("blockNumber", "0"), 16),
                        "transaction_hash": log.get("transactionHash"),
                        "log_index": int(log.get("logIndex", "0"), 16),
                        "topics": log.get("topics", []),
                        "data": log.get("data"),
                        "removed": log.get("removed", False)
                    }
                    transactions.append(transaction_info)
            
            return transactions
        except Exception as e:
            self.logger.error(f"Error monitoring transactions for {address}: {e}")
            return []

    def get_address_history(self, address: str, limit: int = 10) -> List[Dict]:
        """Get transaction history for an address"""
        try:
            # Get recent blocks
            latest_block = self.get_latest_block_number()
            if not latest_block:
                return []
            
            transactions = []
            blocks_to_check = min(limit * 2, 100)  # Check more blocks to find transactions
            
            for i in range(blocks_to_check):
                block_number = latest_block - i
                if block_number < 0:
                    break
                
                block = self.get_block_by_number(block_number, full_transactions=True)
                if block and "transactions" in block:
                    for tx in block["transactions"]:
                        if (tx.get("from", "").lower() == address.lower() or 
                            tx.get("to", "").lower() == address.lower()):
                            transaction_info = {
                                "hash": tx.get("hash"),
                                "block_number": int(tx.get("blockNumber", "0"), 16),
                                "from": tx.get("from"),
                                "to": tx.get("to"),
                                "value": tx.get("value"),
                                "gas": tx.get("gas"),
                                "gas_price": tx.get("gasPrice"),
                                "nonce": tx.get("nonce"),
                                "input": tx.get("input"),
                                "type": "incoming" if tx.get("to", "").lower() == address.lower() else "outgoing"
                            }
                            transactions.append(transaction_info)
                            
                            if len(transactions) >= limit:
                                break
                
                if len(transactions) >= limit:
                    break
            
            return transactions
        except Exception as e:
            self.logger.error(f"Error getting transaction history for {address}: {e}")
            return []

    def generate_new_address(self, index: int = None) -> Optional[Dict]:
        """Generate a new BNB address for the wallet"""
        try:
            mnemonic_key = f"{self.symbol}_MNEMONIC"
            mnemonic = config(mnemonic_key, default=None)
            
            if not mnemonic:
                self.logger.error(f"No mnemonic configured for {self.symbol}")
                return None
            
            # BNB uses Ethereum addresses, so we use the ETH HD wallet
            eth_wallet = ETH()
            wallet = eth_wallet.from_mnemonic(mnemonic=mnemonic)
            
            # Use provided index or generate next available
            if index is None:
                # Find the next available index
                existing_addresses = self.session.query(CryptoAddress).filter_by(
                    account_id=self.account_id,
                    currency_code=self.symbol
                ).all()
                index = len(existing_addresses)
            
            # Create new address
            user_address, priv_key, pub_key = wallet.new_address(index=index)
            
            # Encrypt private key before storing
            encrypted_private_key = self.encrypt_private_key(priv_key)
            
            # Create crypto address record
            crypto_address = CryptoAddress(
                account_id=self.account_id,
                address=user_address,
                label=f"{self.label} Address {index + 1}",
                is_active=True,
                currency_code=self.symbol,
                address_type="hd_wallet",
                private_key=encrypted_private_key,
                public_key=pub_key
            )
            self.session.add(crypto_address)
            
            return {
                "address": user_address,
                "index": index,
                "public_key": pub_key,
                "label": crypto_address.label
            }
            
        except Exception as e:
            self.logger.error(f"Error generating new address: {e}")
            return None

    def get_wallet_addresses(self) -> List[Dict]:
        """Get all addresses for this wallet"""
        try:
            addresses = self.session.query(CryptoAddress).filter_by(
                account_id=self.account_id,
                currency_code=self.symbol,
                is_active=True
            ).all()
            
            return [
                {
                    "address": addr.address,
                    "label": addr.label,
                    "address_type": addr.address_type,
                    "is_active": addr.is_active
                }
                for addr in addresses
            ]
        except Exception as e:
            self.logger.error(f"Error getting wallet addresses: {e}")
            return []

    def get_wallet_summary(self) -> Dict[str, Any]:
        """Get comprehensive wallet summary"""
        try:
            addresses = self.get_wallet_addresses()
            total_balance = 0
            address_balances = []
            
            for addr_info in addresses:
                balance = self.get_balance(addr_info["address"])
                if balance:
                    address_balance = {
                        "address": addr_info["address"],
                        "label": addr_info["label"],
                        "balance_bnb": balance["balance_bnb"],
                        "balance_wei": balance["balance_wei"]
                    }
                    address_balances.append(address_balance)
                    total_balance += balance["balance_bnb"]
            
            return {
                "user_id": self.user_id,
                "account_id": self.account_id,
                "symbol": self.symbol,
                "total_balance_bnb": total_balance,
                "addresses": addresses,
                "address_balances": address_balances,
                "network": self.bnb_config.network
            }
        except Exception as e:
            self.logger.error(f"Error getting wallet summary: {e}")
            return {}

    def validate_and_get_token_info(self, token_address: str) -> Optional[Dict]:
        """Validate token address and get comprehensive token information"""
        try:
            if not self.validate_address(token_address):
                return None
            
            # Get basic token info
            token_info = self.get_bep20_token_info(token_address)
            if not token_info:
                return None
            
            # Get token balance for a test address (optional)
            test_address = "0x28C6c06298d514Db089934071355E5743bf21d60"  # Binance Hot Wallet
            token_balance = self.get_token_balance(token_address, test_address)
            
            return {
                **token_info,
                "is_valid": True,
                "sample_balance": token_balance
            }
        except Exception as e:
            self.logger.error(f"Error validating token {token_address}: {e}")
            return None 