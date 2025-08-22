#!/usr/bin/env python3
"""
TRON Webhook Handler for processing TRONGrid webhook events
Similar to BlockCypher webhook implementation for Bitcoin
"""

import json
import hmac
import hashlib
import base64
import datetime
from flask import Blueprint, request, jsonify
from shared.logger import setup_logging
from decouple import config
from db.connection import session
from db.wallet import CryptoAddress, Transaction, TransactionType, TransactionStatus, Reservation, ReservationType, Account, PaymentProvider

logger = setup_logging()

# TRON webhook blueprint
tron_webhook = Blueprint('tron_webhook', __name__)

def verify_tron_signature(request_body: bytes, signature: str, api_key: str) -> bool:
    """
    Verify TRON webhook signature
    TRON uses HMAC-SHA256 for webhook signature verification
    """
    try:
        # Create expected signature
        expected_signature = hmac.new(
            api_key.encode('utf-8'),
            request_body,
            hashlib.sha256
        ).hexdigest()
        
        # Compare signatures
        return hmac.compare_digest(expected_signature, signature)
        
    except Exception as e:
        logger.error(f"Error verifying TRON signature: {e}")
        return False

def parse_tron_webhook_data(webhook_data: dict) -> dict:
    """
    Parse TRON webhook data and extract relevant information
    """
    try:
        parsed_data = {
            "event_type": webhook_data.get("event", "unknown"),
            "address": webhook_data.get("address", ""),
            "tx_hash": webhook_data.get("hash", ""),
            "block_number": webhook_data.get("block_number", 0),
            "timestamp": webhook_data.get("timestamp", 0),
            "amount": webhook_data.get("value", 0),
            "from_address": webhook_data.get("from", ""),
            "to_address": webhook_data.get("to", ""),
            "contract_address": webhook_data.get("contract_address", ""),
            "token_name": webhook_data.get("token_name", ""),
            "token_symbol": webhook_data.get("token_symbol", ""),
            "decimals": webhook_data.get("decimals", 6),
            "confirmations": webhook_data.get("confirmations", 0),
            "confidence": webhook_data.get("confidence", 0.0)
        }
        
        return parsed_data
        
    except Exception as e:
        logger.error(f"Error parsing TRON webhook data: {e}")
        return {}

def handle_tron_transfer_event(webhook_data: dict):
    """
    Handle TRON transfer events (TRX or TRC20)
    """
    try:
        parsed_data = parse_tron_webhook_data(webhook_data)
        
        if not parsed_data.get("address"):
            logger.error("No address in TRON webhook data")
            return
        
        address = parsed_data["address"]
        tx_hash = parsed_data["tx_hash"]
        amount = parsed_data["amount"]
        from_address = parsed_data["from_address"]
        to_address = parsed_data["to_address"]
        
        logger.info(f"Processing TRON transfer: {tx_hash} -> {address}")
        
        # Check if this address is being watched
        crypto_address = session.query(CryptoAddress).filter_by(
            address=address,
            currency="TRX"
        ).first()
        
        if not crypto_address:
            logger.info(f"Address {address} not being watched")
            return
        
        # Check if transaction already exists
        existing_tx = session.query(Transaction).filter_by(
            tx_hash=tx_hash,
            currency="TRX"
        ).first()
        
        if existing_tx:
            logger.info(f"Transaction {tx_hash} already processed")
            return
        
        # Create new transaction record
        transaction = Transaction(
            account_id=crypto_address.account_id,
            type=TransactionType.DEPOSIT,
            amount=amount,
            currency="TRX",
            tx_hash=tx_hash,
            from_address=from_address,
            to_address=to_address,
            status=TransactionStatus.AWAITING_CONFIRMATION,
            provider=PaymentProvider.CRYPTO,
            metadata_json={
                "block_number": parsed_data["block_number"],
                "timestamp": parsed_data["timestamp"],
                "confirmations": parsed_data["confirmations"],
                "confidence": parsed_data["confidence"],
                "contract_address": parsed_data["contract_address"],
                "token_name": parsed_data["token_name"],
                "token_symbol": parsed_data["token_symbol"],
                "decimals": parsed_data["decimals"]
            }
        )
        
        session.add(transaction)
        session.commit()
        
        logger.info(f"Created TRON transaction: {tx_hash}")
        
        # If confirmed, create reservation and credit account
        if parsed_data["confirmations"] >= 2:
            handle_tron_confirmed_transaction(transaction, parsed_data)
        
    except Exception as e:
        logger.error(f"Error handling TRON transfer event: {e}")
        session.rollback()

def handle_tron_confirmed_transaction(transaction: Transaction, parsed_data: dict):
    """
    Handle confirmed TRON transactions
    """
    try:
        # Update transaction status
        transaction.status = TransactionStatus.COMPLETED
        
        # Get account and lock amount
        account = session.query(Account).filter_by(id=transaction.account_id).with_for_update().first()
        
        if account:
            # Create reservation for the amount
            reservation = Reservation(
                account_id=account.id,
                amount=transaction.amount,
                type=ReservationType.DEPOSIT,
                transaction_id=transaction.id,
                status="active"
            )
            session.add(reservation)
            
            # Credit the account
            account.balance += transaction.amount
            session.add(account)
        
        session.commit()
        
        logger.info(f"Confirmed TRON transaction: {transaction.tx_hash}")
        
        # TODO: Send notification to user about deposit
        
    except Exception as e:
        logger.error(f"Error handling confirmed TRON transaction: {e}")
        session.rollback()

