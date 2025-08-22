"""
ETH Monitor Notification Integration
Integrates ETH transaction monitoring with the notification system
"""
import sys
import os
import logging
from decimal import Decimal
from typing import Optional
from shared.crypto.price_utils import get_crypto_price
from shared.fiat.forex_service import forex_service

# Add paths for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'shared'))

from shared.notification_service import notification_service
from db.connection import get_session
from db.wallet import Account

logger = logging.getLogger(__name__)

class ETHNotificationService:
    """Service for sending ETH transaction notifications"""
    
    def __init__(self):
        # Use real-time prices with fallbacks
        try:
            self.eth_price_usd = Decimal(str(get_crypto_price('ETH') or 2400))
            self.usd_to_ugx_rate = Decimal(str(forex_service.get_exchange_rate('usd', 'ugx')))
        except Exception:
            self.eth_price_usd = Decimal('2400')  # Fallback ETH price
            self.usd_to_ugx_rate = Decimal('3700')  # Fallback exchange rate
    
    def send_deposit_notification(
        self,
        user_id: int,
        transaction_hash: str,
        amount: Decimal,
        wallet_address: str,
        block_number: Optional[int] = None,
        confirmations: int = 0
    ):
        """Send ETH deposit notification"""
        try:
            amount_usd = amount * self.eth_price_usd
            amount_ugx = amount_usd * self.usd_to_ugx_rate
            
            notification_service.send_deposit_notification(
                user_id=user_id,
                transaction_hash=transaction_hash,
                crypto_symbol='ETH',
                amount=amount,
                amount_usd=amount_usd,
                amount_ugx=amount_ugx,
                wallet_address=wallet_address,
                block_number=block_number,
                confirmations=confirmations,
                status='pending'
            )
            
            logger.info(f"📢 ETH deposit notification sent for user {user_id}: {amount} ETH")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error sending ETH deposit notification: {e}")
            return False
    
    def send_withdrawal_notification(
        self,
        user_id: int,
        transaction_hash: str,
        amount: Decimal,
        destination_address: str
    ):
        """Send ETH withdrawal notification"""
        try:
            amount_usd = amount * self.eth_price_usd
            amount_ugx = amount_usd * self.usd_to_ugx_rate
            
            notification_service.send_withdrawal_notification(
                user_id=user_id,
                transaction_hash=transaction_hash,
                crypto_symbol='ETH',
                amount=amount,
                amount_usd=amount_usd,
                amount_ugx=amount_ugx,
                destination_address=destination_address,
                status='pending'
            )
            
            logger.info(f"📢 ETH withdrawal notification sent for user {user_id}: {amount} ETH")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error sending ETH withdrawal notification: {e}")
            return False
    
    def send_confirmation_update(
        self,
        user_id: int,
        transaction_hash: str,
        confirmations: int,
        required_confirmations: int = 15,
        status: str = 'pending'
    ):
        """Send ETH confirmation update notification"""
        try:
            notification_service.send_confirmation_update(
                user_id=user_id,
                transaction_hash=transaction_hash,
                crypto_symbol='ETH',
                confirmations=confirmations,
                required_confirmations=required_confirmations,
                status=status
            )
            
            logger.info(f"📢 ETH confirmation update sent for user {user_id}: {confirmations}/{required_confirmations}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error sending ETH confirmation update: {e}")
            return False

# Global instance
eth_notification_service = ETHNotificationService()
