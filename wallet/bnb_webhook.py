#!/usr/bin/env python3
"""
BNB Smart Chain Webhook Handler
Handles incoming BNB transaction notifications from Alchemy
"""

from flask import Blueprint, request, jsonify
import json
import hmac
import hashlib
from decouple import config
from shared.logger import setup_logging

logger = setup_logging()

bnb_webhook = Blueprint('bnb_webhook', __name__)

def verify_alchemy_signature(payload_body, signature_header):
    """Verify Alchemy webhook signature"""
    try:
        webhook_key = config('ALCHEMY_WEBHOOK_KEY', default='')
        if not webhook_key:
            logger.warning("⚠️ ALCHEMY_WEBHOOK_KEY not configured, skipping signature verification")
            return True
            
        # Alchemy sends signature as 'sha256=<signature>'
        if not signature_header.startswith('sha256='):
            logger.error("❌ Invalid signature format")
            return False
            
        signature = signature_header[7:]  # Remove 'sha256=' prefix
        
        # Calculate expected signature
        expected_signature = hmac.new(
            webhook_key.encode('utf-8'),
            payload_body,
            hashlib.sha256
        ).hexdigest()
        
        # Compare signatures
        is_valid = hmac.compare_digest(signature, expected_signature)
        
        if is_valid:
            logger.info("✅ BNB webhook signature verified")
        else:
            logger.error("❌ BNB webhook signature verification failed")
            
        return is_valid
        
    except Exception as e:
        logger.error(f"❌ Error verifying BNB webhook signature: {e}")
        return False

@bnb_webhook.route('/wallet/bnb/callbacks/address-webhook', methods=['POST'])
def handle_bnb_webhook():
    """Handle BNB Smart Chain transaction webhooks from Alchemy"""
    try:
        # Get raw payload for signature verification
        payload_body = request.get_data()
        signature_header = request.headers.get('X-Alchemy-Signature', '')
        
        # Verify signature if enabled
        verify_signature = config('VERIFY_ALCHEMY_SIGNATURE', default='true').lower() == 'true'
        if verify_signature and not verify_alchemy_signature(payload_body, signature_header):
            return jsonify({"error": "Invalid signature"}), 401
        
        # Parse JSON payload
        try:
            data = json.loads(payload_body.decode('utf-8'))
        except json.JSONDecodeError as e:
            logger.error(f"❌ Invalid JSON in BNB webhook: {e}")
            return jsonify({"error": "Invalid JSON"}), 400
        
        logger.info(f"📨 Received BNB webhook: {json.dumps(data, indent=2)}")
        
        # Extract webhook type and event data
        webhook_type = data.get('type')
        webhook_id = data.get('id')
        created_at = data.get('createdAt')
        event = data.get('event', {})
        
        logger.info(f"🔍 BNB Webhook Details:")
        logger.info(f"   Type: {webhook_type}")
        logger.info(f"   ID: {webhook_id}")
        logger.info(f"   Created: {created_at}")
        
        # Handle different webhook types
        if webhook_type == 'ADDRESS_ACTIVITY':
            return handle_address_activity(event)
        elif webhook_type == 'MINED_TRANSACTION':
            return handle_mined_transaction(event)
        elif webhook_type == 'DROPPED_TRANSACTION':
            return handle_dropped_transaction(event)
        else:
            logger.warning(f"⚠️ Unknown BNB webhook type: {webhook_type}")
            return jsonify({"message": "Webhook received but not processed"}), 200
            
    except Exception as e:
        logger.error(f"❌ Error processing BNB webhook: {e}")
        return jsonify({"error": "Internal server error"}), 500

def handle_address_activity(event):
    """Handle BNB address activity events"""
    try:
        activity = event.get('activity', [])
        
        for tx in activity:
            tx_hash = tx.get('hash')
            from_address = tx.get('fromAddress')
            to_address = tx.get('toAddress')
            value = tx.get('value', 0)
            block_num = tx.get('blockNum')
            
            logger.info(f"🔄 BNB Transaction Activity:")
            logger.info(f"   Hash: {tx_hash}")
            logger.info(f"   From: {from_address}")
            logger.info(f"   To: {to_address}")
            logger.info(f"   Value: {value} wei")
            logger.info(f"   Block: {block_num}")
            
            # Process incoming transaction
            if to_address:
                process_incoming_bnb_transaction(
                    tx_hash=tx_hash,
                    from_address=from_address,
                    to_address=to_address,
                    value_wei=value,
                    block_number=block_num
                )
        
        return jsonify({"message": "BNB address activity processed"}), 200
        
    except Exception as e:
        logger.error(f"❌ Error handling BNB address activity: {e}")
        return jsonify({"error": "Failed to process address activity"}), 500

