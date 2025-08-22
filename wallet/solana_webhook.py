#!/usr/bin/env python3
"""
Solana Webhook Handler for processing Alchemy webhook events
"""

import json
import hmac
import hashlib
import datetime
import requests
from flask import Blueprint, request, jsonify
from shared.logger import setup_logging
from decouple import config
from db.connection import session
from db.wallet import CryptoAddress, Transaction, TransactionType, TransactionStatus, Reservation, ReservationType, Account, PaymentProvider
from shared.currency_precision import AmountConverter
from shared.trading_accounting import TradingAccountingService
from db.accounting import JournalEntry, LedgerTransaction, AccountingAccount

logger = setup_logging()

# Import SOL notification service
try:
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
    from solana_webhook_integration import solana_notification_service
    logger.info("✅ Successfully imported solana_notification_service")
except ImportError as e:
    logger.error(f"❌ Failed to import solana_notification_service: {e}")
    solana_notification_service = None

# Solana webhook blueprint
solana_webhook = Blueprint('solana_webhook', __name__)

def _alchemy_solana_base_url(network: str) -> str:
    network = (network or "SOLANA_DEVNET").upper()
    if "MAINNET" in network:
        return "https://solana-mainnet.g.alchemy.com/v2/"
    if "TESTNET" in network:
        return "https://solana-testnet.g.alchemy.com/v2/"
    return "https://solana-devnet.g.alchemy.com/v2/"

def _create_solana_accounting_entry(transaction: Transaction, account: Account, session_obj) -> None:
    """
    Create accounting journal entry for Solana deposit.
    
    Double-entry bookkeeping:
    Debit: Crypto Assets - SOL (increase asset)
    Credit: User Liabilities - SOL (increase liability)
    """
    try:
        from shared.crypto.price_utils import get_crypto_price
        from shared.fiat.forex_service import ForexService
        from decimal import Decimal
        
        # Get current crypto price in USD and UGX at transaction time
        try:
            sol_price_usd = get_crypto_price("SOL")
            if not sol_price_usd:
                logger.warning("❌ Could not get SOL price in USD")
                return
            
            # Get USD to UGX exchange rate
            forex_service = ForexService()
            usd_to_ugx = forex_service.get_exchange_rate('USD', 'UGX')
            
            sol_price_ugx = sol_price_usd * usd_to_ugx
            
            # Store price metadata in transaction
            if not transaction.metadata_json:
                transaction.metadata_json = {}
            transaction.metadata_json.update({
                "sol_price_usd_at_time": str(sol_price_usd),
                "sol_price_ugx_at_time": str(sol_price_ugx),
                "usd_to_ugx_rate_at_time": str(usd_to_ugx)
            })
            
            logger.info(f"💰 SOL price at transaction time: ${sol_price_usd:.4f} USD, {sol_price_ugx:.2f} UGX")
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to capture price at transaction time: {e}")
        
        # Use TradingAccountingService to create the journal entry
        accounting_service = TradingAccountingService(session_obj)
        
        # Get accounting accounts
        crypto_account = accounting_service.get_account_by_name("Crypto Assets - SOL")
        liability_account = accounting_service.get_account_by_name("User Liabilities - SOL")
        
        if not crypto_account or not liability_account:
            logger.warning("⚠️ Required SOL accounting accounts not found - skipping accounting entry")
            return
        
        # Format amount for description
        formatted_amount = AmountConverter.format_display_amount(transaction.amount_smallest_unit, "SOL")
        description = f"SOL deposit - {formatted_amount} (TX: {transaction.blockchain_txid[:8]}...)"
        
        # Create journal entry
        journal_entry = JournalEntry(description=description)
        accounting_service.session.add(journal_entry)
        accounting_service.session.flush()  # Get the journal entry ID
        
        # Convert amount to standard units for accounting
        amount_standard = AmountConverter.from_smallest_units(transaction.amount_smallest_unit, "SOL")
        
        # Deposit: Debit Crypto Assets, Credit User Liabilities
        # Debit crypto assets (increase our crypto holdings)
        debit_tx = LedgerTransaction(
            journal_entry_id=journal_entry.id,
            account_id=crypto_account.id,
            debit=amount_standard,
            credit=Decimal('0')
        )
        accounting_service.session.add(debit_tx)
        
        # Credit user liabilities (increase what we owe user)
        credit_tx = LedgerTransaction(
            journal_entry_id=journal_entry.id,
            account_id=liability_account.id,
            debit=Decimal('0'),
            credit=amount_standard
        )
        accounting_service.session.add(credit_tx)
        
        logger.info(f"✅ Created ledger transactions for SOL deposit: {formatted_amount}")
        
    except Exception as e:
        logger.error(f"❌ Failed to create accounting entry for Solana deposit: {e}")

