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
from ..HD import TRX  # Tron uses TRX class
from cryptography.fernet import Fernet
import base64


class TronConfig(BaseModel):
    """Pydantic model for Tron configuration"""
    api_key: str
    network: str = "mainnet"
    base_url: str = ""
    timeout: int = 30


@dataclass
class TronWalletConfig:
    """Configuration for Tron client"""
    api_key: str
    network: str = "mainnet"
    base_url: str = ""
    timeout: int = 30

    @classmethod
    def testnet(cls, api_key: str) -> 'TronWalletConfig':
        return cls(
            api_key=api_key,
            network="testnet",
            base_url="https://api.shasta.trongrid.io"
        )

    @classmethod
    def mainnet(cls, api_key: str) -> 'TronWalletConfig':
        return cls(
            api_key=api_key,
            network="mainnet",
            base_url="https://api.trongrid.io"
        )


class TronWallet:
    account_id = None

    def __init__(self, user_id: int, config: TronWalletConfig, session: Session, logger: logging.Logger = None):
        self.user_id = user_id
        self.label = "Tron Wallet"
        self.account_number = generate_unique_account_number(session=session, length=10)
        self.session = session
        self.logger = logger or setup_logging()
        self.symbol = "TRX"
        self.app_secret = config('APP_SECRET', default='your-app-secret-key')
        self.tron_config = config
        self.session_request = requests.Session()
        self.session_request.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'TronWallet/1.0',
            'TRON-PRO-API-KEY': config.api_key
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
        """Create a new Tron wallet account in the database."""
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
            self.logger.error(f"[Tron] Failed to create wallet for user {self.user_id}: {e!r}")
            self.logger.error(traceback.format_exc())
            raise  # Re-raise the exception so the wallet service can handle it

    def create_address(self):
        """Create a new Tron address for the wallet with uniqueness guarantees."""
        try:
            self.logger.info(f"Creating address for user {self.user_id}")
            
            # Use the new method with uniqueness guarantees
            new_address = self.ensure_address_uniqueness()
            if new_address:
                self.logger.info(f"Created unique user address: {new_address['address']}")
            else:
                self.logger.error("Failed to create unique address")
                raise Exception("Failed to create unique Tron address")
                
        except Exception as e:
            self.logger.error(f"[Tron] Failed to create address for user {self.user_id}: {e!r}")
            self.logger.error(traceback.format_exc())
            raise  # Re-raise the exception so the wallet service can handle it
        finally:
            self.logger.info(f"Done creating address for user {self.user_id}")

    # ===== Tron API Methods =====
    
    def make_request(self, endpoint: str, method: str = "GET", data: dict = None) -> Optional[Dict]:
        """Make a request to Tron API"""
        url = f"{self.tron_config.base_url}{endpoint}"
        
        try:
            if method.upper() == "GET":
                response = self.session_request.get(url, timeout=self.tron_config.timeout)
            elif method.upper() == "POST":
                response = self.session_request.post(url, json=data, timeout=self.tron_config.timeout)
            else:
                self.logger.error(f"Unsupported HTTP method: {method}")
                return None
                
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request failed: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
            return None

    def test_connection(self) -> bool:
        """Test the connection to Tron API"""
        self.logger.info("Testing Tron API connection...")
        result = self.make_request("/v1/accounts")
        return result is not None and "data" in result

    def get_account_info(self, address: str) -> Optional[Dict]:
        """Get account information"""
        result = self.make_request(f"/v1/accounts/{address}")
        return result.get("data", [{}])[0] if result and "data" in result else None

    def get_account_balance(self, address: str) -> Optional[Dict]:
        """Get account balance"""
        result = self.make_request(f"/v1/accounts/{address}")
        if result and "data" in result and result["data"]:
            account_data = result["data"][0]
            return {
                "address": address,
                "balance": account_data.get("balance", 0),
                "balance_trx": account_data.get("balance", 0) / (10 ** 6),  # TRX has 6 decimals
                "frozen": account_data.get("frozen", []),
                "tokens": account_data.get("trc20", [])
            }
        return None

    def get_transaction_info(self, tx_id: str) -> Optional[Dict]:
        """Get transaction information"""
        result = self.make_request(f"/v1/transactions/{tx_id}")
        return result.get("data", [{}])[0] if result and "data" in result else None

    def get_transactions_by_address(self, address: str, limit: int = 20) -> Optional[List[Dict]]:
        """Get transactions for an address"""
        result = self.make_request(f"/v1/accounts/{address}/transactions?limit={limit}")
        return result.get("data", []) if result and "data" in result else []

    def get_block_info(self, block_number: int = None) -> Optional[Dict]:
        """Get block information"""
        if block_number:
            result = self.make_request(f"/v1/blocks/{block_number}")
        else:
            result = self.make_request("/v1/blocks/latest")
        return result.get("data", [{}])[0] if result and "data" in result else None

    def get_network_info(self) -> Optional[Dict]:
        """Get network information"""
        result = self.make_request("/v1/networks")
        return result.get("data", [{}])[0] if result and "data" in result else None

    def get_token_info(self, contract_address: str) -> Optional[Dict]:
        """Get TRC-20 token information"""
        result = self.make_request(f"/v1/contracts/{contract_address}")
        return result.get("data", [{}])[0] if result and "data" in result else None

    def get_token_balance(self, contract_address: str, address: str) -> Optional[Dict]:
        """Get TRC-20 token balance"""
        result = self.make_request(f"/v1/accounts/{address}/tokens/trc20/{contract_address}")
        return result.get("data", [{}])[0] if result and "data" in result else None

    def validate_address(self, address: str) -> bool:
        """Validate Tron address format"""
        try:
            # Tron addresses start with 'T' and are 34 characters long
            if not address.startswith("T"):
                return False
            if len(address) != 34:
                return False
            # Basic format validation
            return all(c in "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz" for c in address)
        except:
            return False

    def get_tron_specific_info(self) -> Dict[str, Any]:
        """Get Tron-specific information"""
        try:
            network_info = self.get_network_info()
            
            return {
                "network": "Tron",
                "chain_id": 1 if self.tron_config.network == "mainnet" else 2,  # Mainnet/Testnet
                "consensus": "Delegated Proof of Stake (DPoS)",
                "block_time": "~3 seconds",
                "finality": "~19 seconds (6 blocks)",
                "native_token": "TRX",
                "decimals": 6,
                "address_format": "Base58Check",
                "address_prefix": "T",
                "smart_contracts": "TRC-20, TRC-10",
                "virtual_machine": "TVM (Tron Virtual Machine)",
                "network_info": network_info
            }
        except Exception as e:
            self.logger.error(f"Error getting Tron-specific info: {e}")
            return {}

    def get_tron_features(self) -> Dict[str, Any]:
        """Get Tron-specific features"""
        try:
            return {
                "smart_contracts": True,
                "trc20_tokens": True,
                "trc10_tokens": True,
                "delegated_proof_of_stake": True,
                "high_throughput": True,
                "low_fees": True,
                "energy_system": True,
                "resource_sharing": True,
                "governance": True,
                "decentralized_storage": True
            }
        except Exception as e:
            self.logger.error(f"Error getting Tron features: {e}")
            return {}

    # ===== Address Uniqueness Methods =====

    def generate_new_address(self, index: int = None) -> Optional[Dict]:
        """Generate a new unique Tron address for the wallet"""
        try:
            # Use provided index or find next available
            if index is None:
                existing_addresses = self.session.query(CryptoAddress).filter_by(
                    account_id=self.account_id,
                    currency_code=self.symbol
                ).all()
                index = len(existing_addresses)
            
            # Tron uses the TRX HD wallet
            mnemonic_key = f"{self.symbol}_MNEMONIC"
            mnemonic = config(mnemonic_key, default=None)
            
            if not mnemonic:
                self.logger.error(f"No mnemonic configured for {self.symbol}")
                return None
            
            trx_wallet = TRX()
            wallet = trx_wallet.from_mnemonic(mnemonic=mnemonic)
            
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
            self.logger.error(f"Error generating new Tron address: {e}")
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
                balance = self.get_account_balance(addr_info["address"])
                if balance:
                    address_balance = {
                        "address": addr_info["address"],
                        "label": addr_info["label"],
                        "balance_trx": balance["balance_trx"],
                        "balance": balance["balance"]
                    }
                    address_balances.append(address_balance)
                    total_balance += balance["balance_trx"]
            
            return {
                "user_id": self.user_id,
                "account_id": self.account_id,
                "symbol": self.symbol,
                "total_balance_trx": total_balance,
                "addresses": addresses,
                "address_balances": address_balances,
                "network": self.tron_config.network
            }
        except Exception as e:
            self.logger.error(f"Error getting wallet summary: {e}")
            return {}

    def validate_address_uniqueness(self, address: str) -> Dict[str, Any]:
        """Validate that an address is unique and properly formatted"""
        try:
            # Check if address is valid Tron format
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