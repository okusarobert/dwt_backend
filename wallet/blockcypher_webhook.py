import json
import hmac
import hashlib
import base64
import datetime
from flask import Blueprint, request, jsonify
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from shared.logger import setup_logging
from decouple import config
from db.connection import session
from db.wallet import CryptoAddress, Transaction, TransactionType, TransactionStatus, Reservation, ReservationType, Account, PaymentProvider

logger = setup_logging()

# BlockCypher webhook blueprint
blockcypher_webhook = Blueprint('blockcypher_webhook', __name__)

# BlockCypher's public key for webhook signing verification
BLOCKCYPHER_PUBLIC_KEY = """-----BEGIN PUBLIC KEY-----
MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAEflgGqpIAC9k65JicOPBgXZUExen4
rWLq05KwYmZHphTU/fmi3Oe/ckyxo2w3Ayo/SCO/rU2NB90jtCJfz9i1ow==
-----END PUBLIC KEY-----"""

def verify_blockcypher_signature(request_body: bytes, signature: str, key_id: str = None) -> bool:
    """
    Verify BlockCypher webhook signature using their public key.
    
    Args:
        request_body: Raw request body bytes
        signature: Base64 encoded signature from header
        key_id: Key ID from signature header (optional)
    
    Returns:
        bool: True if signature is valid, False otherwise
    """
    try:
        # Load BlockCypher's public key
        public_key = load_pem_private_key(
            BLOCKCYPHER_PUBLIC_KEY.encode(),
            password=None
        ).public_key()
        
        # Decode the signature
        signature_bytes = base64.b64decode(signature)
        
        # Create hash of the request body
        hash_obj = hashlib.sha256()
        hash_obj.update(request_body)
        message_hash = hash_obj.digest()
        
        # Verify the signature
        public_key.verify(
            signature_bytes,
            message_hash,
            ec.ECDSA(hashes.SHA256())
        )
        
        logger.info("BlockCypher webhook signature verified successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to verify BlockCypher signature: {e}")
        return False

def parse_signature_header(signature_header: str) -> dict:
    """
    Parse the signature header to extract signature and key_id.
    
    Args:
        signature_header: Raw signature header string
    
    Returns:
        dict: Parsed signature components
    """
    try:
        # Parse header format: keyId="...",algorithm="...",signature="..."
        parts = signature_header.split(',')
        parsed = {}
        
        for part in parts:
            if '=' in part:
                key, value = part.split('=', 1)
                key = key.strip()
                value = value.strip().strip('"')
                parsed[key] = value
        
        return parsed
    except Exception as e:
        logger.error(f"Failed to parse signature header: {e}")
        return {}

@blockcypher_webhook.route('/btc/callbacks/address-webhook', methods=['POST'])
def handle_blockcypher_webhook():
    """
    Handle BlockCypher webhook events for BTC addresses.
    
    Expected events:
    - unconfirmed-tx: New unconfirmed transaction
    - confirmed-tx: Transaction confirmed
    - tx-confirmation: Transaction received additional confirmations
    - tx-confidence: Transaction confidence changed
    - double-spend-tx: Double spend detected
    """
    try:
        # Get raw request body for signature verification
        request_body = request.get_data()
        
        # Get signature header
        signature_header = request.headers.get('X-BlockCypher-Signature', '')
        
        if not signature_header:
            logger.warning("No signature header found in webhook request")
            return jsonify({"error": "No signature provided"}), 400
        
        # Parse signature header
        signature_parts = parse_signature_header(signature_header)
        signature = signature_parts.get('signature', '')
        key_id = signature_parts.get('keyId', '')
        
        if not signature:
            logger.warning("No signature found in header")
            return jsonify({"error": "Invalid signature format"}), 400
        
        # Verify signature (optional - you can disable this for testing)
        if config('VERIFY_BLOCKCYPHER_SIGNATURE', default='true').lower() == 'true':
            if not verify_blockcypher_signature(request_body, signature, key_id):
                logger.error("Invalid webhook signature")
                return jsonify({"error": "Invalid signature"}), 401
        
        # Parse webhook payload
        webhook_data = request.get_json()
        
        if not webhook_data:
            logger.error("No JSON data in webhook request")
            return jsonify({"error": "No data provided"}), 400
        
        # Log webhook event
        event_type = webhook_data.get('event', 'unknown')
        address = webhook_data.get('address', 'unknown')
        tx_hash = webhook_data.get('hash', 'unknown')
        
        logger.info(f"Received BlockCypher webhook: {event_type} for address {address}, tx: {tx_hash}")
        
        # Handle different event types
        if event_type == 'unconfirmed-tx':
            handle_unconfirmed_transaction(webhook_data)
        elif event_type == 'confirmed-tx':
            handle_confirmed_transaction(webhook_data)
        elif event_type == 'tx-confirmation':
            handle_transaction_confirmation(webhook_data)
        elif event_type == 'tx-confidence':
            handle_transaction_confidence(webhook_data)
        elif event_type == 'double-spend-tx':
            handle_double_spend_transaction(webhook_data)
        else:
            logger.warning(f"Unknown event type: {event_type}")
        
        return jsonify({"status": "success", "event": event_type}), 200
        
    except Exception as e:
        logger.error(f"Error processing BlockCypher webhook: {e}")
        return jsonify({"error": "Internal server error"}), 500

