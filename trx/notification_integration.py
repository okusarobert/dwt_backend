"""
TRX Monitor Notification Integration
Integrates TRX transaction monitoring with the notification system
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

class TRXNotificationService:
    """Service for sending TRX transaction notifications"""
    
    def __init__(self):
        # Use real-time prices with fallbacks
        try:
            self.trx_price_usd = Decimal(str(get_crypto_price('TRX') or 0.08))
            self.usd_to_ugx_rate = Decimal(str(forex_service.get_exchange_rate('usd', 'ugx')))
        except Exception:
            self.trx_price_usd = Decimal('0.08')  # Fallback TRX price
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
        """Send TRX deposit notification"""
        try:
            amount_usd = amount * self.trx_price_usd
            amount_ugx = amount_usd * self.usd_to_ugx_rate
            
            notification_service.send_deposit_notification(
                user_id=user_id,
                transaction_hash=transaction_hash,
                crypto_symbol='TRX',
                amount=amount,
                amount_usd=amount_usd,
                amount_ugx=amount_ugx,
                wallet_address=wallet_address,
                block_number=block_number,
                confirmations=confirmations,
                status='pending'
            )
            
            logger.info(f"📢 TRX deposit notification sent for user {user_id}: {amount} TRX")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error sending TRX deposit notification: {e}")
            return False
    
    def send_withdrawal_notification(
        self,
        user_id: int,
        transaction_hash: str,
        amount: Decimal,
        destination_address: str
    ):
        """Send TRX withdrawal notification"""
        try:
            amount_usd = amount * self.trx_price_usd
            amount_ugx = amount_usd * self.usd_to_ugx_rate
            
            notification_service.send_withdrawal_notification(
                user_id=user_id,
                transaction_hash=transaction_hash,
                crypto_symbol='TRX',
                amount=amount,
                amount_usd=amount_usd,
                amount_ugx=amount_ugx,
                destination_address=destination_address,
                status='pending'
            )
            
            logger.info(f"📢 TRX withdrawal notification sent for user {user_id}: {amount} TRX")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error sending TRX withdrawal notification: {e}")
            return False
    
    def send_confirmation_update(
        self,
        user_id: int,
        transaction_hash: str,
        confirmations: int,
        required_confirmations: int = 20,
        status: str = 'pending'
    ):
        """Send TRX confirmation update notification"""
        try:
            notification_service.send_confirmation_update(
                user_id=user_id,
                transaction_hash=transaction_hash,
                crypto_symbol='TRX',
                confirmations=confirmations,
                required_confirmations=required_confirmations,
                status=status
            )
            
            logger.info(f"📢 TRX confirmation update sent for user {user_id}: {confirmations}/{required_confirmations}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error sending TRX confirmation update: {e}")
            return False

# Global instance
trx_notification_service = TRXNotificationService()
