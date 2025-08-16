#!/usr/bin/env python3
"""
Script to create a master Ethereum account at index 0 for receiving faucet tokens.
This account will be used to receive test tokens before distributing them to other indices.
"""

import os
import sys
import logging
from datetime import datetime
from decouple import config

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from shared.crypto.clients.eth import ETHWallet, EthereumConfig
from shared.logger import setup_logging
from db.connection import get_db_session
from db.wallet import Account, AccountType, CryptoAddress
from sqlalchemy.orm import Session

logger = setup_logging()


class ETHMasterAccountCreator:
    """Creates a master Ethereum account at index 0 for faucet token reception"""
    
    def __init__(self, user_id: int = None, network: str = "testnet"):
        """
        Initialize the master account creator
        
        Args:
            user_id: User ID for the master account (defaults to 0 for master account)
            network: Ethereum network to use (testnet, mainnet, holesky)
        """
        self.user_id = user_id or 0  # Use 0 for master account
        self.network = network
        self.session = get_db_session()
        self.logger = logger
        
        # Configure Ethereum client
        self._setup_eth_client()
    
    def _setup_eth_client(self):
        """Setup the Ethereum client with appropriate configuration"""
        api_key = config('ALCHEMY_API_KEY', default='')
        if not api_key:
            raise ValueError("ALCHEMY_API_KEY environment variable is required")
        
        # Create Ethereum config based on network
        if self.network == "testnet":
            self.eth_config = EthereumConfig.testnet(api_key)
        elif self.network == "mainnet":
            self.eth_config = EthereumConfig.mainnet(api_key)
        elif self.network == "holesky":
            self.eth_config = EthereumConfig.holesky(api_key)
        else:
            raise ValueError(f"Unsupported network: {self.network}")
        
        # Create ETH wallet instance
        self.eth_wallet = ETHWallet(
            user_id=self.user_id,
            config=self.eth_config,
            session=self.session,
            logger=self.logger
        )
        
        self.logger.info(f"🔧 Initialized ETH client for {self.network} network")
    
    def create_master_account(self, force: bool = False) -> dict:
        """
        Create a master Ethereum account at index 0
        
        Args:
            force: If True, recreate the account even if it exists
            
        Returns:
            dict: Account information including address and account details
        """
        try:
            self.logger.info(f"🚀 Creating master ETH account for user {self.user_id} on {self.network}")
            
            # Check if master account already exists
            existing_account = self.session.query(Account).filter_by(
                user_id=self.user_id,
                currency="ETH",
                account_type=AccountType.CRYPTO
            ).first()
            
            if existing_account and not force:
                self.logger.warning(f"⚠️  Master ETH account already exists for user {self.user_id}")
                return self._get_account_info(existing_account)
            
            # Create the master account
            self.eth_wallet.create_wallet()
            self.session.flush()  # Get the ID without committing
            
            # Set account_id to 0 for master account
            self.eth_wallet.account_id = 0
            
            # Create address at index 0 (master address for faucet)
            self.eth_wallet.create_address(notify=False)  # Don't notify for master account
            
            # Get the created account
            master_account = self.session.query(Account).filter_by(
                user_id=self.user_id,
                currency="ETH",
                account_type=AccountType.CRYPTO
            ).first()
            
            if not master_account:
                raise Exception("Failed to create master ETH account")
            
            # Get the address
            master_address = self.session.query(CryptoAddress).filter_by(
                account_id=master_account.id
            ).first()
            
            if not master_address:
                raise Exception("Failed to create master ETH address")
            
            # Commit the transaction
            self.session.commit()
            
            account_info = self._get_account_info(master_account, master_address)
            
            self.logger.info(f"✅ Successfully created master ETH account")
            self.logger.info(f"📋 Account ID: {master_account.id}")
            self.logger.info(f"📍 Address: {master_address.address}")
            self.logger.info(f"🔗 Network: {self.network}")
            self.logger.info(f"👤 User ID: {self.user_id}")
            
            return account_info
            
        except Exception as e:
            self.session.rollback()
            self.logger.error(f"❌ Failed to create master ETH account: {e}")
            raise
    
    def _get_account_info(self, account: Account, address: CryptoAddress = None) -> dict:
        """Get account information in a structured format"""
        if not address:
            address = self.session.query(CryptoAddress).filter_by(
                account_id=account.id
            ).first()
        
        return {
            "account_id": account.id,
            "user_id": account.user_id,
            "currency": account.currency,
            "account_type": account.account_type.value,
            "account_number": account.account_number,
            "balance": float(account.balance) if account.balance else 0.0,
            "address": address.address if address else None,
            "address_type": address.address_type if address else None,
            "is_active": address.is_active if address else None,
            "created_at": account.created_at.isoformat() if account.created_at else None,
            "network": self.network
        }
    
    def get_master_account_info(self) -> dict:
        """Get information about the existing master account"""
        master_account = self.session.query(Account).filter_by(
            user_id=self.user_id,
            currency="ETH",
            account_type=AccountType.CRYPTO
        ).first()
        
        if not master_account:
            raise Exception(f"No master ETH account found for user {self.user_id}")
        
        return self._get_account_info(master_account)
    
    def list_all_eth_accounts(self) -> list:
        """List all ETH accounts for the user"""
        accounts = self.session.query(Account).filter_by(
            user_id=self.user_id,
            currency="ETH",
            account_type=AccountType.CRYPTO
        ).all()
        
        return [self._get_account_info(account) for account in accounts]
    
    def test_connection(self) -> bool:
        """Test the connection to the Ethereum network"""
        try:
            is_connected = self.eth_wallet.test_connection()
            if is_connected:
                self.logger.info(f"✅ Successfully connected to {self.network}")
            else:
                self.logger.error(f"❌ Failed to connect to {self.network}")
            return is_connected
        except Exception as e:
            self.logger.error(f"❌ Connection test failed: {e}")
            return False
    
    def get_network_info(self) -> dict:
        """Get information about the current network"""
        try:
            network_info = self.eth_wallet.get_network_info()
            self.logger.info(f"🌐 Network info: {network_info}")
            return network_info
        except Exception as e:
            self.logger.error(f"❌ Failed to get network info: {e}")
            return {}
    
    def cleanup(self):
        """Clean up resources"""
        if self.session:
            self.session.close()