@blockcypher_webhook.route('/btc/callbacks/forward-webhook', methods=['POST'])
def handle_forward_webhook():
    """
    Handle BlockCypher address forwarding webhook events.
    This is called when a payment is forwarded to the master address.
    """
    try:
        # Get raw request body for signature verification
        request_body = request.get_data()
        
        # Get signature header
        signature_header = request.headers.get('X-BlockCypher-Signature', '')
        
        if not signature_header:
            logger.warning("No signature header found in forward webhook request")
            return jsonify({"error": "No signature provided"}), 400
        
        # Parse signature header
        signature_parts = parse_signature_header(signature_header)
        signature = signature_parts.get('signature', '')
        key_id = signature_parts.get('keyId', '')
        
        if not signature:
            logger.warning("No signature found in header")
            return jsonify({"error": "Invalid signature format"}), 400
        
        # Verify signature (optional - you can disable this for testing)
        if config('VERIFY_BLOCKCYPHER_SIGNATURE', default='true').lower() == 'true':
            if not verify_blockcypher_signature(request_body, signature, key_id):
                logger.error("Invalid forward webhook signature")
                return jsonify({"error": "Invalid signature"}), 401
        
        # Parse webhook payload
        webhook_data = request.get_json()
        
        if not webhook_data:
            logger.error("No JSON data in forward webhook request")
            return jsonify({"error": "No data provided"}), 400
        
        # Log forward webhook event
        forward_id = webhook_data.get('id', 'unknown')
        input_address = webhook_data.get('input_address', 'unknown')
        destination_address = webhook_data.get('destination_address', 'unknown')
        amount = webhook_data.get('value', 0)
        
        logger.info(f"Received forward webhook: {forward_id}")
        logger.info(f"From: {input_address} -> To: {destination_address}")
        logger.info(f"Amount: {amount} BTC")
        
        # Handle the forward event
        handle_payment_forwarded(webhook_data)
        
        return jsonify({"status": "success", "forward_id": forward_id}), 200
        
    except Exception as e:
        logger.error(f"Error processing forward webhook: {e}")
        return jsonify({"error": "Internal server error"}), 500

def handle_payment_forwarded(data: dict):
    """Handle payment forwarded event."""
    try:
        forward_id = data.get('id')
        input_address = data.get('input_address')
        destination_address = data.get('destination_address')
        amount = data.get('value', 0)
        
        logger.info(f"Payment forwarded: {amount} BTC from {input_address} to {destination_address}")
        
        # Find the crypto address record
        crypto_address = session.query(CryptoAddress).filter(
            CryptoAddress.address == input_address,
            CryptoAddress.currency_code == 'BTC'
        ).first()
        
        if crypto_address:
            # Update metadata to track forwarding
            metadata = crypto_address.metadata_json or {}
            metadata['last_forwarded'] = {
                'forward_id': forward_id,
                'amount': amount,
                'destination': destination_address,
                'timestamp': datetime.utcnow().isoformat()
            }
            crypto_address.metadata_json = metadata
            session.commit()
            
            logger.info(f"Updated forwarding metadata for address {input_address}")
        else:
            logger.warning(f"Address {input_address} not found in database")
            
    except Exception as e:
        logger.error(f"Error handling payment forwarded: {e}")
        session.rollback()

