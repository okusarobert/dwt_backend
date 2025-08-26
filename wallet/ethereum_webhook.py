#!/usr/bin/env python3
"""
Ethereum Webhook Handler for processing Alchemy webhook events
Handles both ETH and ERC-20 token transactions
"""

import json
import hmac
import hashlib
from datetime import datetime
from flask import Blueprint, request, jsonify
from decouple import config
from db.wallet import Transaction, TransactionType, TransactionStatus, PaymentProvider, CryptoAddress, Account
from db.connection import get_session
import logging
import traceback
from shared.fiat.fiat_fx_service import FiatFxService
from shared.currency_precision import AmountConverter
from shared.trading_accounting import TradingAccountingService
from db.accounting import JournalEntry, LedgerTransaction, AccountingAccount, AccountType
from decimal import Decimal
from shared.logger import setup_logging

logger = setup_logging()

# Import ETH notification service
try:
    import sys
    import redis
    import json

    # Initialize Redis client for notifications
    try:
        redis_client = redis.Redis(host='redis', port=6379, db=0, decode_responses=True)
        redis_client.ping()  # Test connection
        logger.info("✅ Successfully connected to Redis for ETH notifications")
    except Exception as e:
        redis_client = None
        logger.error(f"❌ Failed to connect to Redis: {e}")
except ImportError as e:
    logger.error(f"❌ Failed to import Redis: {e}")
    redis_client = None

# ERC-20 token configuration
# Load ERC-20 tokens from environment variable
def load_erc20_tokens():
    """Load ERC-20 token configurations from environment variable"""
    try:
        erc20_contracts_json = config('ETH_ERC20_CONTRACTS', default='{}')
        logger.info(f"Loaded ERC-20 contracts from environment: {erc20_contracts_json}")
        return json.loads(erc20_contracts_json)
    except Exception as e:
        logger.warning(f"Failed to load ERC-20 contracts from environment: {e}")
        # Fallback to hardcoded tokens
        return {
            # USDC on Ethereum mainnet
            "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48": {
                "symbol": "USDC",
                "name": "USD Coin",
                "decimals": 6,
                "smallest_unit": "units"
            },
            # USDT on Ethereum mainnet
            "0xdac17f958d2ee523a2206206994597c13d831ec7": {
                "symbol": "USDT",
                "name": "Tether USD",
                "decimals": 6,
                "smallest_unit": "units"
            }
        }

ERC20_TOKENS = load_erc20_tokens()

# Ethereum webhook blueprint
ethereum_webhook = Blueprint('ethereum_webhook', __name__)

def _alchemy_ethereum_base_url(network: str) -> str:
    network = (network or "ETH_MAINNET").upper()
    if "MAINNET" in network:
        return "https://eth-mainnet.g.alchemy.com/v2/"
    if "SEPOLIA" in network:
        return "https://eth-sepolia.g.alchemy.com/v2/"
    return "https://eth-mainnet.g.alchemy.com/v2/"

