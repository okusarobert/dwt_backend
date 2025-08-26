#!/usr/bin/env python3
"""
Multi-Network Deposit Handler
Manages deposit addresses and transactions for tokens across multiple networks
"""

import sys
import os
from typing import Dict, List, Optional, Tuple
from flask import jsonify

# Add paths for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'shared'))

from shared.multi_network_config import (
    MULTI_NETWORK_TOKENS, 
    NetworkType, 
    get_network_config,
    get_available_networks,
    get_available_networks_filtered,
    get_currency_code_from_network
)
from db.connection import get_session
from db.wallet import Account, CryptoAddress, AccountType
from shared.logger import setup_logging

logger = setup_logging()

class MultiNetworkDepositManager:
    """Manages multi-network deposit addresses and configurations"""
    
    def __init__(self):
        self.session = None
    
    def get_deposit_networks(self, token_symbol: str, include_testnets: bool = False) -> Dict:
        """Get available networks for a token deposit"""
        try:
            # Check if it's a multi-network token first
            if token_symbol in MULTI_NETWORK_TOKENS:
                networks = get_available_networks_filtered(token_symbol, include_testnets)
                return {
                    "success": True,
                    "token_symbol": token_symbol,
                    "networks": networks,
                    "include_testnets": include_testnets
                }
            
            # For single-network currencies, query admin database for network info
            from db.connection import session
            from db.currency import Currency, CurrencyNetwork
            
            try:
                currency = session.query(Currency).filter_by(
                    symbol=token_symbol.upper(),
                    is_enabled=True
                ).first()
                
                if not currency:
                    return {
                        "success": False,
                        "error": f"Currency {token_symbol} not found or not enabled"
                    }
                
                if currency.is_multi_network:
                    # This shouldn't happen, but fallback to multi-network logic
                    networks = get_available_networks_filtered(token_symbol, include_testnets)
                else:
                    # Single network currency - create default network entry
                    networks = [{
                        "network_type": token_symbol.lower(),
                        "network_name": currency.name,
                        "display_name": f"{currency.name} Network",
                        "currency_code": token_symbol.upper(),
                        "confirmation_blocks": self._get_default_confirmations(token_symbol),
                        "explorer_url": self._get_default_explorer(token_symbol),
                        "is_testnet": False
                    }]
                
                return {
                    "success": True,
                    "token_symbol": token_symbol,
                    "networks": networks,
                    "include_testnets": include_testnets
                }
                
            finally:
                session.close()
            
        except Exception as e:
            logger.error(f"Error getting deposit networks for {token_symbol}: {e}")
            return {
                "success": False,
                "error": "Failed to get available networks"
            }
    
    def _get_default_confirmations(self, token_symbol: str) -> int:
        """Get default confirmation blocks for a currency"""
        confirmation_map = {
            'BTC': 6,
            'LTC': 6,
            'ETH': 12,
            'TRX': 19,
            'XRP': 1,
            'SOL': 1,
            'BNB': 15,
            'MATIC': 12,
            'USDT': 12,
            'USDC': 12
        }
        return confirmation_map.get(token_symbol.upper(), 12)
    
    def _get_default_explorer(self, token_symbol: str) -> str:
        """Get default explorer URL for a currency"""
        explorer_map = {
            'BTC': 'https://blockstream.info',
            'LTC': 'https://blockchair.com/litecoin',
            'ETH': 'https://etherscan.io',
            'TRX': 'https://tronscan.org',
            'XRP': 'https://xrpscan.com',
            'SOL': 'https://explorer.solana.com',
            'BNB': 'https://bscscan.com',
            'MATIC': 'https://polygonscan.com',
            'USDT': 'https://etherscan.io',
            'USDC': 'https://etherscan.io'
        }
        return explorer_map.get(token_symbol.upper(), 'https://etherscan.io')
    
    def get_deposit_address(self, user_id: int, token_symbol: str, network_type: str) -> Dict:
        """Get or create deposit address for specific token and network"""
        session = get_session()
        try:
            network_config = get_network_config(token_symbol, network_type)
            if not network_config:
                return {
                    "success": False,
                    "error": f"Network {network_type} not supported for {token_symbol}"
                }
            
            # For multi-network tokens, find existing USDT account (not network-specific)
            base_currency = token_symbol  # Use base symbol like "USDT"
            account = session.query(Account).filter_by(
                user_id=user_id,
                currency=base_currency
            ).first()
            
            if not account:
                # Auto-create the base currency account
                logger.info(f"Creating {base_currency} account for user {user_id}")
                
                # Generate unique account number
                import random
                import string
                account_number = ''.join(random.choices(string.digits, k=10))
                
                account = Account(
                    user_id=user_id,
                    currency=base_currency,
                    account_type=AccountType.CRYPTO,
                    balance=0,
                    locked_amount=0,
                    account_number=account_number
                )
                session.add(account)
                session.flush()  # Get the account ID
            
            # Get parent currency for the network (e.g., TRX for Tron, ETH for Ethereum)
            parent_currency = self._get_parent_currency_for_network(network_type)
            if not parent_currency:
                return {
                    "success": False,
                    "error": f"Parent currency not found for network {network_type}"
                }
            
            # Find crypto address for the parent currency
            # First get the parent currency account, create if doesn't exist
            parent_account = session.query(Account).filter_by(
                user_id=user_id,
                currency=parent_currency,
                account_type=AccountType.CRYPTO
            ).first()
            
            if not parent_account:
                # Auto-create the parent currency account
                logger.info(f"Creating {parent_currency} account for user {user_id}")
                
                # Generate unique account number
                import random
                import string
                account_number = ''.join(random.choices(string.digits, k=10))
                
                parent_account = Account(
                    user_id=user_id,
                    currency=parent_currency,
                    account_number=account_number,
                    account_type=AccountType.CRYPTO,
                    balance=0.0,
                    locked_amount=0.0,
                    crypto_balance_smallest_unit=0
                )
                session.add(parent_account)
                session.flush()  # Get the account ID
            
            crypto_address = session.query(CryptoAddress).filter_by(
                account_id=parent_account.id,
                currency_code=parent_currency,
                is_active=True
            ).first()
            
            if not crypto_address:
                # Auto-generate the parent currency address for existing or new account
                logger.info(f"Generating {parent_currency} address for user {user_id} (account_id: {parent_account.id})")
                address_result = self._generate_parent_currency_address(user_id, parent_account.id, parent_currency, network_type, session)
                logger.warning(f"Address result: {address_result}")
                if not address_result.get("success"):
                    return address_result
                
                # Flush to ensure the address is saved in this transaction
                session.flush()
                
                # Query again for the created address
                crypto_address = session.query(CryptoAddress).filter_by(
                    account_id=parent_account.id,
                    currency_code=parent_currency,
                    is_active=True
                ).first()
                
                # If still not found, there's an issue with address generation
                if not crypto_address:
                    logger.error(f"Failed to create {parent_currency} address for user {user_id} (account_id: {parent_account.id})")
                    return {
                        "success": False,
                        "error": f"Failed to create {parent_currency} address"
                    }
            
            address_info = {
                "success": True,
                "address": crypto_address.address,
                "currency_code": base_currency,
                "network": {
                    "type": network_type,
                    "name": network_config.display_name,
                    "confirmation_blocks": network_config.confirmation_blocks,
                    "explorer_url": network_config.explorer_url
                },
                "token_info": {
                    "symbol": token_symbol,
                    "contract_address": network_config.contract_address,
                    "decimals": network_config.decimals
                }
            }
            
            session.commit()
            return address_info
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error getting deposit address for {user_id}, {token_symbol}, {network_type}: {e}")
            return {
                "success": False,
                "error": "Failed to generate deposit address"
            }
        finally:
            session.close()
    
    def _get_parent_currency_for_network(self, network_type: str) -> Optional[str]:
        """Get the parent currency for a given network type"""
        import os
        
        # Check environment variables for network preferences
        trx_network = os.getenv('TRX_NETWORK', 'mainnet').lower()
        eth_network = os.getenv('ETH_NETWORK', 'mainnet').lower()
        
        # All networks use the same parent currency regardless of mainnet/testnet
        # This ensures unified balances across networks
        network_parent_mapping = {
            # Ethereum networks - all use ETH account
            'ethereum': 'ETH',
            'ethereum_sepolia': 'ETH',
            'ethereum_goerli': 'ETH',
            
            # Layer 2 and side chains - all use ETH account for ETH deposits
            'base': 'ETH',
            'base_sepolia': 'ETH',
            'arbitrum': 'ETH',
            'arbitrum_sepolia': 'ETH',
            'optimism': 'ETH',
            'optimism_sepolia': 'ETH',
            
            # Binance Smart Chain networks - all use BNB account
            'bsc': 'BNB',
            'bsc_testnet': 'BNB',
            
            # Tron networks - all use TRX account
            'tron': 'TRX',
            'tron_shasta': 'TRX',
            
            # Polygon networks - all use MATIC account
            'polygon': 'MATIC',
            'polygon_mumbai': 'MATIC',
            
            # Native blockchain networks
            'bitcoin': 'BTC',
            'bitcoin_testnet': 'BTC',
            'litecoin': 'LTC',
            'litecoin_testnet': 'LTC',
            
            # XRP networks
            'xrp': 'XRP',
            'xrp_testnet': 'XRP',
            
            # Solana networks
            'solana': 'SOL',
            'solana_devnet': 'SOL',
            'solana_testnet': 'SOL'
        }
        return network_parent_mapping.get(network_type.lower())
    
    def _generate_parent_currency_address(self, user_id: int, account_id: int, parent_currency: str, network_type: str, session) -> Dict:
        """Generate address for parent currency (ETH, BNB, TRX, etc.)"""
        try:
            if parent_currency == "ETH":
                logger.info(f"Generating ETH address for user {user_id} (account_id: {account_id})")
                return self._generate_eth_address(user_id, account_id, session)
            elif parent_currency == "BNB":
                logger.info(f"Generating BNB address for user {user_id} (account_id: {account_id})")
                return self._generate_bnb_address(user_id, account_id, session)
            elif parent_currency == "TRX":
                logger.info(f"Generating TRX address for user {user_id} (account_id: {account_id})")
                return self._generate_trx_address(user_id, account_id, session)
            elif parent_currency == "MATIC":
                logger.info(f"Generating MATIC address for user {user_id} (account_id: {account_id})")
                return self._generate_matic_address(user_id, account_id, session)
            elif parent_currency == "BTC":
                logger.info(f"Generating BTC address for user {user_id} (account_id: {account_id})")
                return self._generate_btc_address(user_id, account_id, session)
            elif parent_currency == "LTC":
                logger.info(f"Generating LTC address for user {user_id} (account_id: {account_id})")
                return self._generate_ltc_address(user_id, account_id, session)
            elif parent_currency == "XRP":
                logger.info(f"Generating XRP address for user {user_id} (account_id: {account_id})")
                return self._generate_xrp_address(user_id, account_id, network_type, session)
            elif parent_currency == "SOL":
                logger.info(f"Generating SOL address for user {user_id} (account_id: {account_id})")
                return self._generate_sol_address(user_id, account_id, network_type, session)
            else:
                return {
                    "success": False,
                    "error": f"Address generation not implemented for {parent_currency}"
                }
        except Exception as e:
            logger.error(f"Error generating {parent_currency} address: {e}")
            return {
                "success": False,
                "error": f"Failed to generate {parent_currency} address"
            }
    
    def _generate_eth_address(self, user_id: int, account_id: int, session) -> Dict:
        """Generate ETH address using EVM base client"""
        try:
            from shared.crypto.clients.evm_base_client import create_ethereum_client
            from decouple import config
            
            # Get network configuration
            eth_network = config('ETH_NETWORK', default='mainnet')
            
            # Create ETH wallet instance using EVM base client
            eth_wallet = create_ethereum_client(user_id=user_id, session=session, network=eth_network)
            eth_wallet.account_id = account_id
            
            # Create address
            eth_wallet.create_address(notify=False)
            
            # Commit the session to ensure address is saved
            session.commit()
            
            return {"success": True}
        except Exception as e:
            logger.error(f"Error generating ETH address: {e}")
            return {"success": False, "error": "Failed to generate ETH address"}
    
    def _generate_bnb_address(self, user_id: int, account_id: int, session) -> Dict:
        """Generate BNB address using EVM base client"""
        try:
            from shared.crypto.clients.evm_base_client import create_bnb_client
            logger.info(f"Creating BNB client") 
            # Create BNB wallet instance using EVM base client
            bnb_wallet = create_bnb_client(user_id=user_id, session=session, network="mainnet")
            bnb_wallet.account_id = account_id
            
            # Create address
            res = bnb_wallet.create_address(notify=False)
            logger.info(f"BNB address creation result: {res}")
            
            # Flush to ensure address is saved but don't commit yet
            session.flush()
            
            return {"success": True}
        except Exception as e:
            logger.error(f"Error generating BNB address: {e}")
            return {"success": False, "error": "Failed to generate BNB address"}
    
    def _generate_trx_address(self, user_id: int, account_id: int, session) -> Dict:
        """Generate TRX address"""
        try:
            from shared.crypto.clients.trx_client import TRXWallet
            
            trx_wallet = TRXWallet()
            wallet_data = trx_wallet.create_wallet()
            
            crypto_address = CryptoAddress(
                user_id=user_id,
                account_id=account_id,
                currency_code="TRX",
                address=wallet_data["address"],
                private_key_encrypted=wallet_data["private_key"],
                is_active=True
            )
            session.add(crypto_address)
            
            return {"success": True}
        except Exception as e:
            logger.error(f"Error generating TRX address: {e}")
            return {"success": False, "error": "Failed to generate TRX address"}
    
    def _generate_matic_address(self, user_id: int, account_id: int, session) -> Dict:
        """Generate MATIC address using EVM base client"""
        try:
            from shared.crypto.clients.evm_base_client import create_polygon_client
            
            # Create Polygon wallet instance using EVM base client
            matic_wallet = create_polygon_client(user_id=user_id, session=session, network="mainnet")
            matic_wallet.account_id = account_id
            
            # Create address
            matic_wallet.create_address(notify=False)
            
            # Commit the session to ensure address is saved
            session.commit()
            
            return {"success": True}
        except Exception as e:
            logger.error(f"Error generating MATIC address: {e}")
            return {"success": False, "error": "Failed to generate MATIC address"}
    
    def _generate_network_address(self, user_id: int, account_id: int, currency_code: str, 
                                 network_config, session) -> Dict:
        """Generate address for specific network using EVM base client"""
        try:
            network_type = network_config.network_type.value
            
            # Use appropriate EVM client based on network type
            if network_type in ["ethereum", "ethereum_sepolia"]:
                return self._generate_ethereum_address(user_id, account_id, currency_code, network_config, session)
            elif network_type in ["base", "base_sepolia"]:
                return self._generate_base_address(user_id, account_id, currency_code, network_config, session)
            elif network_type in ["arbitrum_one", "arbitrum_sepolia"]:
                return self._generate_arbitrum_address(user_id, account_id, currency_code, network_config, session)
            elif network_type in ["optimism", "optimism_sepolia"]:
                return self._generate_optimism_address(user_id, account_id, currency_code, network_config, session)
            elif network_type in ["polygon", "polygon_testnet"]:
                return self._generate_polygon_address(user_id, account_id, currency_code, network_config, session)
            elif network_type in ["bsc", "bsc_testnet"]:
                return self._generate_bsc_address(user_id, account_id, currency_code, network_config, session)
            elif network_type == "tron":
                return self._generate_tron_address(user_id, account_id, currency_code, network_config, session)
            else:
                return {
                    "success": False,
                    "error": f"Network {network_type} not supported"
                }
        except Exception as e:
            logger.error(f"Error generating {network_config.network_type.value} address: {e}")
            return {
                "success": False,
                "error": f"Failed to generate {network_config.network_type.value} address"
            }
    
    def _generate_ethereum_address(self, user_id: int, account_id: int, currency_code: str, 
                                  network_config, session) -> Dict:
        """Generate Ethereum-based address (ERC-20) using EVM base client"""
        from shared.crypto.clients.evm_base_client import create_ethereum_client
        from decouple import config
        
        try:
            # Check if user already has an ETH address we can reuse
            existing_eth_address = session.query(CryptoAddress).filter_by(
                account_id=account_id,
                currency_code="ETH",
                is_active=True
            ).first()
            
            if existing_eth_address:
                # Create new CryptoAddress record for this token using same address
                crypto_address = CryptoAddress(
                    account_id=account_id,
                    currency_code=currency_code,
                    address=existing_eth_address.address,
                    private_key=existing_eth_address.private_key,
                    public_key=existing_eth_address.public_key,
                    label=f"{currency_code} Address",
                    is_active=True,
                    address_type="hd_wallet"
                )
                session.add(crypto_address)
                
                return {
                    "success": True,
                    "address": crypto_address.address,
                    "currency_code": currency_code,
                    "network": {
                        "type": network_config.network_type.value,
                        "name": network_config.display_name,
                        "confirmation_blocks": network_config.confirmation_blocks,
                        "explorer_url": network_config.explorer_url
                    },
                    "token_info": {
                        "symbol": network_config.currency_code.split('_')[0],
                        "contract_address": network_config.contract_address,
                        "decimals": network_config.decimals
                    }
                }
            else:
                # Generate new ETH address if none exists
                eth_network = config('ETH_NETWORK', default='mainnet')
                
                # Create ETH wallet instance using EVM base client
                eth_wallet = create_ethereum_client(user_id=user_id, session=session, network=eth_network)
                eth_wallet.account_id = account_id
                
                # Create address
                eth_wallet.create_address(notify=False)
                
                # Commit to ensure address is saved
                session.commit()
                
                # Now get the created ETH address and create token address record
                eth_address = session.query(CryptoAddress).filter_by(
                    account_id=account_id,
                    currency_code="ETH",
                    is_active=True
                ).first()
                
                if eth_address:
                    # Create new CryptoAddress record for this token using same address
                    crypto_address = CryptoAddress(
                        account_id=account_id,
                        currency_code=currency_code,
                        address=eth_address.address,
                        private_key=eth_address.private_key,
                        public_key=eth_address.public_key,
                        label=f"{currency_code} Address",
                        is_active=True,
                        address_type="hd_wallet"
                    )
                    session.add(crypto_address)
                    
                    return {
                        "success": True,
                        "address": crypto_address.address,
                        "currency_code": currency_code,
                        "network": {
                            "type": network_config.network_type.value,
                            "name": network_config.display_name,
                            "confirmation_blocks": network_config.confirmation_blocks,
                            "explorer_url": network_config.explorer_url
                        },
                        "token_info": {
                            "symbol": network_config.currency_code.split('_')[0],
                            "contract_address": network_config.contract_address,
                            "decimals": network_config.decimals
                        }
                    }
                else:
                    return {
                        "success": False,
                        "error": "Failed to create ETH address for token deposit"
                    }
                
        except Exception as e:
            logger.error(f"Error generating Ethereum address: {e}")
            return {
                "success": False,
                "error": "Failed to generate Ethereum address"
            }
    
    def _generate_base_address(self, user_id: int, account_id: int, currency_code: str, 
                              network_config, session) -> Dict:
        """Generate Base network address using EVM base client"""
        from shared.crypto.clients.evm_base_client import create_base_client
        
        try:
            # Check if user already has a Base ETH address we can reuse
            existing_address = session.query(CryptoAddress).filter_by(
                account_id=account_id,
                currency_code="ETH",
                is_active=True
            ).first()
            
            if existing_address:
                # Create new CryptoAddress record for this token using same address
                crypto_address = CryptoAddress(
                    account_id=account_id,
                    currency_code=currency_code,
                    address=existing_address.address,
                    private_key=existing_address.private_key,
                    public_key=existing_address.public_key,
                    label=f"{currency_code} Address (Base)",
                    is_active=True,
                    address_type="hd_wallet"
                )
                session.add(crypto_address)
                
                return {
                    "success": True,
                    "address": crypto_address.address,
                    "currency_code": currency_code,
                    "network": {
                        "type": network_config.network_type.value,
                        "name": network_config.display_name,
                        "confirmation_blocks": network_config.confirmation_blocks,
                        "explorer_url": network_config.explorer_url
                    },
                    "token_info": {
                        "symbol": network_config.currency_code.split('_')[0],
                        "contract_address": network_config.contract_address,
                        "decimals": network_config.decimals
                    }
                }
            else:
                # Generate new Base address if none exists
                network = "testnet" if "sepolia" in network_config.network_type.value else "mainnet"
                base_wallet = create_base_client(user_id=user_id, session=session, network=network)
                base_wallet.account_id = account_id
                base_wallet.create_address(notify=False)
                session.commit()
                
                # Get the created address and create token address record
                base_address = session.query(CryptoAddress).filter_by(
                    account_id=account_id,
                    currency_code="ETH",
                    is_active=True
                ).first()
                
                if base_address:
                    crypto_address = CryptoAddress(
                        account_id=account_id,
                        currency_code=currency_code,
                        address=base_address.address,
                        private_key=base_address.private_key,
                        public_key=base_address.public_key,
                        label=f"{currency_code} Address (Base)",
                        is_active=True,
                        address_type="hd_wallet"
                    )
                    session.add(crypto_address)
                    
                    return {
                        "success": True,
                        "address": crypto_address.address,
                        "currency_code": currency_code,
                        "network": {
                            "type": network_config.network_type.value,
                            "name": network_config.display_name,
                            "confirmation_blocks": network_config.confirmation_blocks,
                            "explorer_url": network_config.explorer_url
                        },
                        "token_info": {
                            "symbol": network_config.currency_code.split('_')[0],
                            "contract_address": network_config.contract_address,
                            "decimals": network_config.decimals
                        }
                    }
                else:
                    return {
                        "success": False,
                        "error": "Failed to create Base address for token deposit"
                    }
                
        except Exception as e:
            logger.error(f"Error generating Base address: {e}")
            return {
                "success": False,
                "error": "Failed to generate Base address"
            }
    
    def _generate_arbitrum_address(self, user_id: int, account_id: int, currency_code: str, 
                                  network_config, session) -> Dict:
        """Generate Arbitrum network address using EVM base client"""
        from shared.crypto.clients.evm_base_client import create_arbitrum_client
        
        try:
            # Check if user already has an Arbitrum ETH address we can reuse
            existing_address = session.query(CryptoAddress).filter_by(
                account_id=account_id,
                currency_code="ETH",
                is_active=True
            ).first()
            
            if existing_address:
                crypto_address = CryptoAddress(
                    account_id=account_id,
                    currency_code=currency_code,
                    address=existing_address.address,
                    private_key=existing_address.private_key,
                    public_key=existing_address.public_key,
                    label=f"{currency_code} Address (Arbitrum)",
                    is_active=True,
                    address_type="hd_wallet"
                )
                session.add(crypto_address)
                
                return {
                    "success": True,
                    "address": crypto_address.address,
                    "currency_code": currency_code,
                    "network": {
                        "type": network_config.network_type.value,
                        "name": network_config.display_name,
                        "confirmation_blocks": network_config.confirmation_blocks,
                        "explorer_url": network_config.explorer_url
                    },
                    "token_info": {
                        "symbol": network_config.currency_code.split('_')[0],
                        "contract_address": network_config.contract_address,
                        "decimals": network_config.decimals
                    }
                }
            else:
                network = "testnet" if "sepolia" in network_config.network_type.value else "mainnet"
                arbitrum_wallet = create_arbitrum_client(user_id=user_id, session=session, network=network)
                arbitrum_wallet.account_id = account_id
                arbitrum_wallet.create_address(notify=False)
                session.commit()
                
                arbitrum_address = session.query(CryptoAddress).filter_by(
                    account_id=account_id,
                    currency_code="ETH",
                    is_active=True
                ).first()
                
                if arbitrum_address:
                    crypto_address = CryptoAddress(
                        account_id=account_id,
                        currency_code=currency_code,
                        address=arbitrum_address.address,
                        private_key=arbitrum_address.private_key,
                        public_key=arbitrum_address.public_key,
                        label=f"{currency_code} Address (Arbitrum)",
                        is_active=True,
                        address_type="hd_wallet"
                    )
                    session.add(crypto_address)
                    
                    return {
                        "success": True,
                        "address": crypto_address.address,
                        "currency_code": currency_code,
                        "network": {
                            "type": network_config.network_type.value,
                            "name": network_config.display_name,
                            "confirmation_blocks": network_config.confirmation_blocks,
                            "explorer_url": network_config.explorer_url
                        },
                        "token_info": {
                            "symbol": network_config.currency_code.split('_')[0],
                            "contract_address": network_config.contract_address,
                            "decimals": network_config.decimals
                        }
                    }
                else:
                    return {
                        "success": False,
                        "error": "Failed to create Arbitrum address for token deposit"
                    }
                
        except Exception as e:
            logger.error(f"Error generating Arbitrum address: {e}")
            return {
                "success": False,
                "error": "Failed to generate Arbitrum address"
            }
    
    def _generate_optimism_address(self, user_id: int, account_id: int, currency_code: str, 
                                  network_config, session) -> Dict:
        """Generate Optimism network address using EVM base client"""
        from shared.crypto.clients.evm_base_client import create_optimism_client
        
        try:
            # Check if user already has an Optimism ETH address we can reuse
            existing_address = session.query(CryptoAddress).filter_by(
                account_id=account_id,
                currency_code="ETH",
                is_active=True
            ).first()
            
            if existing_address:
                crypto_address = CryptoAddress(
                    account_id=account_id,
                    currency_code=currency_code,
                    address=existing_address.address,
                    private_key=existing_address.private_key,
                    public_key=existing_address.public_key,
                    label=f"{currency_code} Address (Optimism)",
                    is_active=True,
                    address_type="hd_wallet"
                )
                session.add(crypto_address)
                
                return {
                    "success": True,
                    "address": crypto_address.address,
                    "currency_code": currency_code,
                    "network": {
                        "type": network_config.network_type.value,
                        "name": network_config.display_name,
                        "confirmation_blocks": network_config.confirmation_blocks,
                        "explorer_url": network_config.explorer_url
                    },
                    "token_info": {
                        "symbol": network_config.currency_code.split('_')[0],
                        "contract_address": network_config.contract_address,
                        "decimals": network_config.decimals
                    }
                }
            else:
                network = "testnet" if "sepolia" in network_config.network_type.value else "mainnet"
                optimism_wallet = create_optimism_client(user_id=user_id, session=session, network=network)
                optimism_wallet.account_id = account_id
                optimism_wallet.create_address(notify=False)
                session.commit()
                
                optimism_address = session.query(CryptoAddress).filter_by(
                    account_id=account_id,
                    currency_code="ETH",
                    is_active=True
                ).first()
                
                if optimism_address:
                    crypto_address = CryptoAddress(
                        account_id=account_id,
                        currency_code=currency_code,
                        address=optimism_address.address,
                        private_key=optimism_address.private_key,
                        public_key=optimism_address.public_key,
                        label=f"{currency_code} Address (Optimism)",
                        is_active=True,
                        address_type="hd_wallet"
                    )
                    session.add(crypto_address)
                    
                    return {
                        "success": True,
                        "address": crypto_address.address,
                        "currency_code": currency_code,
                        "network": {
                            "type": network_config.network_type.value,
                            "name": network_config.display_name,
                            "confirmation_blocks": network_config.confirmation_blocks,
                            "explorer_url": network_config.explorer_url
                        },
                        "token_info": {
                            "symbol": network_config.currency_code.split('_')[0],
                            "contract_address": network_config.contract_address,
                            "decimals": network_config.decimals
                        }
                    }
                else:
                    return {
                        "success": False,
                        "error": "Failed to create Optimism address for token deposit"
                    }
                
        except Exception as e:
            logger.error(f"Error generating Optimism address: {e}")
            return {
                "success": False,
                "error": "Failed to generate Optimism address"
            }
    
    def _generate_polygon_address(self, user_id: int, account_id: int, currency_code: str, 
                                 network_config, session) -> Dict:
        """Generate Polygon network address using EVM base client"""
        from shared.crypto.clients.evm_base_client import create_polygon_client
        
        try:
            # Check if user already has a Polygon MATIC address we can reuse
            existing_address = session.query(CryptoAddress).filter_by(
                account_id=account_id,
                currency_code="MATIC",
                is_active=True
            ).first()
            
            if existing_address:
                crypto_address = CryptoAddress(
                    account_id=account_id,
                    currency_code=currency_code,
                    address=existing_address.address,
                    private_key=existing_address.private_key,
                    public_key=existing_address.public_key,
                    label=f"{currency_code} Address (Polygon)",
                    is_active=True,
                    address_type="hd_wallet"
                )
                session.add(crypto_address)
                
                return {
                    "success": True,
                    "address": crypto_address.address,
                    "currency_code": currency_code,
                    "network": {
                        "type": network_config.network_type.value,
                        "name": network_config.display_name,
                        "confirmation_blocks": network_config.confirmation_blocks,
                        "explorer_url": network_config.explorer_url
                    },
                    "token_info": {
                        "symbol": network_config.currency_code.split('_')[0],
                        "contract_address": network_config.contract_address,
                        "decimals": network_config.decimals
                    }
                }
            else:
                network = "testnet" if "testnet" in network_config.network_type.value else "mainnet"
                polygon_wallet = create_polygon_client(user_id=user_id, session=session, network=network)
                polygon_wallet.account_id = account_id
                polygon_wallet.create_address(notify=False)
                session.commit()
                
                polygon_address = session.query(CryptoAddress).filter_by(
                    account_id=account_id,
                    currency_code="MATIC",
                    is_active=True
                ).first()
                
                if polygon_address:
                    crypto_address = CryptoAddress(
                        account_id=account_id,
                        currency_code=currency_code,
                        address=polygon_address.address,
                        private_key=polygon_address.private_key,
                        public_key=polygon_address.public_key,
                        label=f"{currency_code} Address (Polygon)",
                        is_active=True,
                        address_type="hd_wallet"
                    )
                    session.add(crypto_address)
                    
                    return {
                        "success": True,
                        "address": crypto_address.address,
                        "currency_code": currency_code,
                        "network": {
                            "type": network_config.network_type.value,
                            "name": network_config.display_name,
                            "confirmation_blocks": network_config.confirmation_blocks,
                            "explorer_url": network_config.explorer_url
                        },
                        "token_info": {
                            "symbol": network_config.currency_code.split('_')[0],
                            "contract_address": network_config.contract_address,
                            "decimals": network_config.decimals
                        }
                    }
                else:
                    return {
                        "success": False,
                        "error": "Failed to create Polygon address for token deposit"
                    }
                
        except Exception as e:
            logger.error(f"Error generating Polygon address: {e}")
            return {
                "success": False,
                "error": "Failed to generate Polygon address"
            }
    
    def _generate_bsc_address(self, user_id: int, account_id: int, currency_code: str, 
                             network_config, session) -> Dict:
        """Generate BSC network address using EVM base client"""
        from shared.crypto.clients.evm_base_client import create_bnb_client
        
        try:
            # Check if user already has a BSC BNB address we can reuse
            existing_address = session.query(CryptoAddress).filter_by(
                account_id=account_id,
                currency_code="BNB",
                is_active=True
            ).first()
            
            if existing_address:
                crypto_address = CryptoAddress(
                    account_id=account_id,
                    currency_code=currency_code,
                    address=existing_address.address,
                    private_key=existing_address.private_key,
                    public_key=existing_address.public_key,
                    label=f"{currency_code} Address (BSC)",
                    is_active=True,
                    address_type="hd_wallet"
                )
                session.add(crypto_address)
                
                return {
                    "success": True,
                    "address": crypto_address.address,
                    "currency_code": currency_code,
                    "network": {
                        "type": network_config.network_type.value,
                        "name": network_config.display_name,
                        "confirmation_blocks": network_config.confirmation_blocks,
                        "explorer_url": network_config.explorer_url
                    },
                    "token_info": {
                        "symbol": network_config.currency_code.split('_')[0],
                        "contract_address": network_config.contract_address,
                        "decimals": network_config.decimals
                    }
                }
            else:
                network = "testnet" if "testnet" in network_config.network_type.value else "mainnet"
                bsc_wallet = create_bnb_client(user_id=user_id, session=session, network=network)
                bsc_wallet.account_id = account_id
                bsc_wallet.create_address(notify=False)
                session.commit()
                
                bsc_address = session.query(CryptoAddress).filter_by(
                    account_id=account_id,
                    currency_code="BNB",
                    is_active=True
                ).first()
                
                if bsc_address:
                    crypto_address = CryptoAddress(
                        account_id=account_id,
                        currency_code=currency_code,
                        address=bsc_address.address,
                        private_key=bsc_address.private_key,
                        public_key=bsc_address.public_key,
                        label=f"{currency_code} Address (BSC)",
                        is_active=True,
                        address_type="hd_wallet"
                    )
                    session.add(crypto_address)
                    
                    return {
                        "success": True,
                        "address": crypto_address.address,
                        "currency_code": currency_code,
                        "network": {
                            "type": network_config.network_type.value,
                            "name": network_config.display_name,
                            "confirmation_blocks": network_config.confirmation_blocks,
                            "explorer_url": network_config.explorer_url
                        },
                        "token_info": {
                            "symbol": network_config.currency_code.split('_')[0],
                            "contract_address": network_config.contract_address,
                            "decimals": network_config.decimals
                        }
                    }
                else:
                    return {
                        "success": False,
                        "error": "Failed to create BSC address for token deposit"
                    }
                
        except Exception as e:
            logger.error(f"Error generating BSC address: {e}")
            return {
                "success": False,
                "error": "Failed to generate BSC address"
            }
    
    def _generate_bsc_address(self, user_id: int, account_id: int, currency_code: str, 
                             network_config, session) -> Dict:
        """Generate BSC address (BEP-20)"""
        # BSC uses same address format as Ethereum
        return self._generate_ethereum_address(user_id, account_id, currency_code, network_config, session)
    
    def _generate_tron_address(self, user_id: int, account_id: int, currency_code: str, 
                              network_config, session) -> Dict:
        """Generate Tron address (TRC-20)"""
        return {
            "success": False,
            "error": "Tron address generation not implemented yet"
        }
    
    def _generate_btc_address(self, user_id: int, account_id: int, session) -> Dict:
        """Generate Bitcoin address using existing BTC wallet system"""
        try:
            import os
            from shared.crypto.HD import BTC
            
            # Get BTC mnemonic from environment
            mnemonic = os.getenv('BTC_MNEMONIC')
            if not mnemonic:
                return {
                    "success": False,
                    "error": "BTC_MNEMONIC not configured"
                }
            
            # Create BTC wallet and generate address
            # Determine if testnet based on environment network config
            btc_network = os.getenv('BTC_NETWORK', 'testnet').lower()
            is_testnet = btc_network == 'testnet'
            btc_wallet = BTC(testnet=is_testnet)
            btc_wallet = btc_wallet.from_mnemonic(mnemonic=mnemonic)
            
            # Use account_id as index for deterministic address generation
            index = account_id - 1
            address, priv_key, pub_key = btc_wallet.new_address(index=index)
            
            # Save to database
            crypto_address = CryptoAddress(
                account_id=account_id,
                address=address,
                currency_code="BTC",
                address_type="deposit"
            )
            session.add(crypto_address)
            session.flush()
            
            # Send Kafka notification
            self._send_kafka_notification(user_id, "BTC", address, "bitcoin")
            
            return {
                "success": True,
                "address": address,
                "currency_code": "BTC",
                "network": "bitcoin"
            }
        except Exception as e:
            logger.error(f"Error generating BTC address: {e}")
            return {
                "success": False,
                "error": f"Failed to generate BTC address: {str(e)}"
            }
    
    def _generate_ltc_address(self, user_id: int, account_id: int, session) -> Dict:
        """Generate Litecoin address using existing LTC wallet system"""
        try:
            import os
            from shared.crypto.HD import LTC
            
            # Get LTC mnemonic from environment (fallback to BTC if not set)
            mnemonic = os.getenv('LTC_MNEMONIC') or os.getenv('BTC_MNEMONIC')
            if not mnemonic:
                return {
                    "success": False,
                    "error": "LTC_MNEMONIC or BTC_MNEMONIC not configured"
                }
            
            # Create LTC wallet and generate address
            # Determine if testnet based on environment network config
            ltc_network = os.getenv('LTC_NETWORK', 'testnet').lower()
            is_testnet = ltc_network == 'testnet'
            ltc_wallet = LTC(testnet=is_testnet)
            ltc_wallet = ltc_wallet.from_mnemonic(mnemonic=mnemonic)
            
            # Use account_id as index for deterministic address generation
            index = account_id - 1
            address, priv_key, pub_key = ltc_wallet.new_address(index=index)
            
            # Save to database
            crypto_address = CryptoAddress(
                account_id=account_id,
                address=address,
                currency_code="LTC",
                address_type="deposit"
            )
            session.add(crypto_address)
            session.flush()
            
            # Send Kafka notification
            self._send_kafka_notification(user_id, "LTC", address, "litecoin")
            
            return {
                "success": True,
                "address": address,
                "currency_code": "LTC",
                "network": "litecoin"
            }
        except Exception as e:
            logger.error(f"Error generating LTC address: {e}")
            return {
                "success": False,
                "error": f"Failed to generate LTC address: {str(e)}"
            }
    
    def _generate_xrp_address(self, user_id: int, account_id: int, network_type: str, session) -> Dict:
        """Generate XRP address using HD wallet"""
        try:
            from shared.crypto.HD import XRP
            from shared.multi_network_config import get_network_config
            from db.wallet import CryptoAddress
            from decouple import config
            import base64
            
            # Get network configuration
            network_config = get_network_config("XRP", network_type)
            if not network_config:
                return {
                    "success": False,
                    "error": f"Network configuration not found for XRP on {network_type}"
                }
            
            # Get XRP mnemonic from environment
            mnemonic_key = "XRP_MNEMONIC"
            mnemonic = config(mnemonic_key, default=None)
            if not mnemonic:
                return {
                    "success": False,
                    "error": "XRP_MNEMONIC not configured in environment"
                }
            
            # Create XRP wallet instance
            is_testnet = network_config.is_testnet
            xrp_wallet = XRP(testnet=is_testnet)
            wallet = xrp_wallet.from_mnemonic(mnemonic=mnemonic)
            
            # Generate address using account_id as derivation index
            index = account_id
            xrp_address, priv_key, pub_key = wallet.new_address(index=index)
            
            # Encrypt private key
            encrypted_private_key = base64.b64encode(priv_key.encode()).decode()
            
            # Create crypto address record
            crypto_address = CryptoAddress(
                account_id=account_id,
                currency_code=network_config.currency_code,
                address=xrp_address,
                private_key=encrypted_private_key,
                public_key=pub_key,
                label=f"XRP Address ({network_config.display_name})",
                is_active=True,
                address_type="hd_wallet"
            )
            
            session.add(crypto_address)
            session.commit()
            
            # Send notification
            self._send_kafka_notification(user_id, "XRP", xrp_address, network_type)
            
            logger.info(f"✅ Successfully generated XRP address for user {user_id}: {xrp_address}")
            
            return {
                "success": True,
                "address": xrp_address,
                "currency_code": network_config.currency_code,
                "network": network_type
            }
            
        except Exception as e:
            logger.error(f"Error generating XRP address: {e}")
            return {
                "success": False,
                "error": f"Failed to generate XRP address: {str(e)}"
            }
    
    def _generate_sol_address(self, user_id: int, account_id: int, network_type: str, session) -> Dict:
        """Generate SOL address using HD wallet"""
        try:
            from shared.crypto.HD import SOL
            from shared.multi_network_config import get_network_config
            from db.wallet import CryptoAddress
            from decouple import config
            import base64
            
            # Get network configuration
            network_config = get_network_config("SOL", network_type)
            if not network_config:
                return {
                    "success": False,
                    "error": f"Network configuration not found for SOL on {network_type}"
                }
            
            # Get SOL mnemonic from environment
            mnemonic_key = "SOL_MNEMONIC"
            mnemonic = config(mnemonic_key, default=None)
            if not mnemonic:
                return {
                    "success": False,
                    "error": "SOL_MNEMONIC not configured in environment"
                }
            
            # Create SOL wallet instance
            is_testnet = network_config.is_testnet
            sol_wallet = SOL(testnet=is_testnet)
            wallet = sol_wallet.from_mnemonic(mnemonic=mnemonic)
            
            # Generate address using account_id as derivation index
            index = account_id
            sol_address, priv_key, pub_key = wallet.new_address(index=index)
            
            # Encrypt private key
            encrypted_private_key = base64.b64encode(priv_key.encode()).decode()
            
            # Create crypto address record
            crypto_address = CryptoAddress(
                account_id=account_id,
                currency_code=network_config.currency_code,
                address=sol_address,
                private_key=encrypted_private_key,
                public_key=pub_key,
                label=f"SOL Address ({network_config.display_name})",
                is_active=True,
                address_type="hd_wallet"
            )
            
            session.add(crypto_address)
            session.commit()
            
            # Send notification
            self._send_kafka_notification(user_id, "SOL", sol_address, network_type)
            
            logger.info(f"✅ Successfully generated SOL address for user {user_id}: {sol_address}")
            
            return {
                "success": True,
                "address": sol_address,
                "currency_code": network_config.currency_code,
                "network": network_type
            }
            
        except Exception as e:
            logger.error(f"Error generating SOL address: {e}")
            return {
                "success": False,
                "error": f"Failed to generate SOL address: {str(e)}"
            }
    
    def _send_kafka_notification(self, user_id: int, currency: str, address: str, network: str):
        """Send Kafka notification for new address creation"""
        try:
            from shared.kafka_producer import get_kafka_producer
            producer = get_kafka_producer()
            
            message = {
                "event_type": "crypto_address_created",
                "user_id": user_id,
                "currency": currency,
                "address": address,
                "network": network,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            producer.send("crypto-address-events", message)
            logger.info(f"Sent Kafka notification for {currency} address creation: {address}")
            
        except Exception as e:
            logger.error(f"Failed to send Kafka notification for {currency} address: {e}")

# Global instance
multi_network_deposit_manager = MultiNetworkDepositManager()

def get_multi_network_deposit_options(token_symbol: str):
    """API endpoint to get deposit network options"""
    return multi_network_deposit_manager.get_deposit_networks(token_symbol)

def get_multi_network_deposit_address(user_id: int, token_symbol: str, network_type: str):
    """API endpoint to get deposit address for specific network"""
    return multi_network_deposit_manager.get_deposit_address(user_id, token_symbol, network_type)