def _update_tx_confirmations_and_credit(tx_hash: str, required_confirmations: int = 32,tx_type: TransactionType = TransactionType.DEPOSIT, network: str | None = None) -> None:
    """Query Solana RPC for signature status, update confirmations, and credit on finality.

    - Uses Alchemy Solana endpoint with ALCHEMY_API_KEY
    - If confirmationStatus == 'finalized' or confirmations >= required, mark COMPLETED
      and release reservation, move locked -> balance for the account.
    """
    try:
        api_key = config('ALCHEMY_API_KEY', default='')
        if not api_key:
            logger.warning("ALCHEMY_API_KEY not configured; skipping confirmations update")
            return

        # Load transaction
        tx = session.query(Transaction).filter_by(blockchain_txid=tx_hash, type=tx_type).first()
        if not tx:
            logger.warning(f"SOL confirmations update: tx {tx_hash} not found")
            return

        # Build endpoint from network metadata if present
        tx_net = network or (tx.metadata_json or {}).get('network') or 'SOLANA_DEVNET'
        base = _alchemy_solana_base_url(tx_net)
        url = f"{base}{api_key}"

        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getSignatureStatuses",
            "params": [[tx_hash], {"searchTransactionHistory": True}],
        }
        resp = requests.post(url, json=payload, timeout=10)
        if resp.status_code != 200:
            logger.warning(f"SOL confirmations RPC error {resp.status_code}: {resp.text[:200]}")
            return
        data = resp.json()
        value_list = (data.get("result") or {}).get("value") or []
        status = value_list[0] if value_list else None
        if not status:
            logger.info(f"No status yet for {tx_hash}")
            return

        confirmations = status.get("confirmations")
        confirmation_status = status.get("confirmationStatus")

        # When finalized, 'confirmations' may be None
        if confirmation_status == 'finalized' or (isinstance(confirmations, int) and confirmations >= required_confirmations):
            tx.confirmations = required_confirmations
            tx.status = TransactionStatus.COMPLETED

            # Release reservation and credit account using unified system
            account = session.query(Account).filter_by(id=tx.account_id).first()
            if account:
                reservation_reference = f"sol_deposit_{tx_hash}"
                exists_release = (
                    session.query(Reservation)
                    .filter_by(
                        user_id=account.user_id,
                        reference=reservation_reference,
                        type=ReservationType.RELEASE,
                    )
                    .first()
                )
                if not exists_release:
                    # Use unified amount for reservation
                    sol_amount = AmountConverter.from_smallest_units(int(tx.amount_smallest_unit or 0), "SOL")
                    release_res = Reservation(
                        user_id=account.user_id,
                        reference=reservation_reference,
                        amount=float(sol_amount),
                        type=ReservationType.RELEASE,
                        status="completed",
                    )
                    session.add(release_res)

                amount_lamports = int(tx.amount_smallest_unit or 0)
                # Move locked -> balance using unified balance fields
                if hasattr(account, 'locked_amount_smallest_unit') and hasattr(account, 'balance_smallest_unit'):
                    # Use unified balance system
                    account.locked_amount_smallest_unit = max(0, (account.locked_amount_smallest_unit or 0) - amount_lamports)
                    account.balance_smallest_unit = (account.balance_smallest_unit or 0) + amount_lamports
                else:
                    # Fallback to legacy crypto fields
                    account.crypto_locked_amount_smallest_unit = max(0, (account.crypto_locked_amount_smallest_unit or 0) - amount_lamports)
                    account.crypto_balance_smallest_unit = (account.crypto_balance_smallest_unit or 0) + amount_lamports

                # Create accounting entry for finalized deposit
                try:
                    _create_solana_accounting_entry(tx, account, session)
                except Exception as e:
                    logger.error(f"⚠️ Failed to create accounting entry for finalized SOL deposit: {e}")

            session.commit()
            logger.info(f"🎯 SOL tx {tx_hash} finalized; credited account and released reservation")
            return

        # Update intermediate confirmations
        if isinstance(confirmations, int):
            tx.confirmations = confirmations
            session.commit()
            logger.info(f"⏳ SOL tx {tx_hash} confirmations updated: {confirmations}/{required_confirmations}")

    except Exception as e:
        logger.error(f"Error updating SOL confirmations for {tx_hash}: {e}")
        session.rollback()

