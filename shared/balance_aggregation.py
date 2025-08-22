"""
Balance Aggregation Service

This service handles multi-chain token balance aggregation and currency conversion.
It aggregates tokens like USDT and USDC across different blockchains (ETH, TRX, BNB)
and provides total portfolio value calculations.
"""

from typing import Dict, List, Optional, Any
from decimal import Decimal
from shared.fiat.forex_service import forex_service
from sqlalchemy.orm import Session
from db.wallet import Account, AccountType
from db.crypto_precision import CryptoPrecisionManager
import logging

logger = logging.getLogger(__name__)

class BalanceAggregationService:
    """Service for aggregating multi-chain token balances and currency conversion"""
    
    # Define which tokens can exist on multiple chains
    MULTI_CHAIN_TOKENS = {
        'USDT': ['ETH', 'TRX', 'BNB', 'SOL'],  # USDT exists on multiple chains
        'USDC': ['ETH', 'TRX', 'BNB', 'SOL'],  # USDC exists on multiple chains
        'BTC': ['BTC'],  # Native BTC only
        'ETH': ['ETH'],  # Native ETH only
        'BNB': ['BNB'],  # Native BNB only
        'TRX': ['TRX'],  # Native TRX only
        'SOL': ['SOL'],  # Native SOL only
        'LTC': ['LTC'],  # Native LTC only
    }
    
    # Base currencies (what we aggregate to)
    BASE_CURRENCIES = ['BTC', 'ETH', 'BNB', 'TRX', 'SOL', 'LTC', 'USDT', 'USDC']
    
    def __init__(self, session: Session):
        self.session = session
    
    def get_user_aggregated_balances(self, user_id: int) -> Dict[str, Dict]:
        """
        Get aggregated balances for a user across all chains.
        
        Returns:
            Dict with base currency as key and aggregated balance info as value
        """
        # Get all crypto accounts for the user
        crypto_accounts = self.session.query(Account).filter(
            Account.user_id == user_id,
            Account.account_type == AccountType.CRYPTO
        ).all()
        
        aggregated_balances = {}
        
        # Initialize all base currencies
        for base_currency in self.BASE_CURRENCIES:
            aggregated_balances[base_currency] = {
                'total_balance': 0.0,
                'chains': {},
                'addresses': []
            }
        
        # Process each account
        for account in crypto_accounts:
            currency = account.currency
            parent_currency = self._get_parent_currency(account)
            
            # Determine which base currency this account contributes to
            base_currency = self._determine_base_currency(currency, parent_currency)
            
            if base_currency:
                # Get balance in standard units
                balance_smallest = account.crypto_balance_smallest_unit or 0
                balance_standard = self._convert_to_standard_units(balance_smallest, currency, account)
                
                # Add to aggregated balance
                aggregated_balances[base_currency]['total_balance'] += balance_standard
                
                # Track by chain
                chain_key = parent_currency or currency
                if chain_key not in aggregated_balances[base_currency]['chains']:
                    aggregated_balances[base_currency]['chains'][chain_key] = {
                        'balance': 0.0,
                        'accounts': []
                    }
                
                aggregated_balances[base_currency]['chains'][chain_key]['balance'] += balance_standard
                aggregated_balances[base_currency]['chains'][chain_key]['accounts'].append({
                    'account_id': account.id,
                    'balance': balance_standard,
                    'currency': currency,
                    'parent_currency': parent_currency
                })
                
                # Add addresses from crypto_addresses relationship
                if hasattr(account, 'crypto_addresses'):
                    for crypto_addr in account.crypto_addresses:
                        if crypto_addr.is_active:
                            addr_info = {
                                'address': crypto_addr.address,
                                'memo': crypto_addr.memo,
                                'chain': chain_key,
                                'currency': currency
                            }
                            if addr_info not in aggregated_balances[base_currency]['addresses']:
                                aggregated_balances[base_currency]['addresses'].append(addr_info)
        
        # Return all currencies, including zero balance ones with addresses
        # Filter out only currencies that have no balance AND no addresses
        return {k: v for k, v in aggregated_balances.items() if v['total_balance'] > 0 or v['addresses']}
    
    def get_portfolio_value(self, user_id: int, prices: Dict[str, float], 
                          target_currency: str = 'UGX') -> Dict[str, float]:
        """
        Calculate total portfolio value in target currency.
        
        Args:
            user_id: User ID
            prices: Dict of currency prices in USD
            target_currency: Target currency for conversion (default: UGX)
            
        Returns:
            Dict with portfolio breakdown and total value
        """
        aggregated_balances = self.get_user_aggregated_balances(user_id)
        
        # Exchange rates using real-time forex service
        try:
            exchange_rates = {
                'UGX': forex_service.get_exchange_rate('usd', 'ugx'),
                'USD': 1.0,
                'EUR': forex_service.get_exchange_rate('usd', 'eur'),
                'GBP': forex_service.get_exchange_rate('usd', 'gbp')
            }
        except Exception:
            # Fallback rates if forex service fails
            exchange_rates = {
                'UGX': 3700.0,  # USD to UGX
                'USD': 1.0,
                'EUR': 0.85,
                'GBP': 0.73
            }
        
        portfolio_value = {
            'currencies': {},
            'total_value_usd': 0.0,
            'total_value_target': 0.0,
            'target_currency': target_currency
        }
        
        for currency, balance_info in aggregated_balances.items():
            balance = balance_info['total_balance']
            
            if balance > 0 and currency in prices:
                price_usd = prices[currency]
                # Skip if price is None or invalid
                if price_usd is None or price_usd <= 0:
                    continue
                value_usd = balance * price_usd
                
                portfolio_value['currencies'][currency] = {
                    'balance': balance,
                    'price_usd': price_usd,
                    'value_usd': value_usd,
                    'chains': balance_info['chains']
                }
                
                portfolio_value['total_value_usd'] += value_usd
        
        # Convert to target currency
        if target_currency in exchange_rates:
            rate = exchange_rates[target_currency]
            portfolio_value['total_value_target'] = portfolio_value['total_value_usd'] * rate
        else:
            portfolio_value['total_value_target'] = portfolio_value['total_value_usd']
        
        return portfolio_value
    
    def _get_parent_currency(self, account: Account) -> Optional[str]:
        """Get the parent currency from account precision config"""
        if account.precision_config and isinstance(account.precision_config, dict):
            return account.precision_config.get('parent_currency')
        return None
    
    def _determine_base_currency(self, currency: str, parent_currency: Optional[str]) -> Optional[str]:
        """
        Determine which base currency this account contributes to.
        
        For tokens like USDT-ETH, USDT-TRX, they all contribute to USDT base currency.
        For native currencies like ETH, BTC, they contribute to themselves.
        """
        currency_upper = currency.upper()
        
        # Check if this is a multi-chain token
        for base_curr, chains in self.MULTI_CHAIN_TOKENS.items():
            if currency_upper == base_curr:
                # This could be a multi-chain token or native currency
                if parent_currency:
                    # It's a token on another chain (e.g., USDT on ETH)
                    parent_upper = parent_currency.upper()
                    if parent_upper in chains:
                        return base_curr
                else:
                    # It's either native or we treat it as base currency
                    return base_curr
        
        # If not found in multi-chain tokens, return the currency itself if it's a base currency
        if currency_upper in self.BASE_CURRENCIES:
            return currency_upper
        
        return None
    
    def _convert_to_standard_units(self, balance_smallest: int, currency: str, account: Account) -> float:
        """Convert balance from smallest units to standard units"""
        try:
            return float(CryptoPrecisionManager.from_smallest_unit(balance_smallest, currency))
        except:
            # Fallback conversion based on currency
            currency_upper = currency.upper()
            if currency_upper in ['BTC', 'LTC']:
                return float(balance_smallest) / 100_000_000  # satoshis
            elif currency_upper in ['ETH', 'BNB']:
                return float(balance_smallest) / 10**18  # wei
            elif currency_upper == 'SOL':
                return float(balance_smallest) / 10**9  # lamports
            elif currency_upper in ['USDT', 'USDC', 'TRX']:
                # Check if it's a token with specific decimals
                if account.precision_config and isinstance(account.precision_config, dict):
                    decimals = account.precision_config.get('decimals', 6)
                    return float(balance_smallest) / (10 ** decimals)
                return float(balance_smallest) / 10**6  # default 6 decimals
            else:
                return float(balance_smallest) / 10**8  # default 8 decimals
    
    def get_balance_summary(self, user_id: int) -> Dict:
        """Get a summary of user's balances for quick display"""
        aggregated_balances = self.get_user_aggregated_balances(user_id)
        
        summary = {
            'total_currencies': len([k for k, v in aggregated_balances.items() if v['total_balance'] > 0]),
            'currencies': {},
            'multi_chain_tokens': {}
        }
        
        for currency, balance_info in aggregated_balances.items():
            if balance_info['total_balance'] > 0:
                summary['currencies'][currency] = {
                    'balance': balance_info['total_balance'],
                    'chain_count': len(balance_info['chains'])
                }
                
                # Track multi-chain tokens separately
                if len(balance_info['chains']) > 1:
                    summary['multi_chain_tokens'][currency] = {
                        'total_balance': balance_info['total_balance'],
                        'chains': {k: v['balance'] for k, v in balance_info['chains'].items()}
                    }
        
        return summary
