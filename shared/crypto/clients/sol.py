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
from cryptography.fernet import Fernet
import base64

# Solana SDK imports
try:
    from solana.rpc.api import Client
    from solana.keypair import Keypair
    from solana.publickey import PublicKey
    from solana.transaction import Transaction
    from solana.system_program import TransferParams, transfer
    from solana.rpc.commitment import Commitment
    from solana.rpc.types import TxOpts
    import base58
    SOLANA_AVAILABLE = True
except ImportError:
    SOLANA_AVAILABLE = False
    print("⚠️  Solana SDK not available. Install with: pip install solana solders")


class AlchemySolanaConfig(BaseModel):
    """Pydantic model for Alchemy Solana configuration"""
    api_key: str
    network: str = "mainnet"
    base_url: str = ""
    ws_url: str = ""


@dataclass
class SolanaConfig:
    """Configuration for Solana client"""
    api_key: str
    network: str = "mainnet"
    base_url: str = ""
    ws_url: str = ""
    timeout: int = 30
    commitment: str = "confirmed"

    @classmethod
    def testnet(cls, api_key: str) -> 'SolanaConfig':
        return cls(
            api_key=api_key,
            network="devnet",
            base_url=f"https://solana-devnet.g.alchemy.com/v2/{api_key}",
            ws_url=f"wss://solana-devnet.g.alchemy.com/v2/{api_key}"
        )

    @classmethod
    def mainnet(cls, api_key: str) -> 'SolanaConfig':
        return cls(
            api_key=api_key,
            network="mainnet",
            base_url=f"https://solana-mainnet.g.alchemy.com/v2/{api_key}",
            ws_url=f"wss://solana-mainnet.g.alchemy.com/v2/{api_key}"
        )