def verify_alchemy_signature(request_body: str, signature: str) -> bool:
    """Verify Alchemy webhook signature using HMAC-SHA256 with Webhook Signing Key
    
    Based on official Alchemy documentation:
    https://www.alchemy.com/docs/reference/notify-api-quickstart#webhook-signature--security
    """
    try:
        # Use Webhook Signing Key (official Alchemy method)
        webhook_signing_key = config('ALCHEMY_WEBHOOK_KEY', default=None)
        logger.info(f"Webhook Signing Key: {webhook_signing_key}")
        if not webhook_signing_key:
            logger.error("❌ ALCHEMY_WEBHOOK_KEY not configured")
            return False
        
        # Alchemy expects the signature to be calculated on compact JSON format
        # Parse the request body and re-serialize as compact JSON
        try:
            parsed_json = json.loads(request_body)
            compact_json = json.dumps(parsed_json, separators=(',', ':'))
            request_body_for_signature = compact_json
            logger.info(f"Using compact JSON format for signature verification")
        except json.JSONDecodeError:
            # Fallback to original request body if JSON parsing fails
            request_body_for_signature = request_body
            logger.warning(f"Could not parse JSON, using original request body")
        
        # Follow official Alchemy implementation pattern
        # Use signing key as HMAC key and compact JSON as message
        digest = hmac.new(
            bytes(webhook_signing_key, "utf-8"),
            msg=bytes(request_body_for_signature, "utf-8"),
            digestmod=hashlib.sha256,
        ).hexdigest()
        
        if signature == digest:
            logger.info(f"✅ Signature verified using Webhook Signing Key")
            return True
        
        logger.warning(f"❌ Signature verification failed. Expected: {digest[:16]}..., Received: {signature[:16]}...")
        return False
        
    except Exception as e:
        logger.error(f"Error verifying Alchemy signature: {e}")
        return False

