"""
PnL Calculator Service - Calculates profit/loss based on actual transaction costs from ledger
"""
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from shared.fiat.forex_service import ForexService
from shared.crypto.price_utils import get_crypto_price
from shared.currency_precision import get_currency_info
from db.connection import get_session
from db.wallet import Account, Transaction, Trade
from sqlalchemy import text
from sqlalchemy.orm import Session
import logging
import datetime
from datetime import timedelta

logger = logging.getLogger(__name__)

class PnLCalculator:
    """Calculate profit/loss based on actual transaction costs from double-entry ledger"""
    
    def __init__(self, session: Session):
        self.session = session
        self.usd_to_ugx_rate = 3700  # Default fallback rate
    
    def _get_usd_to_ugx_rate(self):
        """Get current USD/UGX exchange rate"""
        try:
            rate = forex_service.get_exchange_rate('USD', 'UGX')
            logger.info(f"Using live USD/UGX rate: {rate}")
            return rate
        except Exception as e:
            logger.warning(f"Failed to get live USD/UGX rate, using fallback: {e}")
            return 3700
    
    def _get_current_price(self, currency: str) -> float:
        """Get current price for a cryptocurrency in USD"""
        try:
            price = get_crypto_price(currency)
            if price and price > 0:
                logger.info(f"Current price for {currency}: ${price}")
                return float(price)
            else:
                logger.warning(f"No valid price found for {currency}")
                return 0.0
        except Exception as e:
            logger.error(f"Error getting current price for {currency}: {e}")
            return 0.0
    
    async def calculate_user_pnl(self, user_id: int, currency: str = None, period_days: int = 1) -> Dict:
        """
        Calculate PnL for a user based on actual transaction costs from ledger
        
        Args:
            user_id: User ID
            currency: Specific currency to calculate PnL for (None for all)
            period_days: Number of days to look back for PnL calculation
            
        Returns:
            Dict with PnL data including realized and unrealized gains/losses
        """
        try:
            # Get time range for PnL calculation
            end_date = datetime.datetime.now(datetime.timezone.utc)
            start_date = end_date - timedelta(days=period_days)
            
            # Get all crypto positions for user
            positions = self._get_user_positions(user_id, currency)
            
            # Calculate realized PnL from completed trades
            realized_pnl = await self._calculate_realized_pnl(user_id, currency, start_date, end_date)
            
            # Calculate unrealized PnL from current holdings
            unrealized_pnl = await self._calculate_unrealized_pnl(user_id, positions)
            
            # Combine results
            total_pnl_ugx = realized_pnl['total_ugx'] + unrealized_pnl['total_ugx']
            total_pnl_usd = realized_pnl['total_usd'] + unrealized_pnl['total_usd']
            
            # Calculate percentage based on total cost basis from unrealized positions
            total_cost_basis = sum(pos['total_cost_ugx'] for pos in unrealized_pnl['positions'])
            pnl_percentage = 0.0
            if total_cost_basis > 0:
                pnl_percentage = (total_pnl_ugx / total_cost_basis) * 100
            
            return {
                'period_days': period_days,
                'realized_pnl': realized_pnl,
                'unrealized_pnl': unrealized_pnl,
                'total_pnl_ugx': total_pnl_ugx,
                'total_pnl_usd': total_pnl_usd,
                'total_pnl_percentage': pnl_percentage,
                'cost_basis_ugx': total_cost_basis,
                'currency_breakdown': {}
            }
            
        except Exception as e:
            logger.error(f"Error calculating PnL for user {user_id}: {e}")
            return {
                'period_days': period_days,
                'realized_pnl': {'total_ugx': 0, 'total_usd': 0, 'trades': []},
                'unrealized_pnl': {'total_ugx': 0, 'total_usd': 0, 'positions': []},
                'total_pnl_ugx': 0,
                'total_pnl_usd': 0,
                'total_pnl_percentage': 0.0,
                'cost_basis_ugx': 0,
                'currency_breakdown': {}
            }
    
    def _get_user_positions(self, user_id: int, currency: str = None) -> List[Dict]:
        """Get user's current crypto positions"""
        try:
            logger.info(f"Getting positions for user_id: {user_id}, currency: {currency}")
            
            query = """
                SELECT 
                    currency,
                    balance,
                    crypto_balance_smallest_unit,
                    COUNT(*) as transaction_count
                FROM accounts 
                WHERE user_id = :user_id 
                AND account_type = 'CRYPTO'
            """
            
            params = {'user_id': user_id}
            if currency:
                query += " AND currency = :currency"
                params['currency'] = currency
            
            query += " GROUP BY currency, balance, crypto_balance_smallest_unit"
            
            logger.info(f"Executing query: {query} with params: {params}")
            result = self.session.execute(text(query), params)
            positions = []
            
            for row in result:
                logger.info(f"Found account: currency={row.currency}, balance={row.balance}, crypto_balance_smallest_unit={row.crypto_balance_smallest_unit}")
                
                # Get currency info for divisibility
                currency_info = get_currency_info(row.currency)
                divisibility = currency_info.get('divisibility', 8)
                logger.info(f"Currency {row.currency} divisibility: {divisibility}")
                
                # Calculate actual balance from smallest unit
                if row.crypto_balance_smallest_unit and row.crypto_balance_smallest_unit > 0:
                    actual_balance = float(row.crypto_balance_smallest_unit) / (10 ** divisibility)
                    logger.info(f"Using smallest_unit: {row.crypto_balance_smallest_unit} -> actual_balance: {actual_balance}")
                else:
                    actual_balance = float(row.balance or 0)
                    logger.info(f"Using balance field: {row.balance} -> actual_balance: {actual_balance}")
                
                if actual_balance > 0:
                    position = {
                        'currency': row.currency,
                        'balance': actual_balance,
                        'balance_smallest_unit': int(row.crypto_balance_smallest_unit or 0),
                        'transaction_count': row.transaction_count
                    }
                    logger.info(f"Adding position: {position}")
                    positions.append(position)
                else:
                    logger.info(f"Skipping zero balance position for {row.currency}")
            
            logger.info(f"Total positions found: {len(positions)}")
            return positions
            
        except Exception as e:
            logger.error(f"Error getting user positions: {e}")
            return []
    
    async def _calculate_realized_pnl(self, user_id: int, currency: str, start_date: datetime, end_date: datetime) -> Dict:
        """Calculate realized PnL from completed trades"""
        
        # Query for completed trades
        query = """
            SELECT 
                t.id as trade_id,
                t.trade_type,
                t.crypto_currency,
                t.crypto_amount,
                t.fiat_currency,
                t.fiat_amount,
                t.fee_amount,
                t.created_at,
                t.exchange_rate
            FROM trades t
            WHERE t.user_id = :user_id 
                AND t.status = 'completed'
                AND t.created_at BETWEEN :start_date AND :end_date
        """
        
        params = {
            'user_id': user_id,
            'start_date': start_date,
            'end_date': end_date
        }
        
        if currency:
            query += " AND t.crypto_currency = :currency"
            params['currency'] = currency
        
        query += " ORDER BY t.created_at DESC"
        
        try:
            logger.info(f"Calculating realized PnL for user {user_id}, currency: {currency}")
            result = self.session.execute(text(query), params)
            
            trades = []
            total_realized_pnl_ugx = 0
            
            for row in result:
                logger.info(f"Processing trade: {row.trade_id}, type: {row.trade_type}, amount: {row.fiat_amount}")
                
                # Calculate PnL based on trade type and amounts
                if row.trade_type == 'buy':
                    # For buy trades, PnL is negative (cost including fees)
                    pnl_ugx = -(float(row.fiat_amount) + float(row.fee_amount or 0))
                elif row.trade_type == 'sell':
                    # For sell trades, PnL is positive (revenue minus fees)
                    pnl_ugx = float(row.fiat_amount) - float(row.fee_amount or 0)
                else:
                    pnl_ugx = 0
                
                # Convert to USD
                pnl_usd = pnl_ugx / self.usd_to_ugx_rate
                
                trade_data = {
                    'trade_id': row.trade_id,
                    'trade_type': row.trade_type,
                    'crypto_currency': row.crypto_currency,
                    'crypto_amount': float(row.crypto_amount),
                    'fiat_amount': float(row.fiat_amount),
                    'fee_amount': float(row.fee_amount or 0),
                    'pnl_ugx': pnl_ugx,
                    'pnl_usd': pnl_usd,
                    'created_at': row.created_at.isoformat() if row.created_at else None
                }
                
                trades.append(trade_data)
                total_realized_pnl_ugx += pnl_ugx
            
            logger.info(f"Total realized PnL: {total_realized_pnl_ugx} UGX from {len(trades)} trades")
            
            # Use the instance rate
            usd_to_ugx_rate = self.usd_to_ugx_rate
            
            return {
                'total_ugx': total_realized_pnl_ugx,
                'total_usd': total_realized_pnl_ugx / usd_to_ugx_rate,
                'trades': trades
            }
            
        except Exception as e:
            logger.error(f"Error calculating realized PnL: {e}")
            return {'total_ugx': 0, 'total_usd': 0, 'trades': []}
    
    async def _calculate_unrealized_pnl(self, user_id: int, positions: List[Dict]) -> Dict:
        """Calculate unrealized PnL from current holdings vs cost basis"""
        
        unrealized_positions = []
        total_pnl_ugx = 0
        total_pnl_usd = 0
        
        logger.info(f"Calculating unrealized PnL for user {user_id} with {len(positions)} positions")
        
        for position in positions:
            currency = position['currency']
            balance = position['balance']
            
            if balance <= 0:
                continue
                
            # Get adjusted cost base for this currency (weighted average method)
            total_cost_basis, cost_basis_per_unit = self._get_adjusted_cost_base(user_id, currency)
            
            # Calculate unrealized PnL only for the portion we have cost basis for
            cost_basis_crypto_amount = total_cost_basis / cost_basis_per_unit if cost_basis_per_unit > 0 else 0.0
            
            # Get current market value
            current_price = get_crypto_price(currency)
            if current_price and current_price > 0:
                current_price_ugx = current_price * self.usd_to_ugx_rate
                current_value_ugx = balance * current_price_ugx
            else:
                current_value_ugx = 0.0
            
            # Calculate unrealized PnL using proper accounting principles
            if cost_basis_per_unit > 0 and cost_basis_crypto_amount > 0:
                # Only calculate PnL for the portion we have historical cost data for
                pnl_eligible_amount = min(balance, cost_basis_crypto_amount)
                
                # Current value of the portion we can calculate PnL for
                current_value_pnl_portion = pnl_eligible_amount * current_price_ugx
                
                # Historical cost of this portion
                historical_cost_ugx = pnl_eligible_amount * cost_basis_per_unit
                
                # Unrealized PnL = Current Value - Historical Cost
                unrealized_pnl_ugx = current_value_pnl_portion - historical_cost_ugx
                unrealized_pnl_usd = unrealized_pnl_ugx / self.usd_to_ugx_rate
                
                logger.info(f"{currency}: PnL for {pnl_eligible_amount} units - Current: {current_value_pnl_portion:.2f} UGX, Cost: {historical_cost_ugx:.2f} UGX, PnL: {unrealized_pnl_ugx:.2f} UGX")
            else:
                # No historical cost basis available - cannot calculate meaningful PnL
                unrealized_pnl_ugx = 0.0
                unrealized_pnl_usd = 0.0
                historical_cost_ugx = 0.0
                logger.warning(f"{currency}: No cost basis available for PnL calculation")
            
            logger.info(f"Position {currency}: balance={balance}, cost_basis_per_unit={cost_basis_per_unit}, current_price={current_price}, pnl_ugx={unrealized_pnl_ugx}")
            
            unrealized_positions.append({
                'currency': currency,
                'balance': balance,
                'cost_basis_per_unit': cost_basis_per_unit,
                'current_price': current_price,
                'total_cost_ugx': historical_cost_ugx,
                'current_value_ugx': current_value_ugx,
                'unrealized_pnl_ugx': unrealized_pnl_ugx,
                'unrealized_pnl_usd': unrealized_pnl_usd
            })
            
            total_pnl_ugx += unrealized_pnl_ugx
            total_pnl_usd += unrealized_pnl_usd
        
        logger.info(f"Total unrealized PnL: {total_pnl_ugx} UGX, {total_pnl_usd} USD")
        
        return {
            'total_ugx': total_pnl_ugx,
            'total_usd': total_pnl_usd,
            'positions': unrealized_positions
        }
    
    def _get_average_cost_basis(self, user_id: int, currency: str) -> float:
        """Get average cost basis for a currency from all buy transactions"""
        
        query = """
            SELECT 
                SUM(t.crypto_amount) as total_bought,
                SUM(t.fiat_amount) as total_cost
            FROM trades t
            WHERE t.user_id = :user_id 
                AND t.crypto_currency = :currency
                AND t.trade_type = 'buy'
                AND t.status = 'completed'
        """
        
        result = self.session.execute(text(query), {
            'user_id': user_id,
            'currency': currency
        }).fetchone()
        
        if result and result.total_bought and result.total_bought > 0:
            return float(result.total_cost) / float(result.total_bought)
        else:
            return 0.0
    
    def _get_total_cost_basis(self, user_id: int, currency: str = None) -> float:
        """Get total cost basis for user's crypto holdings from ledger entries"""
        try:
            # First try to get cost basis from trades
            trade_cost_basis = self._get_cost_basis_from_trades(user_id, currency)
            if trade_cost_basis > 0:
                return trade_cost_basis
            
            # If no trades, calculate from ledger entries (deposits)
            return self._get_cost_basis_from_ledger(user_id, currency)
            
        except Exception as e:
            logger.error(f"Error calculating cost basis for {currency}: {e}")
            return 0.0
    
    def _get_cost_basis_from_trades(self, user_id: int, currency: str = None) -> float:
        """Get cost basis from completed trades"""
        try:
            query = """
                SELECT SUM(t.fiat_amount) as total_cost
                FROM trades t
                WHERE t.user_id = :user_id 
                    AND t.trade_type = 'buy'
                    AND t.status = 'completed'
            """
            
            params = {'user_id': user_id}
            
            if currency:
                query += " AND t.crypto_currency = :currency"
                params['currency'] = currency
            
            result = self.session.execute(text(query), params).fetchone()
            
            return float(result.total_cost or 0) if result else 0.0
            
        except Exception as e:
            logger.error(f"Error getting cost basis from trades: {e}")
            return 0.0
    
    def _get_current_holdings_from_ledger(self, user_id: int, currency: str = None) -> Dict[str, float]:
        """Calculate current crypto holdings from ledger transactions"""
        
        try:
            from db.accounting import AccountingAccount, LedgerTransaction, JournalEntry
            session = get_session()
            
            # Query all transactions for User Liabilities accounts
            query = session.query(
                AccountingAccount.name.label('account_name'),
                LedgerTransaction.debit.label('debit_amount'),
                LedgerTransaction.credit.label('credit_amount')
            ).join(AccountingAccount, LedgerTransaction.account_id == AccountingAccount.id)\
             .filter(AccountingAccount.name.like('User Liabilities - %'))
            
            if currency:
                query = query.filter(AccountingAccount.name == f'User Liabilities - {currency}')
            
            result = query.all()
            holdings = {}
            
            for row in result:
                # Extract currency from account name
                account_currency = row.account_name.split(" - ")[-1] if " - " in row.account_name else None
                if not account_currency:
                    continue
                
                if account_currency not in holdings:
                    holdings[account_currency] = 0.0
                
                # Credits increase user liabilities (deposits), debits decrease (withdrawals)
                holdings[account_currency] += float(row.credit_amount or 0) - float(row.debit_amount or 0)
            
            logger.info(f"Current holdings from ledger: {holdings}")
            return holdings
            
        except Exception as e:
            logger.error(f"Error getting holdings from ledger: {e}")
            return {}
    
    def _get_adjusted_cost_base(self, user_id: int, currency: str) -> tuple[float, float]:
        """
        Calculate adjusted cost base using weighted average method (Canadian method)
        Returns: (total_cost_basis_ugx, average_cost_per_unit_ugx)
        """
        
        try:
            from db.accounting import AccountingAccount, LedgerTransaction, JournalEntry
            session = get_session()
            
            # Query for deposit transactions (credits to User Liabilities accounts)
            query = session.query(
                LedgerTransaction.credit.label('crypto_amount'),
                LedgerTransaction.created_at,
                JournalEntry.id.label('journal_entry_id')
            ).join(AccountingAccount, LedgerTransaction.account_id == AccountingAccount.id)\
             .join(JournalEntry, LedgerTransaction.journal_entry_id == JournalEntry.id)\
             .filter(
                AccountingAccount.name == f'User Liabilities - {currency}',
                LedgerTransaction.credit > 0  # Credits represent deposits
            ).order_by(LedgerTransaction.created_at)
            
            deposits = query.all()
            
            total_crypto_amount = 0.0
            total_cost_ugx = 0.0
            
            logger.info(f"Calculating adjusted cost base for {currency} from {len(deposits)} deposits")
            
            for deposit in deposits:
                try:
                    # The ledger stores amounts in standard decimal format (not smallest units)
                    crypto_amount = float(deposit.crypto_amount)
                    
                    # Find the corresponding transaction record to get stored price
                    transaction = session.query(Transaction).filter(
                        Transaction.journal_entry_id == deposit.journal_entry_id
                    ).first()
                    
                    price_ugx = None
                    if transaction and transaction.metadata_json:
                        # Try to get stored price from transaction metadata
                        price_key = f"{currency.lower()}_price_ugx_at_time"
                        if price_key in transaction.metadata_json:
                            price_ugx = float(transaction.metadata_json[price_key])
                            logger.info(f"Using stored price: {crypto_amount} {currency} at {price_ugx:.2f} UGX")
                    
                    # If no historical price, use current price as fallback for deposits
                    if price_ugx is None:
                        current_price_usd = self._get_current_price(currency)
                        if current_price_usd:
                            forex_service = ForexService()
                            usd_to_ugx = forex_service.get_exchange_rate('USD', 'UGX')
                            price_ugx = current_price_usd * usd_to_ugx
                            logger.warning(f"No stored price found for {currency} deposit - using current price: {price_ugx:.2f} UGX")
                    
                    if price_ugx and price_ugx > 0:
                        deposit_cost_ugx = crypto_amount * price_ugx
                        total_crypto_amount += crypto_amount
                        total_cost_ugx += deposit_cost_ugx
                        
                        logger.info(f"Added to cost base: {crypto_amount} {currency} at {price_ugx:.2f} UGX = {deposit_cost_ugx:.2f} UGX")
                    
                except Exception as e:
                    logger.error(f"Error processing deposit: {e}")
                    continue
            
            # Calculate weighted average cost per unit
            average_cost_per_unit = total_cost_ugx / total_crypto_amount if total_crypto_amount > 0 else 0.0
            
            logger.info(f"Adjusted cost base for {currency}: {total_cost_ugx:.2f} UGX for {total_crypto_amount} units = {average_cost_per_unit:.2f} UGX per unit")
            
            return total_cost_ugx, average_cost_per_unit
            
        except Exception as e:
            logger.error(f"Error calculating adjusted cost base: {e}")
            return 0.0, 0.0
    
    def calculate_pnl(self, user_id: int, currency: str = None) -> Dict[str, float]:
        """
        Calculate PnL for a user's crypto holdings using ledger_transactions
        
        Args:
            user_id: User ID
            currency: Optional currency filter (e.g., 'ETH', 'BTC')
            
        Returns:
            Dict with PnL calculations
        """
        try:
            # Get current holdings from ledger transactions
            current_holdings = self._get_current_holdings_from_ledger(user_id, currency)
            
            if not current_holdings:
                return {
                    'total_pnl_ugx': 0.0,
                    'total_pnl_usd': 0.0,
                    'holdings': {},
                    'cost_basis_ugx': 0.0,
                    'current_value_ugx': 0.0,
                    'current_value_usd': 0.0
                }
            
            # Calculate cost basis from ledger transactions using stored prices
            cost_basis_ugx = self._get_cost_basis_from_ledger(user_id, currency)
            
            # Calculate current market value
            current_value_ugx = 0.0
            current_value_usd = 0.0
            holdings_detail = {}
            
            for crypto_currency, amount in current_holdings.items():
                if amount <= 0:
                    continue
                    
                try:
                    # Get current price
                    current_price_usd = get_crypto_price(crypto_currency)
                    if current_price_usd and current_price_usd > 0:
                        current_price_ugx = current_price_usd * self.usd_to_ugx_rate
                        
                        crypto_value_usd = amount * current_price_usd
                        crypto_value_ugx = amount * current_price_ugx
                        
                        current_value_usd += crypto_value_usd
                        current_value_ugx += crypto_value_ugx
                        
                        holdings_detail[crypto_currency] = {
                            'amount': amount,
                            'current_price_usd': current_price_usd,
                            'current_price_ugx': current_price_ugx,
                            'value_usd': crypto_value_usd,
                            'value_ugx': crypto_value_ugx
                        }
                        
                        logger.info(f"{crypto_currency}: {amount} @ ${current_price_usd} = ${crypto_value_usd:.2f}")
                    
                except Exception as e:
                    logger.warning(f"Failed to get price for {crypto_currency}: {e}")
            
            # Calculate PnL
            pnl_ugx = current_value_ugx - cost_basis_ugx
            pnl_usd = current_value_usd - (cost_basis_ugx / self.usd_to_ugx_rate)
            
            result = {
                'total_pnl_ugx': pnl_ugx,
                'total_pnl_usd': pnl_usd,
                'holdings': holdings_detail,
                'cost_basis_ugx': cost_basis_ugx,
                'current_value_ugx': current_value_ugx,
                'current_value_usd': current_value_usd,
                'usd_to_ugx_rate': self.usd_to_ugx_rate,
                'data_source': 'ledger_transactions'
            }
            
            logger.info(f"PnL Summary (from ledger_transactions) - Cost Basis: {cost_basis_ugx:,.2f} UGX, Current Value: {current_value_ugx:,.2f} UGX, PnL: {pnl_ugx:,.2f} UGX")
            
            return result
            
        except Exception as e:
            logger.error(f"Error calculating PnL from ledger: {e}")
            return {
                'total_pnl_ugx': 0.0,
                'total_pnl_usd': 0.0,
                'holdings': {},
                'cost_basis_ugx': 0.0,
                'current_value_ugx': 0.0,
                'current_value_usd': 0.0,
                'error': str(e),
                'data_source': 'ledger_transactions'
            }