def _create_ethereum_accounting_entry(transaction: Transaction, account: Account, session_obj) -> None:
    """
    Create accounting journal entry for Ethereum deposit.
    
    Double-entry bookkeeping:
    Debit: Crypto Assets - ETH (increase asset)
    Credit: User Liabilities - ETH (increase liability)
    """
    try:
        from shared.crypto.price_utils import get_crypto_price
        from shared.fiat.forex_service import ForexService
        from decimal import Decimal
        
        # Get current crypto price in USD and UGX at transaction time
        try:
            eth_price_usd = get_crypto_price("ETH")
            if not eth_price_usd:
                logger.warning("❌ Could not get ETH price in USD")
                return
            
            # Get USD to UGX exchange rate
            forex_service = ForexService()
            usd_to_ugx = forex_service.get_exchange_rate('USD', 'UGX')
            eth_price_ugx = eth_price_usd * usd_to_ugx
            
            logger.info(f"💰 ETH price at transaction time: ${eth_price_usd:.4f} USD, {eth_price_ugx:.2f} UGX")
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to capture price at transaction time: {e}")
        
        # Use TradingAccountingService to create the journal entry
        accounting_service = TradingAccountingService(session_obj)
        
        # Get accounting accounts
        crypto_account = accounting_service.get_account_by_name("Crypto Assets - ETH")
        liability_account = accounting_service.get_account_by_name("User Liabilities - ETH")
        
        if not crypto_account or not liability_account:
            logger.warning("⚠️ Required ETH accounting accounts not found - skipping accounting entry")
            return
        
        # Format amount for description
        formatted_amount = AmountConverter.format_display_amount(transaction.amount_smallest_unit, "ETH")
        description = f"ETH deposit - {formatted_amount} (TX: {transaction.blockchain_txid[:8]}...)"
        
        # Create journal entry
        journal_entry = JournalEntry(description=description)
        session_obj.add(journal_entry)
        session_obj.flush()
        
        # Create ledger transactions
        debit_transaction = LedgerTransaction(
            journal_entry_id=journal_entry.id,
            account_id=crypto_account.id,
            debit=transaction.amount,
            credit=Decimal('0'),
        )
        
        credit_transaction = LedgerTransaction(
            journal_entry_id=journal_entry.id,
            account_id=liability_account.id,
            debit=Decimal('0'),
            credit=transaction.amount,
        )
        
        session_obj.add(debit_transaction)
        session_obj.add(credit_transaction)
        session_obj.commit()
        
        logger.info(f"📊 Created accounting entry for ETH deposit: {formatted_amount}")
        
    except Exception as e:
        logger.error(f"❌ Failed to create accounting entry for ETH deposit: {e}")
        session_obj.rollback()