def handle_solana_address_activity(webhook_data: dict):
    """Handle Solana address activity webhook events"""
    try:
        webhook_id = webhook_data.get('webhookId', 'unknown')
        event_data = webhook_data.get('event', {})

        # Two possible Alchemy payload shapes:
        # 1) { event: { activity: [ { hash, fromAddress, toAddress, value } ] } }
        # 2) { event: { transaction: [ { signature, transaction: [...message...], meta: [...] } ], slot, network } }

        activity_list = event_data.get('activity', [])
        transactions_list = event_data.get('transaction') or event_data.get('transactions') or []

        # Prefer the new "transaction" format if present; otherwise fall back to "activity"
        if transactions_list:
            logger.info(f"Processing Solana address activity (transactions): {webhook_id}, {len(transactions_list)} items")

            for tx_entry in transactions_list:
                try:
                    # Transaction signature (tx hash)
                    tx_hash = tx_entry.get('signature') or ''

                    # message structure may be wrapped in single-item lists
                    msg_container = (tx_entry.get('transaction') or [{}])[0]
                    message = (msg_container.get('message') or [{}])[0]

                    account_keys = message.get('account_keys', [])
                    instructions = message.get('instructions', [])

                    # Compute transferred lamports using meta pre/post balances
                    lamports = 0
                    from_address = ''
                    to_address = ''
                    
                    meta_container = (tx_entry.get('meta') or [{}])[0]
                    pre_balances = meta_container.get('pre_balances') or []
                    post_balances = meta_container.get('post_balances') or []

                    # Find sender and recipient by analyzing balance changes
                    if account_keys and pre_balances and post_balances:
                        for i in range(min(len(account_keys), len(pre_balances), len(post_balances))):
                            balance_change = int(post_balances[i]) - int(pre_balances[i])
                            
                            # Skip system accounts (balance = 1) and fee payer analysis
                            if pre_balances[i] <= 1:
                                continue
                                
                            if balance_change > 0:
                                # This account received SOL (recipient)
                                to_address = account_keys[i]
                                lamports = balance_change
                                logger.info(f"Found recipient: {to_address} received {balance_change} lamports")
                            elif balance_change < 0 and not from_address:
                                # This account sent SOL (sender) - exclude transaction fees
                                from_address = account_keys[i]
                                logger.info(f"Found sender: {from_address} sent {abs(balance_change)} lamports (including fees)")

                    # Fallback: try instruction-based detection if balance analysis failed
                    if not to_address and account_keys and instructions:
                        first_ix = instructions[0]
                        idxs = first_ix.get('accounts', [])
                        if isinstance(idxs, list) and len(idxs) >= 2:
                            from_idx, to_idx = idxs[0], idxs[1]
                            if 0 <= from_idx < len(account_keys):
                                from_address = account_keys[from_idx]
                            if 0 <= to_idx < len(account_keys):
                                to_address = account_keys[to_idx]
                                
                            # Try to get lamports from balance change at to_idx
                            if 0 <= to_idx < len(pre_balances) and 0 <= to_idx < len(post_balances):
                                delta_to = int(post_balances[to_idx]) - int(pre_balances[to_idx])
                                if delta_to > 0:
                                    lamports = delta_to

                    # Only process deposits into our monitored address (to_address)
                    if not to_address or lamports <= 0:
                        logger.info(f"Invalid deposit {to_address} {lamports}")
                        continue

                    to_crypto_address = session.query(CryptoAddress).filter_by(
                        address=to_address, currency_code='SOL'
                    ).first()

                    if not to_crypto_address:
                        # Not a monitored deposit; skip
                        logger.info("Not a monitored address")
                        continue

                    # Check for existing transaction to avoid duplicates
                    existing_tx = session.query(Transaction).filter_by(
                        blockchain_txid=tx_hash,
                        address=to_address,
                        type=TransactionType.DEPOSIT
                    ).first()
                    if existing_tx:
                        logger.info(f"Transaction already exists: {existing_tx}")
                        continue

                    # Use unified precision system for SOL conversion
                    amount_sol = AmountConverter.from_smallest_units(lamports, "SOL")
                    formatted_amount = AmountConverter.format_display_amount(lamports, "SOL")
                    logger.info(f"💰 Deposit received: {formatted_amount}")

                    transaction = Transaction(
                        account_id=to_crypto_address.account_id,
                        type=TransactionType.DEPOSIT,
                        amount=float(amount_sol),  # Legacy field for backward compatibility
                        amount_smallest_unit=int(lamports),  # Unified field
                        provider=PaymentProvider.CRYPTO,
                        blockchain_txid=tx_hash,
                        reference_id=f"sol_deposit_{tx_hash}",
                        address=to_address,
                        status=TransactionStatus.AWAITING_CONFIRMATION,
                        confirmations=1,
                        required_confirmations=32,
                        metadata_json={
                            'webhook_id': webhook_id,
                            'from_address': from_address,
                            'to_address': to_address,
                            'slot': webhook_data.get('event', {}).get('slot'),
                            'network': webhook_data.get('event', {}).get('network'),
                            'processed_at': datetime.datetime.utcnow().isoformat(),
                            'unified_system': True,
                            'currency': 'SOL'
                        }
                    )
                    logger.info("created a deposit transaction")

                    # Create reservation and lock funds for deposit confirmations
                    account = session.query(Account).filter_by(id=to_crypto_address.account_id).first()
                    if account:
                        # Unique reservation reference
                        reservation_reference = f"sol_deposit_{tx_hash}"
                        existing_res = (
                            session.query(Reservation)
                            .filter_by(
                                user_id=account.user_id,
                                reference=reservation_reference,
                                type=ReservationType.RESERVE,
                            )
                            .first()
                        )
                        if not existing_res:
                            reservation = Reservation(
                                user_id=account.user_id,
                                reference=reservation_reference,
                                amount=float(amount_sol),
                                type=ReservationType.RESERVE,
                                status="active",
                            )
                            session.add(reservation)
                        
                        # Lock the lamports on account using unified system
                        if hasattr(account, 'locked_amount_smallest_unit'):
                            # Use unified balance system
                            account.locked_amount_smallest_unit = (account.locked_amount_smallest_unit or 0) + int(lamports)
                        else:
                            # Fallback to legacy crypto fields
                            account.crypto_locked_amount_smallest_unit = (
                                (account.crypto_locked_amount_smallest_unit or 0) + int(lamports)
                            )

                    session.add(transaction)
                    
                    # Get user_id before committing (while session is active)
                    user_id = account.user_id if account else None
                    
                    session.commit()
                    formatted_amount = AmountConverter.format_display_amount(lamports, "SOL")
                    logger.info(
                        f"✅ Recorded Solana deposit {tx_hash} for {to_address} amount {formatted_amount} ({lamports:,} lamports) and reserved funds"
                    )

                    # Send websocket notification
                    if solana_notification_service and user_id:
                        try:
                            logger.info(f"🔔 Attempting to send SOL deposit notification for user {user_id}")
                            result = solana_notification_service.send_deposit_notification(
                                user_id=user_id,
                                transaction_hash=tx_hash,
                                amount=amount_sol,
                                wallet_address=to_address,
                                slot=webhook_data.get('event', {}).get('slot'),
                                confirmations=1
                            )
                            logger.info(f"🔔 SOL notification result: {result}")
                        except Exception as e:
                            logger.error(f"❌ Failed to send SOL notification: {e}")

                    # Attempt to update confirmations and credit if finalized
                    _update_tx_confirmations_and_credit(tx_hash, required_confirmations=32, network=webhook_data.get('event', {}).get('network'))

                except Exception as e:
                    session.rollback()
                    logger.error(f"Error processing Solana transaction entry: {e}")

            return

        # Legacy "activity" format
        logger.info(f"Processing Solana address activity (activity): {webhook_id}, {len(activity_list)} items")
        for activity in activity_list:
            tx_hash = activity.get('hash', '')
            from_address = activity.get('fromAddress', '')
            to_address = activity.get('toAddress', '')
            value = activity.get('value', 0)

            # Only process deposits for monitored addresses
            to_crypto_address = session.query(CryptoAddress).filter_by(
                address=to_address, currency_code='SOL'
            ).first()
            logger.info(f"to_crypto_address: {to_crypto_address}")
            if not to_crypto_address:
                continue

            existing_tx = session.query(Transaction).filter_by(
                blockchain_txid=tx_hash,
                address=to_address,
                type=TransactionType.DEPOSIT
            ).first()
            if existing_tx:
                continue
            logger.info("creating transaction")    
            transaction = Transaction(
                account_id=to_crypto_address.account_id,
                type=TransactionType.DEPOSIT,
                amount=float(value),
                amount_smallest_unit=int(float(value) * 1_000_000_000),
                provider=PaymentProvider.CRYPTO,
                blockchain_txid=tx_hash,
                address=to_address,
                status=TransactionStatus.AWAITING_CONFIRMATION,
                reference_id=f"sol_deposit_{tx_hash}",
                confirmations=1,
                required_confirmations=32,
                metadata_json={
                    'webhook_id': webhook_id,
                    'from_address': from_address,
                    'to_address': to_address,
                    'processed_at': datetime.datetime.utcnow().isoformat()
                },
                precision_config={
                    "currency": "SOL",
                    "decimals": 9,
                    "smallest_unit": "lamports"
                },
            )

            # Create reservation and lock funds for deposit confirmations (legacy path)
            account = session.query(Account).filter_by(id=to_crypto_address.account_id).first()
            if account:
                lamports = int(float(value) * 1_000_000_000)
                reservation_reference = f"sol_deposit_{tx_hash}"
                existing_res = (
                    session.query(Reservation)
                    .filter_by(
                        user_id=account.user_id,
                        reference=reservation_reference,
                        type=ReservationType.RESERVE,
                    )
                    .first()
                )
                if not existing_res:
                    reservation = Reservation(
                        user_id=account.user_id,
                        reference=reservation_reference,
                        amount=float(value),
                        type=ReservationType.RESERVE,
                        status="active",
                    )
                    session.add(reservation)
                account.crypto_locked_amount_smallest_unit = (
                    (account.crypto_locked_amount_smallest_unit or 0) + lamports
                )

            session.add(transaction)
            session.commit()
            logger.info(
                f"✅ Recorded Solana deposit {tx_hash} for {to_address} amount {value} SOL and reserved funds"
            )

            _update_tx_confirmations_and_credit(tx_hash, required_confirmations=32)
                    
    except Exception as e:
        logger.error(f"Error handling Solana address activity: {e}")
        session.rollback()

