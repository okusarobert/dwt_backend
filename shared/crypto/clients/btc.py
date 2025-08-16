import traceback
import logging
from db.utils import generate_unique_account_number
from shared.logger import setup_logging
from db.wallet import Account, AccountType, CryptoAddress
# from db.connection import session
from sqlalchemy.orm import Session
from decouple import config
from ..HD import BTC
from cryptography.fernet import Fernet
import base64
from blockcypher import subscribe_to_address_webhook
from blockcypher import create_forwarding_address_with_details
from pydantic import BaseModel
from typing import Optional
import requests
import json
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import subprocess

class BlockCypherForwardingAddress(BaseModel):
    """Pydantic model for BlockCypher forwarding address response"""
    callback_url: str
    destination: str
    id: str
    input_address: str
    token: str


@dataclass
class BitcoinConfig:
    """Configuration for Bitcoin client"""
    endpoint: str
    headers: Dict[str, str]
    rpc_host: str = "localhost"
    rpc_port: int = 18332
    rpc_user: str = "bitcoin"
    rpc_password: str = "bitcoinpassword"
    rpc_timeout: int = 30
    rpc_ssl: bool = False
    rpc_ssl_verify: bool = True

    @classmethod
    def testnet(cls) -> 'BitcoinConfig':
        btc_daemon_url = config('BTC_DAEMON_URL', default='http://localhost:8332')
        return cls(
            endpoint=f'{btc_daemon_url}',
            headers={
                'Content-Type': 'application/json'
            },
            rpc_host=config('BTC_RPC_HOST', default='localhost'),
            rpc_port=int(config('BTC_RPC_PORT', default='18332')),
            rpc_user=config('BTC_RPC_USER', default='bitcoin'),
            rpc_password=config('BTC_RPC_PASSWORD', default='bitcoinpassword'),
            rpc_timeout=int(config('BTC_RPC_TIMEOUT', default='30')),
            rpc_ssl=config('BTC_RPC_SSL', default='false').lower() == 'true',
            rpc_ssl_verify=config('BTC_RPC_SSL_VERIFY', default='true').lower() == 'true'
        )

    @classmethod
    def mainnet(cls) -> 'BitcoinConfig':
        btc_daemon_url = config('BTC_DAEMON_URL', default='http://localhost:8332')
        return cls(
            endpoint=f'{btc_daemon_url}',
            headers={
                'Content-Type': 'application/json'
            },
            rpc_host=config('BTC_RPC_HOST', default='localhost'),
            rpc_port=int(config('BTC_RPC_PORT', default='8332')),
            rpc_user=config('BTC_RPC_USER', default='bitcoin'),
            rpc_password=config('BTC_RPC_PASSWORD', default='bitcoinpassword'),
            rpc_timeout=int(config('BTC_RPC_TIMEOUT', default='30')),
            rpc_ssl=config('BTC_RPC_SSL', default='false').lower() == 'true',
            rpc_ssl_verify=config('BTC_RPC_SSL_VERIFY', default='true').lower() == 'true'
        )