def handle_mined_transaction(event):
    """Handle BNB mined transaction events"""
    try:
        transaction = event.get('transaction', {})
        tx_hash = transaction.get('hash')
        
        logger.info(f"⛏️ BNB Transaction Mined: {tx_hash}")
        
        # Update transaction status to confirmed
        update_bnb_transaction_status(tx_hash, 'confirmed')
        
        return jsonify({"message": "BNB mined transaction processed"}), 200
        
    except Exception as e:
        logger.error(f"❌ Error handling BNB mined transaction: {e}")
        return jsonify({"error": "Failed to process mined transaction"}), 500

def handle_dropped_transaction(event):
    """Handle BNB dropped transaction events"""
    try:
        transaction = event.get('transaction', {})
        tx_hash = transaction.get('hash')
        
        logger.info(f"❌ BNB Transaction Dropped: {tx_hash}")
        
        # Update transaction status to failed
        update_bnb_transaction_status(tx_hash, 'failed')
        
        return jsonify({"message": "BNB dropped transaction processed"}), 200
        
    except Exception as e:
        logger.error(f"❌ Error handling BNB dropped transaction: {e}")
        return jsonify({"error": "Failed to process dropped transaction"}), 500

def process_incoming_bnb_transaction(tx_hash, from_address, to_address, value_wei, block_number):
    """Process incoming BNB transaction"""
    try:
        from db.connection import get_session
        from db.wallet import CryptoAddress, Account, Transaction, TransactionType, TransactionStatus
        from decimal import Decimal
        
        session = get_session()
        
        try:
            # Find the crypto address in our database
            crypto_address = session.query(CryptoAddress).filter_by(
                address=to_address.lower(),
                currency_code='BNB',
                is_active=True
            ).first()
            
            if not crypto_address:
                logger.info(f"ℹ️ BNB address {to_address} not found in our database, ignoring")
                return
            
            # Check if transaction already exists
            existing_tx = session.query(Transaction).filter_by(
                reference_id=tx_hash
            ).first()
            
            if existing_tx:
                logger.info(f"ℹ️ BNB transaction {tx_hash} already processed, ignoring")
                return
            
            # Convert wei to BNB
            value_bnb = Decimal(value_wei) / Decimal(10**18)
            
            # Create incoming transaction
            incoming_transaction = Transaction(
                account_id=crypto_address.account_id,
                amount=float(value_bnb),
                amount_smallest_unit=int(value_wei),
                precision_config={
                    "currency": "BNB",
                    "decimals": 18,
                    "smallest_unit": "wei"
                },
                type=TransactionType.DEPOSIT,
                status=TransactionStatus.COMPLETED,
                reference_id=tx_hash,
                description=f"BNB deposit from {from_address}",
                address=to_address,
                metadata={
                    "from_address": from_address,
                    "to_address": to_address,
                    "block_number": block_number,
                    "tx_hash": tx_hash,
                    "value_wei": value_wei,
                    "source": "bnb_webhook"
                }
            )
            session.add(incoming_transaction)
            
            # Update account balance
            account = session.query(Account).filter_by(id=crypto_address.account_id).first()
            if account:
                current_balance = account.crypto_balance_smallest_unit or 0
                account.crypto_balance_smallest_unit = current_balance + int(value_wei)
                
                logger.info(f"✅ Updated BNB account balance:")
                logger.info(f"   Account ID: {account.id}")
                logger.info(f"   Previous: {current_balance} wei")
                logger.info(f"   Added: {value_wei} wei")
                logger.info(f"   New: {account.crypto_balance_smallest_unit} wei")
            
            session.commit()
            
            logger.info(f"✅ Processed BNB incoming transaction:")
            logger.info(f"   TX Hash: {tx_hash}")
            logger.info(f"   Amount: {value_bnb} BNB")
            logger.info(f"   To Address: {to_address}")
            logger.info(f"   Account ID: {crypto_address.account_id}")
            
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"❌ Error processing BNB incoming transaction: {e}")

def update_bnb_transaction_status(tx_hash, status):
    """Update BNB transaction status"""
    try:
        from db.connection import get_session
        from db.wallet import Transaction, TransactionStatus
        
        session = get_session()
        
        try:
            transaction = session.query(Transaction).filter_by(
                reference_id=tx_hash
            ).first()
            
            if transaction:
                if status == 'confirmed':
                    transaction.status = TransactionStatus.COMPLETED
                elif status == 'failed':
                    transaction.status = TransactionStatus.FAILED
                
                session.commit()
                logger.info(f"✅ Updated BNB transaction {tx_hash} status to {status}")
            else:
                logger.info(f"ℹ️ BNB transaction {tx_hash} not found in database")
                
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"❌ Error updating BNB transaction status: {e}")

@bnb_webhook.route('/api/v1/wallet/bnb/callbacks/health', methods=['GET'])
def bnb_webhook_health():
    """Health check for BNB webhook"""
    return jsonify({
        "status": "healthy",
        "service": "bnb_webhook",
        "message": "BNB webhook service is running"
    }), 200
