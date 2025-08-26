"""
Solana Webhook Integration with Notification System
Handles Solana transaction notifications via webhooks
"""
import sys
import os
import logging
from decimal import Decimal
from typing import Optional, Dict, Any
from shared.crypto.price_utils import get_crypto_price
from shared.fiat.forex_service import forex_service
from flask import Flask, request, jsonify
import json

# Add paths for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'shared'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'db'))

try:
    from shared.notification_service import notification_service
    from db.connection import session
    from db.wallet import Account, CryptoAddress
except ImportError as e:
    logger.warning(f"Import warning in solana_webhook_integration: {e}")
    # Create mock objects for graceful degradation
    notification_service = None
    session = None
    Account = None
    CryptoAddress = None

logger = logging.getLogger(__name__)

class SolanaNotificationService:
    """Service for handling Solana transaction notifications"""
    
    def __init__(self):
        # Use real-time prices with fallbacks
        try:
            self.sol_price_usd = Decimal(str(get_crypto_price('SOL') or 20))
            self.usd_to_ugx_rate = Decimal(str(forex_service.get_exchange_rate('usd', 'ugx')))
        except Exception:
            self.sol_price_usd = Decimal('20')  # Fallback SOL price
            self.usd_to_ugx_rate = Decimal('3700')  # Fallback exchange rate
    
    def process_webhook_transaction(self, webhook_data: Dict[str, Any]):
        """Process incoming Solana webhook transaction"""
        try:
            # Extract transaction data from webhook
            transaction = webhook_data.get('transaction', {})
            tx_hash = transaction.get('signature')
            
            if not tx_hash:
                logger.warning("No transaction signature in webhook data")
                return False
            
            # Extract account changes to determine deposits/withdrawals
            account_data = webhook_data.get('accountData', [])
            
            for account_change in account_data:
                account_address = account_change.get('account')
                native_balance_change = account_change.get('nativeBalanceChange', 0)
                
                if native_balance_change == 0:
                    continue
                
                # Convert lamports to SOL
                sol_amount = Decimal(abs(native_balance_change)) / Decimal(10**9)
                
                # Find user account for this address
                user_id = self._get_user_id_for_address(account_address)
                if not user_id:
                    continue
                
                # Determine if this is a deposit or withdrawal
                if native_balance_change > 0:
                    # Deposit
                    self.send_deposit_notification(
                        user_id=user_id,
                        transaction_hash=tx_hash,
                        amount=sol_amount,
                        wallet_address=account_address,
                        slot=transaction.get('slot'),
                        confirmations=1  # Solana transactions are confirmed when included in block
                    )
                else:
                    # Withdrawal
                    self.send_withdrawal_notification(
                        user_id=user_id,
                        transaction_hash=tx_hash,
                        amount=sol_amount,
                        destination_address=account_address
                    )
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error processing Solana webhook: {e}")
            return False
    
    def _get_user_id_for_address(self, address: str) -> Optional[int]:
        """Get user ID for a Solana address"""
        try:
            if not session or not CryptoAddress or not Account:
                logger.warning("Database dependencies not available")
                return None
                
            crypto_address = session.query(CryptoAddress).filter(
                CryptoAddress.address.ilike(address),
                CryptoAddress.is_active == True
            ).first()
            
            if crypto_address:
                account = session.query(Account).filter_by(id=crypto_address.account_id).first()
                return account.user_id if account else None
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error getting user ID for address {address}: {e}")
            return None
    
    def send_deposit_notification(
        self,
        user_id: int,
        transaction_hash: str,
        amount: Decimal,
        wallet_address: str,
        slot: Optional[int] = None,
        confirmations: int = 1,
        transaction_id: Optional[int] = None
    ):
        """Send Solana deposit notification"""
        try:
            if not notification_service:
                logger.warning("Notification service not available")
                return False
                
            amount_usd = amount * self.sol_price_usd
            amount_ugx = amount_usd * self.usd_to_ugx_rate
            
            notification_service.send_deposit_notification(
                user_id=user_id,
                transaction_hash=transaction_hash,
                crypto_symbol='SOL',
                amount=amount,
                amount_usd=amount_usd,
                amount_ugx=amount_ugx,
                wallet_address=wallet_address,
                block_number=slot,
                confirmations=confirmations,
                status='confirmed',  # Solana transactions are confirmed when included
                transaction_id=transaction_id
            )
            
            logger.info(f"📢 SOL deposit notification sent for user {user_id}: {amount} SOL")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error sending SOL deposit notification: {e}")
            return False
    
    def send_withdrawal_notification(
        self,
        user_id: int,
        transaction_hash: str,
        amount: Decimal,
        destination_address: str,
        transaction_id: Optional[int] = None
    ):
        """Send Solana withdrawal notification"""
        try:
            if not notification_service:
                logger.warning("Notification service not available")
                return False
                
            amount_usd = amount * self.sol_price_usd
            amount_ugx = amount_usd * self.usd_to_ugx_rate
            
            notification_service.send_withdrawal_notification(
                user_id=user_id,
                transaction_hash=transaction_hash,
                crypto_symbol='SOL',
                amount=amount,
                amount_usd=amount_usd,
                amount_ugx=amount_ugx,
                destination_address=destination_address,
                status='confirmed',
                transaction_id=transaction_id
            )
            
            logger.info(f"📢 SOL withdrawal notification sent for user {user_id}: {amount} SOL")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error sending SOL withdrawal notification: {e}")
            return False

# Global instance
solana_notification_service = SolanaNotificationService()

# Flask app for webhook endpoint
app = Flask(__name__)

@app.route('/webhook/solana', methods=['POST'])
def solana_webhook():
    """Solana webhook endpoint"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        success = solana_notification_service.process_webhook_transaction(data)
        
        if success:
            return jsonify({'status': 'success', 'message': 'Transaction processed'})
        else:
            return jsonify({'status': 'error', 'message': 'Failed to process transaction'}), 500
            
    except Exception as e:
        logger.error(f"❌ Error in Solana webhook: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