def handle_tron_contract_log_event(webhook_data: dict):
    """
    Handle TRON contract log events (TRC20 token transfers)
    """
    try:
        parsed_data = parse_tron_webhook_data(webhook_data)
        
        if not parsed_data.get("address"):
            logger.error("No address in TRON contract log data")
            return
        
        address = parsed_data["address"]
        tx_hash = parsed_data["tx_hash"]
        contract_address = parsed_data["contract_address"]
        
        logger.info(f"Processing TRON contract log: {tx_hash} -> {address} (contract: {contract_address})")
        
        # Check if this address is being watched
        crypto_address = session.query(CryptoAddress).filter_by(
            address=address,
            currency="TRX"
        ).first()
        
        if not crypto_address:
            logger.info(f"Address {address} not being watched")
            return
        
        # Check if transaction already exists
        existing_tx = session.query(Transaction).filter_by(
            tx_hash=tx_hash,
            currency="TRX"
        ).first()
        
        if existing_tx:
            logger.info(f"Transaction {tx_hash} already processed")
            return
        
        # Create new transaction record for TRC20
        transaction = Transaction(
            account_id=crypto_address.account_id,
            type=TransactionType.DEPOSIT,
            amount=parsed_data["amount"],
            currency="TRX",  # Store as TRX but with contract info
            tx_hash=tx_hash,
            from_address=parsed_data["from_address"],
            to_address=parsed_data["to_address"],
            status=TransactionStatus.AWAITING_CONFIRMATION,
            provider=PaymentProvider.CRYPTO,
            metadata_json={
                "block_number": parsed_data["block_number"],
                "timestamp": parsed_data["timestamp"],
                "confirmations": parsed_data["confirmations"],
                "confidence": parsed_data["confidence"],
                "contract_address": contract_address,
                "token_name": parsed_data["token_name"],
                "token_symbol": parsed_data["token_symbol"],
                "decimals": parsed_data["decimals"],
                "is_trc20": True
            }
        )
        
        session.add(transaction)
        session.commit()
        
        logger.info(f"Created TRON TRC20 transaction: {tx_hash}")
        
        # If confirmed, create reservation and credit account
        if parsed_data["confirmations"] >= 2:
            handle_tron_confirmed_transaction(transaction, parsed_data)
        
    except Exception as e:
        logger.error(f"Error handling TRON contract log event: {e}")
        session.rollback()

@tron_webhook.route('/trx/callbacks/address-webhook', methods=['POST'])
def handle_tron_webhook():
    """
    Handle TRON webhook events from TRONGrid API
    
    Expected events:
    - transfer: TRX or TRC20 token transfers
    - contractLog: TRC20 token contract events
    """
    try:
        # Get raw request body for signature verification
        request_body = request.get_data()
        
        # Get signature header (TRON uses X-TRON-Signature)
        signature_header = request.headers.get('X-TRON-Signature', '')
        
        if not signature_header:
            logger.warning("No signature header found in TRON webhook request")
            return jsonify({"error": "No signature provided"}), 400
        
        # Verify signature (optional - you can disable this for testing)
        if config('VERIFY_TRON_SIGNATURE', default='true').lower() == 'true':
            api_key = config('TRONGRID_API_KEY')
            if not verify_tron_signature(request_body, signature_header, api_key):
                logger.error("Invalid TRON webhook signature")
                return jsonify({"error": "Invalid signature"}), 401
        
        # Parse webhook payload
        webhook_data = request.get_json()
        
        if not webhook_data:
            logger.error("No JSON data in TRON webhook request")
            return jsonify({"error": "No data provided"}), 400
        
        # Log webhook event
        event_type = webhook_data.get('event', 'unknown')
        address = webhook_data.get('address', 'unknown')
        tx_hash = webhook_data.get('hash', 'unknown')
        
        logger.info(f"Received TRON webhook: {event_type} for address {address}, tx: {tx_hash}")
        
        # Handle different event types
        if event_type == 'transfer':
            handle_tron_transfer_event(webhook_data)
        elif event_type == 'contractLog':
            handle_tron_contract_log_event(webhook_data)
        else:
            logger.warning(f"Unknown TRON event type: {event_type}")
        
        return jsonify({"status": "success", "event": event_type}), 200
        
    except Exception as e:
        logger.error(f"Error processing TRON webhook: {e}")
        return jsonify({"error": "Internal server error"}), 500

@tron_webhook.route('/trx/callbacks/health', methods=['GET'])
def tron_webhook_health():
    """
    Health check endpoint for TRON webhook
    """
    return jsonify({
        "status": "healthy",
        "service": "tron_webhook",
        "timestamp": datetime.datetime.now().isoformat()
    }), 200 