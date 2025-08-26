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

from db.utils import generate_unique_account_number
from shared.logger import setup_logging
from db.wallet import Account, AccountType, CryptoAddress
from sqlalchemy.orm import Session
from decouple import config
from ..HD import ETH
from cryptography.fernet import Fernet
import base64


class AlchemyConfig(BaseModel):
    """Pydantic model for Alchemy configuration"""
    api_key: str
    network: str = "mainnet"
    base_url: str = ""
    ws_url: str = ""


@dataclass
class EthereumConfig:
    """Configuration for Ethereum client"""
    api_key: str
    network: str = "mainnet"
    base_url: str = ""
    ws_url: str = ""
    timeout: int = 30

    @classmethod
    def testnet(cls, api_key: str) -> 'EthereumConfig':
        return cls(
            api_key=api_key,
            network="sepolia",
            base_url=f"https://eth-sepolia.g.alchemy.com/v2/{api_key}",
            ws_url=f"wss://eth-sepolia.g.alchemy.com/v2/{api_key}"
        )

    @classmethod
    def mainnet(cls, api_key: str) -> 'EthereumConfig':
        return cls(
            api_key=api_key,
            network="mainnet",
            base_url=f"https://eth-mainnet.g.alchemy.com/v2/{api_key}",
            ws_url=f"wss://eth-mainnet.g.alchemy.com/v2/{api_key}"
        )

    @classmethod
    def holesky(cls, api_key: str) -> 'EthereumConfig':
        return cls(
            api_key=api_key,
            network="holesky",
            base_url=f"https://eth-holesky.g.alchemy.com/v2/{api_key}",
            ws_url=f"wss://eth-holesky.g.alchemy.com/v2/{api_key}"
        )


