#!/usr/bin/env python3
"""
Multi-Network Token Configuration
Handles tokens that exist across multiple blockchain networks (ERC-20, BEP-20, TRC-20)
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

class NetworkType(Enum):
    ETHEREUM = "ethereum"
    ETHEREUM_SEPOLIA = "ethereum_sepolia"
    ETHEREUM_GOERLI = "ethereum_goerli"
    BSC = "bsc"
    BSC_TESTNET = "bsc_testnet"
    TRON = "tron"
    TRON_SHASTA = "tron_shasta"
    POLYGON = "polygon"
    POLYGON_MUMBAI = "polygon_mumbai"
    BASE = "base"
    BASE_SEPOLIA = "base_sepolia"
    ARBITRUM = "arbitrum"
    ARBITRUM_SEPOLIA = "arbitrum_sepolia"
    OPTIMISM = "optimism"
    OPTIMISM_SEPOLIA = "optimism_sepolia"
    BITCOIN = "bitcoin"
    BITCOIN_TESTNET = "bitcoin_testnet"
    LITECOIN = "litecoin"
    LITECOIN_TESTNET = "litecoin_testnet"
    XRP = "xrp"
    XRP_TESTNET = "xrp_testnet"
    SOLANA = "solana"
    SOLANA_DEVNET = "solana_devnet"
    SOLANA_TESTNET = "solana_testnet"

@dataclass
class NetworkConfig:
    """Configuration for a specific blockchain network"""
    network_type: NetworkType
    network_name: str
    display_name: str
    currency_code: str  # e.g., USDT_ERC20, USDT_BEP20
    contract_address: Optional[str]  # None for native tokens
    decimals: int
    confirmation_blocks: int
    explorer_url: str
    rpc_url_env: str  # Environment variable for RPC URL
    is_testnet: bool = False  # Flag to identify testnet networks
    
@dataclass 
class MultiNetworkToken:
    """Configuration for a token available on multiple networks"""
    base_symbol: str  # e.g., "USDT"
    display_name: str  # e.g., "Tether USD"
    networks: Dict[NetworkType, NetworkConfig]
    
    def get_network_options(self) -> List[Dict]:
        """Get network options for frontend display"""
        return [
            {
                "network_type": config.network_type.value,
                "network_name": config.network_name,
                "display_name": config.display_name,
                "currency_code": config.currency_code,
                "confirmation_blocks": config.confirmation_blocks,
                "explorer_url": config.explorer_url
            }
            for config in self.networks.values()
        ]

# Multi-network token configurations
MULTI_NETWORK_TOKENS = {
    "USDT": MultiNetworkToken(
        base_symbol="USDT",
        display_name="Tether USD",
        networks={
            NetworkType.ETHEREUM: NetworkConfig(
                network_type=NetworkType.ETHEREUM,
                network_name="ethereum",
                display_name="Ethereum (ERC-20)",
                currency_code="USDT_ERC20",
                contract_address="0xdAC17F958D2ee523a2206206994597C13D831ec7",  # Mainnet
                decimals=6,
                confirmation_blocks=3,
                explorer_url="https://etherscan.io",
                rpc_url_env="ETHEREUM_RPC_URL",
                is_testnet=False
            ),
            NetworkType.ETHEREUM_SEPOLIA: NetworkConfig(
                network_type=NetworkType.ETHEREUM_SEPOLIA,
                network_name="ethereum_sepolia",
                display_name="Ethereum Sepolia (ERC-20)",
                currency_code="USDT_ERC20_SEPOLIA",
                contract_address="0x1c7d4b196cb0c7b01d743fbc6116a902379c7238",  # Sepolia USDC (for testing)
                decimals=6,
                confirmation_blocks=1,  # Faster confirmations on testnet
                explorer_url="https://sepolia.etherscan.io",
                rpc_url_env="ETHEREUM_SEPOLIA_RPC_URL",
                is_testnet=True
            ),
            NetworkType.ETHEREUM_GOERLI: NetworkConfig(
                network_type=NetworkType.ETHEREUM_GOERLI,
                network_name="ethereum_goerli",
                display_name="Ethereum Goerli (ERC-20)",
                currency_code="USDT_ERC20_GOERLI",
                contract_address="0x509Ee0d083DdF8AC028f2a56731412edD63223B9",  # Goerli USDT
                decimals=6,
                confirmation_blocks=1,
                explorer_url="https://goerli.etherscan.io",
                rpc_url_env="ETHEREUM_GOERLI_RPC_URL",
                is_testnet=True
            ),
            NetworkType.BSC: NetworkConfig(
                network_type=NetworkType.BSC,
                network_name="bsc",
                display_name="Binance Smart Chain (BEP-20)",
                currency_code="USDT_BEP20",
                contract_address="0x55d398326f99059fF775485246999027B3197955",  # BSC Mainnet
                decimals=18,  # BSC USDT uses 18 decimals
                confirmation_blocks=3,
                explorer_url="https://bscscan.com",
                rpc_url_env="BSC_RPC_URL",
                is_testnet=False
            ),
            NetworkType.BSC_TESTNET: NetworkConfig(
                network_type=NetworkType.BSC_TESTNET,
                network_name="bsc_testnet",
                display_name="BSC Testnet (BEP-20)",
                currency_code="USDT_BEP20_TESTNET",
                contract_address="0x337610d27c682E347C9cD60BD4b3b107C9d34dDd",  # BSC Testnet USDT
                decimals=18,
                confirmation_blocks=1,
                explorer_url="https://testnet.bscscan.com",
                rpc_url_env="BSC_TESTNET_RPC_URL",
                is_testnet=True
            ),
            NetworkType.TRON: NetworkConfig(
                network_type=NetworkType.TRON,
                network_name="tron",
                display_name="Tron Network (TRC-20)",
                currency_code="USDT_TRC20",
                contract_address="TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",  # Tron Mainnet
                decimals=6,
                confirmation_blocks=19,  # Tron confirmation requirement
                explorer_url="https://tronscan.org",
                rpc_url_env="TRON_RPC_URL",
                is_testnet=False
            ),
            NetworkType.TRON_SHASTA: NetworkConfig(
                network_type=NetworkType.TRON_SHASTA,
                network_name="tron_shasta",
                display_name="Tron Shasta Testnet (TRC-20)",
                currency_code="USDT_TRC20_SHASTA",
                contract_address="TG3XXyExBkPp9nzdajDZsozEu4BkaSJozs",  # Shasta Testnet USDT
                decimals=6,
                confirmation_blocks=1,
                explorer_url="https://shasta.tronscan.org",
                rpc_url_env="TRON_SHASTA_RPC_URL",
                is_testnet=True
            )
        }
    ),
    "USDC": MultiNetworkToken(
        base_symbol="USDC",
        display_name="USD Coin",
        networks={
            NetworkType.ETHEREUM: NetworkConfig(
                network_type=NetworkType.ETHEREUM,
                network_name="ethereum",
                display_name="Ethereum (ERC-20)",
                currency_code="USDC_ERC20",
                contract_address="0xA0b86a33E6441b8e7b3c4e6b5b8e9b8e8e8e8e8e",  # Example
                decimals=6,
                confirmation_blocks=3,
                explorer_url="https://etherscan.io",
                rpc_url_env="ETHEREUM_RPC_URL"
            ),
            NetworkType.BSC: NetworkConfig(
                network_type=NetworkType.BSC,
                network_name="bsc",
                display_name="Binance Smart Chain (BEP-20)",
                currency_code="USDC_BEP20",
                contract_address="0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d",  # BSC USDC
                decimals=18,
                confirmation_blocks=3,
                explorer_url="https://bscscan.com",
                rpc_url_env="BSC_RPC_URL"
            )
        }
    ),
    "ETH": MultiNetworkToken(
        base_symbol="ETH",
        display_name="Ethereum",
        networks={
            NetworkType.ETHEREUM: NetworkConfig(
                network_type=NetworkType.ETHEREUM,
                network_name="ethereum",
                display_name="Ethereum Mainnet",
                currency_code="ETH",
                contract_address=None,  # Native token
                decimals=18,
                confirmation_blocks=12,
                explorer_url="https://etherscan.io",
                rpc_url_env="ETHEREUM_RPC_URL",
                is_testnet=False
            ),
            NetworkType.ETHEREUM_SEPOLIA: NetworkConfig(
                network_type=NetworkType.ETHEREUM_SEPOLIA,
                network_name="ethereum_sepolia",
                display_name="Ethereum Sepolia",
                currency_code="ETH_SEPOLIA",
                contract_address=None,  # Native token
                decimals=18,
                confirmation_blocks=1,
                explorer_url="https://sepolia.etherscan.io",
                rpc_url_env="ETHEREUM_SEPOLIA_RPC_URL",
                is_testnet=True
            ),
            NetworkType.BASE: NetworkConfig(
                network_type=NetworkType.BASE,
                network_name="base",
                display_name="Base",
                currency_code="ETH_BASE",
                contract_address=None,  # Native token
                decimals=18,
                confirmation_blocks=3,
                explorer_url="https://basescan.org",
                rpc_url_env="BASE_RPC_URL",
                is_testnet=False
            ),
            NetworkType.BASE_SEPOLIA: NetworkConfig(
                network_type=NetworkType.BASE_SEPOLIA,
                network_name="base_sepolia",
                display_name="Base Sepolia",
                currency_code="ETH_BASE_SEPOLIA",
                contract_address=None,  # Native token
                decimals=18,
                confirmation_blocks=1,
                explorer_url="https://sepolia.basescan.org",
                rpc_url_env="BASE_SEPOLIA_RPC_URL",
                is_testnet=True
            ),
            NetworkType.ARBITRUM: NetworkConfig(
                network_type=NetworkType.ARBITRUM,
                network_name="arbitrum",
                display_name="Arbitrum One",
                currency_code="ETH_ARBITRUM",
                contract_address=None,  # Native token
                decimals=18,
                confirmation_blocks=1,
                explorer_url="https://arbiscan.io",
                rpc_url_env="ARBITRUM_RPC_URL",
                is_testnet=False
            ),
            NetworkType.ARBITRUM_SEPOLIA: NetworkConfig(
                network_type=NetworkType.ARBITRUM_SEPOLIA,
                network_name="arbitrum_sepolia",
                display_name="Arbitrum Sepolia",
                currency_code="ETH_ARBITRUM_SEPOLIA",
                contract_address=None,  # Native token
                decimals=18,
                confirmation_blocks=1,
                explorer_url="https://sepolia.arbiscan.io",
                rpc_url_env="ARBITRUM_SEPOLIA_RPC_URL",
                is_testnet=True
            ),
            NetworkType.OPTIMISM: NetworkConfig(
                network_type=NetworkType.OPTIMISM,
                network_name="optimism",
                display_name="Optimism",
                currency_code="ETH_OPTIMISM",
                contract_address=None,  # Native token
                decimals=18,
                confirmation_blocks=1,
                explorer_url="https://optimistic.etherscan.io",
                rpc_url_env="OPTIMISM_RPC_URL",
                is_testnet=False
            ),
            NetworkType.OPTIMISM_SEPOLIA: NetworkConfig(
                network_type=NetworkType.OPTIMISM_SEPOLIA,
                network_name="optimism_sepolia",
                display_name="Optimism Sepolia",
                currency_code="ETH_OPTIMISM_SEPOLIA",
                contract_address=None,  # Native token
                decimals=18,
                confirmation_blocks=1,
                explorer_url="https://sepolia-optimism.etherscan.io",
                rpc_url_env="OPTIMISM_SEPOLIA_RPC_URL",
                is_testnet=True
            ),
            NetworkType.BSC: NetworkConfig(
                network_type=NetworkType.BSC,
                network_name="bsc",
                display_name="BNB Smart Chain (BEP-20)",
                currency_code="ETH_BEP20",
                contract_address="0x2170Ed0880ac9A755fd29B2688956BD959F933F8",  # ETH on BSC
                decimals=18,
                confirmation_blocks=3,
                explorer_url="https://bscscan.com",
                rpc_url_env="BSC_RPC_URL",
                is_testnet=False
            ),
            NetworkType.BSC_TESTNET: NetworkConfig(
                network_type=NetworkType.BSC_TESTNET,
                network_name="bsc_testnet",
                display_name="BSC Testnet (BEP-20)",
                currency_code="ETH_BEP20_TESTNET",
                contract_address="0x8BaBbB98678facC7342735486C851ABD7A0d17Ca",  # ETH on BSC Testnet
                decimals=18,
                confirmation_blocks=1,
                explorer_url="https://testnet.bscscan.com",
                rpc_url_env="BSC_TESTNET_RPC_URL",
                is_testnet=True
            )
        }
    ),
    "BNB": MultiNetworkToken(
        base_symbol="BNB",
        display_name="BNB",
        networks={
            NetworkType.BSC: NetworkConfig(
                network_type=NetworkType.BSC,
                network_name="bsc",
                display_name="BNB Smart Chain (Native)",
                currency_code="BNB",
                contract_address=None,  # Native token
                decimals=18,
                confirmation_blocks=3,
                explorer_url="https://bscscan.com",
                rpc_url_env="BSC_RPC_URL",
                is_testnet=False
            ),
            NetworkType.BSC_TESTNET: NetworkConfig(
                network_type=NetworkType.BSC_TESTNET,
                network_name="bsc_testnet",
                display_name="BSC Testnet (Native)",
                currency_code="BNB_TESTNET",
                contract_address=None,  # Native token
                decimals=18,
                confirmation_blocks=1,
                explorer_url="https://testnet.bscscan.com",
                rpc_url_env="BSC_TESTNET_RPC_URL",
                is_testnet=True
            )
        }
    ),
    "BTC": MultiNetworkToken(
        base_symbol="BTC",
        display_name="Bitcoin",
        networks={
            NetworkType.BITCOIN: NetworkConfig(
                network_type=NetworkType.BITCOIN,
                network_name="bitcoin",
                display_name="Bitcoin (Native)",
                currency_code="BTC",
                contract_address=None,  # Native token
                decimals=8,
                confirmation_blocks=3,
                explorer_url="https://blockstream.info",
                rpc_url_env="BITCOIN_RPC_URL",
                is_testnet=False
            ),
            NetworkType.BITCOIN_TESTNET: NetworkConfig(
                network_type=NetworkType.BITCOIN_TESTNET,
                network_name="bitcoin_testnet",
                display_name="Bitcoin Testnet",
                currency_code="BTC_TESTNET",
                contract_address=None,  # Native token
                decimals=8,
                confirmation_blocks=1,
                explorer_url="https://blockstream.info/testnet",
                rpc_url_env="BITCOIN_TESTNET_RPC_URL",
                is_testnet=True
            )
        }
    ),
    "LTC": MultiNetworkToken(
        base_symbol="LTC",
        display_name="Litecoin",
        networks={
            NetworkType.LITECOIN: NetworkConfig(
                network_type=NetworkType.LITECOIN,
                network_name="litecoin",
                display_name="Litecoin (Native)",
                currency_code="LTC",
                contract_address=None,  # Native token
                decimals=8,
                confirmation_blocks=6,
                explorer_url="https://blockchair.com/litecoin",
                rpc_url_env="LITECOIN_RPC_URL",
                is_testnet=False
            ),
            NetworkType.LITECOIN_TESTNET: NetworkConfig(
                network_type=NetworkType.LITECOIN_TESTNET,
                network_name="litecoin_testnet",
                display_name="Litecoin Testnet",
                currency_code="LTC_TESTNET",
                contract_address=None,  # Native token
                decimals=8,
                confirmation_blocks=1,
                explorer_url="https://blockchair.com/litecoin/testnet",
                rpc_url_env="LITECOIN_TESTNET_RPC_URL",
                is_testnet=True
            )
        }
    ),
    "XRP": MultiNetworkToken(
        base_symbol="XRP",
        display_name="XRP (Ripple)",
        networks={
            NetworkType.XRP: NetworkConfig(
                network_type=NetworkType.XRP,
                network_name="xrp",
                display_name="XRP Mainnet",
                currency_code="XRP",
                contract_address=None,  # Native token
                decimals=6,
                confirmation_blocks=1,
                explorer_url="https://xrpscan.com",
                rpc_url_env="XRP_RPC_URL",
                is_testnet=False
            ),
            NetworkType.XRP_TESTNET: NetworkConfig(
                network_type=NetworkType.XRP_TESTNET,
                network_name="xrp_testnet",
                display_name="XRP Testnet",
                currency_code="XRP_TESTNET",
                contract_address=None,  # Native token
                decimals=6,
                confirmation_blocks=1,
                explorer_url="https://testnet.xrpl.org",
                rpc_url_env="XRP_TESTNET_RPC_URL",
                is_testnet=True
            )
        }
    ),
    "SOL": MultiNetworkToken(
        base_symbol="SOL",
        display_name="Solana",
        networks={
            NetworkType.SOLANA: NetworkConfig(
                network_type=NetworkType.SOLANA,
                network_name="solana",
                display_name="Solana Mainnet",
                currency_code="SOL",
                contract_address=None,  # Native token
                decimals=9,
                confirmation_blocks=32,
                explorer_url="https://explorer.solana.com",
                rpc_url_env="SOLANA_RPC_URL",
                is_testnet=False
            ),
            NetworkType.SOLANA_DEVNET: NetworkConfig(
                network_type=NetworkType.SOLANA_DEVNET,
                network_name="solana_devnet",
                display_name="Solana Devnet",
                currency_code="SOL_DEVNET",
                contract_address=None,  # Native token
                decimals=9,
                confirmation_blocks=1,
                explorer_url="https://explorer.solana.com?cluster=devnet",
                rpc_url_env="SOLANA_DEVNET_RPC_URL",
                is_testnet=True
            ),
            NetworkType.SOLANA_TESTNET: NetworkConfig(
                network_type=NetworkType.SOLANA_TESTNET,
                network_name="solana_testnet",
                display_name="Solana Testnet",
                currency_code="SOL_TESTNET",
                contract_address=None,  # Native token
                decimals=9,
                confirmation_blocks=1,
                explorer_url="https://explorer.solana.com?cluster=testnet",
                rpc_url_env="SOLANA_TESTNET_RPC_URL",
                is_testnet=True
            )
        }
    ),
    "TRX": MultiNetworkToken(
        base_symbol="TRX",
        display_name="Tron",
        networks={
            NetworkType.TRON: NetworkConfig(
                network_type=NetworkType.TRON,
                network_name="tron",
                display_name="Tron Mainnet",
                currency_code="TRX",
                contract_address=None,  # Native token
                decimals=6,
                confirmation_blocks=19,
                explorer_url="https://tronscan.org",
                rpc_url_env="TRON_RPC_URL",
                is_testnet=False
            ),
            NetworkType.TRON_SHASTA: NetworkConfig(
                network_type=NetworkType.TRON_SHASTA,
                network_name="tron_shasta",
                display_name="Tron Shasta Testnet",
                currency_code="TRX_TESTNET",
                contract_address=None,  # Native token
                decimals=6,
                confirmation_blocks=19,
                explorer_url="https://shasta.tronscan.org",
                rpc_url_env="TRON_SHASTA_RPC_URL",
                is_testnet=True
            )
        }
    )
}

def get_network_config(token_symbol: str, network_type) -> Optional[NetworkConfig]:
    """Get network configuration for a specific token and network"""
    token_config = MULTI_NETWORK_TOKENS.get(token_symbol)
    if not token_config:
        return None
    
    # Handle string input by converting to NetworkType enum
    if isinstance(network_type, str):
        try:
            network_type = NetworkType(network_type)
        except ValueError:
            return None
    
    return token_config.networks.get(network_type)

def get_available_networks(token_symbol: str) -> List[Dict]:
    """Get all available networks for a token"""
    token_config = MULTI_NETWORK_TOKENS.get(token_symbol)
    if not token_config:
        return []
    return token_config.get_network_options()

def is_multi_network_token(token_symbol: str) -> bool:
    """Check if a token is available on multiple networks"""
    return token_symbol in MULTI_NETWORK_TOKENS

def get_currency_code_from_network(token_symbol: str, network_type: NetworkType) -> Optional[str]:
    """Get the specific currency code for a token on a network"""
    config = get_network_config(token_symbol, network_type)
    return config.currency_code if config else None

def get_available_networks_filtered(token_symbol: str, include_testnets: bool = False) -> List[Dict]:
    """Get available networks for a token based on admin_currencies table configuration"""
    try:
        from db.currency import Currency, CurrencyNetwork
        from db.connection import get_session
        
        session = get_session()
        
        # Get currency from admin_currencies table
        currency = session.query(Currency).filter_by(
            symbol=token_symbol,
            is_enabled=True
        ).first()
        
        if not currency:
            return []
        
        # Get enabled networks for this currency
        enabled_networks = session.query(CurrencyNetwork).filter_by(
            currency_id=currency.id,
            is_enabled=True
        ).all()
        
        session.close()
        
        filtered_networks = []
        for network in enabled_networks:
            # Filter based on testnet preference
            if not include_testnets and network.is_testnet:
                continue
            
            # Add network to filtered list
            filtered_networks.append({
                "network_type": network.network_type,
                "network_name": network.network_name,
                "display_name": network.display_name,
                "currency_code": f"{token_symbol}_{network.network_type.upper()}" if network.is_testnet else token_symbol,
                "confirmation_blocks": network.confirmation_blocks,
                "explorer_url": network.explorer_url,
                "is_testnet": network.is_testnet
            })
        
        return filtered_networks
        
    except Exception as e:
        # Fallback to original logic if database query fails
        import os
        
        token_config = MULTI_NETWORK_TOKENS.get(token_symbol)
        if not token_config:
            return []
        
        # Check network environment variables (fallback)
        trx_network = os.getenv('TRX_NETWORK', 'mainnet').lower()
        eth_network = os.getenv('ETH_NETWORK', 'mainnet').lower()
        btc_network = os.getenv('BTC_NETWORK', 'testnet').lower()
        ltc_network = os.getenv('LTC_NETWORK', 'testnet').lower()
        bnb_network = os.getenv('BNB_NETWORK', 'mainnet').lower()
        base_network = os.getenv('BASE_NETWORK', 'mainnet').lower()
        sol_network = os.getenv('SOL_NETWORK', 'devnet').lower()
        
        filtered_networks = []
        for config in token_config.networks.values():
            # Filter based on testnet preference
            if not include_testnets and config.is_testnet:
                continue
                
            # Apply environment variable filtering for fallback
            if config.network_type in [NetworkType.TRON, NetworkType.TRON_SHASTA]:
                if trx_network == 'testnet' and config.network_type == NetworkType.TRON:
                    continue
                elif trx_network == 'mainnet' and config.network_type == NetworkType.TRON_SHASTA:
                    continue
            
            if config.network_type in [NetworkType.BITCOIN, NetworkType.BITCOIN_TESTNET]:
                if btc_network == 'testnet' and config.network_type == NetworkType.BITCOIN:
                    continue
                elif btc_network == 'mainnet' and config.network_type == NetworkType.BITCOIN_TESTNET:
                    continue
            
            if config.network_type in [NetworkType.LITECOIN, NetworkType.LITECOIN_TESTNET]:
                if ltc_network == 'testnet' and config.network_type == NetworkType.LITECOIN:
                    continue
                elif ltc_network == 'mainnet' and config.network_type == NetworkType.LITECOIN_TESTNET:
                    continue
            
            if config.network_type in [NetworkType.BSC, NetworkType.BSC_TESTNET]:
                if bnb_network == 'testnet' and config.network_type == NetworkType.BSC:
                    continue
                elif bnb_network == 'mainnet' and config.network_type == NetworkType.BSC_TESTNET:
                    continue
            
            if config.network_type in [NetworkType.SOLANA, NetworkType.SOLANA_DEVNET, NetworkType.SOLANA_TESTNET]:
                if sol_network == 'devnet' and config.network_type in [NetworkType.SOLANA, NetworkType.SOLANA_TESTNET]:
                    continue
                elif sol_network == 'testnet' and config.network_type in [NetworkType.SOLANA, NetworkType.SOLANA_DEVNET]:
                    continue
                elif sol_network == 'mainnet' and config.network_type in [NetworkType.SOLANA_DEVNET, NetworkType.SOLANA_TESTNET]:
                    continue
            
            # Add to filtered networks
            filtered_networks.append({
                "network_type": config.network_type.value,
                "network_name": config.network_name,
                "display_name": config.display_name,
                "currency_code": config.currency_code,
                "confirmation_blocks": config.confirmation_blocks,
                "explorer_url": config.explorer_url,
                "is_testnet": config.is_testnet
            })
        
        return filtered_networks

def get_mainnet_networks(token_symbol: str) -> List[Dict]:
    """Get only mainnet networks for a token"""
    return get_available_networks_filtered(token_symbol, include_testnets=False)

def get_testnet_networks(token_symbol: str) -> List[Dict]:
    """Get only testnet networks for a token"""
    token_config = MULTI_NETWORK_TOKENS.get(token_symbol)
    if not token_config:
        return []
    
    testnet_networks = []
    for config in token_config.networks.values():
        if config.is_testnet:
            testnet_networks.append({
                "network_type": config.network_type.value,
                "network_name": config.network_name,
                "display_name": config.display_name,
                "currency_code": config.currency_code,
                "confirmation_blocks": config.confirmation_blocks,
                "explorer_url": config.explorer_url,
                "is_testnet": config.is_testnet
            })
    
    return testnet_networks
