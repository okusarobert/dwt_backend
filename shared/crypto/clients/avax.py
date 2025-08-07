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
from ..HD import ETH  # Avalanche uses Ethereum addresses
from cryptography.fernet import Fernet
import base64


class AlchemyAvalancheConfig(BaseModel):
    """Pydantic model for Alchemy Avalanche configuration"""
    api_key: str
    network: str = "mainnet"
    base_url: str = ""
    ws_url: str = ""


@dataclass
class AvalancheConfig:
    """Configuration for Avalanche client"""
    api_key: str
    network: str = "mainnet"
    base_url: str = ""
    ws_url: str = ""
    timeout: int = 30

    @classmethod
    def testnet(cls, api_key: str) -> 'AvalancheConfig':
        return cls(
            api_key=api_key,
            network="testnet",
            base_url=f"https://avax-testnet.g.alchemy.com/v2/{api_key}",
            ws_url=f"wss://avax-testnet.g.alchemy.com/v2/{api_key}"
        )

    @classmethod
    def mainnet(cls, api_key: str) -> 'AvalancheConfig':
        return cls(
            api_key=api_key,
            network="mainnet",
            base_url=f"https://avax-mainnet.g.alchemy.com/v2/{api_key}",
            ws_url=f"wss://avax-mainnet.g.alchemy.com/v2/{api_key}"
        )


class AVAXWallet:
    account_id = None

    def __init__(self, user_id: int, config: AvalancheConfig, session: Session, logger: logging.Logger = None):
        self.user_id = user_id
        self.label = "AVAX Wallet"
        self.account_number = generate_unique_account_number(session=session, length=10)
        self.session = session
        self.logger = logger or setup_logging()
        self.symbol = "AVAX"
        self.app_secret = config('APP_SECRET', default='your-app-secret-key')
        self.config = config
        self.session_request = requests.Session()
        self.session_request.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'AVAXWallet/1.0'
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
        """Create a new AVAX wallet account in the database."""
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
            self.logger.error(f"[AVAX] Failed to create wallet for user {self.user_id}: {e!r}")
            self.logger.error(traceback.format_exc())
            raise  # Re-raise the exception so the wallet service can handle it

    def create_address(self):
        """Create a new AVAX address for the wallet."""
        try:
            self.logger.info(f"Creating address for user {self.user_id}")
            mnemonic_key = f"{self.symbol}_MNEMONIC"
            mnemonic = config(mnemonic_key, default=None)
            if mnemonic:
                # Avalanche uses Ethereum addresses, so we use the ETH HD wallet
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
            self.logger.error(f"[AVAX] Failed to create address for user {self.user_id}: {e!r}")
            self.logger.error(traceback.format_exc())
            raise  # Re-raise the exception so the wallet service can handle it
        finally:
            self.logger.info(f"Done creating address for user {self.user_id}")

    # ===== Avalanche API Methods =====
    
    def make_request(self, method: str, params: list = None) -> Optional[Dict]:
        """Make a JSON-RPC request to Avalanche API"""
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params or []
        }
        
        try:
            response = self.session_request.post(
                self.config.base_url,
                json=payload,
                timeout=self.config.timeout
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
        """Test the connection to Avalanche API"""
        self.logger.info("Testing Avalanche API connection...")
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
            balance_avax = balance_wei / (10 ** 18)
            return {
                "address": address,
                "balance_wei": balance_wei,
                "balance_avax": balance_avax
            }
        return None

    def get_gas_price(self) -> Optional[Dict]:
        """Get current gas price"""
        result = self.make_request("eth_gasPrice")
        if result and "result" in result:
            gas_price_wei = int(result["result"], 16)
            gas_price_navax = gas_price_wei / (10 ** 9)  # nAVAX (nano-AVAX)
            return {
                "gas_price_wei": gas_price_wei,
                "gas_price_navax": gas_price_navax
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

    # ===== Avalanche-specific methods =====

    def get_token_balance(self, token_address: str, wallet_address: str) -> Optional[Dict]:
        """Get ERC-20 token balance on Avalanche"""
        try:
            # ERC-20 balanceOf function signature
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
                "network": self.config.network,
                "latest_block": latest_block,
                "gas_price": gas_price,
                "base_url": self.config.base_url,
                "ws_url": self.config.ws_url
            }
        except Exception as e:
            self.logger.error(f"Error getting network info: {e}")
            return {}

    def validate_address(self, address: str) -> bool:
        """Validate Avalanche address format (same as Ethereum)"""
        try:
            # Avalanche uses Ethereum addresses, so same validation
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
                "network": self.config.network,
                "latest_block": latest_block,
                "gas_price": gas_price,
                "recent_blocks": recent_blocks,
                "connection_status": self.test_connection()
            }
        except Exception as e:
            self.logger.error(f"Error getting blockchain info: {e}")
            return {}

    def get_avalanche_specific_info(self) -> Dict[str, Any]:
        """Get Avalanche-specific information"""
        try:
            # Get Avalanche specific information
            latest_block = self.get_latest_block_number()
            gas_price = self.get_gas_price()
            
            return {
                "network": "Avalanche",
                "chain_id": 43114 if self.config.network == "mainnet" else 43113,  # Avalanche mainnet/testnet
                "latest_block": latest_block,
                "gas_price": gas_price,
                "consensus": "Proof of Stake",
                "subnet": "C-Chain",
                "native_token": "AVAX"
            }
        except Exception as e:
            self.logger.error(f"Error getting Avalanche-specific info: {e}")
            return {}

    def get_subnet_info(self) -> Dict[str, Any]:
        """Get Avalanche subnet information"""
        try:
            # Avalanche has multiple subnets, but we're focusing on C-Chain (EVM compatible)
            return {
                "subnet": "C-Chain",
                "description": "EVM-compatible smart contract platform",
                "consensus": "Proof of Stake",
                "block_time": "~2 seconds",
                "finality": "~3 seconds",
                "gas_limit": "8,000,000",
                "compatibility": "Ethereum EVM"
            }
        except Exception as e:
            self.logger.error(f"Error getting subnet info: {e}")
            return {} 