def verify_alchemy_signature(payload: bytes, signature: str, signing_key: str) -> bool:
    """Verify Alchemy webhook signature"""
    try:
        expected_signature = hmac.new(
            signing_key.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        # Remove 'sha256=' prefix if present
        if signature.startswith('sha256='):
            signature = signature[7:]
        
        return hmac.compare_digest(expected_signature, signature)
    except Exception as e:
        logger.error(f"❌ Error verifying signature: {e}")
        return False

def _verify_webhook_signature(payload: bytes, signature: str) -> bool:
    """Verify Alchemy webhook signature"""
    try:
        signing_key = config('ALCHEMY_WEBHOOK_SIGNING_KEY')
        if not signing_key:
            logger.warning("⚠️ No webhook signing key configured")
            return True  # Allow in development
        
        expected_signature = hmac.new(
            signing_key.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        # Remove 'sha256=' prefix if present
        if signature and signature.startswith('sha256='):
            signature = signature[7:]
        
        return hmac.compare_digest(expected_signature, signature or '')
    except Exception as e:
        logger.error(f"❌ Error verifying signature: {e}")
        return False

def _process_address_activity(activity, network):
    """Process a single address activity from webhook"""
    try:
        tx_hash = activity.get('hash')
        from_address = activity.get('fromAddress', '').lower()
        to_address = activity.get('toAddress', '').lower()
        value = activity.get('value', '0')
        block_num = activity.get('blockNum')
        category = activity.get('category', 'external')
        
        logger.info(f"🔍 Processing activity: {tx_hash}")
        logger.info(f"   From: {from_address}")
        logger.info(f"   To: {to_address}")
        logger.info(f"   Value: {value}")
        logger.info(f"   Category: {category}")
        
        # Check if this is an ERC-20 transfer
        if category == 'token':
            return _process_erc20_transfer(activity, network)
        else:
            return _process_eth_transfer(activity, network)
            
    except Exception as e:
        logger.error(f"❌ Error processing address activity: {e}")
        return None

def _process_eth_transfer(activity, network):
    """Process native ETH transfer"""
    try:
        tx_hash = activity.get('hash')
        from_address = activity.get('fromAddress', '').lower()
        to_address = activity.get('toAddress', '').lower()
        value = activity.get('value', '0')
        block_num = activity.get('blockNum')
        
        if not tx_hash:
            logger.warning("⚠️ Transaction missing hash")
            return None
        
        # Convert value from ETH to wei (smallest unit)
        try:
            value_decimal = Decimal(str(value))
            value_wei = int(value_decimal * Decimal('1000000000000000000'))  # 10^18 wei per ETH
        except (ValueError, TypeError) as e:
            logger.error(f"❌ Invalid ETH value format: {value} - {e}")
            return None
        
        # Skip zero-value transactions
        if value_wei == 0:
            logger.info(f"⏭️ Skipping zero-value ETH transaction: {tx_hash}")
            return None
        
        return _create_transaction_record(
            tx_hash=tx_hash,
            from_address=from_address,
            to_address=to_address,
            value_smallest_unit=value_wei,
            currency='ETH',
            block_num=block_num,
            category='external'
        )
        
    except Exception as e:
        logger.error(f"❌ Error processing ETH transfer: {e}")
        return None

def _process_erc20_transfer(activity, network):
    """Process ERC-20 token transfer"""
    try:
        tx_hash = activity.get('hash')
        from_address = activity.get('fromAddress', '').lower()
        to_address = activity.get('toAddress', '').lower()
        value = activity.get('value', '0')
        block_num = activity.get('blockNum')
        
        # Get ERC-20 specific data
        erc20_metadata = activity.get('erc20Metadata', {})
        contract_address = erc20_metadata.get('contractAddress', '').lower()
        token_symbol = erc20_metadata.get('asset', 'UNKNOWN')
        token_decimals = erc20_metadata.get('decimals', 18)
        
        if not tx_hash or not contract_address:
            logger.warning(f"⚠️ ERC-20 transaction missing required data: hash={tx_hash}, contract={contract_address}")
            return None
        
        logger.info(f"🪙 Processing ERC-20 {token_symbol} transfer: {tx_hash}")
        logger.info(f"   Contract: {contract_address}")
        logger.info(f"   From: {from_address}")
        logger.info(f"   To: {to_address}")
        logger.info(f"   Value: {value} {token_symbol}")
        
        # Check if we support this token
        token_config = ERC20_TOKENS.get(contract_address)
        if not token_config:
            logger.info(f"⏭️ Unsupported ERC-20 token: {contract_address} ({token_symbol})")
            return None
        
        # Convert value to smallest unit based on token decimals
        try:
            value_decimal = Decimal(str(value))
            decimals = token_config.get('decimals', 18)
            value_smallest_unit = int(value_decimal * Decimal(10 ** decimals))
        except (ValueError, TypeError) as e:
            logger.error(f"❌ Invalid ERC-20 value format: {value} - {e}")
            return None
        
        # Skip zero-value transactions
        if value_smallest_unit == 0:
            logger.info(f"⏭️ Skipping zero-value ERC-20 transaction: {tx_hash}")
            return None
        
        return _create_transaction_record(
            tx_hash=tx_hash,
            from_address=from_address,
            to_address=to_address,
            value_smallest_unit=value_smallest_unit,
            currency=token_config['symbol'],
            block_num=block_num,
            category='erc20',
            contract_address=contract_address
        )
        
    except Exception as e:
        logger.error(f"❌ Error processing ERC-20 transfer: {e}")
        return None

def _create_transaction_record(tx_hash, from_address, to_address, value_smallest_unit, currency, block_num, category, contract_address=None):
    """Create transaction record in database"""
    session = get_session()
    try:
        # Check if we have this address in our database
        crypto_address = session.query(CryptoAddress).filter(
            CryptoAddress.address == to_address,
            CryptoAddress.currency == currency
        ).first()
        
        if not crypto_address:
            logger.info(f"⏭️ Address {to_address} not monitored for {currency}, skipping")
            return None
        
        # Check if transaction already exists
        existing_tx = session.query(Transaction).filter(
            Transaction.blockchain_txid == tx_hash,
            Transaction.currency == currency
        ).first()
        
        if existing_tx:
            logger.info(f"⏭️ Transaction {tx_hash} already processed for {currency}")
            return {"tx_hash": tx_hash, "status": "already_processed", "currency": currency}
        
        # Get user account
        account = session.query(Account).filter(
            Account.id == crypto_address.account_id
        ).first()
        
        if not account:
            logger.error(f"❌ Account not found for address {to_address}")
            return None
        
        # Create transaction record
        metadata = {
            "block_number": block_num,
            "category": category,
            "webhook_processed": True,
            "processed_at": datetime.datetime.utcnow().isoformat()
        }
        
        if contract_address:
            metadata["contract_address"] = contract_address
        
        transaction = Transaction(
            account_id=account.id,
            transaction_type=TransactionType.DEPOSIT,
            amount_smallest_unit=value_smallest_unit,
            currency=currency,
            status=TransactionStatus.PENDING,  # Will be confirmed by finality listener
            blockchain_txid=tx_hash,
            from_address=from_address,
            to_address=to_address,
            payment_provider=PaymentProvider.ALCHEMY,
            metadata_json=metadata
        )
        
        session.add(transaction)
        session.flush()
        
        # Create accounting entry
        if currency == 'ETH':
            _create_ethereum_accounting_entry(transaction, account, session)
        else:
            _create_erc20_accounting_entry(transaction, account, session, currency)
        
        # Send Redis notification
        if redis_client:
            try:
                formatted_amount = AmountConverter.format_display_amount(value_smallest_unit, currency)
                notification_data = {
                    'transaction_id': str(transaction.id),
                    'user_id': account.user_id,
                    'type': 'deposit',
                    'currency': currency,
                    'amount': formatted_amount,
                    'tx_hash': tx_hash,
                    'status': 'completed',
                    'timestamp': datetime.utcnow().isoformat()
                }
                
                redis_client.publish('transaction_updates', json.dumps(notification_data))
                logger.info(f"📧 Sent Redis notification for {formatted_amount} {currency}")
            except Exception as e:
                logger.error(f"❌ Failed to send Redis notification: {e}")
        
        session.commit()
        
        formatted_amount = AmountConverter.format_display_amount(value_smallest_unit, currency)
        logger.info(f"✅ Processed {currency} deposit: {formatted_amount} for user {account.user_id}")
        
        return {
            "tx_hash": tx_hash,
            "status": "processed",
            "amount": formatted_amount,
            "currency": currency,
            "user_id": account.user_id,
            "address": to_address
        }
        
    except Exception as e:
        logger.error(f"❌ Error creating transaction record: {e}")
        session.rollback()
        return None
    finally:
        session.close()

def _create_erc20_accounting_entry(transaction: Transaction, account: Account, session_obj, currency: str) -> None:
    """Create accounting journal entry for ERC-20 token deposit"""
    try:
        # Use TradingAccountingService to create the journal entry
        accounting_service = TradingAccountingService(session_obj)
        
        # Get accounting accounts for the specific token
        crypto_account = accounting_service.get_account_by_name(f"Crypto Assets - {currency}")
        liability_account = accounting_service.get_account_by_name(f"User Liabilities - {currency}")
        
        if not crypto_account or not liability_account:
            logger.warning(f"⚠️ Required {currency} accounting accounts not found - skipping accounting entry")
            return
        
        # Format amount for description
        formatted_amount = AmountConverter.format_display_amount(transaction.amount_smallest_unit, currency)
        description = f"{currency} deposit - {formatted_amount} (TX: {transaction.blockchain_txid[:8]}...)"
        
        # Create journal entry
        journal_entry = JournalEntry(description=description)
        session_obj.add(journal_entry)
        session_obj.flush()
        
        # Create ledger transactions
        debit_transaction = LedgerTransaction(
            journal_entry_id=journal_entry.id,
            account_id=crypto_account.id,
            debit=transaction.amount,
            credit=Decimal('0'),
        )
        
        credit_transaction = LedgerTransaction(
            journal_entry_id=journal_entry.id,
            account_id=liability_account.id,
            debit=Decimal('0'),
            credit=transaction.amount,
        )
        
        session_obj.add(debit_transaction)
        session_obj.add(credit_transaction)
        session_obj.commit()
        
        logger.info(f"📊 Created accounting entry for {currency} deposit: {formatted_amount}")
        
    except Exception as e:
        logger.error(f"❌ Failed to create accounting entry for {currency} deposit: {e}")
        session_obj.rollback()

def verify_alchemy_signature(request_body: str, signature: str) -> bool:
    """Verify Alchemy webhook signature using HMAC-SHA256 with Webhook Signing Key
    
    Based on official Alchemy documentation:
    https://www.alchemy.com/docs/reference/notify-api-quickstart#webhook-signature--security
    """
    try:
        # Use Webhook Signing Key (official Alchemy method)
        webhook_signing_key = config('ALCHEMY_ETH_WEBHOOK_KEY', default=None)
        logger.info(f"ETH Webhook Signing Key configured: {bool(webhook_signing_key)}")
        if not webhook_signing_key:
            logger.error("❌ ALCHEMY_ETH_WEBHOOK_KEY not configured")
            return False
        
        # Alchemy expects the signature to be calculated on compact JSON format
        # Parse the request body and re-serialize as compact JSON
        try:
            parsed_json = json.loads(request_body)
            compact_json = json.dumps(parsed_json, separators=(',', ':'))
            request_body_for_signature = compact_json
            logger.info(f"Using compact JSON format for ETH signature verification")
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
            logger.info(f"✅ ETH signature verified using Webhook Signing Key")
            return True
        
        logger.warning(f"❌ ETH signature verification failed. Expected: {digest[:16]}..., Received: {signature[:16]}...")
        return False
        
    except Exception as e:
        logger.error(f"Error verifying Alchemy ETH signature: {e}")
        return False

# Main webhook endpoint for Alchemy notifications
@ethereum_webhook.route('/wallet/eth/callbacks/address-webhook', methods=['POST'])
def handle_ethereum_webhook():
    """Handle Alchemy webhook notifications for Ethereum transactions"""
    try:
        request_body = request.get_data()
        signature_header = request.headers.get('X-Alchemy-Signature', '')
        
        logger.info(f"🔔 Received ETH webhook request with signature: {signature_header}")
        logger.warning(f"🔔 Received ETH webhook request with body: {request_body}")
        
        if not signature_header:
            logger.warning("❌ No signature header found in ETH webhook request 1122")
            # Check if we should bypass signature verification for testing
            if config('BYPASS_SIGNATURE_VERIFICATION', default='false').lower() == 'true':
                logger.warning("⚠️ Bypassing signature verification - no signature header but bypass enabled")
            else:
                return jsonify({"error": "No signature provided"}), 400
        
        # Verify signature (only if not bypassing and signature exists)
        if (config('VERIFY_ALCHEMY_SIGNATURE', default='true').lower() == 'true' and 
            config('BYPASS_SIGNATURE_VERIFICATION', default='false').lower() != 'true' and 
            signature_header):
            
            # Use simple signature format as per official Alchemy documentation
            signature_to_verify = signature_header
            
            # Additional verification: Check webhook ID in request body
            try:
                webhook_data = json.loads(request_body.decode('utf-8'))
                webhook_id_from_request = webhook_data.get('webhookId')
                expected_webhook_id = config('ALCHEMY_ETH_WEBHOOK_ID', default=None)
                
                if expected_webhook_id and webhook_id_from_request:
                    if webhook_id_from_request != expected_webhook_id:
                        logger.warning(f"❌ ETH Webhook ID mismatch. Expected: {expected_webhook_id}, Received: {webhook_id_from_request}")
                        return jsonify({"error": "Invalid webhook ID"}), 401
                    else:
                        logger.info(f"✅ ETH Webhook ID verified: {webhook_id_from_request}")
            except Exception as e:
                logger.warning(f"Could not verify ETH webhook ID: {e}")
            
            str_body = str(request_body, "utf-8")
            if not verify_alchemy_signature(str_body, signature_to_verify):
                logger.error("❌ Invalid Alchemy ETH webhook signature")
                return jsonify({"error": "Invalid signature"}), 401
        elif config('BYPASS_SIGNATURE_VERIFICATION', default='false').lower() == 'true':
            logger.warning("⚠️ Bypassing signature verification for testing")
        elif not signature_header:
            logger.warning("⚠️ No signature header - webhook may need signing key configuration")
        
        webhook_data = request.get_json()
        if not webhook_data:
            logger.error("❌ No JSON data in ETH webhook request")
            return jsonify({"error": "No data provided"}), 400
        
        logger.info(f"📋 Processing ETH webhook data: {json.dumps(webhook_data, indent=2)}")
        
        # Extract webhook type and event data
        webhook_type = webhook_data.get('type', '')
        webhook_event = webhook_data.get('event', {})
        
        if webhook_type == 'ADDRESS_ACTIVITY':
            # Process address activity webhook
            activity = webhook_event.get('activity', [])
            
            for tx_activity in activity:
                try:
                    # Extract transaction details
                    tx_hash = tx_activity.get('hash', '')
                    from_address = tx_activity.get('fromAddress', '').lower()
                    to_address = tx_activity.get('toAddress', '').lower()
                    value = tx_activity.get('value', 0)
                    category = tx_activity.get('category', '')
                    
                    logger.info(f"📝 Processing transaction: {tx_hash}")
                    logger.info(f"   From: {from_address}")
                    logger.info(f"   To: {to_address}")
                    logger.info(f"   Value: {value}")
                    logger.info(f"   Category: {category}")
                    
                    # Check if this is a transaction to one of our monitored addresses
                    session = get_session()
                    try:
                        # Find the crypto address in our database
                        crypto_address = session.query(CryptoAddress).filter(
                            CryptoAddress.address == to_address,
                            CryptoAddress.is_active == True
                        ).first()
                        
                        if crypto_address:
                            logger.info(f"✅ Found monitored address: {to_address}")
                            
                            # Check if transaction already exists
                            existing_tx = session.query(Transaction).filter(
                                Transaction.blockchain_txid == tx_hash
                            ).first()
                            
                            if existing_tx:
                                logger.info(f"ℹ️ Transaction {tx_hash} already exists, skipping")
                                continue
                            
                            # Process the transaction based on category
                            if category == 'external':
                                # ETH transfer
                                _process_eth_transaction(tx_activity, crypto_address, session)
                            elif category == 'token':
                                # ERC-20 token transfer
                                logger.info(f"Processing ERC-20 token transfer: {tx_hash}")
                                _process_erc20_transaction(tx_activity, crypto_address, session)
                            else:
                                logger.warning(f"ℹ️ Ignoring transaction category: {category}")
                        else:
                            logger.warning(f"ℹ️ Address {to_address} not monitored, skipping")
                            
                    finally:
                        session.close()
                        
                except Exception as e:
                    logger.error(f"❌ Error processing transaction activity: {e}")
                    continue
        
        return jsonify({"status": "success", "message": "Webhook processed"}), 200
        
    except Exception as e:
        logger.error(f"❌ Error processing ETH webhook: {e}")
        return jsonify({"error": str(e)}), 500

def _process_eth_transaction(tx_activity, crypto_address, session):
    """Process ETH transaction from webhook"""
    try:
        tx_hash = tx_activity.get('hash', '')
        
        # Handle value conversion - Alchemy sends value as float (in ETH) and rawValue as hex (in wei)
        raw_contract = tx_activity.get('rawContract', {})
        if 'rawValue' in raw_contract:
            # Use rawValue (hex wei) for precise calculation
            value_wei = int(raw_contract['rawValue'], 16)
        else:
            # Fallback: convert float ETH value to wei
            value_eth = float(tx_activity.get('value', 0))
            value_wei = int(value_eth * 10**18)  # Convert ETH to wei
        
        # Convert wei to ETH using AmountConverter
        amount_eth = AmountConverter.from_smallest_units(value_wei, 'ETH')
        
        logger.info(f"💰 ETH transaction: {amount_eth} ETH ({value_wei} wei)")
        
        # Create transaction record
        transaction = Transaction(
            account_id=crypto_address.account_id,
            type=TransactionType.DEPOSIT,
            amount=amount_eth,
            amount_smallest_unit=value_wei,
            blockchain_txid=tx_hash,
            status=TransactionStatus.COMPLETED,
            provider=PaymentProvider.CRYPTO,
            address=tx_activity.get('toAddress', ''),
            metadata_json={
                "from_address": tx_activity.get('fromAddress', ''),
                "to_address": tx_activity.get('toAddress', ''),
                "block_number": tx_activity.get('blockNum', ''),
                "webhook_processed": True
            }
        )
        
        session.add(transaction)
        
        # Get account for accounting
        account = session.query(Account).filter(Account.id == crypto_address.account_id).first()
        if account:
            # Create accounting entry
            _create_ethereum_accounting_entry(transaction, account, session)
        
        session.commit()
        
        # Send notification via Redis
        if redis_client:
            try:
                formatted_amount = AmountConverter.format_display_amount(transaction.amount_smallest_unit, 'ETH')
                notification_data = {
                    'transaction_id': str(transaction.id),
                    'user_id': account.user_id,
                    'type': 'deposit',
                    'currency': 'ETH',
                    'amount': formatted_amount,
                    'tx_hash': transaction.blockchain_txid,
                    'status': 'completed',
                    'timestamp': datetime.utcnow().isoformat()
                }
                
                redis_client.publish('transaction_updates', json.dumps(notification_data))
                logger.info(f"📧 Sent Redis notification for {formatted_amount} ETH")
            except Exception as e:
                logger.error(f"❌ Failed to send Redis notification: {e}")
        
        logger.info(f"✅ Successfully processed ETH deposit: {amount_eth} ETH")
        
    except Exception as e:
        logger.error(f"❌ Error processing ETH transaction: {e}")
        session.rollback()
        raise

def _process_erc20_transaction(tx_activity, crypto_address, session):
    """Process ERC-20 token transaction from webhook"""
    try:
        tx_hash = tx_activity.get('hash', '')
        asset = tx_activity.get('asset', 'USDT')
        raw_contract = tx_activity.get('rawContract', {})
        contract_address = raw_contract.get('address', '').lower()
        value_hex = raw_contract.get('rawValue', '0x0')
        
        # Convert hex value to integer
        value_units = int(value_hex, 16) if isinstance(value_hex, str) else int(value_hex)
        
        # Check if this is a supported ERC-20 token
        token_info = ERC20_TOKENS.get(asset)
        logger.info(f"Tokens: {ERC20_TOKENS}")
        logger.info(f"Token info: {token_info}")
        if not token_info:
            logger.info(f"ℹ️ Unsupported ERC-20 token: {contract_address}")
            return

        if token_info.get('address').lower() != contract_address.lower():
            logger.info(f"ℹ️ Unsupported ERC-20 token: {contract_address}")
            return
        
        decimals = token_info.get('decimals')
        
        # Convert to token amount
        amount_tokens = value_units / (10 ** decimals)
        
        logger.info(f"💰 {asset} transaction: {amount_tokens} {asset} ({value_units} units)")
        
        # Find the token account for this user that matches the token currency
        eth_account = session.query(Account).filter(Account.id == crypto_address.account_id).first()
        if not eth_account:
            logger.error(f"❌ ETH account not found for address {crypto_address.address}")
            return
        token_accounts = session.query(Account).filter_by(user_id=eth_account.user_id, currency=asset).all()
        token_account = None
        for t_acc in token_accounts:
            if (t_acc.precision_config or {}).get('parent_currency','').upper() == 'ETH':
                token_account = t_acc
                break

        if not token_account:
            logger.info(f"No token account found for {asset}")
            return
        if not (token_account.currency and token_account.currency.upper() == asset and (token_account.precision_config or {}).get('parent_currency','').upper() == 'ETH'):
            logger.info(f"Account does not match")
            return
            

        # Get block number for confirmation tracking
        block_number = None
        if tx_activity.get('blockNum'):
            try:
                block_number = int(tx_activity.get('blockNum'), 16)
            except (ValueError, TypeError):
                logger.warning(f"Invalid block number format: {tx_activity.get('blockNum')}")

        # Create transaction record for ERC-20 token with AWAITING_CONFIRMATION status for confirmation tracking
        transaction = Transaction(
            account_id=token_account.id,  # Use token account, not ETH account
            type=TransactionType.DEPOSIT,
            amount=Decimal(str(amount_tokens)),
            amount_smallest_unit=value_units,
            blockchain_txid=tx_hash,
            status=TransactionStatus.AWAITING_CONFIRMATION,  # Use AWAITING_CONFIRMATION for finality monitor
            provider=PaymentProvider.CRYPTO,
            address=tx_activity.get('toAddress', ''),
            confirmations=0,  # Initialize confirmations
            required_confirmations=3,  # Set required confirmations for ERC-20
            metadata_json={
                "from_address": tx_activity.get('fromAddress', ''),
                "to_address": tx_activity.get('toAddress', ''),
                "contract_address": contract_address,
                "token_symbol": asset,
                "token_decimals": decimals,
                "block_number": tx_activity.get('blockNum', ''),
                "webhook_processed": True,
                "token_type": "ERC20",
                "eth_address": crypto_address.address
            }
        )
        
        # Set block number if available
        if block_number:
            transaction.metadata_json["block_number_int"] = block_number
        
        session.add(transaction)
        
        # Create accounting entry for token using token account
        _create_token_accounting_entry(transaction, token_account, asset, session)
        
        session.commit()
        
        # Send notification via Redis
        if redis_client:
            try:
                # For ERC-20 tokens, send clean amount without currency suffix
                clean_amount = f"{amount_tokens:.6f}".rstrip('0').rstrip('.')
                notification_data = {
                    'transaction_id': str(transaction.id),
                    'user_id': token_account.user_id,
                    'type': 'deposit',
                    'currency': asset,
                    'amount': clean_amount,
                    'tx_hash': transaction.blockchain_txid,
                    'status': 'completed',
                    'timestamp': datetime.utcnow().isoformat(),
                    'token_type': 'ERC20'
                }
                
                redis_client.publish('transaction_updates', json.dumps(notification_data))
                logger.info(f"📧 Sent Redis notification for {clean_amount} {asset}")
            except Exception as e:
                logger.error(f"❌ Failed to send Redis notification: {e}")
                logger.error(traceback.format_exc())
        
        logger.info(f"✅ Successfully processed {asset} deposit: {amount_tokens} {asset}")
        
    except Exception as e:
        logger.error(f"❌ Error processing ERC-20 transaction: {e}")
        session.rollback()
        raise

def _create_token_accounting_entry(transaction: Transaction, account: Account, token_symbol: str, session_obj) -> None:
    """Create accounting journal entry for ERC-20 token deposit"""
    try:
        # Use TradingAccountingService to get accounts
        accounting_service = TradingAccountingService(session_obj)
        
        # Get or create accounting accounts
        crypto_account_name = f"Crypto Assets - {token_symbol}"
        liability_account_name = f"User Liabilities - {token_symbol}"
        
        crypto_account = accounting_service.get_account_by_name(crypto_account_name)
        if not crypto_account:
            crypto_account = AccountingAccount(
                name=crypto_account_name,
                type=AccountType.ASSET,
                parent_id=None
            )
            session_obj.add(crypto_account)
            session_obj.flush()
        
        liability_account = accounting_service.get_account_by_name(liability_account_name)
        if not liability_account:
            liability_account = AccountingAccount(
                name=liability_account_name,
                type=AccountType.LIABILITY,
                parent_id=None
            )
            session_obj.add(liability_account)
            session_obj.flush()
        
        # Format amount for description
        formatted_amount = f"{float(transaction.amount):.6f} {token_symbol}".rstrip('0').rstrip('.')
        description = f"{token_symbol} deposit - {formatted_amount} (TX: {transaction.blockchain_txid[:8]}...)"
        
        # Create journal entry
        journal_entry = JournalEntry(description=description)
        session_obj.add(journal_entry)
        session_obj.flush()
        
        # Create ledger transactions
        debit_transaction = LedgerTransaction(
            journal_entry_id=journal_entry.id,
            account_id=crypto_account.id,
            debit=transaction.amount,
            credit=Decimal('0'),
        )
        
        credit_transaction = LedgerTransaction(
            journal_entry_id=journal_entry.id,
            account_id=liability_account.id,
            debit=Decimal('0'),
            credit=transaction.amount,
        )

        session_obj.add(debit_transaction)
        session_obj.add(credit_transaction)

        logger.info(f"📊 Created accounting entry for {token_symbol} deposit: {formatted_amount}")
        
    except Exception as e:
        logger.error(f"❌ Failed to create accounting entry for {token_symbol} deposit: {e}")
        logger.error(traceback.format_exc())
        session_obj.rollback()

# Health check endpoint
@ethereum_webhook.route('/wallet/eth/callbacks/health', methods=['GET'])
def health_check():
    """Health check endpoint for Ethereum webhook"""
    return jsonify({
        "status": "healthy",
        "service": "ethereum_webhook",
        "timestamp": datetime.datetime.utcnow().isoformat()
    }), 200
