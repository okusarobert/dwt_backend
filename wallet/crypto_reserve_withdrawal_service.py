#!/usr/bin/env python3
"""
Crypto Reserve Withdrawal Service
Handles crypto withdrawals from index 0 reserve addresses
"""

import os
import sys
import logging
import traceback
from decimal import Decimal
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from sqlalchemy.orm import Session

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.async_connection import get_db_session
from db.wallet import Account, AccountType, CryptoAddress, Transaction, TransactionType, TransactionStatus
from shared.crypto.HD import BTC, ETH, TRX
from shared.crypto.clients.sol import SOLWallet, SolanaConfig
from shared.currency_precision import AmountConverter
from shared.logger import setup_logging

# Configure logging
logger = setup_logging(__name__)

@dataclass
class WithdrawalRequest:
    """Crypto withdrawal request"""
    user_id: int
    currency: str
    amount: Decimal
    to_address: str
    reference_id: str
    account_id: Optional[int] = None

@dataclass
class WithdrawalResult:
    """Result of a withdrawal operation"""
    success: bool
    tx_hash: Optional[str] = None
    error: Optional[str] = None
    fee_amount: Optional[Decimal] = None

class CryptoReserveWithdrawalService:
    """Service to handle crypto withdrawals from reserve addresses"""
    
    def __init__(self):
        self.session = get_db_session()
        self.reserve_addresses = {}
        self.network_fees = {
            'BTC': Decimal('0.0001'),  # 10,000 satoshis
            'ETH': Decimal('0.002'),   # ~$5 at current prices
            'SOL': Decimal('0.000005'), # 5,000 lamports
            'TRX': Decimal('1'),       # 1 TRX
        }
        self.setup_reserve_addresses()
    
    def setup_reserve_addresses(self):
        """Initialize reserve addresses and private keys for each currency"""
        try:
            # Get BTC reserve address and private key
            btc_wallet = BTC()
            btc_mnemonic = os.getenv('BTC_MNEMONIC')
            if btc_mnemonic:
                btc_wallet.from_mnemonic(mnemonic=btc_mnemonic)
                address, priv_key, pub_key = btc_wallet.new_address(index=0)
                self.reserve_addresses['BTC'] = {
                    'address': address,
                    'private_key': priv_key,
                    'network': 'testnet'
                }
                logger.info(f"✅ BTC reserve address configured: {address}")
            
            # Get ETH reserve address and private key
            eth_wallet = ETH()
            eth_mnemonic = os.getenv('ETH_MNEMONIC')
            if eth_mnemonic:
                eth_wallet.from_mnemonic(mnemonic=eth_mnemonic)
                address, priv_key, pub_key = eth_wallet.new_address(index=0)
                self.reserve_addresses['ETH'] = {
                    'address': address,
                    'private_key': priv_key,
                    'network': 'mainnet'
                }
                logger.info(f"✅ ETH reserve address configured: {address}")
            
            # Get TRX reserve address and private key
            trx_wallet = TRX()
            trx_mnemonic = os.getenv('TRX_MNEMONIC')
            if trx_mnemonic:
                trx_wallet.from_mnemonic(mnemonic=trx_mnemonic)
                address, priv_key, pub_key = trx_wallet.new_address(index=0)
                self.reserve_addresses['TRX'] = {
                    'address': address,
                    'private_key': priv_key,
                    'network': 'mainnet'
                }
                logger.info(f"✅ TRX reserve address configured: {address}")
            
            # Get SOL reserve address and private key
            try:
                from solders.keypair import Keypair
                import hashlib
                import base58
                
                base_seed = b'dwt_solana_wallet_seed_v1'
                user_bytes = (0).to_bytes(8, 'big')
                index_bytes = (0).to_bytes(4, 'big')
                combined_seed = base_seed + user_bytes + index_bytes
                seed_hash = hashlib.sha256(combined_seed).digest()
                
                keypair = Keypair.from_seed(seed_hash)
                private_key = base58.b58encode(bytes(keypair)).decode()
                
                self.reserve_addresses['SOL'] = {
                    'address': str(keypair.pubkey()),
                    'private_key': private_key,
                    'network': 'mainnet'
                }
                logger.info(f"✅ SOL reserve address configured: {str(keypair.pubkey())}")
                
            except ImportError:
                logger.warning("❌ Solana SDK not available for SOL reserve address")
            
        except Exception as e:
            logger.error(f"Error setting up reserve addresses: {e}")
            logger.error(traceback.format_exc())
    
    def process_withdrawal(self, withdrawal_request: WithdrawalRequest) -> WithdrawalResult:
        """Process a crypto withdrawal from reserve address"""
        try:
            logger.info(f"🏦 Processing withdrawal: {withdrawal_request.amount} {withdrawal_request.currency} to {withdrawal_request.to_address}")
            
            # Validate currency support
            if withdrawal_request.currency not in self.reserve_addresses:
                return WithdrawalResult(
                    success=False,
                    error=f"Currency {withdrawal_request.currency} not supported or reserve address not configured"
                )
            
            # Validate withdrawal amount
            if withdrawal_request.amount <= 0:
                return WithdrawalResult(
                    success=False,
                    error="Withdrawal amount must be greater than 0"
                )
            
            # Check if user has sufficient balance
            if not self.validate_user_balance(withdrawal_request):
                return WithdrawalResult(
                    success=False,
                    error="Insufficient balance for withdrawal"
                )
            
            # Validate destination address
            if not self.validate_address(withdrawal_request.to_address, withdrawal_request.currency):
                return WithdrawalResult(
                    success=False,
                    error=f"Invalid {withdrawal_request.currency} address: {withdrawal_request.to_address}"
                )
            
            # Calculate network fee
            network_fee = self.network_fees.get(withdrawal_request.currency, Decimal('0'))
            total_amount = withdrawal_request.amount + network_fee
            
            # Check reserve balance
            reserve_balance = self.get_reserve_balance(withdrawal_request.currency)
            if not reserve_balance or reserve_balance < total_amount:
                return WithdrawalResult(
                    success=False,
                    error=f"Insufficient reserve balance. Available: {reserve_balance}, Required: {total_amount}"
                )
            
            # Execute withdrawal transaction
            result = self.execute_withdrawal(withdrawal_request, network_fee)
            
            if result.success:
                # Record withdrawal transaction
                self.record_withdrawal_transaction(withdrawal_request, result)
                logger.info(f"✅ Withdrawal successful: {result.tx_hash}")
            else:
                logger.error(f"❌ Withdrawal failed: {result.error}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing withdrawal: {e}")
            logger.error(traceback.format_exc())
            return WithdrawalResult(
                success=False,
                error=f"Internal error: {str(e)}"
            )
    
    def validate_user_balance(self, withdrawal_request: WithdrawalRequest) -> bool:
        """Validate that user has sufficient balance for withdrawal"""
        try:
            # Get user's crypto account
            account = self.session.query(Account).filter_by(
                user_id=withdrawal_request.user_id,
                currency=withdrawal_request.currency,
                account_type=AccountType.CRYPTO
            ).first()
            
            if not account:
                logger.warning(f"No {withdrawal_request.currency} account found for user {withdrawal_request.user_id}")
                return False
            
            # Check account balance (using unified balance system)
            if hasattr(account, 'crypto_balance_smallest_unit') and account.crypto_balance_smallest_unit:
                balance = AmountConverter.from_smallest_units(
                    account.crypto_balance_smallest_unit, 
                    withdrawal_request.currency
                )
            else:
                # Fallback to legacy balance field
                balance = getattr(account, 'balance', Decimal('0'))
            
            logger.info(f"User {withdrawal_request.user_id} {withdrawal_request.currency} balance: {balance}")
            
            return balance >= withdrawal_request.amount
            
        except Exception as e:
            logger.error(f"Error validating user balance: {e}")
            return False
    
    def validate_address(self, address: str, currency: str) -> bool:
        """Validate cryptocurrency address format"""
        try:
            if currency == 'BTC':
                # Basic BTC address validation
                return len(address) >= 26 and len(address) <= 35 and (
                    address.startswith('1') or address.startswith('3') or 
                    address.startswith('bc1') or address.startswith('m') or address.startswith('2')
                )
            elif currency == 'ETH':
                # Basic ETH address validation
                return len(address) == 42 and address.startswith('0x')
            elif currency == 'SOL':
                # Basic SOL address validation
                return len(address) >= 32 and len(address) <= 44
            elif currency == 'TRX':
                # Basic TRX address validation
                return len(address) == 34 and address.startswith('T')
            else:
                return False
                
        except Exception as e:
            logger.error(f"Error validating address {address} for {currency}: {e}")
            return False
    
    def get_reserve_balance(self, currency: str) -> Optional[Decimal]:
        """Get current balance of reserve address"""
        try:
            reserve_info = self.reserve_addresses.get(currency)
            if not reserve_info:
                return None
            
            address = reserve_info['address']
            
            if currency == 'BTC':
                return self.get_btc_balance(address)
            elif currency == 'ETH':
                return self.get_eth_balance(address)
            elif currency == 'SOL':
                return self.get_sol_balance(address)
            elif currency == 'TRX':
                return self.get_trx_balance(address)
            else:
                return None
                
        except Exception as e:
            logger.error(f"Error getting reserve balance for {currency}: {e}")
            return None
    
    def get_btc_balance(self, address: str) -> Optional[Decimal]:
        """Get BTC balance for an address"""
        # TODO: Implement BTC balance checking via RPC
        logger.info(f"TODO: Implement BTC balance check for {address}")
        return Decimal('1.0')  # Mock balance for testing
    
    def get_eth_balance(self, address: str) -> Optional[Decimal]:
        """Get ETH balance for an address"""
        # TODO: Implement ETH balance checking via Web3
        logger.info(f"TODO: Implement ETH balance check for {address}")
        return Decimal('10.0')  # Mock balance for testing
    
    def get_sol_balance(self, address: str) -> Optional[Decimal]:
        """Get SOL balance for an address"""
        try:
            sol_config = SolanaConfig.mainnet(os.getenv('ALCHEMY_SOLANA_API_KEY', 'demo'))
            sol_wallet = SOLWallet(user_id=0, config=sol_config, session=self.session)
            
            balance_info = sol_wallet.get_balance(address)
            if balance_info:
                return Decimal(str(balance_info.get('sol_balance', 0)))
            return Decimal('0')
            
        except Exception as e:
            logger.error(f"Error getting SOL balance for {address}: {e}")
            return Decimal('100.0')  # Mock balance for testing
    
    def get_trx_balance(self, address: str) -> Optional[Decimal]:
        """Get TRX balance for an address"""
        # TODO: Implement TRX balance checking via Tron API
        logger.info(f"TODO: Implement TRX balance check for {address}")
        return Decimal('1000.0')  # Mock balance for testing
    
    def execute_withdrawal(self, withdrawal_request: WithdrawalRequest, network_fee: Decimal) -> WithdrawalResult:
        """Execute the actual withdrawal transaction"""
        try:
            currency = withdrawal_request.currency
            reserve_info = self.reserve_addresses[currency]
            
            if currency == 'BTC':
                return self.execute_btc_withdrawal(withdrawal_request, reserve_info, network_fee)
            elif currency == 'ETH':
                return self.execute_eth_withdrawal(withdrawal_request, reserve_info, network_fee)
            elif currency == 'SOL':
                return self.execute_sol_withdrawal(withdrawal_request, reserve_info, network_fee)
            elif currency == 'TRX':
                return self.execute_trx_withdrawal(withdrawal_request, reserve_info, network_fee)
            else:
                return WithdrawalResult(
                    success=False,
                    error=f"Withdrawal not implemented for {currency}"
                )
                
        except Exception as e:
            return WithdrawalResult(
                success=False,
                error=f"Error executing withdrawal: {str(e)}"
            )
    
    def execute_btc_withdrawal(self, withdrawal_request: WithdrawalRequest, 
                              reserve_info: Dict, network_fee: Decimal) -> WithdrawalResult:
        """Execute BTC withdrawal"""
        # TODO: Implement BTC withdrawal using bitcoin RPC
        logger.info(f"TODO: Execute BTC withdrawal of {withdrawal_request.amount} to {withdrawal_request.to_address}")
        
        # Mock successful withdrawal for testing
        return WithdrawalResult(
            success=True,
            tx_hash="mock_btc_tx_hash_" + withdrawal_request.reference_id,
            fee_amount=network_fee
        )
    
    def execute_eth_withdrawal(self, withdrawal_request: WithdrawalRequest, 
                              reserve_info: Dict, network_fee: Decimal) -> WithdrawalResult:
        """Execute ETH withdrawal"""
        # TODO: Implement ETH withdrawal using Web3
        logger.info(f"TODO: Execute ETH withdrawal of {withdrawal_request.amount} to {withdrawal_request.to_address}")
        
        # Mock successful withdrawal for testing
        return WithdrawalResult(
            success=True,
            tx_hash="mock_eth_tx_hash_" + withdrawal_request.reference_id,
            fee_amount=network_fee
        )
    
    def execute_sol_withdrawal(self, withdrawal_request: WithdrawalRequest, 
                              reserve_info: Dict, network_fee: Decimal) -> WithdrawalResult:
        """Execute SOL withdrawal"""
        try:
            # TODO: Implement SOL withdrawal using Solana client
            logger.info(f"TODO: Execute SOL withdrawal of {withdrawal_request.amount} to {withdrawal_request.to_address}")
            
            # Mock successful withdrawal for testing
            return WithdrawalResult(
                success=True,
                tx_hash="mock_sol_tx_hash_" + withdrawal_request.reference_id,
                fee_amount=network_fee
            )
            
        except Exception as e:
            return WithdrawalResult(
                success=False,
                error=f"SOL withdrawal error: {str(e)}"
            )
    
    def execute_trx_withdrawal(self, withdrawal_request: WithdrawalRequest, 
                              reserve_info: Dict, network_fee: Decimal) -> WithdrawalResult:
        """Execute TRX withdrawal"""
        # TODO: Implement TRX withdrawal using Tron API
        logger.info(f"TODO: Execute TRX withdrawal of {withdrawal_request.amount} to {withdrawal_request.to_address}")
        
        # Mock successful withdrawal for testing
        return WithdrawalResult(
            success=True,
            tx_hash="mock_trx_tx_hash_" + withdrawal_request.reference_id,
            fee_amount=network_fee
        )
    
    def record_withdrawal_transaction(self, withdrawal_request: WithdrawalRequest, 
                                    withdrawal_result: WithdrawalResult):
        """Record withdrawal transaction in database"""
        try:
            # Get user's crypto account
            account = self.session.query(Account).filter_by(
                user_id=withdrawal_request.user_id,
                currency=withdrawal_request.currency,
                account_type=AccountType.CRYPTO
            ).first()
            
            if not account:
                logger.error(f"No account found for user {withdrawal_request.user_id} currency {withdrawal_request.currency}")
                return
            
            # Create withdrawal transaction record
            transaction = Transaction(
                account_id=account.id,
                transaction_type=TransactionType.WITHDRAWAL,
                amount_smallest_unit=AmountConverter.to_smallest_units(
                    withdrawal_request.amount, 
                    withdrawal_request.currency
                ),
                currency=withdrawal_request.currency,
                status=TransactionStatus.COMPLETED,
                reference_id=withdrawal_request.reference_id,
                description=f"Crypto withdrawal: {withdrawal_request.amount} {withdrawal_request.currency}",
                metadata_json={
                    'to_address': withdrawal_request.to_address,
                    'tx_hash': withdrawal_result.tx_hash,
                    'network_fee': str(withdrawal_result.fee_amount) if withdrawal_result.fee_amount else None,
                    'from_reserve': True,
                    'reserve_address': self.reserve_addresses[withdrawal_request.currency]['address']
                }
            )
            
            self.session.add(transaction)
            
            # Update account balance (deduct withdrawal amount)
            if hasattr(account, 'crypto_balance_smallest_unit'):
                current_balance_smallest = account.crypto_balance_smallest_unit or 0
                withdrawal_smallest = AmountConverter.to_smallest_units(
                    withdrawal_request.amount, 
                    withdrawal_request.currency
                )
                account.crypto_balance_smallest_unit = current_balance_smallest - withdrawal_smallest
            else:
                # Fallback to legacy balance field
                current_balance = getattr(account, 'balance', Decimal('0'))
                account.balance = current_balance - withdrawal_request.amount
            
            self.session.commit()
            
            logger.info(f"📝 Recorded withdrawal transaction: {transaction.reference_id}")
            
        except Exception as e:
            logger.error(f"Error recording withdrawal transaction: {e}")
            self.session.rollback()
    
    def get_reserve_summary(self) -> Dict[str, Dict]:
        """Get summary of all reserve addresses and balances"""
        summary = {}
        
        for currency, reserve_info in self.reserve_addresses.items():
            balance = self.get_reserve_balance(currency)
            summary[currency] = {
                'address': reserve_info['address'],
                'balance': balance,
                'network': reserve_info['network'],
                'network_fee': self.network_fees.get(currency, Decimal('0'))
            }
        
        return summary
    
    def __del__(self):
        """Cleanup database session"""
        if hasattr(self, 'session'):
            self.session.close()

def main():
    """Main function to test the withdrawal service"""
    logger.info("🏦 Crypto Reserve Withdrawal Service Test")
    
    try:
        withdrawal_service = CryptoReserveWithdrawalService()
        
        # Show reserve summary
        logger.info("📊 Reserve Summary:")
        summary = withdrawal_service.get_reserve_summary()
        for currency, info in summary.items():
            logger.info(f"  {currency}: {info['address']} (Balance: {info['balance']}, Fee: {info['network_fee']})")
        
        # Test withdrawal (mock)
        test_withdrawal = WithdrawalRequest(
            user_id=123,
            currency='SOL',
            amount=Decimal('0.1'),
            to_address='9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM',
            reference_id='test_withdrawal_001'
        )
        
        logger.info(f"\n🧪 Testing withdrawal: {test_withdrawal.amount} {test_withdrawal.currency}")
        result = withdrawal_service.process_withdrawal(test_withdrawal)
        
        if result.success:
            logger.info(f"✅ Test withdrawal successful: {result.tx_hash}")
        else:
            logger.error(f"❌ Test withdrawal failed: {result.error}")
        
    except Exception as e:
        logger.error(f"❌ Error in withdrawal service test: {e}")
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    main()