def handle_unconfirmed_transaction(data: dict):
    """Handle unconfirmed transaction event."""
    logger.info(f"Processing unconfirmed transaction: {data.get('hash')}")
    
    try:
        tx_hash = data.get('hash')
        address = data.get('address')
        amount = data.get('value', 0)
        
        # Find the crypto address in database
        crypto_address = session.query(CryptoAddress).filter(
            CryptoAddress.address == address,
            CryptoAddress.currency_code == 'BTC'
        ).first()
        
        if not crypto_address:
            logger.warning(f"Address {address} not found in database")
            return
        
        # Check if transaction already exists
        existing_tx = session.query(Transaction).filter(
            Transaction.blockchain_txid == tx_hash
        ).first()
        
        if existing_tx:
            logger.info(f"Transaction {tx_hash} already exists")
            return
        
        # Create new transaction record
        new_transaction = Transaction(
            account_id=crypto_address.account_id,
            blockchain_txid=tx_hash,
            type=TransactionType.DEPOSIT,
            amount=amount,
            confirmations=0,
            status=TransactionStatus.AWAITING_CONFIRMATION,
            address=address,
            provider=PaymentProvider.CRYPTO,
            metadata_json=data
        )
        
        session.add(new_transaction)
        session.commit()
        
        logger.info(f"Created unconfirmed transaction record for {address}")
        
    except Exception as e:
        logger.error(f"Error handling unconfirmed transaction: {e}")
        session.rollback()

def handle_confirmed_transaction(data: dict):
    """Handle confirmed transaction event."""
    logger.info(f"Processing confirmed transaction: {data.get('hash')}")
    
    try:
        tx_hash = data.get('hash')
        address = data.get('address')
        amount = data.get('value', 0)
        confirmations = data.get('confirmations', 1)
        
        # Find the transaction in database
        transaction = session.query(Transaction).filter(
            Transaction.blockchain_txid == tx_hash
        ).first()
        
        if not transaction:
            logger.warning(f"Transaction {tx_hash} not found in database")
            return
        
        # Get the account
        account = session.query(Account).filter(Account.id == transaction.account_id).first()
        if not account:
            logger.error(f"Account {transaction.account_id} not found")
            return
        
        # Update transaction status to confirmed
        transaction.status = TransactionStatus.COMPLETED
        transaction.confirmations = confirmations
        
        # Create reservation to lock the amount
        reservation = Reservation(
            user_id=account.user_id,
            reference=f"crypto_deposit_{tx_hash}",
            amount=amount,
            type=ReservationType.RESERVE,
            status="active"
        )
        
        session.add(reservation)
        
        # Lock the amount in the account
        account.locked_amount += amount
        
        session.commit()
        
        logger.info(f"Confirmed transaction {tx_hash}, locked {amount} in account {account.id}")
        
        # If we have 2 or more confirmations, credit the wallet
        if confirmations >= 2:
            credit_wallet_after_confirmation(transaction, account, amount, tx_hash)
        
    except Exception as e:
        logger.error(f"Error handling confirmed transaction: {e}")
        session.rollback()

def handle_transaction_confirmation(data: dict):
    """Handle transaction confirmation event."""
    confirmations = data.get('confirmations', 0)
    tx_hash = data.get('hash')
    
    logger.info(f"Transaction {tx_hash} has {confirmations} confirmations")
    
    try:
        # Find and update transaction
        transaction = session.query(Transaction).filter(
            Transaction.blockchain_txid == tx_hash
        ).first()
        
        if not transaction:
            logger.warning(f"Transaction {tx_hash} not found")
            return
        
        # Update confirmations
        transaction.confirmations = confirmations
        
        # Get the account
        account = session.query(Account).filter(Account.id == transaction.account_id).first()
        if not account:
            logger.error(f"Account {transaction.account_id} not found")
            return
        
        # If we have 2 or more confirmations, credit the wallet
        if confirmations >= 2:
            credit_wallet_after_confirmation(transaction, account, transaction.amount, tx_hash)
        
        session.commit()
        logger.info(f"Updated transaction {tx_hash} confirmations to {confirmations}")
        
    except Exception as e:
        logger.error(f"Error handling transaction confirmation: {e}")
        session.rollback()