class ETHWallet:
    account_id = None

    def __init__(self, user_id: int, eth_config: EthereumConfig, session: Session, logger: logging.Logger = None):
        self.user_id = user_id
        self.label = "ETH Wallet"
        self.account_number = generate_unique_account_number(session=session, length=10)
        self.session = session
        self.logger = logger or setup_logging()
        self.symbol = "ETH"
        self.app_secret = config('APP_SECRET', default='your-app-secret-key')
        self.config = eth_config
        self.session_request = requests.Session()
        self.session_request.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'ETHWallet/1.0'
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
        """Create a new ETH wallet account in the database."""
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
            self.create_address(notify=True)
            self.logger.info(
                f"[Wallet] Created {self.symbol} crypto account for user {self.user_id}")
        except Exception as e:
            self.logger.error(f"[ETH] Failed to create wallet for user {self.user_id}: {e!r}")
            self.logger.error(traceback.format_exc())
            raise  # Re-raise the exception so the wallet service can handle it

    def create_address(self, notify: bool = True):
        """Create a new ETH address for the wallet."""
        try:
            self.logger.info(f"Creating address for user {self.user_id}")
            mnemonic_key = f"{self.symbol}_MNEMONIC"
            mnemonic = config(mnemonic_key, default=None)
            if mnemonic:
                eth_wallet = ETH()
                wallet = eth_wallet.from_mnemonic(mnemonic=mnemonic)

                index = self.account_id
                
                # Create user's address
                user_address, priv_key, pub_key = wallet.new_address(index=index)
                
                # Encrypt private key before storing
                encrypted_private_key = self.encrypt_private_key(priv_key)
                
                # Create crypto address record for user's address
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
                
                # Send Kafka notification about new address creation (if enabled)
                if notify:
                    self._notify_address_created(user_address)
                    
        except Exception as e:
            self.logger.error(f"[ETH] Failed to create address for user {self.user_id}: {e!r}")
            self.logger.error(traceback.format_exc())
            raise  # Re-raise the exception so the wallet service can handle it
        finally:
            self.logger.info(f"Done creating address for user {self.user_id}")

    def _notify_address_created(self, address: str):
        """Notify about new Ethereum address creation via Kafka"""
        try:
            # Import here to avoid circular imports
            from shared.kafka_producer import get_kafka_producer
            
            producer = get_kafka_producer()
            producer.send("ethereum-address-events", {
                "event_type": "ethereum_address_created",
                "address_data": {
                    "address": address,
                    "currency_code": self.symbol,
                    "account_id": self.account_id,
                    "user_id": self.user_id,
                    "timestamp": datetime.utcnow().isoformat()
                }
            })
            self.logger.info(f"📨 Sent Ethereum address creation event for {address}")
        except Exception as e:
            self.logger.error(f"Failed to notify Ethereum address creation: {e}")
            # Don't raise the exception to avoid breaking the address creation process

    def notify_existing_address(self, address: str):
        """Manually send notification for an existing address"""
        self._notify_address_created(address)
    
    def _register_address_for_webhook_monitoring(self, address: str, crypto_address_id: int):
        """Register address for webhook monitoring"""
        try:
            # Import webhook integration
            import sys
            import os
            sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'wallet'))
            from ethereum_webhook_integration import register_eth_address_for_monitoring
            
            success = register_eth_address_for_monitoring(address, crypto_address_id)
            if success:
                self.logger.info(f"✅ Registered ETH address {address} for webhook monitoring")
            else:
                self.logger.warning(f"⚠️ Failed to register ETH address {address} for webhook monitoring")
                
        except ImportError as e:
            self.logger.warning(f"⚠️ Webhook integration not available: {e}")
        except Exception as e:
            self.logger.error(f"❌ Error registering address for webhook monitoring: {e}")

    # ===== Alchemy API Methods =====
    
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

    def test_connection(self) -> bool:
        """Test the connection to Alchemy API"""
        self.logger.info("Testing Alchemy API connection...")
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
            balance_eth = balance_wei / (10 ** 18)
            return {
                "address": address,
                "balance_wei": balance_wei,
                "balance_eth": balance_eth
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
        self.logger.info(f"Logs: {result}")
        return result.get("result") if result else None

    def get_asset_transfers(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Call Alchemy Transfers API (alchemy_getAssetTransfers) and auto-paginate using pageKey.
        Docs: https://www.alchemy.com/docs/reference/transfers-api-quickstart
        """
        transfers: List[Dict[str, Any]] = []
        try:
            req_params = dict(params) if params else {}
            while True:
                resp = self.make_request("alchemy_getAssetTransfers", [req_params])
                if not resp or "result" not in resp:
                    break
                result = resp.get("result") or {}
                batch = result.get("transfers") or []
                transfers.extend(batch)
                page_key = result.get("pageKey")
                if not page_key:
                    break
                req_params = {**req_params, "pageKey": page_key}
        except Exception as e:
            self.logger.error(f"Error calling alchemy_getAssetTransfers: {e}")
        return transfers

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
        """Validate Ethereum address format"""
        try:
            # Basic Ethereum address validation
            if not address.startswith("0x"):
                return False
            if len(address) != 42:  # 0x + 40 hex chars
                return False
            # Check if it's a valid hex string
            int(address[2:], 16)
            return True
        except:
            return False

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
    
    def send_transaction(self, to_address: str, amount_eth: float, gas_limit: int = 21000) -> Optional[Dict]:
        """
        Send an Ethereum transaction
        
        Args:
            to_address: Destination address
            amount_eth: Amount in ETH
            gas_limit: Gas limit for the transaction
            
        Returns:
            Dict with transaction hash and status
        """
        try:
            # Get the crypto address for this account
            crypto_address = self.session.query(CryptoAddress).filter_by(
                account_id=self.account_id,
                currency_code="ETH",
                is_active=True
            ).first()
            
            if not crypto_address:
                raise ValueError(f"No active ETH address found for account {self.account_id}")
            
            # Decrypt the private key
            private_key = self.decrypt_private_key(crypto_address.private_key)
            
            # Get current gas price
            gas_price_result = self.get_gas_price()
            if not gas_price_result:
                raise ValueError("Failed to get gas price")
            
            gas_price = gas_price_result.get("gas_price_wei", 0)
            
            # Get nonce
            nonce = self.get_transaction_count(crypto_address.address)
            if nonce is None:
                raise ValueError("Failed to get transaction count")
            
            # Convert amount to wei
            amount_wei = int(amount_eth * 10**18)
            
            # Create transaction parameters
            tx_params = {
                "from": crypto_address.address,
                "to": to_address,
                "value": hex(amount_wei),
                "gas": hex(gas_limit),
                "gasPrice": hex(gas_price),
                "nonce": hex(nonce)
            }
            
            # Estimate gas if needed
            gas_estimate = self.estimate_gas(crypto_address.address, to_address, hex(amount_wei))
            if gas_estimate:
                estimated_gas = int(gas_estimate.get("result", "0x0"), 16)
                tx_params["gas"] = hex(max(estimated_gas, gas_limit))
            
            # Sign and send transaction using Alchemy's eth_sendRawTransaction
            # First, we need to sign the transaction with the private key
            from eth_account import Account
            
            # Create the transaction for signing
            transaction = {
                'to': to_address,
                'value': amount_wei,
                'gas': gas_limit,
                'gasPrice': gas_price,
                'nonce': nonce,
                'chainId': 11155111  # Sepolia testnet chain ID
            }
            
            # Sign the transaction
            signed_txn = Account.sign_transaction(transaction, private_key)
            
            # Send the signed transaction
            raw_tx_hash = signed_txn.raw_transaction.hex()
            send_result = self.make_request("eth_sendRawTransaction", [raw_tx_hash])
            
            if not send_result or "result" not in send_result:
                error_msg = send_result.get("error", {}).get("message", "Unknown error") if send_result else "No response"
                raise ValueError(f"Failed to send transaction: {error_msg}")
            
            tx_hash = send_result["result"]
            
            self.logger.info(f"📤 ETH transaction sent: {amount_eth} ETH to {to_address}")
            self.logger.info(f"   Transaction Hash: {tx_hash}")
            self.logger.info(f"   Gas Price: {gas_price} wei")
            self.logger.info(f"   Gas Limit: {gas_limit}")
            self.logger.info(f"   Nonce: {nonce}")
            
            return {
                "status": "sent",
                "transaction_hash": tx_hash,
                "transaction_params": tx_params,
                "from_address": crypto_address.address,
                "to_address": to_address,
                "amount_eth": amount_eth,
                "amount_wei": amount_wei,
                "gas_price": gas_price,
                "gas_limit": gas_limit,
                "nonce": nonce,
                "estimated_cost_wei": gas_price * gas_limit,
                "estimated_cost_eth": (gas_price * gas_limit) / 10**18
            }
            
        except Exception as e:
            self.logger.error(f"❌ Error sending ETH transaction: {e}")
            raise

    def send_erc20_transfer(self, contract_address: str, to_address: str, amount_standard: float, decimals: int) -> Optional[Dict]:
        """Send an ERC-20 transfer using raw calldata (transfer(address,uint256))."""
        try:
            # Get sender crypto address
            crypto_address = self.session.query(CryptoAddress).filter_by(
                account_id=self.account_id,
                currency_code="ETH",
                is_active=True,
            ).first()
            if not crypto_address:
                raise ValueError(f"No active ETH address found for account {self.account_id}")

            self.logger.info(f"Sending ERC20 transfer: {amount_standard} {crypto_address.address} to {to_address} on {contract_address}")
            # Decrypt private key
            private_key = self.decrypt_private_key(crypto_address.private_key)

            # Gas price and nonce
            gas_price_result = self.get_gas_price()
            if not gas_price_result:
                raise ValueError("Failed to get gas price")
            gas_price = gas_price_result.get("gas_price_wei", 0)
            nonce = self.get_transaction_count(crypto_address.address)
            if nonce is None:
                raise ValueError("Failed to get transaction count")

            # Value (smallest units)
            value_smallest = int(round(amount_standard * (10 ** int(decimals or 0))))

            # Build ERC-20 transfer calldata: function selector 0xa9059cbb + 32-byte addr + 32-byte value
            fn_selector = "0xa9059cbb"
            to_padded = to_address.lower().replace("0x", "").rjust(64, "0")
            value_padded = hex(value_smallest)[2:].rjust(64, "0")
            data = fn_selector + to_padded + value_padded

            # Estimate gas
            gas_limit = 100000  # default upper bound
            try:
                est = self.estimate_gas(crypto_address.address, contract_address, "0x0", data)
                if est and "gas_estimate" in est:
                    gas_limit = max(gas_limit, int(est["gas_estimate"]))
            except Exception:
                pass

            # Sign and send raw transaction
            from eth_account import Account as EthAccount
            chain_id = 11155111 if self.config.network == "sepolia" else 1
            tx = {
                "to": contract_address,
                "value": 0,
                "gas": gas_limit,
                "gasPrice": gas_price,
                "nonce": nonce,
                "data": data,
                "chainId": chain_id,
            }
            signed = EthAccount.sign_transaction(tx, private_key)
            raw = signed.raw_transaction.hex()
            send_result = self.make_request("eth_sendRawTransaction", [raw])
            if not send_result or "result" not in send_result:
                error_msg = send_result.get("error", {}).get("message", "Unknown error") if send_result else "No response"
                raise ValueError(f"Failed to send ERC20 transfer: {error_msg}")
            tx_hash = send_result["result"]
            self.logger.info(f"📤 ERC20 transfer sent: {amount_standard} to {to_address} on {contract_address}; tx={tx_hash}")
            return {
                "status": "sent",
                "transaction_hash": tx_hash,
                "from_address": crypto_address.address,
                "to_address": to_address,
                "contract_address": contract_address,
                "amount_standard": amount_standard,
                "amount_smallest": value_smallest,
                "gas_price": gas_price,
                "gas_limit": gas_limit,
                "nonce": nonce,
            }
        except Exception as e:
            self.logger.error(f"❌ Error sending ERC20 transfer: {e}")
            raise

    # ===== Token account helpers (ERC-20) =====

    def create_token_account(self, token_symbol: str, token_decimals: int = 18, label: Optional[str] = None) -> Optional[Account]:
        """
        Create a CRYPTO `Account` for an ERC-20 token (e.g., USDT/USDC) for this user on Ethereum.

        Notes:
        - Token account reuses the existing ETH on-chain address; no new CryptoAddress is created here.
        - `precision_config` is set with provided `token_decimals` and `parent_currency='ETH'`.
        - Idempotent per (user, symbol, parent ETH): if one exists, return it.
        """
        try:
            # Check if a token account already exists for this user on ETH
            existing = (
                self.session.query(Account)
                .filter(
                    Account.user_id == self.user_id,
                    Account.account_type == AccountType.CRYPTO,
                    Account.currency == token_symbol.upper(),
                )
                .all()
            )
            for acc in existing:
                cfg = acc.precision_config or {}
                if str(cfg.get("parent_currency", "")).upper() == "ETH":
                    self.logger.info("[%s] Token account already exists for user %s (id=%s)", token_symbol.upper(), self.user_id, acc.id)
                    return acc

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
                    "decimals": int(token_decimals),
                    "smallest_unit": "units",
                    "parent_currency": "ETH",
                },
            )
            self.session.add(token_account)
            self.session.commit()
            self.session.refresh(token_account)
            self.logger.info("[%s] Created token account for user %s (id=%s)", token_symbol.upper(), self.user_id, token_account.id)
            return token_account
        except Exception as e:
            self.logger.error("Failed to create token account %s for user %s: %s", token_symbol, self.user_id, e)
            self.session.rollback()
            return None

    def create_usdt_account(self) -> Optional[Account]:
        """Convenience helper to create a USDT (ERC-20) account with 6 decimals."""
        return self.create_token_account("USDT", token_decimals=6, label="USDT Wallet")

    def create_usdc_account(self) -> Optional[Account]:
        """Convenience helper to create a USDC (ERC-20) account with 6 decimals."""
        return self.create_token_account("USDC", token_decimals=6, label="USDC Wallet")
    
    def get_transaction_status(self, tx_hash: str) -> Optional[Dict]:
        """Get transaction status and receipt"""
        try:
            receipt = self.get_transaction_receipt(tx_hash)
            if not receipt:
                return {"status": "pending", "tx_hash": tx_hash}
            
            status = "success" if receipt.get("status") == "0x1" else "failed"
            gas_used = int(receipt.get("gasUsed", "0x0"), 16)
            block_number = int(receipt.get("blockNumber", "0x0"), 16)
            
            return {
                "status": status,
                "tx_hash": tx_hash,
                "gas_used": gas_used,
                "block_number": block_number,
                "receipt": receipt
            }
        except Exception as e:
            self.logger.error(f"❌ Error getting transaction status: {e}")
            return None 