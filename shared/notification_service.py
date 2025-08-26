"""
Notification Service for Crypto Deposit Notifications
Handles sending notifications via Kafka for real-time delivery to users
"""
import json
import logging
from typing import Optional, Dict, Any
from decimal import Decimal
import uuid
from datetime import datetime
import redis
import os

logger = logging.getLogger(__name__)

class NotificationService:
    def __init__(self):
        # Initialize Redis connection
        redis_host = os.getenv('REDIS_HOST', 'redis')
        redis_port = int(os.getenv('REDIS_PORT', 6379))
        self.redis_client = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)
        self.notification_channel = "crypto_notifications"
    
    def send_deposit_notification(
        self,
        user_id: int,
        transaction_hash: str,
        crypto_symbol: str,
        amount: Decimal,
        amount_usd: Decimal,
        amount_ugx: Decimal,
        wallet_address: str,
        block_number: Optional[int] = None,
        confirmations: int = 0,
        status: str = "pending",
        transaction_id: Optional[int] = None
    ):
        """
        Send a crypto deposit notification to the user
        
        Args:
            user_id: ID of the user receiving the deposit
            transaction_hash: Blockchain transaction hash
            crypto_symbol: Symbol of the cryptocurrency (BTC, ETH, SOL, TRX, etc.)
            amount: Amount in crypto units
            amount_usd: USD equivalent value
            amount_ugx: UGX equivalent value
            wallet_address: Receiving wallet address
            block_number: Block number (if applicable)
            confirmations: Number of confirmations
            status: Transaction status (pending, confirmed, failed)
        """
        try:
            title = f"New {crypto_symbol} Deposit"
            message = f"You received {amount} {crypto_symbol} (≈ {amount_ugx:,.0f} UGX)"
            priority = "high" if amount_usd > 1000 else "normal"
            
            notification_message = {
                "message_id": str(uuid.uuid4()),
                "user_id": user_id,
                "type": "crypto_deposit",
                "timestamp": datetime.utcnow().isoformat(),
                "notification": {
                    "title": title,
                    "message": message,
                    "priority": priority,
                    "category": "deposit",
                    "action_url": f"/dashboard/transactions/{transaction_id}" if transaction_id else f"/dashboard/transactions?search={transaction_hash}"
                },
                "transaction": {
                    "hash": transaction_hash,
                    "crypto_symbol": crypto_symbol,
                    "amount": str(amount),
                    "amount_usd": str(amount_usd),
                    "amount_ugx": str(amount_ugx),
                    "wallet_address": wallet_address,
                    "block_number": block_number,
                    "confirmations": confirmations,
                    "status": status
                }
            }
            
            message_json = json.dumps(notification_message, default=str)
            logger.info(f"🔔 Publishing to Redis channel '{self.notification_channel}' for user {user_id}")
            logger.info(f"🔔 Message payload: {message_json}")
            
            result = self.redis_client.publish(
                self.notification_channel,
                message_json
            )
            
            logger.info(f"🔔 Redis publish result: {result} subscribers received the message")
            logger.info(f"Sent deposit notification for user {user_id}: {crypto_symbol} {amount}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send deposit notification: {e}")
            return False
    
    def send_withdrawal_notification(
        self,
        user_id: int,
        transaction_hash: str,
        crypto_symbol: str,
        amount: Decimal,
        amount_usd: Decimal,
        amount_ugx: Decimal,
        destination_address: str,
        status: str = "pending",
        transaction_id: Optional[int] = None
    ):
        """Send a crypto withdrawal notification to the user"""
        try:
            notification_data = {
                "type": "crypto_withdrawal",
                "user_id": user_id,
                "transaction": {
                    "hash": transaction_hash,
                    "crypto_symbol": crypto_symbol,
                    "amount": str(amount),
                    "amount_usd": str(amount_usd),
                    "amount_ugx": str(amount_ugx),
                    "destination_address": destination_address,
                    "status": status
                },
                "notification": {
                    "title": f"{crypto_symbol} Withdrawal",
                    "message": f"Withdrawal of {amount} {crypto_symbol} is {status}",
                    "priority": "high",
                    "category": "withdrawal",
                    "action_url": f"/dashboard/transactions/{transaction_id}" if transaction_id else f"/dashboard/transactions?search={transaction_hash}"
                },
                "timestamp": datetime.utcnow().isoformat(),
                "created_at": datetime.utcnow().isoformat()
            }
            
            self.redis_client.publish(
                self.notification_channel,
                json.dumps(notification_data, default=str)
            )
            logger.info(f"Sent withdrawal notification for user {user_id}: {crypto_symbol} {amount}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send withdrawal notification: {e}")
            return False
    
    def send_confirmation_update(
        self,
        user_id: int,
        transaction_hash: str,
        crypto_symbol: str,
        confirmations: int,
        required_confirmations: int,
        status: str,
        transaction_id: Optional[int] = None
    ):
        """Send confirmation update notification"""
        try:
            notification_data = {
                "type": "confirmation_update",
                "user_id": user_id,
                "transaction": {
                    "hash": transaction_hash,
                    "crypto_symbol": crypto_symbol,
                    "confirmations": confirmations,
                    "required_confirmations": required_confirmations,
                    "status": status
                },
                "notification": {
                    "title": f"{crypto_symbol} Transaction Update",
                    "message": f"Transaction has {confirmations}/{required_confirmations} confirmations",
                    "priority": "normal",
                    "category": "confirmation",
                    "action_url": f"/dashboard/transactions/{transaction_id}" if transaction_id else f"/dashboard/transactions?search={transaction_hash}"
                },
                "timestamp": datetime.utcnow().isoformat(),
                "created_at": datetime.utcnow().isoformat()
            }
            
            self.redis_client.publish(
                self.notification_channel,
                json.dumps(notification_data, default=str)
            )
            logger.info(f"Sent confirmation update for user {user_id}: {transaction_hash} - {confirmations}/{required_confirmations}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send confirmation update: {e}")
            return False

# Global instance
notification_service = NotificationService()
