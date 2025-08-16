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
from decouple import config as env_config
from ..HD import TRX  # Tron uses TRX class
from cryptography.fernet import Fernet
import base64
import binascii


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

    def __init__(self, user_id: int, tron_config: TronWalletConfig, session: Session, logger: logging.Logger = None):
        self.user_id = user_id
        self.label = "Tron Wallet"
        self.account_number = generate_unique_account_number(session=session, length=10)
        self.session = session
        self.logger = logger or setup_logging()
        self.symbol = "TRX"
        self.app_secret = env_config('APP_SECRET', default='your-app-secret-key')
        self.tron_config = tron_config
        self.session_request = requests.Session()
        self.session_request.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'TronWallet/1.0',
            'TRON-PRO-API-KEY': tron_config.api_key
        })

    # ===== Address helpers =====

    @staticmethod
    def _to_base58_address(maybe_hex: str) -> str:
        """Convert 41-prefixed hex TRON address to base58check using tronpy.keys."""
        try:
            if not maybe_hex:
                return maybe_hex
            if maybe_hex.startswith('T'):
                return maybe_hex
            hex_str = maybe_hex.lower().replace('0x', '')
            if not hex_str.startswith('41'):
                return maybe_hex
            from tronpy import keys as tron_keys
            return tron_keys.to_base58check_address(bytes.fromhex(hex_str))
        except Exception:
            return maybe_hex
        
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
        """Get transaction info (prefer solidity API for confirmed data with blockNumber)."""
        # Try solidity endpoint first (GET info with blockNumber once confirmed)
        info = self.make_request("/walletsolidity/gettransactioninfobyid", method="POST", data={"value": tx_id})
        if info and isinstance(info, dict) and (info.get("id") or info.get("blockNumber") or info.get("receipt")):
            return info
        # Fallback to full node
        info = self.make_request("/wallet/gettransactioninfobyid", method="POST", data={"value": tx_id})
        if info and isinstance(info, dict):
            return info
        # As a last resort, try TronGrid v1 (may not always be enabled for all resources)
        grid = self.make_request(f"/v1/transactions/{tx_id}", method="GET")
        if grid and isinstance(grid, dict):
            if grid.get("data"):
                return grid["data"][0]
            return grid
        return None

    def get_transactions_by_address(self, address: str, limit: int = 20) -> Optional[List[Dict]]:
        """
        Get transactions for an address and normalize entries to a unified shape that our
        monitor can consume easily.

        Input payload example (TronGrid v1):
        {"data": [ {"txID": "...", "raw_data": {"contract":[{"parameter":{"value":{"owner_address":"41...","to_address":"41...","amount":2000000}}} ]}, "blockNumber": 56938742, ... }], "success": true}

        Returns a list of dicts with keys: txid, from, to, value (sun), blockNumber
        """
        # Prefer TronGrid v1 and filter for incoming transfers
        res = self.make_request(
            f"/v1/accounts/{address}/transactions?limit={limit}&only_to=true"
        )
        data_list = []
        self.logger.info(f"TronGrid v1 transactions for {address}: {res}")
        if res and isinstance(res, dict) and res.get("data") is not None:
            data_list = res.get("data", [])
            self.logger.info(f"TronGrid v1 transactions for {address}: {data_list}")
        else:
            # Fallback: try without only_to filter
            res = self.make_request(f"/v1/accounts/{address}/transactions?limit={limit}")
            if res and isinstance(res, dict):
                data_list = res.get("data", [])

        normalized: List[Dict] = []
        for item in data_list:
            try:
                txid = item.get("txID") or item.get("txid") or item.get("hash") or item.get("transaction_id")
                blk = item.get("blockNumber") or item.get("block") or 0
                from_addr = item.get("from") or item.get("ownerAddress") or item.get("owner_address")
                to_addr = item.get("to") or item.get("toAddress") or item.get("to_address")
                amount_sun = item.get("amount") or item.get("value")

                if not (from_addr and to_addr and amount_sun):
                    rd = item.get("raw_data") or {}
                    contracts = rd.get("contract") or []
                    if contracts:
                        c0 = contracts[0]
                        pv = ((c0.get("parameter") or {}).get("value") or {})
                        from_addr = from_addr or pv.get("owner_address") or pv.get("from")
                        to_addr = to_addr or pv.get("to_address") or pv.get("to")
                        amount_sun = amount_sun or pv.get("amount")

                # Normalize addresses to base58 (convert 41-hex to base58 if needed)
                from_b58 = self._to_base58_address(from_addr) if from_addr else None
                to_b58 = self._to_base58_address(to_addr) if to_addr else None

                if not (txid and to_b58 and amount_sun is not None):
                    continue

                normalized.append({
                    "txid": txid,
                    "from": from_b58,
                    "to": to_b58,
                    "value": int(amount_sun),  # sun
                    "blockNumber": int(blk or 0)
                })
            except Exception as e:
                self.logger.error("Failed to normalize TRX tx item: %s", e)
                continue
        self.logger.info(f"Normalized transactions: {normalized}")
        return normalized

    def get_trc20_transactions_by_address(
        self,
        address: str,
        limit: int = 20,
        only_to: bool = True,
        contract_addresses: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get TRC-20 token transfer transactions for an address via TronGrid v1 and
        normalize to a consistent shape.

        - Endpoint (Shasta): /v1/accounts/{address}/transactions/trc20
        - Docs: https://developers.tron.network/reference/

        Returns a list of dicts with at least:
          {
            "txid": str,                 # transaction_id
            "from": str,                 # base58 address
            "to": str,                   # base58 address
            "token_symbol": str,
            "token_address": str,
            "decimals": int,
            "value_smallest": int,       # integer value in token smallest units
            "block_timestamp": int,      # ms
            "type": str                  # typically "Transfer"
          }
        """
        try:
            url = f"/v1/accounts/{address}/transactions/trc20?limit={limit}"
            if only_to:
                url += "&only_to=true"

            result = self.make_request(url, method="GET")
            items = []
            if result and isinstance(result, dict):
                items = result.get("data", []) or []

            normalized: List[Dict[str, Any]] = []
            for item in items:
                try:
                    txid = item.get("transaction_id")
                    from_addr = item.get("from")
                    to_addr = item.get("to")
                    token_info = item.get("token_info") or {}
                    token_symbol = token_info.get("symbol")
                    token_address = token_info.get("address")
                    decimals = int(token_info.get("decimals", 0))
                    value_str = item.get("value")
                    value_smallest = int(value_str) if value_str is not None else 0
                    block_ts = int(item.get("block_timestamp") or 0)
                    tx_type = item.get("type", "Transfer")

                    # Optional filtering by specific token contracts
                    if contract_addresses and token_address not in contract_addresses:
                        continue

                    # Basic validation
                    if not (txid and to_addr and value_smallest is not None and token_address):
                        continue

                    normalized.append({
                        "txid": txid,
                        "from": from_addr,
                        "to": to_addr,
                        "token_symbol": token_symbol,
                        "token_address": token_address,
                        "decimals": decimals,
                        "value_smallest": value_smallest,
                        "block_timestamp": block_ts,
                        "type": tx_type,
                    })
                except Exception as e:
                    self.logger.error("Failed to normalize TRC20 tx item: %s", e)
                    continue

            return normalized
        except Exception as e:
            self.logger.error("Error fetching TRC20 transactions: %s", e)
            return []

    # ===== Token account helpers =====

    def create_token_account(self, token_symbol: str, token_decimals: int = 6, label: Optional[str] = None) -> Optional[Account]:
        """
        Create a CRYPTO account for a TRC-20 token (e.g., USDT) for this user.

        Notes:
        - The token account shares the same on-chain address as the TRX account.
        - We do NOT create a new CryptoAddress row to avoid duplicating the same address
          (the CryptoAddress.address column is globally unique). Token monitoring should
          reference the user's TRX address.
        - The account's precision_config is set with the provided token_decimals.
        """
        try:
            # Check if token account already exists
            existing = self.session.query(Account).filter_by(
                user_id=self.user_id,
                currency=token_symbol.upper(),
                account_type=AccountType.CRYPTO,
            ).first()
            if existing:
                self.logger.info("[%s] Token account already exists for user %s", token_symbol, self.user_id)
                return existing

            token_account = Account(
                user_id=self.user_id,
                balance=0,
                locked_amount=0,
                currency=token_symbol.upper(),
                account_type=AccountType.CRYPTO,
                account_number=generate_unique_account_number(session=self.session, length=10),
                label=label or f"{token_symbol.upper()} Account",
                precision_config={
                    "currency": token_symbol.upper(),
                    "decimals": token_decimals,
                    "smallest_unit": "units",
                    "parent_currency": "TRX"
                },
            )
            self.session.add(token_account)
            self.session.commit()
            self.session.refresh(token_account)
            self.logger.info("[%s] Created token account for user %s (id=%s)", token_symbol, self.user_id, token_account.id)
            return token_account
        except Exception as e:
            self.logger.error("Failed to create token account %s for user %s: %s", token_symbol, self.user_id, e)
            self.session.rollback()
            return None

    def create_usdt_account(self) -> Optional[Account]:
        """Convenience helper to create a USDT (TRC-20) account with 6 decimals."""
        return self.create_token_account("USDT", token_decimals=6, label="USDT Wallet")

    def get_block_info(self, block_number: int = None) -> Optional[Dict]:
        """Get block information from TronGrid (v1) with Shasta-compatible fallbacks."""
        try:
            if block_number is None:
                # Prefer Solidity API (GET) for latest block
                r = self.make_request("/walletsolidity/getnowblock", method="GET")
                if isinstance(r, dict) and r:
                    return r
                # Fallback to full node (POST)
                fr = self.make_request("/wallet/getnowblock", method="POST", data={})
                if isinstance(fr, dict) and fr:
                    return fr
                # Last resort: TronGrid v1 query for latest
                vg = self.make_request("/v1/blocks?limit=1&sort=-number", method="GET")
                if vg and isinstance(vg, dict) and vg.get("data"):
                    return vg["data"][0]
                return None
            else:
                # Specific block by number: try Solidity POST first
                r = self.make_request("/walletsolidity/getblockbynum", method="POST", data={"num": int(block_number)})
                if isinstance(r, dict) and r:
                    return r
                # Fallback to full node POST
                fr = self.make_request("/wallet/getblockbynum", method="POST", data={"num": int(block_number)})
                if isinstance(fr, dict) and fr:
                    return fr
                # Last resort: TronGrid v1
                vg = self.make_request(f"/v1/blocks/{block_number}", method="GET")
                if vg and isinstance(vg, dict) and vg.get("data"):
                    return vg["data"][0]
                return None
        except Exception as e:
            self.logger.error("Error fetching Tron block info: %s", e)
            return None

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
            mnemonic = env_config(mnemonic_key, default=None)
            
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
                new_address = self.generate_new_address(index=self.account_id)
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

    # ===== Sending Transactions (TRX) =====

    def send_transaction(self, to_address: str, amount_trx: float) -> Optional[Dict[str, Any]]:
        """
        Send a TRX transfer from the wallet's active address.

        Uses tronpy for signing and broadcasting. Requires `tronpy` to be installed.
        """
        try:
            # Lazy import to avoid hard dependency when unused
            from tronpy import Tron
            from tronpy.keys import PrivateKey
        except Exception as e:
            self.logger.error(f"tronpy is required for TRX withdrawals: {e}")
            raise

        try:
            # Get the active address for this account
            crypto_address = self.session.query(CryptoAddress).filter_by(
                account_id=self.account_id,
                currency_code=self.symbol,
                is_active=True
            ).first()

            if not crypto_address:
                raise ValueError(f"No active {self.symbol} address found for account {self.account_id}")

            # Decrypt private key
            private_key_plain = self.decrypt_private_key(crypto_address.private_key)

            # Select network
            network = 'mainnet' if self.tron_config.network == 'mainnet' else 'shasta'
            client = Tron(network=network)

            # Amount in Sun (1 TRX = 1_000_000 Sun)
            amount_sun = int(amount_trx * 1_000_000)

            txn = (
                client.trx
                .transfer(crypto_address.address, to_address, amount_sun)
                .build()
                .sign(PrivateKey(bytes.fromhex(private_key_plain)))
                .broadcast()
            )

            # tronpy returns a dict-like object with txid
            tx_id = txn.get('txid') if isinstance(txn, dict) else getattr(txn, 'txid', None)

            if not tx_id:
                raise ValueError("Failed to obtain TRX transaction id from broadcast response")

            self.logger.info(f"📤 TRX transaction sent: {amount_trx} TRX to {to_address}, txid={tx_id}")

            return {
                "status": "sent",
                "transaction_hash": tx_id,
                "from_address": crypto_address.address,
                "to_address": to_address,
                "amount_trx": amount_trx,
                "amount_sun": amount_sun,
            }
        except Exception as e:
            self.logger.error(f"❌ Error sending TRX transaction: {e}")
            raise

    # ===== Sending Transactions (TRC-20) =====

    def send_trc20_transfer(
        self,
        contract_address: str,
        to_address: str,
        amount_standard: float,
        decimals: int,
    ) -> Optional[Dict[str, Any]]:
        """
        Send a TRC-20 token transfer from the wallet's active TRX address.

        - contract_address: base58 contract address (e.g., USDT on Shasta)
        - to_address: recipient base58 address
        - amount_standard: human-readable token amount (e.g., 1.5 USDT)
        - decimals: token decimals (e.g., 6 for USDT)
        """
        try:
            from tronpy import Tron
            from tronpy.keys import PrivateKey
        except Exception as e:
            self.logger.error(f"tronpy is required for TRC20 withdrawals: {e}")
            raise

        try:
            # Use the active TRX address for signing
            crypto_address = self.session.query(CryptoAddress).filter_by(
                account_id=self.account_id,
                currency_code=self.symbol,
                is_active=True,
            ).first()
            if not crypto_address:
                raise ValueError(f"No active {self.symbol} address found for account {self.account_id}")

            private_key_plain = self.decrypt_private_key(crypto_address.private_key)
            network = 'mainnet' if self.tron_config.network == 'mainnet' else 'shasta'
            client = Tron(network=network)

            amount_smallest = int(round(amount_standard * (10 ** int(decimals or 0))))
            contract = client.get_contract(contract_address)

            txn = (
                contract.functions.transfer(to_address, amount_smallest)
                .with_owner(crypto_address.address)
                .fee_limit(10_000_000)
                .build()
                .sign(PrivateKey(bytes.fromhex(private_key_plain)))
                .broadcast()
            )

            tx_id = txn.get('txid') if isinstance(txn, dict) else getattr(txn, 'txid', None)
            if not tx_id:
                raise ValueError("Failed to obtain TRC20 transaction id from broadcast response")

            self.logger.info(
                "📤 TRC20 transfer sent: %s (%s decimals=%s) to %s, txid=%s",
                amount_standard,
                contract_address,
                decimals,
                to_address,
                tx_id,
            )

            return {
                "status": "sent",
                "transaction_hash": tx_id,
                "from_address": crypto_address.address,
                "to_address": to_address,
                "amount_standard": amount_standard,
                "amount_smallest": amount_smallest,
                "contract_address": contract_address,
                "decimals": decimals,
            }
        except Exception as e:
            self.logger.error(f"❌ Error sending TRC20 transfer: {e}")
            raise

    # ===== Helpers for confirmations =====

    def get_latest_block_number(self) -> Optional[int]:
        try:
            info = self.get_block_info()
            if not info:
                return None
            # TronGrid v1 shape
            if 'number' in info:
                try:
                    return int(info['number'])
                except Exception:
                    pass
            # Fullnode shape
            header = info.get('block_header') if isinstance(info, dict) else None
            if header and isinstance(header, dict):
                raw_data = header.get('raw_data') or {}
                if 'number' in raw_data:
                    return int(raw_data['number'])
            return None
        except Exception as e:
            self.logger.error("Error getting latest Tron block number: %s", e)
            return None

    def extract_block_number_from_tx(self, tx_info: Dict[str, Any]) -> Optional[int]:
        try:
            if not tx_info:
                return None
            # Try TronGrid shapes
            if 'blockNumber' in tx_info:
                return int(tx_info['blockNumber'])
            if 'block' in tx_info:
                return int(tx_info['block'])
            # Try nested receipt info
            receipt = tx_info.get('receipt') or tx_info.get('ret', [{}])[0]
            if isinstance(receipt, dict) and 'blockNumber' in receipt:
                return int(receipt['blockNumber'])
            return None
        except Exception:
            return None 