@solana_webhook.route('/sol/callbacks/address-webhook', methods=['POST'])
def handle_solana_webhook():
    """Handle Solana webhook events from Alchemy API"""
    try:
        request_body = request.get_data()
        signature_header = request.headers.get('X-Alchemy-Signature', '')
        
        logger.info(f"Received Solana webhook request: {request_body} signature: {signature_header}")
        
        if not signature_header:
            logger.warning("No signature header found in Solana webhook request")
            return jsonify({"error": "No signature provided"}), 400
        
        # Verify signature
        if config('VERIFY_ALCHEMY_SIGNATURE', default='true').lower() == 'true':
            # Use simple signature format as per official Alchemy documentation
            signature_to_verify = signature_header
            
            # Additional verification: Check webhook ID in request body
            try:
                webhook_data = json.loads(request_body.decode('utf-8'))
                webhook_id_from_request = webhook_data.get('webhookId')
                expected_webhook_id = config('ALCHEMY_WEBHOOK_ID', default=None)
                
                if expected_webhook_id and webhook_id_from_request:
                    if webhook_id_from_request != expected_webhook_id:
                        logger.warning(f"❌ Webhook ID mismatch. Expected: {expected_webhook_id}, Received: {webhook_id_from_request}")
                        return jsonify({"error": "Invalid webhook ID"}), 401
                    else:
                        logger.info(f"✅ Webhook ID verified: {webhook_id_from_request}")
            except Exception as e:
                logger.warning(f"Could not verify webhook ID: {e}")
            
            str_body = str(request_body, "utf-8")
            # signature = request.headers["x-alchemy-signature"]
            # Temporary: Allow bypassing signature verification for testing
            if config('BYPASS_SIGNATURE_VERIFICATION', default='false').lower() == 'true':
                logger.warning("Bypassing signature verification for testing")
            elif not verify_alchemy_signature(str_body, signature_to_verify):
                logger.error("Invalid Alchemy webhook signature")
                return jsonify({"error": "Invalid signature"}), 401
        
        webhook_data = request.get_json()
        if not webhook_data:
            logger.error("No JSON data in Solana webhook request")
            return jsonify({"error": "No data provided"}), 400
        
        webhook_type = webhook_data.get('type', 'unknown')
        logger.info(f"Processing Solana webhook: {webhook_type}")
        
        if webhook_type == 'ADDRESS_ACTIVITY':
            handle_solana_address_activity(webhook_data)
        else:
            logger.warning(f"Unknown Solana webhook type: {webhook_type}")
        
        return jsonify({"status": "success", "type": webhook_type}), 200
        
    except Exception as e:
        logger.error(f"Error processing Solana webhook: {e}")
        return jsonify({"error": "Internal server error"}), 500


