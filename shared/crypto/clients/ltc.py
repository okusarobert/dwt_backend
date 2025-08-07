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
from ..HD import LTC  # Litecoin uses LTC class
from cryptography.fernet import Fernet
import base64


class LitecoinConfig(BaseModel):
    """Pydantic model for Litecoin configuration"""
    rpc_url: str
    rpc_username: str
    rpc_password: str
    network: str = "mainnet"
    timeout: int = 30


@dataclass
class LitecoinWalletConfig:
    """Configuration for Litecoin client"""
    rpc_url: str
    rpc_username: str
    rpc_password: str
    network: str = "mainnet"
    timeout: int = 30

    @classmethod
    def testnet(cls, rpc_url: str, rpc_username: str, rpc_password: str) -> 'LitecoinWalletConfig':
        return cls(
            rpc_url=rpc_url,
            rpc_username=rpc_username,
            rpc_password=rpc_password,
            network="testnet"
        )

    @classmethod
    def mainnet(cls, rpc_url: str, rpc_username: str, rpc_password: str) -> 'LitecoinWalletConfig':
        return cls(
            rpc_url=rpc_url,
            rpc_username=rpc_username,
            rpc_password=rpc_password,
            network="mainnet"
        )


class LitecoinWallet:
    account_id = None

    def __init__(self, user_id: int, config: LitecoinWalletConfig, session: Session, logger: logging.Logger = None):
        self.user_id = user_id
        self.label = "Litecoin Wallet"
        self.account_number = generate_unique_account_number(session=session, length=10)
        self.session = session
        self.logger = logger or setup_logging()
        self.symbol = "LTC"
        self.app_secret = config('APP_SECRET', default='your-app-secret-key')
        self.ltc_config = config
        self.session_request = requests.Session()
        self.session_request.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'LitecoinWallet/1.0'
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
        """Create a new Litecoin wallet account in the database."""
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
            self.logger.error(f"[Litecoin] Failed to create wallet for user {self.user_id}: {e!r}")
            self.logger.error(traceback.format_exc())
            raise  # Re-raise the exception so the wallet service can handle it

    def create_address(self):
        """Create a new Litecoin address for the wallet with uniqueness guarantees."""
        try:
            self.logger.info(f"Creating address for user {self.user_id}")
            
            # Use the new method with uniqueness guarantees
            new_address = self.ensure_address_uniqueness()
            if new_address:
                self.logger.info(f"Created unique user address: {new_address['address']}")
            else:
                self.logger.error("Failed to create unique address")
                raise Exception("Failed to create unique Litecoin address")
                
        except Exception as e:
            self.logger.error(f"[Litecoin] Failed to create address for user {self.user_id}: {e!r}")
            self.logger.error(traceback.format_exc())
            raise  # Re-raise the exception so the wallet service can handle it
        finally:
            self.logger.info(f"Done creating address for user {self.user_id}")

    # ===== Litecoin RPC Methods =====
    
    def make_rpc_request(self, method: str, params: list = None) -> Optional[Dict]:
        """Make a JSON-RPC request to Litecoin node"""
        payload = {
            "jsonrpc": "1.0",
            "id": "litecoin_wallet",
            "method": method,
            "params": params or []
        }
        
        try:
            response = self.session_request.post(
                self.ltc_config.rpc_url,
                json=payload,
                auth=(self.ltc_config.rpc_username, self.ltc_config.rpc_password),
                timeout=self.ltc_config.timeout
            )
            response.raise_for_status()
            result = response.json()
            
            if "error" in result and result["error"] is not None:
                self.logger.error(f"RPC error: {result['error']}")
                return None
                
            return result.get("result")
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request failed: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
            return None

    def test_connection(self) -> bool:
        """Test the connection to Litecoin node"""
        self.logger.info("Testing Litecoin RPC connection...")
        result = self.make_rpc_request("getblockchaininfo")
        return result is not None

    def get_blockchain_info(self) -> Optional[Dict]:
        """Get blockchain information"""
        return self.make_rpc_request("getblockchaininfo")

    def get_network_info(self) -> Optional[Dict]:
        """Get network information"""
        return self.make_rpc_request("getnetworkinfo")

    def get_wallet_info(self) -> Optional[Dict]:
        """Get wallet information"""
        return self.make_rpc_request("getwalletinfo")

    def get_balance(self, address: str = None, minconf: int = 1) -> Optional[Dict]:
        """Get balance for address or wallet"""
        if address:
            # Get balance for specific address
            result = self.make_rpc_request("getreceivedbyaddress", [address, minconf])
            if result is not None:
                return {
                    "address": address,
                    "balance": result,
                    "balance_ltc": result / (10 ** 8)  # LTC has 8 decimals
                }
        else:
            # Get total wallet balance
            result = self.make_rpc_request("getbalance", ["*", minconf])
            if result is not None:
                return {
                    "balance": result,
                    "balance_ltc": result / (10 ** 8)  # LTC has 8 decimals
                }
        return None

    def get_new_address(self, label: str = "") -> Optional[str]:
        """Get a new address from the wallet"""
        result = self.make_rpc_request("getnewaddress", [label])
        return result

    def get_address_info(self, address: str) -> Optional[Dict]:
        """Get address information"""
        result = self.make_rpc_request("getaddressinfo", [address])
        return result

    def validate_address(self, address: str) -> Optional[Dict]:
        """Validate Litecoin address"""
        result = self.make_rpc_request("validateaddress", [address])
        return result

    def get_transaction(self, txid: str) -> Optional[Dict]:
        """Get transaction details"""
        result = self.make_rpc_request("gettransaction", [txid])
        return result

    def get_raw_transaction(self, txid: str, verbose: bool = True) -> Optional[Dict]:
        """Get raw transaction details"""
        result = self.make_rpc_request("getrawtransaction", [txid, verbose])
        return result

    def get_block(self, block_hash: str, verbose: bool = True) -> Optional[Dict]:
        """Get block information"""
        result = self.make_rpc_request("getblock", [block_hash, verbose])
        return result

    def get_block_hash(self, height: int) -> Optional[str]:
        """Get block hash by height"""
        result = self.make_rpc_request("getblockhash", [height])
        return result

    def get_block_count(self) -> Optional[int]:
        """Get current block count"""
        result = self.make_rpc_request("getblockcount")
        return result

    def get_difficulty(self) -> Optional[float]:
        """Get current difficulty"""
        result = self.make_rpc_request("getdifficulty")
        return result

    def get_connection_count(self) -> Optional[int]:
        """Get number of connections"""
        result = self.make_rpc_request("getconnectioncount")
        return result

    def get_mempool_info(self) -> Optional[Dict]:
        """Get mempool information"""
        result = self.make_rpc_request("getmempoolinfo")
        return result

    def get_mempool_ancestors(self, txid: str) -> Optional[List[str]]:
        """Get mempool ancestors of a transaction"""
        result = self.make_rpc_request("getmempoolancestors", [txid])
        return result

    def get_mempool_descendants(self, txid: str) -> Optional[List[str]]:
        """Get mempool descendants of a transaction"""
        result = self.make_rpc_request("getmempooldescendants", [txid])
        return result

    def estimate_fee(self, blocks: int = 6) -> Optional[float]:
        """Estimate fee rate"""
        result = self.make_rpc_request("estimatesmartfee", [blocks])
        if result and "feerate" in result:
            return result["feerate"]
        return None

    def get_peer_info(self) -> Optional[List[Dict]]:
        """Get peer information"""
        result = self.make_rpc_request("getpeerinfo")
        return result

    def get_mining_info(self) -> Optional[Dict]:
        """Get mining information"""
        result = self.make_rpc_request("getmininginfo")
        return result

    def get_network_hashps(self, blocks: int = 120) -> Optional[float]:
        """Get network hash rate"""
        result = self.make_rpc_request("getnetworkhashps", [blocks])
        return result

    def get_litecoin_specific_info(self) -> Dict[str, Any]:
        """Get Litecoin-specific information"""
        try:
            blockchain_info = self.get_blockchain_info()
            network_info = self.get_network_info()
            
            return {
                "network": "Litecoin",
                "chain": blockchain_info.get("chain", "main") if blockchain_info else "main",
                "blocks": blockchain_info.get("blocks", 0) if blockchain_info else 0,
                "headers": blockchain_info.get("headers", 0) if blockchain_info else 0,
                "bestblockhash": blockchain_info.get("bestblockhash", "") if blockchain_info else "",
                "difficulty": blockchain_info.get("difficulty", 0) if blockchain_info else 0,
                "verificationprogress": blockchain_info.get("verificationprogress", 0) if blockchain_info else 0,
                "size_on_disk": blockchain_info.get("size_on_disk", 0) if blockchain_info else 0,
                "pruned": blockchain_info.get("pruned", False) if blockchain_info else False,
                "automatic_pruning": blockchain_info.get("automatic_pruning", False) if blockchain_info else False,
                "pruneheight": blockchain_info.get("pruneheight", 0) if blockchain_info else 0,
                "networkactive": network_info.get("networkactive", False) if network_info else False,
                "connections": network_info.get("connections", 0) if network_info else 0,
                "consensus": "Proof of Work (PoW)",
                "block_time": "~2.5 minutes",
                "algorithm": "Scrypt",
                "native_token": "LTC",
                "decimals": 8,
                "address_format": "Base58Check",
                "address_prefix": "L (mainnet), m/t (testnet)",
                "segwit_support": True,
                "lightning_network": False
            }
        except Exception as e:
            self.logger.error(f"Error getting Litecoin-specific info: {e}")
            return {}

    def get_litecoin_features(self) -> Dict[str, Any]:
        """Get Litecoin-specific features"""
        try:
            return {
                "proof_of_work": True,
                "scrypt_algorithm": True,
                "segwit_support": True,
                "lightning_network": False,
                "atomic_swaps": True,
                "confidential_transactions": False,
                "smart_contracts": False,
                "token_support": False,
                "fast_transactions": True,
                "low_fees": True,
                "decentralized": True,
                "open_source": True
            }
        except Exception as e:
            self.logger.error(f"Error getting Litecoin features: {e}")
            return {}

    def validate_litecoin_address(self, address: str) -> bool:
        """Validate Litecoin address format"""
        try:
            # Basic Litecoin address validation
            if not address:
                return False
            
            # Check length (Litecoin addresses are typically 26-35 characters)
            if len(address) < 26 or len(address) > 35:
                return False
            
            # Check prefix (L for mainnet, m/t for testnet)
            if not (address.startswith('L') or address.startswith('m') or address.startswith('t')):
                return False
            
            # Basic Base58Check validation
            valid_chars = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
            return all(c in valid_chars for c in address)
        except:
            return False

    # ===== Address Uniqueness Methods =====

    def generate_new_address(self, index: int = None) -> Optional[Dict]:
        """Generate a new unique Litecoin address for the wallet"""
        try:
            # Use provided index or find next available
            if index is None:
                existing_addresses = self.session.query(CryptoAddress).filter_by(
                    account_id=self.account_id,
                    currency_code=self.symbol
                ).all()
                index = len(existing_addresses)
            
            # Litecoin uses the LTC HD wallet
            mnemonic_key = f"{self.symbol}_MNEMONIC"
            mnemonic = config(mnemonic_key, default=None)
            
            if not mnemonic:
                self.logger.error(f"No mnemonic configured for {self.symbol}")
                return None
            
            ltc_wallet = LTC()
            wallet = ltc_wallet.from_mnemonic(mnemonic=mnemonic)
            
            # Create new address
            user_address, priv_key, pub_key = wallet.new_address(index=index)
            
            # Check for address collision (extremely unlikely but good practice)
            if self._address_exists(user_address):
                self.logger.warning(f"Address collision detected for {user_address}, regenerating...")
                return self.generate_new_address(index + 1)
            
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
            self.logger.error(f"Error generating new Litecoin address: {e}")
            return None

    def _address_exists(self, address: str) -> bool:
        """Check if an address already exists in the database"""
        try:
            existing_address = self.session.query(CryptoAddress).filter_by(
                address=address,
                currency_code=self.symbol
            ).first()
            return existing_address is not None
        except Exception as e:
            self.logger.error(f"Error checking address existence: {e}")
            return False

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
                        "balance_ltc": balance["balance_ltc"],
                        "balance": balance["balance"]
                    }
                    address_balances.append(address_balance)
                    total_balance += balance["balance_ltc"]
            
            return {
                "user_id": self.user_id,
                "account_id": self.account_id,
                "symbol": self.symbol,
                "total_balance_ltc": total_balance,
                "addresses": addresses,
                "address_balances": address_balances,
                "network": self.ltc_config.network
            }
        except Exception as e:
            self.logger.error(f"Error getting wallet summary: {e}")
            return {}

    def validate_address_uniqueness(self, address: str) -> Dict[str, Any]:
        """Validate that an address is unique and properly formatted"""
        try:
            # Check if address is valid Litecoin format
            is_valid = self.validate_litecoin_address(address)
            
            # Check if address exists in database
            exists_in_db = self._address_exists(address)
            
            # Check if address exists on blockchain (optional, for extra verification)
            blockchain_info = self.get_address_info(address) if is_valid else None
            
            return {
                "address": address,
                "is_valid_format": is_valid,
                "exists_in_database": exists_in_db,
                "exists_on_blockchain": blockchain_info is not None,
                "is_unique": not exists_in_db,
                "blockchain_info": blockchain_info
            }
        except Exception as e:
            self.logger.error(f"Error validating address uniqueness: {e}")
            return {
                "address": address,
                "is_valid_format": False,
                "exists_in_database": False,
                "exists_on_blockchain": False,
                "is_unique": False,
                "error": str(e)
            }

    def get_address_generation_stats(self) -> Dict[str, Any]:
        """Get statistics about address generation for this wallet"""
        try:
            addresses = self.session.query(CryptoAddress).filter_by(
                account_id=self.account_id,
                currency_code=self.symbol
            ).all()
            
            total_addresses = len(addresses)
            active_addresses = len([addr for addr in addresses if addr.is_active])
            
            # Get unique addresses (check for any duplicates)
            unique_addresses = len(set(addr.address for addr in addresses))
            
            return {
                "total_addresses": total_addresses,
                "active_addresses": active_addresses,
                "unique_addresses": unique_addresses,
                "has_duplicates": total_addresses != unique_addresses,
                "duplicate_count": total_addresses - unique_addresses if total_addresses != unique_addresses else 0
            }
        except Exception as e:
            self.logger.error(f"Error getting address generation stats: {e}")
            return {}

    def regenerate_address_if_collision(self, address: str) -> Optional[Dict]:
        """Regenerate address if a collision is detected"""
        try:
            if self._address_exists(address):
                self.logger.warning(f"Address collision detected for {address}, regenerating...")
                return self.generate_new_address()
            return None
        except Exception as e:
            self.logger.error(f"Error regenerating address: {e}")
            return None

    def ensure_address_uniqueness(self, max_attempts: int = 10) -> Optional[Dict]:
        """Generate a new address with guaranteed uniqueness"""
        try:
            for attempt in range(max_attempts):
                new_address = self.generate_new_address()
                if new_address:
                    # Double-check uniqueness
                    if not self._address_exists(new_address["address"]):
                        self.logger.info(f"Generated unique address on attempt {attempt + 1}")
                        return new_address
                    else:
                        self.logger.warning(f"Address collision on attempt {attempt + 1}, retrying...")
            
            self.logger.error(f"Failed to generate unique address after {max_attempts} attempts")
            return None
            
        except Exception as e:
            self.logger.error(f"Error ensuring address uniqueness: {e}")
            return None 