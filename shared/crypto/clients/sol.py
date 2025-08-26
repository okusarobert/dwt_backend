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
    from solders.keypair import Keypair
    from solders.pubkey import Pubkey as PublicKey
    from solders.transaction import Transaction
    from solders.system_program import TransferParams, transfer
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

    def __init__(self, user_id: int, sol_config: SolanaConfig, session: Session, logger: logging.Logger = None):
        self.user_id = user_id
        self.label = "SOL Wallet"
        self.account_number = generate_unique_account_number(session=session, length=10)
        self.session = session
        self.logger = logger or setup_logging()
        self.symbol = "SOL"
        self.app_secret = config('APP_SECRET', default='your-app-secret-key')
        self.config = sol_config
        self.session_request = requests.Session()
        self.session_request.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'SOLWallet/1.0'
        })
        
        # Initialize Solana client if SDK is available
        if SOLANA_AVAILABLE:
            if sol_config.network == "mainnet":
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

    def register_all_addresses_with_webhook(self) -> Dict[str, Any]:
        """Register all existing addresses for this wallet with Alchemy webhook"""
        try:
            addresses = self.get_wallet_addresses()
            registered_count = 0
            failed_count = 0
            results = []
            
            for addr_info in addresses:
                address = addr_info["address"]
                success = self.register_address_with_webhook(address)
                
                if success:
                    registered_count += 1
                    results.append({"address": address, "status": "registered"})
                else:
                    failed_count += 1
                    results.append({"address": address, "status": "failed"})
            
            return {
                "total_addresses": len(addresses),
                "registered_count": registered_count,
                "failed_count": failed_count,
                "results": results
            }
            
        except Exception as e:
            self.logger.error(f"Error registering all addresses with webhook: {e}")
            return {
                "total_addresses": 0,
                "registered_count": 0,
                "failed_count": 0,
                "error": str(e)
            }

    def register_address_with_webhook(self, address: str) -> bool:
        """Register a Solana address with existing Alchemy webhook or create new one"""
        try:
            # Get Alchemy Auth Key for dashboard API
            alchemy_auth_key = config('ALCHEMY_AUTH_KEY', default=None)
            if not alchemy_auth_key:
                self.logger.warning("ALCHEMY_AUTH_KEY not configured, skipping webhook registration")
                return False
            
            # Prepare the webhook URL
            webhook_url = config('WEBHOOK_BASE_URL', default='http://localhost:3030')
            webhook_endpoint = f"{webhook_url}/api/v1/wallet/sol/callbacks/address-webhook"
            
            # Use the Alchemy dashboard API
            dashboard_url = "https://dashboard.alchemy.com/api"
            
            # First, check if a webhook already exists
            existing_webhooks = self._get_existing_webhooks_dashboard(dashboard_url, alchemy_auth_key)
            
            if existing_webhooks:
                # Use the first existing webhook and add the address to it
                webhook_id = existing_webhooks[0]['id']
                return self._add_address_to_webhook_dashboard(dashboard_url, webhook_id, address, alchemy_auth_key)
            else:
                # Create a new webhook with this address
                return self._create_webhook_with_address_dashboard(dashboard_url, webhook_endpoint, address, alchemy_auth_key)
                
        except Exception as e:
            self.logger.error(f"Error registering address {address} with webhook: {e}")
            return False

    def _get_existing_webhooks_dashboard(self, dashboard_url: str, auth_key: str) -> list:
        """Get existing webhooks from Alchemy dashboard API"""
        try:
            headers = {
                'X-Alchemy-Token': auth_key
            }
            
            response = requests.get(
                f"{dashboard_url}/team-webhooks",
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                # Handle the response format: {"data": [...]}
                webhooks = result.get('data', []) if isinstance(result, dict) else result
                return webhooks if isinstance(webhooks, list) else []
            else:
                self.logger.warning(f"Failed to get existing webhooks: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            self.logger.error(f"Error getting existing webhooks: {e}")
            return []

    def _create_webhook_with_address_dashboard(self, dashboard_url: str, webhook_endpoint: str, address: str, auth_key: str) -> bool:
        """Create a new webhook with the specified address using dashboard API"""
        try:
            payload = {
                "network": "SOL_MAINNET" if self.config.network == "mainnet" else "SOL_DEVNET",
                "webhook_type": "ADDRESS_ACTIVITY",
                "webhook_url": webhook_endpoint,
                "addresses": [address]
            }
            
            headers = {
                'Content-Type': 'application/json',
                'X-Alchemy-Token': auth_key
            }
            
            self.logger.info(f"Attempting to create webhook with payload: {payload}")
            
            response = requests.post(
                f"{dashboard_url}/create-webhook",
                json=payload,
                headers=headers,
                timeout=30
            )
            
            self.logger.info(f"Webhook creation response: {response.status_code} - {response.text}")
            
            if response.status_code == 200:
                result = response.json()
                self.logger.info(f"Successfully created webhook with address {address}")
                self.logger.info(f"Webhook ID: {result.get('id', 'N/A')}")
                self.logger.info(f"Signing Key: {result.get('signing_key', 'N/A')}")
                return True
            else:
                self.logger.error(f"Failed to create webhook for {address}: {response.status_code} - {response.text}")
                self.logger.warning("Webhook creation failed. This might be due to:")
                self.logger.warning("1. Invalid API endpoint")
                self.logger.warning("2. Incorrect authentication")
                self.logger.warning("3. Missing required parameters")
                self.logger.warning("4. Network restrictions")
                return False
                
        except Exception as e:
            self.logger.error(f"Error creating webhook with address {address}: {e}")
            return False

    def _add_address_to_webhook_dashboard(self, dashboard_url: str, webhook_id: str, address: str, auth_key: str) -> bool:
        """Add an address to an existing webhook using dashboard API"""
        try:
            payload = {
                "webhook_id": webhook_id,
                "addresses_to_add": [address],
                "addresses_to_remove": []
            }
            
            headers = {
                'Content-Type': 'application/json',
                'X-Alchemy-Token': auth_key
            }
            
            self.logger.info(f"Adding address {address} to webhook {webhook_id}")
            
            response = requests.patch(
                f"{dashboard_url}/update-webhook-addresses",
                json=payload,
                headers=headers,
                timeout=30
            )
            
            self.logger.info(f"Webhook update response: {response.status_code} - {response.text}")
            
            if response.status_code == 200:
                self.logger.info(f"Successfully added address {address} to webhook {webhook_id}")
                return True
            else:
                self.logger.error(f"Failed to add address {address} to webhook {webhook_id}: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error adding address {address} to webhook {webhook_id}: {e}")
            return False

    def _remove_address_from_webhook_dashboard(self, dashboard_url: str, webhook_id: str, address: str, auth_key: str) -> bool:
        """Remove an address from an existing webhook using dashboard API"""
        try:
            payload = {
                "webhook_id": webhook_id,
                "addresses_to_add": [],
                "addresses_to_remove": [address]
            }
            
            headers = {
                'Content-Type': 'application/json',
                'X-Alchemy-Token': auth_key
            }
            
            self.logger.info(f"Removing address {address} from webhook {webhook_id}")
            
            response = requests.patch(
                f"{dashboard_url}/update-webhook-addresses",
                json=payload,
                headers=headers,
                timeout=30
            )
            
            self.logger.info(f"Webhook update response: {response.status_code} - {response.text}")
            
            if response.status_code == 200:
                self.logger.info(f"Successfully removed address {address} from webhook {webhook_id}")
                return True
            else:
                self.logger.error(f"Failed to remove address {address} from webhook {webhook_id}: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error removing address {address} from webhook {webhook_id}: {e}")
            return False

    def delete_webhook(self, webhook_id: str) -> bool:
        """Delete a webhook using the Alchemy dashboard API"""
        try:
            # Get Alchemy Auth Key for dashboard API
            alchemy_auth_key = config('ALCHEMY_AUTH_KEY', default=None)
            if not alchemy_auth_key:
                self.logger.warning("ALCHEMY_AUTH_KEY not configured, skipping webhook deletion")
                return False
            
            # Use the Alchemy dashboard API
            dashboard_url = "https://dashboard.alchemy.com/api"
            
            headers = {
                'X-Alchemy-Token': alchemy_auth_key
            }
            
            params = {
                'webhook_id': webhook_id
            }
            
            self.logger.info(f"Deleting webhook {webhook_id}")
            
            response = requests.delete(
                f"{dashboard_url}/delete-webhook",
                headers=headers,
                params=params,
                timeout=30
            )
            
            self.logger.info(f"Webhook deletion response: {response.status_code} - {response.text}")
            
            if response.status_code == 200:
                self.logger.info(f"Successfully deleted webhook {webhook_id}")
                return True
            else:
                self.logger.error(f"Failed to delete webhook {webhook_id}: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error deleting webhook {webhook_id}: {e}")
            return False

    def list_webhooks(self) -> list:
        """List all webhooks using the Alchemy dashboard API"""
        try:
            # Get Alchemy Auth Key for dashboard API
            alchemy_auth_key = config('ALCHEMY_AUTH_KEY', default=None)
            if not alchemy_auth_key:
                self.logger.warning("ALCHEMY_AUTH_KEY not configured, skipping webhook listing")
                return []
            
            # Use the Alchemy dashboard API
            dashboard_url = "https://dashboard.alchemy.com/api"
            
            headers = {
                'X-Alchemy-Token': alchemy_auth_key
            }
            
            self.logger.info("Listing webhooks")
            
            response = requests.get(
                f"{dashboard_url}/team-webhooks",
                headers=headers,
                timeout=30
            )
            
            self.logger.info(f"Webhook listing response: {response.status_code} - {response.text}")
            
            if response.status_code == 200:
                result = response.json()
                webhooks = result.get('data', []) if isinstance(result, dict) else result
                self.logger.info(f"Found {len(webhooks)} webhooks")
                return webhooks
            else:
                self.logger.error(f"Failed to list webhooks: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            self.logger.error(f"Error listing webhooks: {e}")
            return []

    def unregister_address_from_webhook(self, address: str) -> bool:
        """Remove a Solana address from existing Alchemy webhook"""
        try:
            # Get Alchemy Auth Key for dashboard API
            alchemy_auth_key = config('ALCHEMY_AUTH_KEY', default=None)
            if not alchemy_auth_key:
                self.logger.warning("ALCHEMY_AUTH_KEY not configured, skipping webhook unregistration")
                return False
            
            # Use the Alchemy dashboard API
            dashboard_url = "https://dashboard.alchemy.com/api"
            
            # Get existing webhooks
            existing_webhooks = self._get_existing_webhooks_dashboard(dashboard_url, alchemy_auth_key)
            
            if not existing_webhooks:
                self.logger.warning("No existing webhooks found")
                return False
            
            # Remove address from the first webhook (assuming one webhook per network)
            webhook_id = existing_webhooks[0]['id']
            return self._remove_address_from_webhook_dashboard(dashboard_url, webhook_id, address, alchemy_auth_key)
                
        except Exception as e:
            self.logger.error(f"Error unregistering address {address} from webhook: {e}")
            return False

    def create_address(self):
        """Create a new SOL address for the wallet with uniqueness guarantees."""
        try:
            self.logger.info(f"Creating address for user {self.user_id}")
            
            if SOLANA_AVAILABLE:
                # Use the new method with uniqueness guarantees
                new_address = self.ensure_address_uniqueness()
                if new_address:
                    self.logger.info(f"Created unique user address: {new_address['address']}")
                    
                    # Register the address with Alchemy webhook for monitoring
                    webhook_registered = self.register_address_with_webhook(new_address['address'])
                    if webhook_registered:
                        self.logger.info(f"Address {new_address['address']} registered with webhook for monitoring")
                    else:
                        self.logger.warning(f"Failed to register address {new_address['address']} with webhook")
                else:
                    self.logger.error("Failed to create unique address")
                    raise Exception("Failed to create unique Solana address")
            else:
                # Fallback: create a placeholder address (valid Solana address format)
                placeholder_address = "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM"  # Valid Solana address
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
                # First decode base58, then create PublicKey
                decoded_bytes = base58.b58decode(address)
                if len(decoded_bytes) != 32:
                    return False
                PublicKey(decoded_bytes)
                return True
            else:
                # Basic validation: check length and base58 format
                if len(address) != 44:  # Solana addresses are 44 characters
                    return False
                # Check if it's valid base58 and 32 bytes
                try:
                    decoded_bytes = base58.b58decode(address)
                    return len(decoded_bytes) == 32
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

    def _generate_deterministic_keypair(self, user_id: int, index: int) -> 'Keypair':
        """Generate a deterministic Solana keypair using user_id and index"""
        try:
            # Create a deterministic seed using user_id and index
            base_seed = b'dwt_solana_wallet_seed_v1'
            user_bytes = user_id.to_bytes(8, 'big')
            index_bytes = index.to_bytes(4, 'big')
            
            import hashlib
            combined_seed = base_seed + user_bytes + index_bytes
            seed_hash = hashlib.sha256(combined_seed).digest()
            
            # Create keypair from the 32-byte seed
            keypair = Keypair.from_seed(seed_hash)
            return keypair
            
        except Exception as e:
            self.logger.error(f"Error generating deterministic keypair: {e}")
            raise

    def generate_new_address(self, index: int = None) -> Optional[Dict]:
        """Generate a deterministic Solana address for the wallet using seed derivation"""
        try:
            if not SOLANA_AVAILABLE:
                self.logger.error("Solana SDK not available")
                return None
            
            # Use account_id as the index for deterministic generation
            if index is None:
                index = self.account_id
            
            # Generate deterministic keypair using seed + user_id + account_id
            keypair = self._generate_deterministic_keypair(self.user_id, index)
            public_key = keypair.pubkey()
            # Store the full 64-byte keypair, not just the 32-byte secret
            private_key = base58.b58encode(bytes(keypair)).decode()
            
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

    def send_transaction(self, to_address: str, amount: float, priority_fee: int = 5000) -> Dict[str, Any]:
        """Send SOL to an external address"""
        try:
            if not SOLANA_AVAILABLE:
                raise Exception("Solana SDK not available")
            
            # Validate Solana address
            if not self.validate_address(to_address):
                raise Exception(f"Invalid Solana address: {to_address}")
            
            # Get the user's SOL account
            sol_account = self.session.query(Account).filter_by(
                user_id=self.user_id,
                currency="SOL",
                account_type=AccountType.CRYPTO
            ).first()
            
            if not sol_account:
                raise Exception("No SOL account found for user")
            
            # Get the crypto address for this account
            crypto_address = self.session.query(CryptoAddress).filter_by(
                account_id=sol_account.id,
                currency_code="SOL",
                is_active=True
            ).first()
            
            if not crypto_address:
                raise Exception("No active SOL address found for user")
            
            # Decrypt the private key
            private_key_base58 = self.decrypt_private_key(crypto_address.private_key)
            
            # Convert amount to lamports (smallest unit)
            amount_lamports = int(amount * 1_000_000_000)  # 1 SOL = 1,000,000,000 lamports
            
            # Create keypair from private key
            private_key_bytes = base58.b58decode(private_key_base58)
            
            # Handle both old format (32-byte secret) and new format (64-byte keypair)
            if len(private_key_bytes) == 32:
                # Old format: 32-byte secret, create keypair from seed
                keypair = Keypair.from_seed(private_key_bytes)
            elif len(private_key_bytes) == 64:
                # New format: 64-byte keypair
                keypair = Keypair.from_bytes(private_key_bytes)
            else:
                raise Exception(f"Invalid private key format. Expected 32 or 64 bytes, got {len(private_key_bytes)}")
            
            # Get recent blockhash
            recent_blockhash = self.solana_client.get_latest_blockhash()
            if not recent_blockhash.value:
                raise Exception("Failed to get recent blockhash")
            
            # Create transfer instruction
            transfer_instruction = transfer(
                TransferParams(
                    from_pubkey=keypair.pubkey(),
                    to_pubkey=PublicKey(base58.b58decode(to_address)),
                    lamports=amount_lamports
                )
            )
            
            # Create transaction with new API
            from solders.hash import Hash
            transaction = Transaction.new_signed_with_payer(
                [transfer_instruction],
                keypair.pubkey(),
                [keypair],
                recent_blockhash.value.blockhash
            )
            
            # Send transaction
            tx_opts = TxOpts(skip_preflight=False, preflight_commitment=Commitment("confirmed"))
            result = self.solana_client.send_transaction(transaction, opts=tx_opts)
            
            if result.value:
                signature = str(result.value)  # Convert Signature object to string
                
                # Get transaction details
                tx_info = {
                    "transaction_hash": signature,
                    "from_address": str(keypair.pubkey()),
                    "to_address": to_address,
                    "amount_sol": amount,
                    "amount_lamports": amount_lamports,
                    "estimated_cost_sol": 0.000005,  # Typical Solana transaction fee
                    "transaction_params": {
                        "recent_blockhash": str(recent_blockhash.value.blockhash),
                        "priority_fee": priority_fee
                    }
                }
                
                self.logger.info(f"✅ SOL transaction sent successfully")
                self.logger.info(f"   From: {tx_info['from_address']}")
                self.logger.info(f"   To: {tx_info['to_address']}")
                self.logger.info(f"   Amount: {amount} SOL ({amount_lamports} lamports)")
                self.logger.info(f"   Signature: {signature}")
                
                return tx_info
            else:
                raise Exception("Failed to send transaction")
                
        except Exception as e:
            self.logger.error(f"❌ Error sending SOL transaction: {e}")
            raise 