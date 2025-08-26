#!/usr/bin/env python3
"""
Crypto Sweeper Service
Sweeps deposited amounts from user addresses to index 0 reserve addresses
"""

import os
import sys
import time
import logging
import traceback
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

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
class ReserveAddress:
    """Reserve address configuration"""
    currency: str
    address: str
    private_key: str
    network: str

@dataclass
class SweepResult:
    """Result of a sweep operation"""
    success: bool
    currency: str
    from_address: str
    to_address: str
    amount: Decimal
    tx_hash: Optional[str] = None
    error: Optional[str] = None

class CryptoSweeperService:
    """Service to sweep crypto deposits to reserve addresses"""
    
    def __init__(self):
        self.session = get_db_session()
        self.reserve_addresses = {}
        self.min_sweep_amounts = {
            'BTC': Decimal('0.0001'),  # 10,000 satoshis
            'ETH': Decimal('0.001'),   # 0.001 ETH
            'SOL': Decimal('0.01'),    # 0.01 SOL
            'TRX': Decimal('10'),      # 10 TRX
        }
        self.setup_reserve_addresses()
    
    def setup_reserve_addresses(self):
        """Initialize reserve addresses for each currency"""
        try:
            # Get BTC reserve address
            btc_wallet = BTC()
            btc_mnemonic = os.getenv('BTC_MNEMONIC')
            if btc_mnemonic:
                btc_wallet.from_mnemonic(mnemonic=btc_mnemonic)
                address, priv_key, pub_key = btc_wallet.new_address(index=0)
                self.reserve_addresses['BTC'] = ReserveAddress(
                    currency='BTC',
                    address=address,
                    private_key=priv_key,
                    network='testnet'
                )
                logger.info(f"✅ BTC reserve address: {address}")
            
            # Get ETH reserve address
            eth_wallet = ETH()
            eth_mnemonic = os.getenv('ETH_MNEMONIC')
            if eth_mnemonic:
                eth_wallet.from_mnemonic(mnemonic=eth_mnemonic)
                address, priv_key, pub_key = eth_wallet.new_address(index=0)
                self.reserve_addresses['ETH'] = ReserveAddress(
                    currency='ETH',
                    address=address,
                    private_key=priv_key,
                    network='mainnet'
                )
                logger.info(f"✅ ETH reserve address: {address}")
            
            # Get TRX reserve address
            trx_wallet = TRX()
            trx_mnemonic = os.getenv('TRX_MNEMONIC')
            if trx_mnemonic:
                trx_wallet.from_mnemonic(mnemonic=trx_mnemonic)
                address, priv_key, pub_key = trx_wallet.new_address(index=0)
                self.reserve_addresses['TRX'] = ReserveAddress(
                    currency='TRX',
                    address=address,
                    private_key=priv_key,
                    network='mainnet'
                )
                logger.info(f"✅ TRX reserve address: {address}")
            
            # Get SOL reserve address
            try:
                from solders.keypair import Keypair
                import hashlib
                
                base_seed = b'dwt_solana_wallet_seed_v1'
                user_bytes = (0).to_bytes(8, 'big')
                index_bytes = (0).to_bytes(4, 'big')
                combined_seed = base_seed + user_bytes + index_bytes
                seed_hash = hashlib.sha256(combined_seed).digest()
                
                keypair = Keypair.from_seed(seed_hash)
                import base58
                private_key = base58.b58encode(bytes(keypair)).decode()
                
                self.reserve_addresses['SOL'] = ReserveAddress(
                    currency='SOL',
                    address=str(keypair.pubkey()),
                    private_key=private_key,
                    network='mainnet'
                )
                logger.info(f"✅ SOL reserve address: {str(keypair.pubkey())}")
                
            except ImportError:
                logger.warning("❌ Solana SDK not available for SOL reserve address")
            
        except Exception as e:
            logger.error(f"Error setting up reserve addresses: {e}")
            logger.error(traceback.format_exc())
    
    def get_addresses_to_sweep(self, currency: str) -> List[Tuple[CryptoAddress, Decimal]]:
        """Get addresses with balances that need to be swept"""
        try:
            reserve_address = self.reserve_addresses.get(currency)
            if not reserve_address:
                logger.warning(f"No reserve address configured for {currency}")
                return []
            
            # Get all crypto addresses for this currency (excluding reserve address)
            addresses = self.session.query(CryptoAddress).join(Account).filter(
                and_(
                    CryptoAddress.currency_code == currency,
                    CryptoAddress.is_active == True,
                    CryptoAddress.address != reserve_address.address,
                    Account.account_type == AccountType.CRYPTO
                )
            ).all()
            
            addresses_to_sweep = []
            min_amount = self.min_sweep_amounts.get(currency, Decimal('0'))
            
            for addr in addresses:
                # Check if address has sufficient balance to sweep
                balance = self.get_address_balance(addr.address, currency)
                if balance and balance > min_amount:
                    addresses_to_sweep.append((addr, balance))
                    logger.info(f"📍 {currency} address {addr.address} has {balance} to sweep")
            
            return addresses_to_sweep
            
        except Exception as e:
            logger.error(f"Error getting addresses to sweep for {currency}: {e}")
            return []
    
    def get_address_balance(self, address: str, currency: str) -> Optional[Decimal]:
        """Get the current balance of an address"""
        try:
            if currency == 'BTC':
                return self.get_btc_balance(address)
            elif currency == 'ETH':
                return self.get_eth_balance(address)
            elif currency == 'SOL':
                return self.get_sol_balance(address)
            elif currency == 'TRX':
                return self.get_trx_balance(address)
            else:
                logger.warning(f"Unsupported currency for balance check: {currency}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting balance for {address} ({currency}): {e}")
            return None
    
    def get_btc_balance(self, address: str) -> Optional[Decimal]:
        """Get BTC balance for an address"""
        # TODO: Implement BTC balance checking via RPC or API
        logger.info(f"TODO: Implement BTC balance check for {address}")
        return None
    
    def get_eth_balance(self, address: str) -> Optional[Decimal]:
        """Get ETH balance for an address"""
        # TODO: Implement ETH balance checking via Web3
        logger.info(f"TODO: Implement ETH balance check for {address}")
        return None
    
    def get_sol_balance(self, address: str) -> Optional[Decimal]:
        """Get SOL balance for an address"""
        try:
            # Use SOL client to check balance
            sol_config = SolanaConfig.mainnet(os.getenv('ALCHEMY_SOLANA_API_KEY', 'demo'))
            sol_wallet = SOLWallet(user_id=0, config=sol_config, session=self.session)
            
            balance_info = sol_wallet.get_balance(address)
            if balance_info:
                return Decimal(str(balance_info.get('sol_balance', 0)))
            return None
            
        except Exception as e:
            logger.error(f"Error getting SOL balance for {address}: {e}")
            return None
    
    def get_trx_balance(self, address: str) -> Optional[Decimal]:
        """Get TRX balance for an address"""
        # TODO: Implement TRX balance checking via Tron API
        logger.info(f"TODO: Implement TRX balance check for {address}")
        return None
    
    def sweep_currency(self, currency: str) -> List[SweepResult]:
        """Sweep all addresses for a specific currency"""
        logger.info(f"🧹 Starting sweep for {currency}")
        results = []
        
        try:
            addresses_to_sweep = self.get_addresses_to_sweep(currency)
            if not addresses_to_sweep:
                logger.info(f"🧹 Sweep cycle completed: {len([r for r in results if r.success])} successful")
                return results
            
            reserve_address = self.reserve_addresses[currency]
            
            for crypto_address, balance in addresses_to_sweep:
                try:
                    result = self.sweep_address(
                        currency=currency,
                        from_address=crypto_address.address,
                        private_key=crypto_address.private_key,
                        to_address=reserve_address.address,
                        amount=balance
                    )
                    results.append(result)
                    
                    if result.success:
                        logger.info(f"✅ Swept {result.amount} {currency} from {result.from_address}")
                        # Record sweep transaction
                        self.record_sweep_transaction(crypto_address, result)
                    else:
                        logger.error(f"❌ Failed to sweep {currency} from {crypto_address.address}: {result.error}")
                        
                except Exception as e:
                    logger.error(f"Error sweeping {crypto_address.address}: {e}")
                    results.append(SweepResult(
                        success=False,
                        currency=currency,
                        from_address=crypto_address.address,
                        to_address=reserve_address.address,
                        amount=balance,
                        error=str(e)
                    ))
            
        except Exception as e:
            logger.error(f"Error during {currency} sweep: {e}")
            logger.error(traceback.format_exc())
        
        return results
    
    def sweep_address(self, currency: str, from_address: str, private_key: str, 
                     to_address: str, amount: Decimal) -> SweepResult:
        """Sweep funds from one address to another"""
        try:
            if currency == 'BTC':
                return self.sweep_btc(from_address, private_key, to_address, amount)
            elif currency == 'ETH':
                return self.sweep_eth(from_address, private_key, to_address, amount)
            elif currency == 'SOL':
                return self.sweep_sol(from_address, private_key, to_address, amount)
            elif currency == 'TRX':
                return self.sweep_trx(from_address, private_key, to_address, amount)
            else:
                return SweepResult(
                    success=False,
                    currency=currency,
                    from_address=from_address,
                    to_address=to_address,
                    amount=amount,
                    error=f"Unsupported currency: {currency}"
                )
                
        except Exception as e:
            return SweepResult(
                success=False,
                currency=currency,
                from_address=from_address,
                to_address=to_address,
                amount=amount,
                error=str(e)
            )
    
    def sweep_btc(self, from_address: str, private_key: str, to_address: str, amount: Decimal) -> SweepResult:
        """Sweep BTC from address with minimal transaction fees"""
        try:
            import bitcoin
            from bitcoin import *
            
            # Convert BTC to satoshis
            amount_satoshis = int(amount * 100_000_000)
            
            # Estimate transaction fee (use 1 sat/byte for low priority)
            # Typical transaction size is ~250 bytes
            fee_rate_sat_per_byte = 1  # Very low fee for sweep operations
            estimated_tx_size = 250
            fee_satoshis = fee_rate_sat_per_byte * estimated_tx_size
            
            # Ensure we have enough to cover fees
            if amount_satoshis <= fee_satoshis:
                logger.warning(f"Amount {amount} BTC too small to cover transaction fees")
                return SweepResult(
                    success=False,
                    currency='BTC',
                    from_address=from_address,
                    to_address=to_address,
                    amount=amount,
                    error="Amount too small to cover fees"
                )
            
            # Send amount minus transaction fee
            send_amount_satoshis = amount_satoshis - fee_satoshis
            
            # Get UTXOs for the address (this would need to be implemented with a BTC node/API)
            # For now, we'll use a placeholder implementation
            logger.info(f"✅ BTC sweep prepared: {send_amount_satoshis} satoshis")
            logger.info(f"   Fee rate: {fee_rate_sat_per_byte} sat/byte (minimal)")
            logger.info(f"   Estimated fee: {fee_satoshis} satoshis")
            logger.info(f"   Amount to sweep: {send_amount_satoshis / 100_000_000:.8f} BTC")
            
            # TODO: Implement actual BTC transaction creation and broadcasting
            # This requires:
            # 1. Fetch UTXOs from Bitcoin node/API
            # 2. Create transaction inputs from UTXOs
            # 3. Create transaction output to reserve address
            # 4. Sign transaction with private key
            # 5. Broadcast to Bitcoin network
            
            return SweepResult(
                success=False,  # Set to False until fully implemented
                currency='BTC',
                from_address=from_address,
                to_address=to_address,
                amount=amount,
                error="BTC sweep implementation pending - Bitcoin node integration required"
            )
            
        except Exception as e:
            logger.error(f"Error sweeping BTC: {e}")
            return SweepResult(
                success=False,
                currency='BTC',
                from_address=from_address,
                to_address=to_address,
                amount=amount,
                error=str(e)
            )
    
    def sweep_eth(self, from_address: str, private_key: str, to_address: str, amount: Decimal) -> SweepResult:
        """Sweep ETH from address with minimal gas fees"""
        try:
            from web3 import Web3
            from eth_account import Account
            
            # Connect to Ethereum node
            infura_key = os.getenv('INFURA_PROJECT_ID') or os.getenv('ALCHEMY_ETH_API_KEY')
            if not infura_key:
                raise Exception("No Ethereum RPC key found")
            
            w3 = Web3(Web3.HTTPProvider(f'https://mainnet.infura.io/v3/{infura_key}'))
            
            # Load account from private key
            account = Account.from_key(private_key)
            
            # Get current gas prices for optimization
            gas_price = w3.eth.gas_price
            
            # Use 80% of current gas price for slower but cheaper transaction
            optimized_gas_price = int(gas_price * 0.8)
            
            # Calculate gas limit for simple ETH transfer
            gas_limit = 21000
            
            # Calculate total gas cost
            gas_cost_wei = optimized_gas_price * gas_limit
            amount_wei = int(amount * 10**18)
            
            # Ensure we leave enough for gas
            if amount_wei <= gas_cost_wei:
                logger.warning(f"Amount {amount} ETH too small to cover gas costs")
                return SweepResult(
                    success=False,
                    currency='ETH',
                    from_address=from_address,
                    to_address=to_address,
                    amount=amount,
                    error="Amount too small to cover gas"
                )
            
            # Send amount minus gas costs
            send_amount = amount_wei - gas_cost_wei
            
            # Build transaction
            transaction = {
                'to': to_address,
                'value': send_amount,
                'gas': gas_limit,
                'gasPrice': optimized_gas_price,
                'nonce': w3.eth.get_transaction_count(from_address),
                'chainId': 1  # Mainnet
            }
            
            # Sign and send transaction
            signed_txn = account.sign_transaction(transaction)
            tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            
            logger.info(f"✅ ETH sweep transaction sent: {tx_hash.hex()}")
            logger.info(f"   Gas price: {optimized_gas_price} wei (20% discount)")
            logger.info(f"   Amount swept: {send_amount / 10**18:.8f} ETH")
            
            return SweepResult(
                success=True,
                currency='ETH',
                from_address=from_address,
                to_address=to_address,
                amount=Decimal(send_amount) / Decimal(10**18),
                transaction_hash=tx_hash.hex()
            )
            
        except Exception as e:
            logger.error(f"Error sweeping ETH: {e}")
            return SweepResult(
                success=False,
                currency='ETH',
                from_address=from_address,
                to_address=to_address,
                amount=amount,
                error=str(e)
            )
    
    def sweep_sol(self, from_address: str, private_key: str, to_address: str, amount: Decimal) -> SweepResult:
        """Sweep SOL from address with minimal transaction fees"""
        try:
            from solders.keypair import Keypair
            from solders.pubkey import Pubkey
            from solders.transaction import Transaction
            from solders.system_program import TransferParams, transfer
            from solana.rpc.api import Client
            import base58
            
            # Connect to Solana RPC
            rpc_url = f"https://solana-mainnet.g.alchemy.com/v2/{os.getenv('ALCHEMY_SOLANA_API_KEY', 'demo')}"
            client = Client(rpc_url)
            
            # Load keypair from private key
            keypair = Keypair.from_base58_string(private_key)
            
            # Convert addresses to Pubkey
            from_pubkey = keypair.pubkey()
            to_pubkey = Pubkey.from_string(to_address)
            
            # Get recent blockhash
            recent_blockhash = client.get_latest_blockhash().value.blockhash
            
            # SOL has fixed transaction fee of 5000 lamports (0.000005 SOL)
            transaction_fee_lamports = 5000
            amount_lamports = int(amount * 10**9)  # Convert SOL to lamports
            
            # Ensure we have enough to cover fees
            if amount_lamports <= transaction_fee_lamports:
                logger.warning(f"Amount {amount} SOL too small to cover transaction fees")
                return SweepResult(
                    success=False,
                    currency='SOL',
                    from_address=from_address,
                    to_address=to_address,
                    amount=amount,
                    error="Amount too small to cover fees"
                )
            
            # Send amount minus transaction fee
            send_amount_lamports = amount_lamports - transaction_fee_lamports
            
            # Create transfer instruction
            transfer_instruction = transfer(
                TransferParams(
                    from_pubkey=from_pubkey,
                    to_pubkey=to_pubkey,
                    lamports=send_amount_lamports
                )
            )
            
            # Create transaction
            transaction = Transaction.new_with_payer([transfer_instruction], from_pubkey)
            transaction.partial_sign([keypair], recent_blockhash)
            
            # Send transaction
            response = client.send_transaction(transaction)
            tx_hash = str(response.value)
            
            logger.info(f"✅ SOL sweep transaction sent: {tx_hash}")
            logger.info(f"   Transaction fee: {transaction_fee_lamports} lamports (0.000005 SOL)")
            logger.info(f"   Amount swept: {send_amount_lamports / 10**9:.9f} SOL")
            
            return SweepResult(
                success=True,
                currency='SOL',
                from_address=from_address,
                to_address=to_address,
                amount=Decimal(send_amount_lamports) / Decimal(10**9),
                transaction_hash=tx_hash
            )
            
        except Exception as e:
            logger.error(f"Error sweeping SOL: {e}")
            return SweepResult(
                success=False,
                currency='SOL',
                from_address=from_address,
                to_address=to_address,
                amount=amount,
                error=str(e)
            )
    
    def sweep_trx(self, from_address: str, private_key: str, to_address: str, amount: Decimal) -> SweepResult:
        """Sweep TRX from address with minimal energy/bandwidth costs"""
        try:
            from tronpy import Tron
            from tronpy.keys import PrivateKey
            
            # Connect to Tron network
            tron = Tron(network='mainnet')
            
            # Load private key
            priv_key = PrivateKey(bytes.fromhex(private_key))
            
            # Convert TRX to SUN (1 TRX = 1,000,000 SUN)
            amount_sun = int(amount * 1_000_000)
            
            # TRX transactions typically cost 0.1 TRX in energy/bandwidth
            # Use conservative estimate of 0.15 TRX for fees
            fee_sun = 150_000  # 0.15 TRX in SUN
            
            # Ensure we have enough to cover fees
            if amount_sun <= fee_sun:
                logger.warning(f"Amount {amount} TRX too small to cover transaction fees")
                return SweepResult(
                    success=False,
                    currency='TRX',
                    from_address=from_address,
                    to_address=to_address,
                    amount=amount,
                    error="Amount too small to cover fees"
                )
            
            # Send amount minus estimated fees
            send_amount_sun = amount_sun - fee_sun
            
            # Create and sign transaction
            txn = (
                tron.trx.transfer(from_address, to_address, send_amount_sun)
                .memo("Sweep to reserve")
                .build()
                .sign(priv_key)
            )
            
            # Broadcast transaction
            result = txn.broadcast()
            tx_hash = result.get('txid', '')
            
            if result.get('result', False):
                logger.info(f"✅ TRX sweep transaction sent: {tx_hash}")
                logger.info(f"   Estimated fee: {fee_sun} SUN (0.15 TRX)")
                logger.info(f"   Amount swept: {send_amount_sun / 1_000_000:.6f} TRX")
                
                return SweepResult(
                    success=True,
                    currency='TRX',
                    from_address=from_address,
                    to_address=to_address,
                    amount=Decimal(send_amount_sun) / Decimal(1_000_000),
                    transaction_hash=tx_hash
                )
            else:
                error_msg = result.get('message', 'Transaction failed')
                logger.error(f"TRX sweep failed: {error_msg}")
                return SweepResult(
                    success=False,
                    currency='TRX',
                    from_address=from_address,
                    to_address=to_address,
                    amount=amount,
                    error=error_msg
                )
                
        except Exception as e:
            logger.error(f"Error sweeping TRX: {e}")
            return SweepResult(
                success=False,
                currency='TRX',
                from_address=from_address,
                to_address=to_address,
                amount=amount,
                error=str(e)
            )
    
    def record_sweep_transaction(self, crypto_address: CryptoAddress, sweep_result: SweepResult):
        """Record a sweep transaction in the database"""
        try:
            # Create transaction record
            transaction = Transaction(
                account_id=crypto_address.account_id,
                transaction_type=TransactionType.SWEEP,
                amount_smallest_unit=AmountConverter.to_smallest_units(sweep_result.amount, sweep_result.currency),
                currency=sweep_result.currency,
                status=TransactionStatus.COMPLETED,
                reference_id=f"sweep_{sweep_result.tx_hash or int(time.time())}",
                description=f"Sweep {sweep_result.amount} {sweep_result.currency} to reserve address",
                metadata_json={
                    'from_address': sweep_result.from_address,
                    'to_address': sweep_result.to_address,
                    'tx_hash': sweep_result.tx_hash,
                    'sweep_timestamp': datetime.utcnow().isoformat()
                }
            )
            
            self.session.add(transaction)
            self.session.commit()
            
            logger.info(f"📝 Recorded sweep transaction: {transaction.reference_id}")
            
        except Exception as e:
            for result in failed_sweeps:
                logger.error(f"  ❌ {result.currency}: Failed to sweep from {result.from_address} - {result.error}")
        
        return total_results
    
    def get_reserve_balances(self) -> Dict[str, Decimal]:
        """Get current balances of all reserve addresses"""
        balances = {}
        
        for currency, reserve_addr in self.reserve_addresses.items():
            try:
                balance = self.get_address_balance(reserve_addr.address, currency)
                balances[currency] = balance or Decimal('0')
                logger.info(f"💰 {currency} reserve balance: {balances[currency]}")
            except Exception as e:
                logger.error(f"Error getting {currency} reserve balance: {e}")
                balances[currency] = Decimal('0')
        
        return balances
    
    def sweep_address_on_deposit(self, address: str, currency: str, transaction_hash: str):
        """
        Sweep a specific address immediately after a deposit is confirmed.
        This is called from webhook handlers when deposits are confirmed.
        """
        logger.info(f"🧹 Triggering immediate sweep for {currency} address {address} (tx: {transaction_hash})")
        
        try:
            # Get the crypto address from database
            crypto_address = self.session.query(CryptoAddress).filter_by(
                address=address,
                currency_code=currency
            ).first()
            
            if not crypto_address:
                logger.warning(f"Address {address} not found in database for {currency}")
                return False
            
            # Check if this is a reserve address (index 0) - don't sweep reserve addresses
            if crypto_address.address_index == 0:
                logger.info(f"Skipping sweep for reserve address {address}")
                return True
            
            # Load reserve address
            reserve_address = self.reserve_addresses.get(currency)
            
            if not reserve_address:
                logger.error(f"Missing reserve address for {currency}")
                return False
            
            # Check balance of the address
            balance = self.get_address_balance(address, currency)
            
            if balance is None or balance <= self.min_sweep_amounts.get(currency, 0):
                logger.info(f"Balance {balance} below minimum sweep threshold for {currency}")
                return True
            
            # Get private key for the address
            address_private_key = self._get_address_private_key(crypto_address)
            
            # Perform the sweep
            success = self._execute_sweep(
                from_address=address,
                to_address=reserve_address.address,
                private_key=address_private_key,
                amount=balance,
                currency=currency
            )
            
            if success:
                # Record the sweep transaction
                self._record_sweep_transaction(
                    from_address=address,
                    to_address=reserve_address.address,
                    amount=balance,
                    currency=currency,
                    trigger_tx_hash=transaction_hash
                )
                logger.info(f"✅ Successfully swept {balance} {currency} from {address} to reserve")
            else:
                logger.error(f"❌ Failed to sweep {currency} from {address}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error in immediate sweep for {address}: {e}")
            return False

    def __del__(self):
        """Cleanup database session"""

def main():
    """Main function to run the sweeper service"""
    logger.info("🧹 Crypto Sweeper Service Starting")
    
    try:
        sweeper = CryptoSweeperService()
        
        # Show reserve addresses
        logger.info("🏦 Reserve Addresses:")
        for currency, reserve_addr in sweeper.reserve_addresses.items():
            logger.info(f"  {currency}: {reserve_addr.address}")
        
        # Get current reserve balances
        logger.info("\n💰 Current Reserve Balances:")
        balances = sweeper.get_reserve_balances()
        
        # Run sweep cycle
        logger.info("\n🧹 Running Sweep Cycle:")
        results = sweeper.run_sweep_cycle()
        
        logger.info("✅ Crypto Sweeper Service Complete")
        
    except Exception as e:
        logger.error(f"❌ Error in crypto sweeper service: {e}")
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    main()
