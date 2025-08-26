#!/usr/bin/env python3
"""
Seed script to populate currency management tables with sample data
"""
import sys
import os
sys.path.append('/app')

from db.connection import session
from db.currency import Currency, CurrencyNetwork
import uuid

def seed_currencies():
    try:
        # Clear existing data
        session.query(CurrencyNetwork).delete()
        session.query(Currency).delete()
        
        # Bitcoin - Multi-network
        btc_id = str(uuid.uuid4())
        btc = Currency(
            id=btc_id,
            symbol='BTC',
            name='Bitcoin',
            is_enabled=True,
            is_multi_network=True,
            decimals=8
        )
        session.add(btc)
        
        # Bitcoin networks
        btc_mainnet = CurrencyNetwork(
            currency_id=btc_id,
            network_type='bitcoin',
            network_name='Bitcoin',
            display_name='Bitcoin Mainnet',
            is_enabled=True,
            confirmation_blocks=6,
            explorer_url='https://blockstream.info',
            is_testnet=False
        )
        session.add(btc_mainnet)
        
        btc_testnet = CurrencyNetwork(
            currency_id=btc_id,
            network_type='bitcoin_testnet',
            network_name='Bitcoin Testnet',
            display_name='Bitcoin Testnet',
            is_enabled=True,
            confirmation_blocks=6,
            explorer_url='https://blockstream.info/testnet',
            is_testnet=True
        )
        session.add(btc_testnet)
        
        # Ethereum - Multi-network
        eth_id = str(uuid.uuid4())
        eth = Currency(
            id=eth_id,
            symbol='ETH',
            name='Ethereum',
            is_enabled=True,
            is_multi_network=True,
            decimals=18
        )
        session.add(eth)
        
        # Ethereum networks
        eth_mainnet = CurrencyNetwork(
            currency_id=eth_id,
            network_type='ethereum',
            network_name='Ethereum',
            display_name='Ethereum Mainnet',
            is_enabled=True,
            confirmation_blocks=12,
            explorer_url='https://etherscan.io',
            is_testnet=False
        )
        session.add(eth_mainnet)
        
        eth_sepolia = CurrencyNetwork(
            currency_id=eth_id,
            network_type='ethereum_sepolia',
            network_name='Ethereum Sepolia',
            display_name='Ethereum Sepolia',
            is_enabled=True,
            confirmation_blocks=12,
            explorer_url='https://sepolia.etherscan.io',
            is_testnet=True
        )
        session.add(eth_sepolia)
        
        # BNB - Multi-network
        bnb_id = str(uuid.uuid4())
        bnb = Currency(
            id=bnb_id,
            symbol='BNB',
            name='BNB',
            is_enabled=True,
            is_multi_network=True,
            decimals=18
        )
        session.add(bnb)
        
        # BNB networks
        bsc_mainnet = CurrencyNetwork(
            currency_id=bnb_id,
            network_type='bsc',
            network_name='BSC',
            display_name='BNB Smart Chain',
            is_enabled=True,
            confirmation_blocks=15,
            explorer_url='https://bscscan.com',
            is_testnet=False
        )
        session.add(bsc_mainnet)
        
        bsc_testnet = CurrencyNetwork(
            currency_id=bnb_id,
            network_type='bsc_testnet',
            network_name='BSC Testnet',
            display_name='BNB Smart Chain Testnet',
            is_enabled=True,
            confirmation_blocks=15,
            explorer_url='https://testnet.bscscan.com',
            is_testnet=True
        )
        session.add(bsc_testnet)
        
        # Base - Multi-network
        base_id = str(uuid.uuid4())
        base = Currency(
            id=base_id,
            symbol='BASE',
            name='Base',
            is_enabled=True,
            is_multi_network=True,
            decimals=18
        )
        session.add(base)
        
        # Base networks
        base_mainnet = CurrencyNetwork(
            currency_id=base_id,
            network_type='base',
            network_name='Base',
            display_name='Base Mainnet',
            is_enabled=True,
            confirmation_blocks=12,
            explorer_url='https://basescan.org',
            is_testnet=False
        )
        session.add(base_mainnet)
        
        base_sepolia = CurrencyNetwork(
            currency_id=base_id,
            network_type='base_sepolia',
            network_name='Base Sepolia',
            display_name='Base Sepolia',
            is_enabled=True,
            confirmation_blocks=12,
            explorer_url='https://sepolia.basescan.org',
            is_testnet=True
        )
        session.add(base_sepolia)
        
        # USDT - Multi-network token
        usdt_id = str(uuid.uuid4())
        usdt = Currency(
            id=usdt_id,
            symbol='USDT',
            name='Tether USD',
            is_enabled=True,
            is_multi_network=True,
            decimals=6
        )
        session.add(usdt)
        
        # USDT on Ethereum
        usdt_eth = CurrencyNetwork(
            currency_id=usdt_id,
            network_type='ethereum',
            network_name='Ethereum',
            display_name='Ethereum Mainnet',
            is_enabled=True,
            contract_address='0xdAC17F958D2ee523a2206206994597C13D831ec7',
            confirmation_blocks=12,
            explorer_url='https://etherscan.io',
            is_testnet=False
        )
        session.add(usdt_eth)
        
        # USDT on BSC
        usdt_bsc = CurrencyNetwork(
            currency_id=usdt_id,
            network_type='bsc',
            network_name='BSC',
            display_name='BNB Smart Chain',
            is_enabled=True,
            contract_address='0x55d398326f99059fF775485246999027B3197955',
            confirmation_blocks=15,
            explorer_url='https://bscscan.com',
            is_testnet=False
        )
        session.add(usdt_bsc)
        
        # Solana - Multi-network
        sol_id = str(uuid.uuid4())
        sol = Currency(
            id=sol_id,
            symbol='SOL',
            name='Solana',
            is_enabled=True,
            is_multi_network=True,
            decimals=9
        )
        session.add(sol)
        
        # Solana networks
        sol_mainnet = CurrencyNetwork(
            currency_id=sol_id,
            network_type='solana',
            network_name='Solana',
            display_name='Solana Mainnet',
            is_enabled=True,
            confirmation_blocks=1,
            explorer_url='https://explorer.solana.com',
            is_testnet=False
        )
        session.add(sol_mainnet)
        
        sol_devnet = CurrencyNetwork(
            currency_id=sol_id,
            network_type='solana_devnet',
            network_name='Solana Devnet',
            display_name='Solana Devnet',
            is_enabled=True,
            confirmation_blocks=1,
            explorer_url='https://explorer.solana.com/?cluster=devnet',
            is_testnet=True
        )
        session.add(sol_devnet)
        
        sol_testnet = CurrencyNetwork(
            currency_id=sol_id,
            network_type='solana_testnet',
            network_name='Solana Testnet',
            display_name='Solana Testnet',
            is_enabled=False,  # Disabled by default, can be enabled via admin
            confirmation_blocks=1,
            explorer_url='https://explorer.solana.com/?cluster=testnet',
            is_testnet=True
        )
        session.add(sol_testnet)
        
        # Tron - Multi-network
        trx_id = str(uuid.uuid4())
        trx = Currency(
            id=trx_id,
            symbol='TRX',
            name='Tron',
            is_enabled=True,
            is_multi_network=True,
            decimals=6
        )
        session.add(trx)
        
        # Tron networks
        trx_mainnet = CurrencyNetwork(
            currency_id=trx_id,
            network_type='tron',
            network_name='Tron',
            display_name='Tron Mainnet',
            is_enabled=True,
            confirmation_blocks=19,
            explorer_url='https://tronscan.org',
            is_testnet=False
        )
        session.add(trx_mainnet)
        
        trx_shasta = CurrencyNetwork(
            currency_id=trx_id,
            network_type='tron_shasta',
            network_name='Tron Shasta',
            display_name='Tron Shasta Testnet',
            is_enabled=True,
            confirmation_blocks=19,
            explorer_url='https://shasta.tronscan.org',
            is_testnet=True
        )
        session.add(trx_shasta)
        
        # XRP - Multi-network
        xrp_id = str(uuid.uuid4())
        xrp = Currency(
            id=xrp_id,
            symbol='XRP',
            name='XRP',
            is_enabled=True,
            is_multi_network=True,
            decimals=6
        )
        session.add(xrp)
        
        # XRP networks
        xrp_mainnet = CurrencyNetwork(
            currency_id=xrp_id,
            network_type='xrp',
            network_name='XRP Ledger',
            display_name='XRP Mainnet',
            is_enabled=True,
            confirmation_blocks=1,
            explorer_url='https://xrpscan.com',
            is_testnet=False
        )
        session.add(xrp_mainnet)
        
        xrp_testnet = CurrencyNetwork(
            currency_id=xrp_id,
            network_type='xrp_testnet',
            network_name='XRP Testnet',
            display_name='XRP Testnet',
            is_enabled=True,
            confirmation_blocks=1,
            explorer_url='https://testnet.xrpl.org',
            is_testnet=True
        )
        session.add(xrp_testnet)
        
        session.commit()
        print("✅ Successfully seeded currency data!")
        print(f"Created {session.query(Currency).count()} currencies")
        print(f"Created {session.query(CurrencyNetwork).count()} network configurations")
        
    except Exception as e:
        session.rollback()
        print(f"❌ Error seeding currencies: {e}")
        raise
    finally:
        session.close()

if __name__ == '__main__':
    seed_currencies()
