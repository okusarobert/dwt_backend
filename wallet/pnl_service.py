"""
PnL Service for Wallet API - Provides endpoints for ledger-based PnL calculations
"""
from flask import jsonify, g
from sqlalchemy.orm import Session
from shared.pnl_calculator import PnLCalculator
from db.connection import session
import logging
import asyncio

logger = logging.getLogger(__name__)

class WalletPnLService:
    """Service for handling PnL calculations in wallet API"""
    
    @staticmethod
    def get_user_pnl(user_id: int, currency: str = None, period_days: int = 1) -> dict:
        """
        Get PnL data for user based on actual transaction costs
        
        Args:
            user_id: User ID
            currency: Optional currency filter
            period_days: Period for PnL calculation (default 1 day)
            
        Returns:
            Dict with PnL data or error response
        """
        try:
            # session is already imported from db.connection
            calculator = PnLCalculator(session)
            
            # Run async method in event loop
            pnl_data = asyncio.run(calculator.calculate_user_pnl(
                user_id=user_id,
                currency=currency,
                period_days=period_days
            ))
            
            return {
                'success': True,
                'data': pnl_data
            }
            
        except Exception as e:
            logger.error(f"Error getting PnL for user {user_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'data': {
                    'period_days': period_days,
                    'realized_pnl': {'total_ugx': 0, 'total_usd': 0, 'trades': []},
                    'unrealized_pnl': {'total_ugx': 0, 'total_usd': 0, 'positions': []},
                    'total_pnl_ugx': 0,
                    'total_pnl_usd': 0,
                    'total_pnl_percentage': 0.0,
                    'cost_basis_ugx': 0,
                    'currency_breakdown': {}
                }
            }
    
    @staticmethod
    def get_portfolio_summary(user_id: int) -> dict:
        """
        Get portfolio summary with accurate PnL based on cost basis
        
        Args:
            user_id: User ID
            
        Returns:
            Dict with portfolio summary including accurate PnL
        """
        try:
            # session is already imported from db.connection
            calculator = PnLCalculator(session)
            
            # Get overall PnL for different periods
            daily_pnl = asyncio.run(calculator.calculate_user_pnl(user_id, period_days=1))
            weekly_pnl = asyncio.run(calculator.calculate_user_pnl(user_id, period_days=7))
            monthly_pnl = asyncio.run(calculator.calculate_user_pnl(user_id, period_days=30))
            
            # Get current positions
            positions = calculator._get_user_positions(user_id)
            
            # Calculate total portfolio value
            total_value_ugx = 0
            total_cost_basis = 0
            
            for position in positions:
                currency = position['currency']
                balance = position['balance']
                cost_basis = calculator._get_average_cost_basis(user_id, currency)
                current_price = asyncio.run(calculator._get_current_price(currency))
                
                total_value_ugx += balance * current_price
                total_cost_basis += balance * cost_basis
            
            return {
                'success': True,
                'data': {
                    'total_value_ugx': total_value_ugx,
                    'total_cost_basis_ugx': total_cost_basis,
                    'total_unrealized_pnl_ugx': total_value_ugx - total_cost_basis,
                    'total_unrealized_pnl_percentage': ((total_value_ugx - total_cost_basis) / total_cost_basis * 100) if total_cost_basis > 0 else 0,
                    'daily_pnl': daily_pnl,
                    'weekly_pnl': weekly_pnl,
                    'monthly_pnl': monthly_pnl,
                    'positions': positions,
                    'currency_breakdown': daily_pnl.get('currency_breakdown', {})
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting portfolio summary for user {user_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'data': {
                    'total_value_ugx': 0,
                    'total_cost_basis_ugx': 0,
                    'total_unrealized_pnl_ugx': 0,
                    'total_unrealized_pnl_percentage': 0,
                    'daily_pnl': {},
                    'weekly_pnl': {},
                    'monthly_pnl': {},
                    'positions': [],
                    'currency_breakdown': {}
                }
            }
