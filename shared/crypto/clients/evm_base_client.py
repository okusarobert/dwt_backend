import traceback
import logging
import os
import json
import requests
import time
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from pydantic import BaseModel
from datetime import datetime
from abc import ABC, abstractmethod

from db.utils import generate_unique_account_number
from shared.logger import setup_logging
from db.wallet import Account, AccountType, CryptoAddress
from sqlalchemy.orm import Session
from decouple import config
from ..HD import ETH
from cryptography.fernet import Fernet
import base64


@dataclass
class EVMConfig:
    """Configuration for EVM-compatible chains"""
    api_key: str
    network: str = "mainnet"
    base_url: str = ""
    ws_url: str = ""
    timeout: int = 30
    chain_id: int = 1
    currency_symbol: str = "ETH"
    
    @classmethod
    def ethereum_mainnet(cls, api_key: str) -> 'EVMConfig':
        return cls(
            api_key=api_key,
            network="mainnet",
            base_url=f"https://eth-mainnet.g.alchemy.com/v2/{api_key}",
            ws_url=f"wss://eth-mainnet.g.alchemy.com/v2/{api_key}",
            chain_id=1,
            currency_symbol="ETH"
        )
    
    @classmethod
    def ethereum_sepolia(cls, api_key: str) -> 'EVMConfig':
        return cls(
            api_key=api_key,
            network="sepolia",
            base_url=f"https://eth-sepolia.g.alchemy.com/v2/{api_key}",
            ws_url=f"wss://eth-sepolia.g.alchemy.com/v2/{api_key}",
            chain_id=11155111,
            currency_symbol="ETH"
        )
    
    @classmethod
    def bnb_mainnet(cls, api_key: str) -> 'EVMConfig':
        return cls(
            api_key=api_key,
            network="mainnet",
            base_url=f"https://bnb-mainnet.g.alchemy.com/v2/{api_key}",
            ws_url=f"wss://bnb-mainnet.g.alchemy.com/v2/{api_key}",
            chain_id=56,
            currency_symbol="BNB"
        )
    
    @classmethod
    def bnb_testnet(cls, api_key: str) -> 'EVMConfig':
        return cls(
            api_key=api_key,
            network="testnet",
            base_url=f"https://bnb-testnet.g.alchemy.com/v2/{api_key}",
            ws_url=f"wss://bnb-testnet.g.alchemy.com/v2/{api_key}",
            chain_id=97,
            currency_symbol="BNB"
        )
    
    @classmethod
    def polygon_mainnet(cls, api_key: str) -> 'EVMConfig':
        return cls(
            api_key=api_key,
            network="mainnet",
            base_url=f"https://polygon-mainnet.g.alchemy.com/v2/{api_key}",
            ws_url=f"wss://polygon-mainnet.g.alchemy.com/v2/{api_key}",
            chain_id=137,
            currency_symbol="MATIC"
        )
    
    @classmethod
    def polygon_testnet(cls, api_key: str) -> 'EVMConfig':
        return cls(
            api_key=api_key,
            network="testnet",
            base_url=f"https://polygon-amoy.g.alchemy.com/v2/{api_key}",
            ws_url=f"wss://polygon-amoy.g.alchemy.com/v2/{api_key}",
            chain_id=80002,
            currency_symbol="MATIC"
        )
    
    @classmethod
    def optimism_mainnet(cls, api_key: str) -> 'EVMConfig':
        return cls(
            api_key=api_key,
            network="mainnet",
            base_url=f"https://opt-mainnet.g.alchemy.com/v2/{api_key}",
            ws_url=f"wss://opt-mainnet.g.alchemy.com/v2/{api_key}",
            chain_id=10,
            currency_symbol="ETH"
        )
    
    @classmethod
    def optimism_testnet(cls, api_key: str) -> 'EVMConfig':
        return cls(
            api_key=api_key,
            network="testnet",
            base_url=f"https://opt-sepolia.g.alchemy.com/v2/{api_key}",
            ws_url=f"wss://opt-sepolia.g.alchemy.com/v2/{api_key}",
            chain_id=11155420,
            currency_symbol="ETH"
        )
    
    @classmethod
    def arbitrum_mainnet(cls, api_key: str) -> 'EVMConfig':
        return cls(
            api_key=api_key,
            network="mainnet",
            base_url=f"https://arb-mainnet.g.alchemy.com/v2/{api_key}",
            ws_url=f"wss://arb-mainnet.g.alchemy.com/v2/{api_key}",
            chain_id=42161,
            currency_symbol="ETH"
        )
    
    @classmethod
    def arbitrum_testnet(cls, api_key: str) -> 'EVMConfig':
        return cls(
            api_key=api_key,
            network="testnet",
            base_url=f"https://arb-sepolia.g.alchemy.com/v2/{api_key}",
            ws_url=f"wss://arb-sepolia.g.alchemy.com/v2/{api_key}",
            chain_id=421614,
            currency_symbol="ETH"
        )
    
    @classmethod
    def base_mainnet(cls, api_key: str) -> 'EVMConfig':
        return cls(
            api_key=api_key,
            network="mainnet",
            base_url=f"https://base-mainnet.g.alchemy.com/v2/{api_key}",
            ws_url=f"wss://base-mainnet.g.alchemy.com/v2/{api_key}",
            chain_id=8453,
            currency_symbol="ETH"
        )
    
    @classmethod
    def base_testnet(cls, api_key: str) -> 'EVMConfig':
        return cls(
            api_key=api_key,
            network="testnet",
            base_url=f"https://base-sepolia.g.alchemy.com/v2/{api_key}",
            ws_url=f"wss://base-sepolia.g.alchemy.com/v2/{api_key}",
            chain_id=84532,
            currency_symbol="ETH"
        )
    
    @classmethod
    def avalanche_mainnet(cls, api_key: str) -> 'EVMConfig':
        return cls(
            api_key=api_key,
            network="mainnet",
            base_url=f"https://avax-mainnet.g.alchemy.com/v2/{api_key}",
            ws_url=f"wss://avax-mainnet.g.alchemy.com/v2/{api_key}",
            chain_id=43114,
            currency_symbol="AVAX"
        )
    
    @classmethod
    def avalanche_testnet(cls, api_key: str) -> 'EVMConfig':
        return cls(
            api_key=api_key,
            network="testnet",
            base_url=f"https://avax-fuji.g.alchemy.com/v2/{api_key}",
            ws_url=f"wss://avax-fuji.g.alchemy.com/v2/{api_key}",
            chain_id=43113,
            currency_symbol="AVAX"
        )
    
    @classmethod
    def world_mainnet(cls, api_key: str) -> 'EVMConfig':
        return cls(
            api_key=api_key,
            network="mainnet",
            base_url=f"https://worldchain-mainnet.g.alchemy.com/v2/{api_key}",
            ws_url=f"wss://worldchain-mainnet.g.alchemy.com/v2/{api_key}",
            chain_id=480,
            currency_symbol="ETH"
        )
    
    @classmethod
    def world_testnet(cls, api_key: str) -> 'EVMConfig':
        return cls(
            api_key=api_key,
            network="testnet",
            base_url=f"https://worldchain-sepolia.g.alchemy.com/v2/{api_key}",
            ws_url=f"wss://worldchain-sepolia.g.alchemy.com/v2/{api_key}",
            chain_id=4801,
            currency_symbol="ETH"
        )
    
    @classmethod
    def apechain_mainnet(cls, api_key: str) -> 'EVMConfig':
        return cls(
            api_key=api_key,
            network="mainnet",
            base_url=f"https://apechain-mainnet.g.alchemy.com/v2/{api_key}",
            ws_url=f"wss://apechain-mainnet.g.alchemy.com/v2/{api_key}",
            chain_id=33139,
            currency_symbol="APE"
        )
    
    @classmethod
    def apechain_testnet(cls, api_key: str) -> 'EVMConfig':
        return cls(
            api_key=api_key,
            network="testnet",
            base_url=f"https://apechain-curtis.g.alchemy.com/v2/{api_key}",
            ws_url=f"wss://apechain-curtis.g.alchemy.com/v2/{api_key}",
            chain_id=33111,
            currency_symbol="APE"
        )
    
    @classmethod
    def zetachain_mainnet(cls, api_key: str) -> 'EVMConfig':
        return cls(
            api_key=api_key,
            network="mainnet",
            base_url=f"https://zetachain-mainnet.g.alchemy.com/v2/{api_key}",
            ws_url=f"wss://zetachain-mainnet.g.alchemy.com/v2/{api_key}",
            chain_id=7000,
            currency_symbol="ZETA"
        )
    
    @classmethod
    def zetachain_testnet(cls, api_key: str) -> 'EVMConfig':
        return cls(
            api_key=api_key,
            network="testnet",
            base_url=f"https://zetachain-testnet.g.alchemy.com/v2/{api_key}",
            ws_url=f"wss://zetachain-testnet.g.alchemy.com/v2/{api_key}",
            chain_id=7001,
            currency_symbol="ZETA"
        )