class BTCWallet:
    account_id = None

    def __init__(self, user_id: int, btc_config: BitcoinConfig, session: Session, logger: logging.Logger = None):
        self.user_id = user_id
        self.label = "BTC Wallet"
        self.account_number = generate_unique_account_number(session=session, length=10)
        self.session = session
        self.logger = logger or setup_logging()
        self.symbol = "BTC"
        self.app_secret = config('APP_SECRET', default='your-app-secret-key')
        self.config = btc_config
        self.session_request = requests.Session()
        self.session_request.headers.update(btc_config.headers)
        
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
        """Create a new BTC wallet account in the database."""
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
            self.logger.error(f"[BTC] Failed to create wallet for user {self.user_id}: {e!r}")
            self.logger.error(traceback.format_exc())
            raise  # Re-raise the exception so the wallet service can handle it

    def create_address(self):
        """Create a new BTC address for the wallet and set up BlockCypher address forwarding."""
        try:
            self.logger.info(f"Creating address for user {self.user_id}")
            mnemonic_key = f"{self.symbol}_MNEMONIC"
            mnemonic = config(mnemonic_key, default=None)
            if mnemonic:
                btc_wallet = BTC()
                wallet = btc_wallet.from_mnemonic(mnemonic=mnemonic)
                index = self.account_id
                
                # Create user's address
                user_address, priv_key, pub_key = wallet.new_address(index=index)
                
                
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
                # self.session.flush()
                
                # Create webhook subscriptions and store IDs
                
                self.logger.info(f"Created user address: {user_address}")
                    
        except Exception as e:
            self.logger.info(f"[BTC] Failed to create address for user {self.user_id}: {e!r}")
            self.logger.info(traceback.format_exc())
            raise  # Re-raise the exception so the wallet service can handle it
        finally:
            self.logger.info(f"Done creating address for user {self.user_id}")

    # ===== Bitcoin RPC Client Methods =====
    
    def _make_rpc_request(self, method: str, params: list = None, request_id: str = "btc_wallet", wallet: str = None) -> Dict[str, Any]:
        """Make JSON-RPC request to Bitcoin node over HTTP/HTTPS"""
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or [],
            "id": request_id
        }
        
        try:
            # Build the URL for the RPC endpoint
            protocol = "https" if self.config.rpc_ssl else "http"
            url = f"{protocol}://{self.config.rpc_host}:{self.config.rpc_port}"
            
            # Add wallet path to URL if specified
            if wallet:
                url = f"{url}/wallet/{wallet}"
            
            # Set up authentication
            auth = (self.config.rpc_user, self.config.rpc_password)
            
            # Prepare headers
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "BTCWallet/1.0"
            }
            
            # Make the HTTP request
            response = self.session_request.post(
                url,
                json=payload,
                auth=auth,
                headers=headers,
                timeout=self.config.rpc_timeout,
                verify=self.config.rpc_ssl_verify
            )
            
            # Check for HTTP errors
            response.raise_for_status()
            
            # Parse JSON response
            result = response.json()
            
            # Check for RPC errors
            if "error" in result and result["error"] is not None:
                error_msg = f"RPC Error: {result['error']}"
                self.logger.error(error_msg)
                return {"error": error_msg}
            
            return result
                
        except requests.exceptions.Timeout:
            error_msg = f"RPC request timed out after {self.config.rpc_timeout} seconds"
            self.logger.error(error_msg)
            return {"error": error_msg}
        except requests.exceptions.ConnectionError as e:
            error_msg = f"Connection error: {e}"
            self.logger.error(error_msg)
            return {"error": error_msg}
        except requests.exceptions.RequestException as e:
            error_msg = f"Request failed: {e}"
            self.logger.error(error_msg)
            return {"error": error_msg}
        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON response: {e}"
            self.logger.error(error_msg)
            return {"error": error_msg}
        except Exception as e:
            error_msg = f"Unexpected error: {e}"
            self.logger.error(error_msg)
            return {"error": error_msg}

    def test_rpc_connection(self) -> bool:
        """Test basic connection to Bitcoin node"""
        try:
            response = self._make_rpc_request("getblockchaininfo")
            return "result" in response and "error" not in response
        except Exception as e:
            self.logger.error(f"RPC connection test failed: {e}")
            return False

    def get_blockchain_info(self) -> Dict[str, Any]:
        """Get blockchain information"""
        return self._make_rpc_request("getblockchaininfo")

    def get_block_count(self) -> int:
        """Get current block count"""
        response = self._make_rpc_request("getblockcount")
        return response.get("result", 0)

    def get_best_block_hash(self) -> str:
        """Get the hash of the best (tip) block"""
        response = self._make_rpc_request("getbestblockhash")
        return response.get("result", "")

    def get_block(self, block_hash: str, verbosity: int = 1) -> Dict[str, Any]:
        """Get block information by hash"""
        return self._make_rpc_request("getblock", [block_hash, verbosity])

    def get_block_hash(self, height: int) -> str:
        """Get block hash by height"""
        response = self._make_rpc_request("getblockhash", [height])
        return response.get("result", "")

    def get_raw_transaction(self, txid: str, verbose: bool = True) -> Dict[str, Any]:
        """Get raw transaction data"""
        return self._make_rpc_request("getrawtransaction", [txid, verbose])

    def get_network_info(self) -> Dict[str, Any]:
        """Get network information"""
        return self._make_rpc_request("getnetworkinfo")

    def get_mempool_info(self) -> Dict[str, Any]:
        """Get mempool information"""
        return self._make_rpc_request("getmempoolinfo")

    def get_difficulty(self) -> float:
        """Get current difficulty"""
        response = self._make_rpc_request("getdifficulty")
        return response.get("result", 0.0)

    def get_mining_info(self) -> Dict[str, Any]:
        """Get mining information"""
        return self._make_rpc_request("getmininginfo")

    def estimate_smart_fee(self, conf_target: int, estimate_mode: str = "CONSERVATIVE") -> Dict[str, Any]:
        """Estimate smart fee"""
        return self._make_rpc_request("estimatesmartfee", [conf_target, estimate_mode])

    def validate_address(self, address: str) -> Dict[str, Any]:
        """Validate a Bitcoin address"""
        return self._make_rpc_request("validateaddress", [address])

    def get_new_address(self) -> str:
        """Get a new Bitcoin address"""
        response = self._make_rpc_request("getnewaddress")
        return response.get("result", "")

    def generate_to_address(self, address: str, blocks: int = 1) -> List[str]:
        """Generate blocks to a specific address"""
        response = self._make_rpc_request("generatetoaddress", [blocks, address])
        return response.get("result", [])

    # Wallet and UTXO methods
    def list_wallets(self) -> List[str]:
        """List all available wallets"""
        response = self._make_rpc_request("listwallets")
        return response.get("result", [])

    def create_wallet_rpc(self, wallet_name: str, disable_private_keys: bool = True, 
                         blank: bool = True, passphrase: str = "", 
                         avoid_reuse: bool = False, descriptors: bool = False, 
                         load_on_startup: bool = True) -> Dict[str, Any]:
        """Create a new wallet via RPC"""
        params = [wallet_name, disable_private_keys, blank, passphrase, 
                 avoid_reuse, descriptors, load_on_startup]
        return self._make_rpc_request("createwallet", params)

    def load_wallet(self, wallet_name: str) -> Dict[str, Any]:
        """Load a wallet"""
        return self._make_rpc_request("loadwallet", [wallet_name])

    def import_address(self, address: str, label: str = "", rescan: bool = False, wallet: str = None) -> Dict[str, Any]:
        """Import an address to a wallet (legacy wallets only)"""
        return self._make_rpc_request("importaddress", [address, label, rescan], wallet=wallet)

    def import_descriptors(self, descriptors: List[Dict[str, Any]], wallet: str = None) -> Dict[str, Any]:
        """Import descriptors to a wallet (descriptor wallets)"""
        return self._make_rpc_request("importdescriptors", [descriptors], wallet=wallet)

    def list_unspent(self, min_conf: int = 0, max_conf: int = 9999999, 
                     addresses: List[str] = None, wallet: str = None) -> List[Dict[str, Any]]:
        """List unspent transaction outputs"""
        params = [min_conf, max_conf]
        if addresses:
            params.append(addresses)
        response = self._make_rpc_request("listunspent", params, wallet=wallet)
        return response.get("result", [])

    def get_utxos_for_address(self, address: str, wallet_name: str = "watchonly") -> List[Dict[str, Any]]:
        """Get UTXOs for a specific address"""
        try:
            # First, try to import the address if it's not already imported
            try:
                self.import_address(address, wallet=wallet_name)
                self.logger.info(f"Address {address} imported to wallet {wallet_name}")
            except Exception as e:
                if "already imported" not in str(e).lower():
                    self.logger.warning(f"Address import warning: {e}")
            
            # Now get the UTXOs
            utxos = self.list_unspent(0, 9999999, [address], wallet=wallet_name)
            return utxos
        except Exception as e:
            self.logger.error(f"Error getting UTXOs: {e}")
            return []

    def setup_watch_only_wallet(self, wallet_name: str = "watchonly") -> bool:
        """Setup a watch-only wallet for monitoring addresses"""
        try:
            # Check if wallet already exists
            wallets = self.list_wallets()
            if wallet_name in wallets:
                self.logger.info(f"Wallet '{wallet_name}' already exists")
                return True
            
            # Create watch-only wallet
            self.logger.info(f"Creating watch-only wallet '{wallet_name}'...")
            result = self.create_wallet_rpc(
                wallet_name=wallet_name,
                disable_private_keys=True,  # Watch-only
                blank=True,  # Empty wallet
                descriptors=False  # Legacy wallet for importaddress
            )
            
            if "result" in result and "error" not in result:
                self.logger.info(f"Wallet '{wallet_name}' created successfully")
                return True
            else:
                self.logger.error(f"Failed to create wallet: {result}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error setting up wallet: {e}")
            return False

    def get_sync_status(self) -> Dict[str, Any]:
        """Get Bitcoin node synchronization status"""
        try:
            blockchain_info = self.get_blockchain_info()
            result = blockchain_info.get("result", {})
            
            return {
                "chain": result.get("chain", "unknown"),
                "blocks": result.get("blocks", 0),
                "headers": result.get("headers", 0),
                "verification_progress": result.get("verificationprogress", 0.0),
                "initial_block_download": result.get("initialblockdownload", True),
                "pruned": result.get("pruned", False),
                "prune_height": result.get("pruneheight", 0),
                "best_block_hash": result.get("bestblockhash", ""),
                "size_on_disk": result.get("size_on_disk", 0)
            }
        except Exception as e:
            self.logger.error(f"Error getting sync status: {e}")
            return {}

    def is_fully_synced(self) -> bool:
        """Check if Bitcoin node is fully synced"""
        try:
            status = self.get_sync_status()
            return (
                status.get("initial_block_download", True) == False and
                status.get("blocks", 0) > 0 and
                status.get("headers", 0) > 0 and
                status.get("blocks", 0) >= status.get("headers", 0)
            )
        except Exception as e:
            self.logger.error(f"Error checking sync status: {e}")
            return False

    def get_node_info(self) -> Dict[str, Any]:
        """Get comprehensive Bitcoin node information"""
        try:
            blockchain_info = self.get_blockchain_info()
            network_info = self.get_network_info()
            mempool_info = self.get_mempool_info()
            mining_info = self.get_mining_info()
            
            return {
                "blockchain": blockchain_info.get("result", {}),
                "network": network_info.get("result", {}),
                "mempool": mempool_info.get("result", {}),
                "mining": mining_info.get("result", {}),
                "sync_status": self.get_sync_status(),
                "is_fully_synced": self.is_fully_synced()
            }
        except Exception as e:
            self.logger.error(f"Error getting node info: {e}")
            return {}