def credit_wallet_after_confirmation(transaction, account, amount, tx_hash):
    """Credit the wallet after 2 confirmations and release the reservation."""
    try:
        # Check if we already processed this transaction
        existing_reservation = session.query(Reservation).filter(
            Reservation.reference == f"crypto_deposit_{tx_hash}",
            Reservation.type == ReservationType.RELEASE
        ).first()
        
        if existing_reservation:
            logger.info(f"Transaction {tx_hash} already credited to wallet")
            return
        
        # Create release reservation
        release_reservation = Reservation(
            user_id=account.user_id,
            reference=f"crypto_deposit_{tx_hash}",
            amount=amount,
            type=ReservationType.RELEASE,
            status="completed"
        )
        
        session.add(release_reservation)
        
        # Unlock the amount and credit the wallet
        account.locked_amount -= amount
        account.balance += amount
        
        # Update transaction status
        transaction.status = TransactionStatus.COMPLETED
        
        session.commit()
        
        logger.info(f"Credited {amount} to wallet for transaction {tx_hash}")
        
        # Note: BlockCypher handles forwarding automatically via address forwarding setup
        
    except Exception as e:
        logger.error(f"Error crediting wallet for transaction {tx_hash}: {e}")
        session.rollback()

# Note: BlockCypher address forwarding handles this automatically
# No need for manual forwarding logic

def handle_transaction_confidence(data: dict):
    """Handle transaction confidence event."""
    confidence = data.get('confidence', 0)
    tx_hash = data.get('hash')
    
    logger.info(f"Transaction {tx_hash} confidence: {confidence}")
    
    try:
        # Find and update transaction confidence
        transaction = session.query(Transaction).filter(
            Transaction.blockchain_txid == tx_hash
        ).first()
        
        if transaction:
            # Update confidence in metadata
            metadata = transaction.metadata_json or {}
            metadata['confidence'] = confidence
            transaction.metadata_json = metadata
            session.commit()
            logger.info(f"Updated transaction {tx_hash} confidence to {confidence}")
        
    except Exception as e:
        logger.error(f"Error handling transaction confidence: {e}")
        session.rollback()

def handle_double_spend_transaction(data: dict):
    """Handle double spend transaction event."""
    tx_hash = data.get('hash')
    
    logger.warning(f"Double spend detected for transaction: {tx_hash}")
    
    try:
        # Find the transaction
        transaction = session.query(Transaction).filter(
            Transaction.blockchain_txid == tx_hash
        ).first()
        
        if not transaction:
            logger.warning(f"Transaction {tx_hash} not found in database")
            return
        
        # Get the account
        account = session.query(Account).filter(Account.id == transaction.account_id).first()
        if not account:
            logger.error(f"Account {transaction.account_id} not found")
            return
        
        # Update transaction status to failed
        transaction.status = TransactionStatus.FAILED
        
        # Update metadata to flag as double spend
        metadata = transaction.metadata_json or {}
        metadata['double_spend_detected'] = True
        metadata['double_spend_data'] = data
        transaction.metadata_json = metadata
        
        # Remove locked amount if it was locked
        if account.locked_amount >= transaction.amount:
            account.locked_amount -= transaction.amount
            logger.info(f"Removed locked amount {transaction.amount} for double spend transaction {tx_hash}")
        
        # Create a failed reservation record
        failed_reservation = Reservation(
            user_id=account.user_id,
            reference=f"crypto_deposit_{tx_hash}",
            amount=transaction.amount,
            type=ReservationType.RESERVE,
            status="failed"
        )
        
        session.add(failed_reservation)
        session.commit()
        
        logger.warning(f"Failed transaction {tx_hash} due to double spend")
        
    except Exception as e:
        logger.error(f"Error handling double spend transaction: {e}")
        session.rollback()

# Register the blueprint in your main wallet app
# In your main wallet/app.py, add:
# from wallet.blockcypher_webhook import blockcypher_webhook
# app.register_blueprint(blockcypher_webhook) 