class SOLWallet:
    account_id = None

    def __init__(self, user_id: int, config: SolanaConfig, session: Session, logger: logging.Logger = None):
        self.user_id = user_id
        self.label = "SOL Wallet"
        self.account_number = generate_unique_account_number(session=session, length=10)
        self.session = session
        self.logger = logger or setup_logging()
        self.symbol = "SOL"
        self.app_secret = config('APP_SECRET', default='your-app-secret-key')
        self.config = config
        self.session_request = requests.Session()
        self.session_request.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'SOLWallet/1.0'
        })
        
        # Initialize Solana client if SDK is available
        if SOLANA_AVAILABLE:
            if config.network == "mainnet":
                self.solana_client = Client("https://api.mainnet-beta.solana.com")
            else:
                self.solana_client = Client("https://api.devnet.solana.com")
        else:
            self.solana_client = None
            self.logger.warning("Solana SDK not available. Install with: pip install solana solders")
        
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
        """Create a new SOL wallet account in the database."""
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
            self.logger.error(f"[SOL] Failed to create wallet for user {self.user_id}: {e!r}")
            self.logger.error(traceback.format_exc())
            raise  # Re-raise the exception so the wallet service can handle it

    def create_address(self):
        """Create a new SOL address for the wallet with uniqueness guarantees."""
        try:
            self.logger.info(f"Creating address for user {self.user_id}")
            
            if SOLANA_AVAILABLE:
                # Use the new method with uniqueness guarantees
                new_address = self.ensure_address_uniqueness()
                if new_address:
                    self.logger.info(f"Created unique user address: {new_address['address']}")
                else:
                    self.logger.error("Failed to create unique address")
                    raise Exception("Failed to create unique Solana address")
            else:
                # Fallback: create a placeholder address
                placeholder_address = "11111111111111111111111111111111"  # System Program
                self.logger.warning(f"Created placeholder address: {placeholder_address} (Solana SDK not available)")
                
        except Exception as e:
            self.logger.error(f"[SOL] Failed to create address for user {self.user_id}: {e!r}")
            self.logger.error(traceback.format_exc())
            raise  # Re-raise the exception so the wallet service can handle it
        finally:
            self.logger.info(f"Done creating address for user {self.user_id}")

    # ===== Solana API Methods =====
    
    def make_request(self, method: str, params: list = None) -> Optional[Dict]:
        """Make a JSON-RPC request to Solana API"""
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
        """Test the connection to Solana API"""
        self.logger.info("Testing Solana API connection...")
        result = self.make_request("getSlot")
        return result is not None and "result" in result

    def get_latest_slot(self) -> Optional[int]:
        """Get the latest slot number"""
        result = self.make_request("getSlot")
        if result and "result" in result:
            return result["result"]
        return None

    def get_balance(self, address: str) -> Optional[Dict]:
        """Get account balance in lamports and SOL"""
        result = self.make_request("getBalance", [address])
        if result and "result" in result:
            balance_data = result["result"]
            lamports = balance_data.get("value", 0)
            sol_balance = lamports / 1_000_000_000  # Convert lamports to SOL
            
            return {
                "address": address,
                "lamports": lamports,
                "sol_balance": sol_balance,
                "confirmed": True
            }
        return None

    def get_account_info(self, address: str) -> Optional[Dict]:
        """Get comprehensive account information"""
        result = self.make_request("getAccountInfo", [address, {"encoding": "jsonParsed"}])
        if result and "result" in result:
            account_data = result["result"]
            if account_data and "value" in account_data:
                account_info = account_data["value"]
                
                return {
                    "address": address,
                    "lamports": account_info.get("lamports", 0),
                    "sol_balance": account_info.get("lamports", 0) / 1_000_000_000,
                    "owner": account_info.get("owner"),
                    "executable": account_info.get("executable", False),
                    "rent_epoch": account_info.get("rentEpoch"),
                    "data": account_info.get("data")
                }
        return None

    def get_token_accounts(self, address: str) -> Optional[List[Dict]]:
        """Get token accounts for an address"""
        result = self.make_request("getTokenAccountsByOwner", [
            address,
            {"programId": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"},
            {"encoding": "jsonParsed"}
        ])
        
        if result and "result" in result:
            accounts = result["result"].get("value", [])
            token_accounts = []
            
            for account in accounts:
                account_data = account.get("account", {}).get("data", {}).get("parsed", {})
                if account_data:
                    token_accounts.append({
                        "mint": account_data.get("info", {}).get("mint"),
                        "owner": account_data.get("info", {}).get("owner"),
                        "amount": account_data.get("info", {}).get("tokenAmount", {}).get("uiAmount"),
                        "decimals": account_data.get("info", {}).get("tokenAmount", {}).get("decimals")
                    })
            
            return token_accounts
        return None

    def get_recent_blocks(self, count: int = 5) -> List[Dict]:
        """Get information about recent blocks"""
        blocks = []
        latest_slot = self.get_latest_slot()
        
        if latest_slot is None:
            return blocks
        
        for i in range(count):
            slot = latest_slot - i
            if slot >= 0:
                block_data = self.get_block_by_slot(slot)
                if block_data:
                    block_info = {
                        "slot": slot,
                        "blockhash": block_data.get("blockhash"),
                        "parent_slot": block_data.get("parentSlot"),
                        "transactions_count": len(block_data.get("transactions", [])),
                        "rewards": block_data.get("rewards", [])
                    }
                    blocks.append(block_info)
        
        return blocks

    def get_block_by_slot(self, slot: int) -> Optional[Dict]:
        """Get block information by slot"""
        result = self.make_request("getBlock", [slot, {"encoding": "jsonParsed"}])
        return result.get("result") if result else None

    def get_block_by_signature(self, signature: str) -> Optional[Dict]:
        """Get block information by signature"""
        result = self.make_request("getBlock", [signature, {"encoding": "jsonParsed"}])
        return result.get("result") if result else None

    def get_signature_status(self, signature: str) -> Optional[Dict]:
        """Get transaction signature status"""
        result = self.make_request("getSignatureStatuses", [[signature]])
        if result and "result" in result:
            statuses = result["result"].get("value", [])
            return statuses[0] if statuses else None
        return None

    def get_transaction(self, signature: str) -> Optional[Dict]:
        """Get transaction details"""
        result = self.make_request("getTransaction", [signature, {"encoding": "jsonParsed"}])
        return result.get("result") if result else None

    def get_transaction_count(self, address: str) -> Optional[int]:
        """Get transaction count for an address"""
        result = self.make_request("getSignatureForAddress", [address])
        if result and "result" in result:
            signatures = result["result"].get("value", [])
            return len(signatures)
        return None

    def get_supply(self) -> Optional[Dict]:
        """Get current supply information"""
        result = self.make_request("getSupply")
        if result and "result" in result:
            supply_data = result["result"].get("value", {})
            return {
                "total": supply_data.get("total"),
                "circulating": supply_data.get("circulating"),
                "non_circulating": supply_data.get("nonCirculating")
            }
        return None

    def get_version(self) -> Optional[Dict]:
        """Get Solana version information"""
        result = self.make_request("getVersion")
        return result.get("result") if result else None

    def get_cluster_nodes(self) -> Optional[List[Dict]]:
        """Get cluster nodes information"""
        result = self.make_request("getClusterNodes")
        return result.get("result") if result else None

    def get_leader_schedule(self, slot: int = None) -> Optional[Dict]:
        """Get leader schedule"""
        params = [slot] if slot else []
        result = self.make_request("getLeaderSchedule", params)
        return result.get("result") if result else None

    # ===== Solana-specific methods =====

    def get_solana_specific_info(self) -> Dict[str, Any]:
        """Get Solana-specific information"""
        try:
            latest_slot = self.get_latest_slot()
            supply = self.get_supply()
            version = self.get_version()
            
            return {
                "network": "Solana",
                "latest_slot": latest_slot,
                "supply": supply,
                "version": version,
                "consensus": "Proof of Stake",
                "block_time": "~400ms",
                "finality": "~400ms",
                "native_token": "SOL"
            }
        except Exception as e:
            self.logger.error(f"Error getting Solana-specific info: {e}")
            return {}

    def get_network_info(self) -> Dict[str, Any]:
        """Get network information"""
        try:
            latest_slot = self.get_latest_slot()
            supply = self.get_supply()
            
            return {
                "network": self.config.network,
                "latest_slot": latest_slot,
                "supply": supply,
                "base_url": self.config.base_url,
                "ws_url": self.config.ws_url
            }
        except Exception as e:
            self.logger.error(f"Error getting network info: {e}")
            return {}

    def validate_address(self, address: str) -> bool:
        """Validate Solana address format"""
        try:
            if SOLANA_AVAILABLE:
                # Use Solana SDK to validate
                PublicKey(address)
                return True
            else:
                # Basic validation: check length and base58 format
                if len(address) != 44:  # Solana addresses are 44 characters
                    return False
                # Check if it's valid base58
                try:
                    base58.b58decode(address)
                    return True
                except:
                    return False
        except:
            return False

    def get_blockchain_info(self) -> Dict[str, Any]:
        """Get comprehensive blockchain information"""
        try:
            latest_slot = self.get_latest_slot()
            supply = self.get_supply()
            recent_blocks = self.get_recent_blocks(3)
            
            return {
                "network": self.config.network,
                "latest_slot": latest_slot,
                "supply": supply,
                "recent_blocks": recent_blocks,
                "connection_status": self.test_connection()
            }
        except Exception as e:
            self.logger.error(f"Error getting blockchain info: {e}")
            return {}

    def get_token_balance(self, token_mint: str, wallet_address: str) -> Optional[Dict]:
        """Get SPL token balance for a specific token"""
        try:
            # Get all token accounts for the wallet
            token_accounts = self.get_token_accounts(wallet_address)
            if token_accounts:
                for account in token_accounts:
                    if account.get("mint") == token_mint:
                        return {
                            "mint": token_mint,
                            "wallet_address": wallet_address,
                            "amount": account.get("amount"),
                            "decimals": account.get("decimals")
                        }
            return None
        except Exception as e:
            self.logger.error(f"Error getting token balance: {e}")
            return None

    def get_account_info_comprehensive(self, address: str) -> Optional[Dict]:
        """Get comprehensive account information"""
        try:
            balance = self.get_balance(address)
            account_info = self.get_account_info(address)
            token_accounts = self.get_token_accounts(address)
            tx_count = self.get_transaction_count(address)
            
            return {
                "address": address,
                "balance": balance,
                "account_info": account_info,
                "token_accounts": token_accounts,
                "transaction_count": tx_count
            }
        except Exception as e:
            self.logger.error(f"Error getting comprehensive account info: {e}")
            return None

    def get_solana_features(self) -> Dict[str, Any]:
        """Get Solana-specific features"""
        try:
            return {
                "high_performance": True,
                "fast_finality": "~400ms",
                "high_throughput": "65,000+ TPS",
                "low_fees": True,
                "spl_tokens": True,
                "programs": True,
                "cross_program_invocation": True,
                "parallel_processing": True
            }
        except Exception as e:
            self.logger.error(f"Error getting Solana features: {e}")
            return {}

    def get_spl_token_info(self, token_mint: str) -> Optional[Dict]:
        """Get SPL token information"""
        try:
            result = self.make_request("getAccountInfo", [token_mint, {"encoding": "jsonParsed"}])
            if result and "result" in result:
                account_data = result["result"]
                if account_data and "value" in account_data:
                    account_info = account_data["value"]
                    data = account_info.get("data", {}).get("parsed", {})
                    
                    if data and data.get("type") == "mint":
                        mint_info = data.get("info", {})
                        return {
                            "mint": token_mint,
                            "decimals": mint_info.get("decimals"),
                            "freeze_authority": mint_info.get("freezeAuthority"),
                            "mint_authority": mint_info.get("mintAuthority"),
                            "supply": mint_info.get("supply"),
                            "is_initialized": mint_info.get("isInitialized")
                        }
            return None
        except Exception as e:
            self.logger.error(f"Error getting SPL token info: {e}")
            return None

    def generate_new_address(self, index: int = None) -> Optional[Dict]:
        """Generate a new unique Solana address for the wallet"""
        try:
            if not SOLANA_AVAILABLE:
                self.logger.error("Solana SDK not available")
                return None
            
            # Use provided index or find next available
            if index is None:
                existing_addresses = self.session.query(CryptoAddress).filter_by(
                    account_id=self.account_id,
                    currency_code=self.symbol
                ).all()
                index = len(existing_addresses)
            
            # Generate a new Solana keypair
            keypair = Keypair()
            public_key = keypair.public_key
            private_key = base58.b58encode(keypair.secret_key).decode()
            
            # Check for address collision (extremely unlikely but good practice)
            if self._address_exists(str(public_key)):
                self.logger.warning(f"Address collision detected for {public_key}, regenerating...")
                return self.generate_new_address(index + 1)
            
            # Encrypt private key before storing
            encrypted_private_key = self.encrypt_private_key(private_key)
            
            # Create crypto address record
            crypto_address = CryptoAddress(
                account_id=self.account_id,
                address=str(public_key),
                label=f"{self.label} Address {index + 1}",
                is_active=True,
                currency_code=self.symbol,
                address_type="keypair",
                private_key=encrypted_private_key,
                public_key=str(public_key)
            )
            self.session.add(crypto_address)
            
            return {
                "address": str(public_key),
                "index": index,
                "public_key": str(public_key),
                "label": crypto_address.label
            }
            
        except Exception as e:
            self.logger.error(f"Error generating new Solana address: {e}")
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
                        "balance_sol": balance["sol_balance"],
                        "balance_lamports": balance["lamports"]
                    }
                    address_balances.append(address_balance)
                    total_balance += balance["sol_balance"]
            
            return {
                "user_id": self.user_id,
                "account_id": self.account_id,
                "symbol": self.symbol,
                "total_balance_sol": total_balance,
                "addresses": addresses,
                "address_balances": address_balances,
                "network": self.config.network
            }
        except Exception as e:
            self.logger.error(f"Error getting wallet summary: {e}")
            return {}

    def validate_address_uniqueness(self, address: str) -> Dict[str, Any]:
        """Validate that an address is unique and properly formatted"""
        try:
            # Check if address is valid Solana format
            is_valid = self.validate_address(address)
            
            # Check if address exists in database
            exists_in_db = self._address_exists(address)
            
            # Check if address exists on blockchain (optional, for extra verification)
            blockchain_info = self.get_account_info(address) if is_valid else None
            
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