def main():
    """Main function to create master ETH account"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Create master Ethereum account for faucet tokens")
    parser.add_argument("--user-id", type=int, default=0, help="User ID for master account (default: 0)")
    parser.add_argument("--network", choices=["testnet", "mainnet", "holesky"], default="testnet", 
                       help="Ethereum network to use (default: testnet)")
    parser.add_argument("--force", action="store_true", help="Force recreation of existing account")
    parser.add_argument("--test-connection", action="store_true", help="Test network connection only")
    parser.add_argument("--list-accounts", action="store_true", help="List all ETH accounts for user")
    parser.add_argument("--info", action="store_true", help="Get master account information")
    
    args = parser.parse_args()
    
    creator = None
    try:
        creator = ETHMasterAccountCreator(user_id=args.user_id, network=args.network)
        
        if args.test_connection:
            # Test connection only
            success = creator.test_connection()
            if success:
                creator.get_network_info()
            sys.exit(0 if success else 1)
        
        if args.list_accounts:
            # List all accounts
            accounts = creator.list_all_eth_accounts()
            print(f"\n📋 ETH Accounts for User {args.user_id}:")
            for account in accounts:
                print(f"  Account ID: {account['account_id']}")
                print(f"  Address: {account['address']}")
                print(f"  Balance: {account['balance']} ETH")
                print(f"  Network: {account['network']}")
                print("  ---")
            sys.exit(0)
        
        if args.info:
            # Get master account info
            try:
                info = creator.get_master_account_info()
                print(f"\n📋 Master ETH Account Information:")
                print(f"  Account ID: {info['account_id']}")
                print(f"  Address: {info['address']}")
                print(f"  Balance: {info['balance']} ETH")
                print(f"  Network: {info['network']}")
                print(f"  Created: {info['created_at']}")
            except Exception as e:
                print(f"❌ {e}")
                sys.exit(1)
            sys.exit(0)
        
        # Create master account
        print(f"🚀 Creating master ETH account for user {args.user_id} on {args.network}...")
        
        account_info = creator.create_master_account(force=args.force)
        
        print(f"\n✅ Master ETH Account Created Successfully!")
        print(f"📋 Account ID: {account_info['account_id']}")
        print(f"📍 Address: {account_info['address']}")
        print(f"🌐 Network: {account_info['network']}")
        print(f"👤 User ID: {account_info['user_id']}")
        print(f"💰 Balance: {account_info['balance']} ETH")
        print(f"📅 Created: {account_info['created_at']}")
        
        print(f"\n💡 Use this address to receive faucet tokens for testing!")
        print(f"🔗 You can now distribute tokens from this master account to other indices.")
        
    except Exception as e:
        logger.error(f"❌ Failed to create master ETH account: {e}")
        print(f"❌ Error: {e}")
        sys.exit(1)
    finally:
        if creator:
            creator.cleanup()


if __name__ == "__main__":
    main() 