class EVMBaseWallet:
    """Base class for all EVM-compatible chain wallets"""
    
    def __init__(self, user_id: int, config: EVMConfig, session: Session, logger: logging.Logger = None):
        self.user_id = user_id
        self.config = config
        self.session = session
        self.logger = logger or setup_logging()
        self.symbol = config.currency_symbol
        self.label = f"{config.currency_symbol} Wallet"
        self.account_number = generate_unique_account_number(session=session, length=10)
        self.account_id = None
        from decouple import config as decouple_config
        self.app_secret = decouple_config('APP_SECRET', default='your-app-secret-key')
        
        # HTTP session for API requests
        self.session_request = requests.Session()
        self.session_request.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': f'{config.currency_symbol}Wallet/1.0'
        })
    
    def encrypt_private_key(self, private_key: str) -> str:
        """Encrypt private key using APP_SECRET."""
        try:
            key = base64.urlsafe_b64encode(self.app_secret.encode()[:32].ljust(32, b'0'))
            cipher = Fernet(key)
            encrypted_key = cipher.encrypt(private_key.encode())
            return encrypted_key.decode()
        except Exception as e:
            self.logger.error(f"Failed to encrypt private key: {e}")
            return private_key
            
    def decrypt_private_key(self, encrypted_private_key: str) -> str:
        """Decrypt private key using APP_SECRET."""
        try:
            key = base64.urlsafe_b64encode(self.app_secret.encode()[:32].ljust(32, b'0'))
            cipher = Fernet(key)
            decrypted_key = cipher.decrypt(encrypted_private_key.encode())
            return decrypted_key.decode()
        except Exception as e:
            self.logger.error(f"Failed to decrypt private key: {e}")
            return encrypted_private_key
    
    def make_request(self, method: str, params: list = None) -> Optional[Dict]:
        """Make a JSON-RPC request to Alchemy API"""
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
    
    def create_wallet(self):
        """Create a new wallet account in the database."""
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
            self.session.flush()
            self.account_id = crypto_account.id
            self.create_address(notify=True)
            self.logger.info(f"[Wallet] Created {self.symbol} crypto account for user {self.user_id}")
        except Exception as e:
            self.logger.error(f"[{self.symbol}] Failed to create wallet for user {self.user_id}: {e!r}")
            self.logger.error(traceback.format_exc())
            raise
    
    def create_address(self, notify: bool = True):
        """Create a new address for the wallet."""
        self.logger.info(f"create_address is called")
        try:
            self.logger.info(f"Creating address for user {self.user_id}")
            mnemonic_key = f"ETH_MNEMONIC"
            mnemonic = config(mnemonic_key, default=None)
            if mnemonic:
                eth_wallet = ETH()  # All EVM chains use same address generation
                wallet = eth_wallet.from_mnemonic(mnemonic=mnemonic)
                
                index = self.account_id
                user_address, priv_key, pub_key = wallet.new_address(index=index)
                encrypted_private_key = self.encrypt_private_key(priv_key)
                
                crypto_address = CryptoAddress(
                    account_id=self.account_id,
                    address=user_address.lower(),
                    label=self.label,
                    is_active=True,
                    currency_code=self.symbol,
                    address_type="hd_wallet",
                    private_key=encrypted_private_key,
                    public_key=pub_key
                )
                self.session.add(crypto_address)
                self.logger.info(f"Created user address: {user_address}")
                
                if notify:
                    self._notify_address_created(user_address)
                    
                # Register address for webhook monitoring (ETH only for now)
                if self.symbol == "ETH":
                    self._register_address_for_webhook_monitoring(user_address, crypto_address.id)
                    
        except Exception as e:
            self.logger.error(f"[{self.symbol}] Failed to create address for user {self.user_id}: {e!r}")
            self.logger.error(traceback.format_exc())
            raise
        finally:
            self.logger.info(f"Done creating address for user {self.user_id}")
    
    def _notify_address_created(self, address: str):
        """Notify about new address creation via Kafka"""
        try:
            from shared.kafka_producer import get_kafka_producer
            
            producer = get_kafka_producer()
            producer.send(f"{self.symbol.lower()}-address-events", {
                "event_type": f"{self.symbol.lower()}_address_created",
                "address_data": {
                    "address": address,
                    "currency_code": self.symbol,
                    "account_id": self.account_id,
                    "user_id": self.user_id,
                    "timestamp": datetime.utcnow().isoformat()
                }
            })
            self.logger.info(f"📨 Sent {self.symbol} address creation event for {address}")
        except Exception as e:
            self.logger.error(f"Failed to notify {self.symbol} address creation: {e}")
    
    def _register_address_for_webhook_monitoring(self, address: str, crypto_address_id: int):
        """Register address for webhook monitoring (ETH only for now)"""
        try:
            # Import webhook integration
            import sys
            import os
            sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'wallet'))
            from ethereum_webhook_integration import register_eth_address_for_monitoring
            
            success = register_eth_address_for_monitoring(address, crypto_address_id)
            if success:
                self.logger.info(f"✅ Registered {self.symbol} address {address} for webhook monitoring")
            else:
                self.logger.warning(f"⚠️ Failed to register {self.symbol} address {address} for webhook monitoring")
                
        except ImportError as e:
            self.logger.warning(f"⚠️ Webhook integration not available: {e}")
        except Exception as e:
            self.logger.error(f"❌ Error registering address for webhook monitoring: {e}")
    
    # ===== Common EVM API Methods =====
    
    def test_connection(self) -> bool:
        """Test the connection to API"""
        self.logger.info("Testing API connection...")
        result = self.make_request("eth_blockNumber")
        return result is not None and "result" in result
    
    def get_latest_block_number(self) -> Optional[int]:
        """Get the latest block number"""
        result = self.make_request("eth_blockNumber")
        if result and "result" in result:
            return int(result["result"], 16)
        return None
    
    def get_balance(self, address: str) -> Optional[Dict]:
        """Get account balance"""
        result = self.make_request("eth_getBalance", [address, "latest"])
        if result and "result" in result:
            balance_wei = int(result["result"], 16)
            balance_native = balance_wei / (10 ** 18)
            return {
                "address": address,
                "balance_wei": balance_wei,
                f"balance_{self.symbol.lower()}": balance_native
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
    
    def get_transaction_count(self, address: str) -> Optional[int]:
        """Get transaction count (nonce) for an address"""
        result = self.make_request("eth_getTransactionCount", [address, "latest"])
        if result and "result" in result:
            return int(result["result"], 16)
        return None
    
    def validate_address(self, address: str) -> bool:
        """Validate EVM address format"""
        try:
            if not address.startswith("0x"):
                return False
            if len(address) != 42:  # 0x + 40 hex chars
                return False
            int(address[2:], 16)
            return True
        except:
            return False
    
    def send_native_transaction(self, to_address: str, amount: float, gas_limit: int = 21000) -> Optional[Dict]:
        """Send native currency transaction (ETH, BNB, MATIC, etc.)"""
        try:
            crypto_address = self.session.query(CryptoAddress).filter_by(
                account_id=self.account_id,
                currency_code=self.symbol,
                is_active=True
            ).first()
            
            if not crypto_address:
                raise ValueError(f"No active {self.symbol} address found for account {self.account_id}")
            
            private_key = self.decrypt_private_key(crypto_address.private_key)
            gas_price_result = self.get_gas_price()
            if not gas_price_result:
                raise ValueError("Failed to get gas price")
            
            gas_price = gas_price_result.get("gas_price_wei", 0)
            nonce = self.get_transaction_count(crypto_address.address)
            if nonce is None:
                raise ValueError("Failed to get transaction count")
            
            amount_wei = int(amount * 10**18)
            
            from eth_account import Account
            transaction = {
                'to': to_address,
                'value': amount_wei,
                'gas': gas_limit,
                'gasPrice': gas_price,
                'nonce': nonce,
                'chainId': self.config.chain_id
            }
            
            signed_txn = Account.sign_transaction(transaction, private_key)
            raw_tx_hash = signed_txn.raw_transaction.hex()
            send_result = self.make_request("eth_sendRawTransaction", [raw_tx_hash])
            
            if not send_result or "result" not in send_result:
                error_msg = send_result.get("error", {}).get("message", "Unknown error") if send_result else "No response"
                raise ValueError(f"Failed to send transaction: {error_msg}")
            
            tx_hash = send_result["result"]
            
            self.logger.info(f"📤 {self.symbol} transaction sent: {amount} {self.symbol} to {to_address}")
            self.logger.info(f"   Transaction Hash: {tx_hash}")
            
            return {
                "status": "sent",
                "transaction_hash": tx_hash,
                "from_address": crypto_address.address,
                "to_address": to_address,
                f"amount_{self.symbol.lower()}": amount,
                "amount_wei": amount_wei,
                "gas_price": gas_price,
                "gas_limit": gas_limit,
                "nonce": nonce,
                "chain_id": self.config.chain_id
            }
            
        except Exception as e:
            self.logger.error(f"❌ Error sending {self.symbol} transaction: {e}")
            raise


# Factory functions for easy client creation
def get_common_alchemy_api_key() -> str:
    """Get common Alchemy API key with fallback options"""
    return config('ALCHEMY_API_KEY', default=config('ETHEREUM_API_KEY', default=''))

def create_ethereum_client(user_id: int, session: Session, network: str = "mainnet", api_key: str = None) -> EVMBaseWallet:
    """Create Ethereum client"""
    api_key = api_key or config('ALCHEMY_ETH_API_KEY', default=get_common_alchemy_api_key())
    if network == "mainnet":
        eth_config = EVMConfig.ethereum_mainnet(api_key)
    else:
        eth_config = EVMConfig.ethereum_sepolia(api_key)
    return EVMBaseWallet(user_id, eth_config, session)

def create_bnb_client(user_id: int, session: Session, network: str = "mainnet", api_key: str = None) -> EVMBaseWallet:
    """Create BNB Smart Chain client"""
    api_key = api_key or config('ALCHEMY_BNB_API_KEY', default=get_common_alchemy_api_key())
    if network == "mainnet":
        bnb_config = EVMConfig.bnb_mainnet(api_key)
    else:
        bnb_config = EVMConfig.bnb_testnet(api_key)
    return EVMBaseWallet(user_id, bnb_config, session)

def create_polygon_client(user_id: int, session: Session, network: str = "mainnet", api_key: str = None) -> EVMBaseWallet:
    """Create Polygon client"""
    api_key = api_key or config('ALCHEMY_POLYGON_API_KEY', default=get_common_alchemy_api_key())
    if network == "mainnet":
        polygon_config = EVMConfig.polygon_mainnet(api_key)
    else:
        polygon_config = EVMConfig.polygon_testnet(api_key)
    return EVMBaseWallet(user_id, polygon_config, session)

def create_optimism_client(user_id: int, session: Session, network: str = "mainnet", api_key: str = None) -> EVMBaseWallet:
    """Create Optimism client"""
    api_key = api_key or config('ALCHEMY_OPTIMISM_API_KEY', default=get_common_alchemy_api_key())
    if network == "mainnet":
        optimism_config = EVMConfig.optimism_mainnet(api_key)
    else:
        optimism_config = EVMConfig.optimism_testnet(api_key)
    return EVMBaseWallet(user_id, optimism_config, session)

def create_arbitrum_client(user_id: int, session: Session, network: str = "mainnet", api_key: str = None) -> EVMBaseWallet:
    """Create Arbitrum client"""
    api_key = api_key or config('ALCHEMY_ARBITRUM_API_KEY', default=get_common_alchemy_api_key())
    if network == "mainnet":
        arbitrum_config = EVMConfig.arbitrum_mainnet(api_key)
    else:
        arbitrum_config = EVMConfig.arbitrum_testnet(api_key)
    return EVMBaseWallet(user_id, arbitrum_config, session)

def create_base_client(user_id: int, session: Session, network: str = "mainnet", api_key: str = None) -> EVMBaseWallet:
    """Create Base client"""
    api_key = api_key or config('ALCHEMY_BASE_API_KEY', default=get_common_alchemy_api_key())
    if network == "mainnet":
        base_config = EVMConfig.base_mainnet(api_key)
    else:
        base_config = EVMConfig.base_testnet(api_key)
    return EVMBaseWallet(user_id, base_config, session)

def create_avalanche_client(user_id: int, session: Session, network: str = "mainnet", api_key: str = None) -> EVMBaseWallet:
    """Create Avalanche client"""
    api_key = api_key or config('ALCHEMY_AVALANCHE_API_KEY', default=get_common_alchemy_api_key())
    if network == "mainnet":
        avalanche_config = EVMConfig.avalanche_mainnet(api_key)
    else:
        avalanche_config = EVMConfig.avalanche_testnet(api_key)
    return EVMBaseWallet(user_id, avalanche_config, session)

def create_world_client(user_id: int, session: Session, network: str = "mainnet", api_key: str = None) -> EVMBaseWallet:
    """Create World Chain client"""
    api_key = api_key or config('ALCHEMY_WORLD_API_KEY', default=get_common_alchemy_api_key())
    if network == "mainnet":
        world_config = EVMConfig.world_mainnet(api_key)
    else:
        world_config = EVMConfig.world_testnet(api_key)
    return EVMBaseWallet(user_id, world_config, session)

def create_apechain_client(user_id: int, session: Session, network: str = "mainnet", api_key: str = None) -> EVMBaseWallet:
    """Create ApeChain client"""
    api_key = api_key or config('ALCHEMY_APECHAIN_API_KEY', default=get_common_alchemy_api_key())
    if network == "mainnet":
        apechain_config = EVMConfig.apechain_mainnet(api_key)
    else:
        apechain_config = EVMConfig.apechain_testnet(api_key)
    return EVMBaseWallet(user_id, apechain_config, session)

def create_zetachain_client(user_id: int, session: Session, network: str = "mainnet", api_key: str = None) -> EVMBaseWallet:
    """Create ZetaChain client"""
    api_key = api_key or config('ALCHEMY_ZETACHAIN_API_KEY', default=get_common_alchemy_api_key())
    if network == "mainnet":
        zetachain_config = EVMConfig.zetachain_mainnet(api_key)
    else:
        zetachain_config = EVMConfig.zetachain_testnet(api_key)
    return EVMBaseWallet(user_id, zetachain_config, session)
