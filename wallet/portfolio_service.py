"""
Portfolio Service for Aggregation and Analysis

This service is responsible for calculating and maintaining portfolio values
based on account balances and ledger entries.
"""
import logging
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func, desc, text

from db.wallet import (
    Account, PortfolioSnapshot, LedgerEntry, TransactionType, AccountType
)
from shared.crypto.price_cache_service import get_price_cache_service
from shared.fiat.fiat_fx_service import get_fiat_fx_service

logger = logging.getLogger(__name__)

logger = logging.getLogger(__name__)


class PortfolioService:
    """Service for portfolio aggregation and analysis"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def get_dashboard_summary(self, user_id: int) -> Dict:
        """Get a lightweight dashboard summary."""
        try:
            # Get current portfolio value and 24h change
            current_portfolio = self._calculate_current_portfolio(user_id)

            # Get recent transactions for activity feed
            recent_transactions = self._get_recent_transactions(user_id, limit=5)

            return {
                "user_id": user_id,
                "total_portfolio_value": current_portfolio.get("total_value_usd", 0),
                "portfolio_change_24h_pct": current_portfolio.get("change_24h_pct", 0),
                "total_assets": current_portfolio.get("total_assets", 0),
                "recent_activity": recent_transactions,
                "last_updated": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to get dashboard summary for user {user_id}: {e}")
            raise

    def get_portfolio_summary(self, user_id: int) -> Dict:
        """Get comprehensive portfolio summary with current values and changes"""
        try:
            # Get current portfolio value
            current_portfolio = self._calculate_current_portfolio(user_id)
            
            # Get historical snapshots
            snapshots = self._get_recent_snapshots(user_id)
            
            # Get recent transactions
            recent_transactions = self._get_recent_transactions(user_id)
            
            return {
                "user_id": user_id,
                "current_portfolio": current_portfolio,
                "historical_snapshots": snapshots,
                "recent_transactions": recent_transactions,
                "last_updated": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get portfolio summary for user {user_id}: {e}")
            raise
    
    def get_portfolio_analysis(self, user_id: int, period: str = "30d") -> Dict:
        """Get detailed portfolio analysis for specified period"""
        try:
            # Parse period
            end_date = date.today()
            if period == "24h":
                start_date = end_date - timedelta(days=1)
            elif period == "7d":
                start_date = end_date - timedelta(days=7)
            elif period == "30d":
                start_date = end_date - timedelta(days=30)
            elif period == "90d":
                start_date = end_date - timedelta(days=90)
            else:
                raise ValueError("Invalid period. Use: 24h, 7d, 30d, or 90d")
            
            # Get portfolio snapshots for the period
            snapshots = self._get_snapshots_for_period(user_id, start_date, end_date)
            
            # Get ledger entries for the period
            ledger_entries = self._get_ledger_entries_for_period(user_id, start_date, end_date)
            
            # Calculate performance metrics
            performance_metrics = self._calculate_performance_metrics_from_snapshots(snapshots, ledger_entries)
            
            # Get asset allocation
            asset_allocation = self._get_asset_allocation(user_id)
            
            return {
                "user_id": user_id,
                "period": period,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "snapshots": snapshots,
                "ledger_entries": ledger_entries,
                "performance_metrics": performance_metrics,
                "asset_allocation": asset_allocation
            }
            
        except Exception as e:
            logger.error(f"Failed to get portfolio analysis for user {user_id}: {e}")
            raise
    
    def get_ledger_history(self, user_id: int, currency: str = None, limit: int = 100) -> Dict:
        """Get ledger history for user with optional currency filter"""
        try:
            query = self.session.query(LedgerEntry).filter(LedgerEntry.user_id == user_id)
            
            if currency:
                query = query.filter(LedgerEntry.currency == currency.upper())
            
            # Get total count for pagination
            total_count = query.count()
            
            # Get ledger entries with pagination
            ledger_entries = query.order_by(desc(LedgerEntry.created_at)).limit(limit).all()
            
            # Format entries
            formatted_entries = []
            for entry in ledger_entries:
                formatted_entries.append({
                    "id": entry.id,
                    "transaction_id": entry.transaction_id,
                    "amount": float(entry.amount),
                    "currency": entry.currency,
                    "entry_type": entry.entry_type,
                    "transaction_type": entry.transaction_type.value,
                    "balance_before": float(entry.balance_before),
                    "balance_after": float(entry.balance_after),
                    "price_usd": float(entry.price_usd) if entry.price_usd else None,
                    "description": entry.description,
                    "reference_id": entry.reference_id,
                    "created_at": entry.created_at.isoformat()
                })
            
            return {
                "user_id": user_id,
                "currency": currency,
                "total_count": total_count,
                "entries": formatted_entries,
                "limit": limit
            }
            
        except Exception as e:
            logger.error(f"Failed to get ledger history for user {user_id}: {e}")
            raise
    
    def _calculate_current_portfolio(self, user_id: int) -> Dict[str, Any]:
        """Calculate current portfolio value and composition based on account balances.
        
        This method:
        1. Gets all user accounts with their current balances
        2. Converts all balances to USD using appropriate rates
        3. Tracks the source of each balance (account type, ledger entries)
        
        Returns:
            Dict containing portfolio summary and asset details
        """
        # Initialize services
        price_service = get_price_cache_service()
        fx_service = get_fiat_fx_service()
        
        # Get all user accounts with non-zero balances
        accounts = (
            self.session.query(Account)
            .options(joinedload(Account.transactions))
            .filter(
                Account.user_id == user_id,
                Account.currency.isnot(None),
                # Exclude reserve accounts from portfolio calculation
                or_(Account.label.is_(None), ~Account.label.startswith("RESERVE_")),
                or_(
                    and_(
                        Account.account_type == AccountType.CRYPTO,
                        Account.crypto_balance_smallest_unit > 0
                    ),
                    and_(
                        Account.account_type == AccountType.FIAT,
                        Account.balance > 0
                    )
                )
            )
            .all()
        )
        
        if not accounts:
            return {
                'total_value_usd': 0.0,
                'asset_details': {},
                'last_updated': datetime.utcnow().isoformat(),
                'currency_count': 0
            }
        
        # Get account IDs for ledger query
        account_ids = [acc.id for acc in accounts]
        
        # Get the latest ledger entry for each account
        latest_ledger_entries = {
            le.account_id: le for le in self.session.query(LedgerEntry)
            .filter(
                LedgerEntry.user_id == user_id,
                LedgerEntry.account_id.in_(account_ids)
            )
            .order_by(LedgerEntry.account_id, LedgerEntry.created_at.desc())
            .distinct(LedgerEntry.account_id)
            .all()
        }
        
        total_value_usd = 0.0
        asset_details = {}
        price_cache: Dict[str, float] = {}
        currency_count = 0  # Initialize currency counter
        
        for account in accounts:
            currency = account.currency.upper()
            
            # Get the current balance from the account
            balance = self._get_account_balance(account, currency)
            
            if balance <= 0:
                continue
                
            # Get USD value and price
            value_usd = 0.0
            price_usd = 0.0
            
            try:
                # Get price from cache or service
                if currency not in price_cache:
                    if account.account_type == AccountType.CRYPTO:
                        price_usd = price_service.get_price_with_fallback(currency) or 0.0
                    else:
                        price_usd = fx_service.get_rate_to_usd(currency) if currency != 'USD' else 1.0
                    price_cache[currency] = price_usd
                else:
                    price_usd = price_cache[currency]
                
                # Calculate USD value
                if account.account_type == AccountType.CRYPTO:
                    value_usd = balance * price_usd
                else:
                    value_usd = fx_service.convert_to_usd(balance, currency)
                
                # Get the latest ledger entry for this account
                ledger_entry = latest_ledger_entries.get(account.id)
                last_updated = ledger_entry.created_at if ledger_entry else account.updated_at
                
                # Add to asset details
                asset_details[currency] = {
                    'balance': balance,
                    'price_usd': price_usd,
                    'value_usd': value_usd,
                    'percentage': 0.0,  # Will be calculated below
                    'type': 'crypto' if account.account_type == AccountType.CRYPTO else 'fiat',
                    'account_id': account.id,
                    'last_updated': last_updated.isoformat() if last_updated else None,
                    'ledger_entry_id': ledger_entry.id if ledger_entry else None
                }
                
                total_value_usd += value_usd
                currency_count += 1  # Increment for each valid account with balance
                
            except Exception as e:
                logger.error(
                    f"Error calculating value for {currency} account {account.id}: {e}",
                    extra={
                        "user_id": user_id,
                        "account_id": account.id,
                        "currency": currency,
                        "account_type": account.account_type.value,
                        "balance": balance
                    },
                    exc_info=True
                )
                continue
        
        # Calculate percentages
        if total_value_usd > 0:
            for currency in asset_details:
                asset_details[currency]['percentage'] = (asset_details[currency]['value_usd'] / total_value_usd) * 100
        
        return {
            'total_value_usd': total_value_usd,
            'currency_count': currency_count,
            'asset_details': asset_details
        }
    
    def _get_recent_snapshots(self, user_id: int, limit: int = 10) -> List[Dict]:
        """Get recent portfolio snapshots"""
        snapshots = self.session.query(PortfolioSnapshot).filter(
            PortfolioSnapshot.user_id == user_id
        ).order_by(desc(PortfolioSnapshot.snapshot_date)).limit(limit).all()
        
        formatted_snapshots = []
        for snapshot in snapshots:
            formatted_snapshots.append({
                "id": snapshot.id,
                "snapshot_type": snapshot.snapshot_type,
                "snapshot_date": snapshot.snapshot_date.isoformat(),
                "total_value_usd": float(snapshot.total_value_usd),
                "total_change_24h": float(snapshot.total_change_24h) if snapshot.total_change_24h else 0.0,
                "total_change_7d": float(snapshot.total_change_7d) if snapshot.total_change_7d else 0.0,
                "total_change_30d": float(snapshot.total_change_30d) if snapshot.total_change_30d else 0.0,
                "change_percent_24h": float(snapshot.change_percent_24h) if snapshot.change_percent_24h else 0.0,
                "change_percent_7d": float(snapshot.change_percent_7d) if snapshot.change_percent_7d else 0.0,
                "change_percent_30d": float(snapshot.change_percent_30d) if snapshot.change_percent_30d else 0.0,
                "currency_count": snapshot.currency_count,
                "asset_details": snapshot.asset_details or {}
            })
        
        return formatted_snapshots
    
    def _get_recent_transactions(self, user_id: int, limit: int = 20) -> List[Dict]:
        """Get recent transactions for portfolio context"""
        # Get recent ledger entries
        ledger_entries = self.session.query(LedgerEntry).filter(
            LedgerEntry.user_id == user_id
        ).order_by(desc(LedgerEntry.created_at)).limit(limit).all()
        
        formatted_transactions = []
        for entry in ledger_entries:
            formatted_transactions.append({
                "id": entry.id,
                "transaction_id": entry.transaction_id,
                "amount": float(entry.amount),
                "currency": entry.currency,
                "entry_type": entry.entry_type,
                "transaction_type": entry.transaction_type.value,
                "description": entry.description,
                "price_usd": float(entry.price_usd) if entry.price_usd else None,
                "created_at": entry.created_at.isoformat()
            })
        
        return formatted_transactions
    
    def _get_snapshots_for_period(self, user_id: int, start_date: date, end_date: date) -> List[Dict]:
        """Get portfolio snapshots for a specific period"""
        snapshots = self.session.query(PortfolioSnapshot).filter(
            and_(
                PortfolioSnapshot.user_id == user_id,
                PortfolioSnapshot.snapshot_date >= start_date,
                PortfolioSnapshot.snapshot_date <= end_date
            )
        ).order_by(PortfolioSnapshot.snapshot_date).all()
        
        formatted_snapshots = []
        for snapshot in snapshots:
            formatted_snapshots.append({
                "date": snapshot.snapshot_date.isoformat(),
                "total_value_usd": float(snapshot.total_value_usd),
                "change_24h": float(snapshot.total_change_24h) if snapshot.total_change_24h else 0.0,
                "change_percent_24h": float(snapshot.change_percent_24h) if snapshot.change_percent_24h else 0.0
            })
        
        return formatted_snapshots
    
    def _get_ledger_entries_for_period(self, user_id: int, start_date: date, end_date: date) -> List[Dict]:
        """Get ledger entries for a specific period"""
        entries = self.session.query(LedgerEntry).filter(
            and_(
                LedgerEntry.user_id == user_id,
                LedgerEntry.created_at >= datetime.combine(start_date, datetime.min.time()),
                LedgerEntry.created_at <= datetime.combine(end_date, datetime.max.time())
            )
        ).order_by(LedgerEntry.created_at).all()
        
        formatted_entries = []
        for entry in entries:
            formatted_entries.append({
                "id": entry.id,
                "amount": float(entry.amount),
                "currency": entry.currency,
                "entry_type": entry.entry_type,
                "transaction_type": entry.transaction_type.value,
                "description": entry.description,
                "price_usd": float(entry.price_usd) if entry.price_usd else None,
                "created_at": entry.created_at.isoformat()
            })
        
        return formatted_entries
    
    def _calculate_performance_metrics_from_snapshots(self, snapshots: List[Dict], ledger_entries: List[Dict]) -> Dict:
        """Calculate performance metrics from snapshots and ledger entries"""
        if not snapshots:
            return {
                "total_return": 0.0,
                "total_return_percent": 0.0,
                "volatility": 0.0,
                "best_day": None,
                "worst_day": None
            }
        
        # Calculate total return
        first_value = snapshots[0]['total_value_usd']
        last_value = snapshots[-1]['total_value_usd']
        total_return = last_value - first_value
        total_return_percent = (total_return / first_value * 100) if first_value > 0 else 0.0
        
        # Calculate daily returns for volatility
        daily_returns = []
        for i in range(1, len(snapshots)):
            prev_value = snapshots[i-1]['total_value_usd']
            curr_value = snapshots[i]['total_value_usd']
            if prev_value > 0:
                daily_return = (curr_value - prev_value) / prev_value
                daily_returns.append(daily_return)
        
        # Calculate volatility (standard deviation of daily returns)
        volatility = 0.0
        if daily_returns:
            mean_return = sum(daily_returns) / len(daily_returns)
            variance = sum((r - mean_return) ** 2 for r in daily_returns) / len(daily_returns)
            volatility = variance ** 0.5
        
        # Find best and worst days
        best_day = None
        worst_day = None
        if snapshots:
            best_day = max(snapshots, key=lambda x: x['change_24h'])
            worst_day = min(snapshots, key=lambda x: x['change_24h'])
        
        return {
            "total_return": total_return,
            "total_return_percent": total_return_percent,
            "volatility": volatility,
            "best_day": best_day,
            "worst_day": worst_day,
            "days_analyzed": len(snapshots)
        }
    
    def _get_asset_allocation(self, user_id: int) -> Dict:
        """Get current asset allocation breakdown"""
        current_portfolio = self._calculate_current_portfolio(user_id)
        asset_details = current_portfolio.get('asset_details', {})
        
        # Group by asset type
        allocation = {
            "crypto": {"total_value_usd": 0.0, "assets": {}},
            "fiat": {"total_value_usd": 0.0, "assets": {}}
        }
        
        for currency, details in asset_details.items():
            if details.get('type') == 'crypto':
                allocation["crypto"]["total_value_usd"] += details['value_usd']
                allocation["crypto"]["assets"][currency] = details
            else:
                allocation["fiat"]["total_value_usd"] += details['value_usd']
                allocation["fiat"]["assets"][currency] = details
        
        # Calculate percentages for each asset type
        total_value = current_portfolio['total_value_usd']
        if total_value > 0:
            allocation["crypto"]["percentage"] = (allocation["crypto"]["total_value_usd"] / total_value) * 100
            allocation["fiat"]["percentage"] = (allocation["fiat"]["total_value_usd"] / total_value) * 100
        else:
            allocation["crypto"]["percentage"] = 0.0
            allocation["fiat"]["percentage"] = 0.0
        
        return allocation
    
    def _get_account_balance(self, account: Account, currency: str) -> float:
        """Get available balance for an account.
        
        This method ensures we're always working with the correct
        balance field based on account type and handles any necessary conversions.
        """
        try:
            if account.account_type == AccountType.CRYPTO:
                if account.crypto_balance_smallest_unit is not None:
                    return float(account._convert_smallest_to_standard(account.crypto_balance_smallest_unit))
                return 0.0
            return float(account.balance or 0)
        except Exception as e:
            logger.error(
                f"Error getting balance for account {account.id} ({currency}): {e}",
                extra={
                    "account_id": account.id,
                    "currency": currency,
                    "account_type": account.account_type.value
                },
                exc_info=True
            )
            return 0.0
    
    def _get_historical_portfolio_snapshots(
        self, 
        user_id: int, 
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """Get historical portfolio snapshots for the specified time period.
        
        Args:
            user_id: The user ID to get snapshots for
            days: Number of days of history to retrieve
            
        Returns:
            List of portfolio snapshots with daily values
        """
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=days)
        
        try:
            # Get all snapshots for the date range
            snapshots = (
                self.session.query(PortfolioSnapshot)
                .filter(
                    PortfolioSnapshot.user_id == user_id,
                    PortfolioSnapshot.snapshot_date >= start_date,
                    PortfolioSnapshot.snapshot_date <= end_date,
                    PortfolioSnapshot.snapshot_type == 'daily'
                )
                .order_by(PortfolioSnapshot.snapshot_date.asc())
                .all()
            )
            
            # Convert snapshots to dict format
            result = []
            for snapshot in snapshots:
                result.append({
                    'date': snapshot.snapshot_date.isoformat(),
                    'total_value_usd': float(snapshot.total_value_usd),
                    'asset_details': snapshot.asset_details or {},
                    'change_24h': float(snapshot.change_percent_24h) if snapshot.change_percent_24h else 0.0,
                    'change_7d': float(snapshot.change_percent_7d) if snapshot.change_percent_7d else 0.0,
                    'change_30d': float(snapshot.change_percent_30d) if snapshot.change_percent_30d else 0.0
                })
            
            return result
            
        except Exception as e:
            logger.error(
                f"Error getting historical portfolio snapshots for user {user_id}: {e}",
                exc_info=True
            )
            return []
    
    def _calculate_performance_metrics(
        self,
        portfolio: Dict[str, Any],
        historical_data: List[Dict[str, Any]],
        days: int = 30
    ) -> Dict[str, Any]:
        """Calculate performance metrics for the portfolio.
        
        Args:
            portfolio: Current portfolio data
            historical_data: List of historical portfolio snapshots
            days: Number of days to calculate metrics for
            
        Returns:
            Dict containing performance metrics
        """
        if not historical_data or len(historical_data) < 2:
            return {
                'daily_change': 0.0,
                'weekly_change': 0.0,
                'monthly_change': 0.0,
                'all_time_high': portfolio.get('total_value_usd', 0.0),
                'all_time_low': portfolio.get('total_value_usd', 0.0),
                'volatility_30d': 0.0
            }
        
        # Sort historical data by date
        historical_data_sorted = sorted(historical_data, key=lambda x: x['date'])
        
        # Get values for different time periods
        current_value = portfolio.get('total_value_usd', 0.0)
        
        # Calculate daily change
        daily_change = 0.0
        if len(historical_data_sorted) >= 2:
            prev_day_value = historical_data_sorted[-2].get('total_value_usd', current_value)
            if prev_day_value > 0:
                daily_change = ((current_value - prev_day_value) / prev_day_value) * 100
        
        # Calculate weekly change (7 days)
        weekly_change = 0.0
        if len(historical_data_sorted) >= 8:
            week_ago_value = historical_data_sorted[-8].get('total_value_usd', current_value)
            if week_ago_value > 0:
                weekly_change = ((current_value - week_ago_value) / week_ago_value) * 100
        
        # Calculate monthly change (30 days)
        monthly_change = 0.0
        if len(historical_data_sorted) >= 30:
            month_ago_value = historical_data_sorted[-30].get('total_value_usd', current_value)
            if month_ago_value > 0:
                monthly_change = ((current_value - month_ago_value) / month_ago_value) * 100
        
        # Calculate all-time high/low
        values = [d['total_value_usd'] for d in historical_data_sorted]
        all_time_high = max(values) if values else current_value
        all_time_low = min(values) if values else current_value
        
        # Calculate 30-day volatility (standard deviation of daily returns)
        volatility_30d = 0.0
        if len(historical_data_sorted) >= 2:
            returns = []
            for i in range(1, min(30, len(historical_data_sorted))):
                prev_value = historical_data_sorted[i-1]['total_value_usd']
                curr_value = historical_data_sorted[i]['total_value_usd']
                if prev_value > 0:
                    returns.append((curr_value - prev_value) / prev_value)
            
            if returns:
                import numpy as np
                volatility_30d = np.std(returns) * 100  # as percentage
        
        return {
            'daily_change': round(daily_change, 4),
            'weekly_change': round(weekly_change, 4),
            'monthly_change': round(monthly_change, 4),
            'all_time_high': round(all_time_high, 2),
            'all_time_low': round(all_time_low, 2),
            'volatility_30d': round(volatility_30d, 4)
        }
    
    def _is_crypto_currency(self, currency: str) -> bool:
        """Check if currency is crypto.
        
        Note: This is a legacy method kept for backward compatibility.
        We now use account_type from the Account model instead of hardcoded lists.
        """
        return False


def get_portfolio_summary(session: Session, user_id: int) -> Dict:
    """Get portfolio summary for a user.
    
    This function provides a comprehensive view of the user's portfolio,
    including current balances, values in USD, and historical performance.
    
    Args:
        session: Database session
        user_id: ID of the user to get the portfolio for
        
    Returns:
        Dict containing portfolio summary with current values and historical data
    """
    service = PortfolioService(session)
    
    # Get current portfolio
    portfolio = service._calculate_current_portfolio(user_id)
    
    # Add historical data (last 30 days)
    historical_data = service._get_historical_portfolio_snapshots(user_id, days=30)
    
    # Calculate performance metrics
    performance = service._calculate_performance_metrics(portfolio, historical_data)
    
    # Combine all data
    result = {
        'total_value_usd': portfolio.get('total_value_usd', 0.0),
        'currency_count': portfolio.get('currency_count', 0),
        'last_updated': datetime.utcnow().isoformat(),
        'assets': portfolio.get('asset_details', {}),
        'historical_data': historical_data,
        'performance': performance
    }
    
    return result


def get_portfolio_analysis(session: Session, user_id: int, period: str = "30d") -> Dict:
    """Convenience function for portfolio analysis"""
    service = PortfolioService(session)
    return service.get_portfolio_analysis(user_id, period)


def get_ledger_history(session: Session, user_id: int, currency: str = None, limit: int = 100) -> Dict:
    """Convenience function for ledger history"""
    service = PortfolioService(session)
    return service.get_ledger_history(user_id, currency, limit)

def get_dashboard_summary(session: Session, user_id: int) -> Dict:
    """Convenience function for dashboard summary"""
    service = PortfolioService(session)
    return service.get_dashboard_summary(user_id)
