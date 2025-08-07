from flask import Flask, Blueprint, request, jsonify, g
from db.utils import token_required, model_to_dict, ensure_kafka_topic, is_admin, generate_unique_account_number
from flasgger import Swagger
import db.connection
from service import (
    create_account, get_balance, deposit, withdraw, transfer, get_transaction_history, process_credit_message,
    get_account_by_user_id, create_account_for_user, get_all_transactions
)
import threading
import os
import json
from confluent_kafka import Consumer
from db.wallet import TransactionType, Reservation, ReservationType, Transaction, PaymentProvider, TransactionStatus, AccountType
from db import Account
import logging
import datetime
from sqlalchemy.orm import Session
from decimal import Decimal
import traceback
from db import User
import hmac
import hashlib
from lib.payment_metadata import PROVIDER_METADATA_MODELS
from lib.relworx_client import RelworxApiClient
from shared.kafka_producer import get_kafka_producer
import phonenumbers
from pydantic import ValidationError
from confluent_kafka import Producer
import redis
from shared.crypto.HD import TRX as TRX_WALLET
from decouple import config
from db.wallet import CryptoAddress
import traceback
from shared.crypto import cryptos
from shared.crypto.HD import BTC, ETH, BNB, WORLD, OPTIMISM, LTC, BCH, GRS, TRX
from blockcypher_webhook import blockcypher_webhook
from shared.crypto.clients.btc import BTCWallet

app = Flask(__name__)
Swagger(app)

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
KAFKA_CREDIT_TOPIC = os.getenv("KAFKA_CREDIT_TOPIC", "wallet-credit-requests")
USER_REGISTERED_TOPIC = os.getenv("USER_REGISTERED_TOPIC", "user.registered")
WALLET_DEPOSIT_TOPIC = os.getenv(
    "WALLET_DEPOSIT_TOPIC", "wallet-deposit-requests")
WALLET_WITHDRAW_TOPIC = os.getenv(
    "WALLET_WITHDRAW_TOPIC", "wallet-withdraw-requests")


class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        if record.exc_info:
            log_record["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info)
            }
        if hasattr(record, "extra"):
            log_record.update(record.extra)
        return json.dumps(log_record)


def setup_logging():
    logger = logging.getLogger("wallet_service")
    logger.setLevel(logging.INFO)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(JSONFormatter())
    logger.handlers = []  # Remove any existing handlers
    logger.addHandler(console_handler)
    return logger


app.logger = setup_logging()

def start_merged_consumer():
    from db.connection import get_session
    logger = setup_logging()
    consumer = Consumer({
        'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS,
        'group.id': 'wallet-merged-consumer',
        'auto.offset.reset': 'earliest',
        'enable.auto.commit': False
    })
    consumer.subscribe([KAFKA_CREDIT_TOPIC, USER_REGISTERED_TOPIC, WALLET_DEPOSIT_TOPIC, WALLET_WITHDRAW_TOPIC])
    logger.info(f"[Wallet] Started merged Kafka consumer for topics: {KAFKA_CREDIT_TOPIC}, {USER_REGISTERED_TOPIC}, {WALLET_DEPOSIT_TOPIC}, {WALLET_WITHDRAW_TOPIC}")
    while True:
        msg = consumer.poll(1.0)
        if msg is None:
            continue
        if msg.error():
            logger.error(f"[Wallet] Kafka error: {msg.error()}")
            continue
        try:
            data = json.loads(msg.value().decode('utf-8'))
            topic = msg.topic()
            if topic == KAFKA_CREDIT_TOPIC:
                user_id = data['user_id']
                amount = float(data['amount'])
                reference_id = data['reference_id']
                description = data.get('description', '')
                session = get_session()
                try:
                    tx = process_credit_message(user_id, amount, reference_id, description, session)
                    session.commit()
                    logger.info(f"[Wallet] Credited user {user_id} amount {amount} (tx: {tx.id})")
                except Exception as e:
                    session.rollback()
                    logger.error(f"[Wallet] Failed to credit user {user_id}: {e}")
                finally:
                    session.close()
            elif topic == USER_REGISTERED_TOPIC:
                user_id = data.get('user_id')
                if user_id:
                    session = get_session()
                    try:
                        # Create fiat accounts for the user
                        fiat_currencies = ["UGX", "USD", "KES", "TZS"]
                        created_accounts = []
                        
                        for currency in fiat_currencies:
                            try:
                                # Check if account already exists for this currency
                                existing_account = session.query(Account).filter_by(
                                    user_id=user_id, 
                                    currency=currency,
                                    account_type=AccountType.FIAT
                                ).first()
                                
                                if not existing_account:
                                    account_number = generate_unique_account_number(session, length=10)
                                    account = Account(
                                        user_id=user_id,
                                        balance=0,
                                        locked_amount=0,
                                        currency=currency,
                                        account_type=AccountType.FIAT,
                                        account_number=account_number,
                                        label=f"{currency} Account"
                                    )
                                    session.add(account)
                                    created_accounts.append(account)
                                    logger.info(f"[Wallet] Created {currency} account for user {user_id}")
                                else:
                                    created_accounts.append(existing_account)
                                    logger.info(f"[Wallet] {currency} account already exists for user {user_id}")
                                    
                            except Exception as e:
                                logger.error(f"[Wallet] Failed to create {currency} account for user {user_id}: {e}")
                                continue
                        
                        # Commit all changes
                        # session.commit()
                        # Create crypto wallet for BTC
                        existing_account_btc = session.query(Account).filter_by(
                                    user_id=user_id,
                                    currency="BTC",
                                    account_type=AccountType.CRYPTO
                                ).first()
                        if not existing_account_btc:
                            logger.info(
                                f"[Wallet] Created BTC account for user {user_id}")
                            btc_wallet = BTCWallet(user_id=user_id, session=session, logger=logger)
                            btc_wallet.create_wallet()
                            session.commit()
                        # btc_wallet.create_address()
                        
                        logger.info(f"[Wallet] Successfully created all accounts and wallets for user {user_id}")
                        
                        # Create crypto accounts and addresses
                        
                    except Exception as e:
                        logger.error(f"[Wallet] Could not create wallets for user {user_id}: {e!r}")
                        logger.error(traceback.format_exc())
                        session.rollback()
                    finally:
                        session.close()
                else:
                    logger.info(f"[Wallet] Received registration event without user_id: {data}")
            elif topic == WALLET_DEPOSIT_TOPIC:
                user_id = data.get('user_id')
                account = get_account_by_user_id(user_id, db.connection.session)
                amount = data.get('amount')
                reference_id = data.get('reference_id')
                description = data.get('description')
                provider = data.get('provider')
                phone_number = data.get('phone_number')

                transaction = session.query(Transaction).filter_by(
                                        reference_id=reference_id).first()
                if not transaction:
                    logger.error(f"[Wallet] Transaction not found for reference_id: {reference_id}")
                    continue

                if provider == "relworx":
                    try:
                        client = RelworxApiClient()
                        resp = client.request_payment(reference_id, phone_number, amount, description)
                        provider_reference = resp.get('internal_reference')
                        transaction.provider_reference = provider_reference
                        db.connection.session.commit()

                    except Exception as e:
                        transaction.status = TransactionStatus.FAILED
                        error = {"error": "Could not request payment"}
                        transaction.metadata_json = error | transaction.metadata_json
                        db.connection.session.commit()
                        logger.error(f"[Wallet] Could not request payment for user {user_id}: {e!r}")

            elif topic == WALLET_WITHDRAW_TOPIC:
                user_id = data.get('user_id')
                amount = data.get('amount')
                reference_id = data.get('reference_id')
                description = data.get('description')
                provider = data.get('provider', 'relworx')
                phone_number = data.get('phone_number')
                metadata = data.get('metadata', {})
                # Only query for the transaction (do not create)
                tx = session.query(Transaction).filter_by(reference_id=reference_id, type=TransactionType.WITHDRAWAL).first()
                if not tx:
                    logger.error(f"[Wallet] Withdrawal transaction not found for reference_id: {reference_id}")
                    consumer.commit(msg)
                    continue
                # Call payment provider (Relworx example)
                if provider == 'relworx':
                    try:
                        client = RelworxApiClient()
                        resp = client.send_payment(reference_id, phone_number, amount, description)
                        provider_reference = resp.get('internal_reference')
                        tx.provider_reference = provider_reference
                        # Do NOT set tx.status here!
                        # Merge/validate provider metadata
                        meta = tx.metadata_json or {}
                        meta.update(resp)
                        # try:
                        #     validated_metadata = validate_and_serialize_metadata(provider, meta)
                        #     tx.metadata_json = validated_metadata
                        # except Exception as e:
                        #     logger.error(f"[Wallet] Metadata validation failed: {e!r}")
                        tx.metadata_json = meta
                        session.commit()
                    except Exception as e:
                        # Do NOT set tx.status = FAILED here!
                        meta = tx.metadata_json or {}
                        meta['error'] = f"Could not send payment: {e!r}"
                        tx.metadata_json = meta
                        session.commit()
                        logger.error(f"[Wallet] Could not request payment for user {user_id}: {e!r}")
                # TODO: Add logic for other providers if needed
                consumer.commit(msg)
        except Exception as e:
            print(f"[Wallet] Failed to process message: {e}")
            # Do not commit offset so message can be retried

def transaction_hash(user_id, amount, description, provider, account_id, timestamp):
    hash_input = json.dumps({
        "user_id": user_id,
        "amount": amount,
        "description": description,
        "provider": provider,
        "account_id": account_id,
        "timestamp": timestamp
    }, sort_keys=True)
    return hashlib.sha256(hash_input.encode("utf-8")).hexdigest()

# Ensure the Kafka topics exist before starting the consumer
ensure_kafka_topic(KAFKA_CREDIT_TOPIC)
ensure_kafka_topic(USER_REGISTERED_TOPIC)
ensure_kafka_topic(WALLET_DEPOSIT_TOPIC)
ensure_kafka_topic(WALLET_WITHDRAW_TOPIC)

# Start the merged consumer in a background thread when the app starts
threading.Thread(target=start_merged_consumer, daemon=True).start()

def validate_and_serialize_metadata(provider: str, metadata: dict) -> dict:
    model_cls = PROVIDER_METADATA_MODELS.get(provider)
    if not model_cls:
        raise ValueError(f"No metadata model for provider: {provider}")
    return model_cls(**metadata).dict()

def notify_transaction_update(transaction_id, status):
    r = redis.Redis(host='redis', port=6379, db=0)
    app.logger.info(f"Notifying transaction update: {transaction_id} - {status}")
    message = json.dumps({'transaction_id': transaction_id, 'status': status})
    r.publish('transaction_updates', message)

@app.route("/health", methods=["GET"])
@token_required
def health():
    return {"status": "ok"}, 200

@app.route("/wallet/account", methods=["POST"])
@token_required
def wallet_create_account():
    try:
        user_id = g.user.id
        account = create_account(user_id, db.connection.session)
        return jsonify(model_to_dict(account)), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/wallet/balance", methods=["GET"])
@token_required
def wallet_get_balance():
    try:
        user_id = g.user.id
        balance = get_balance(user_id, db.connection.session)
        return jsonify(balance), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/wallet/deposit", methods=["POST"])
@token_required
def wallet_deposit():
    try:
        user_id = g.user.id
        data = request.get_json()
        phone_number = data.get("phone_number")
        amount = data.get("amount")
        reference_id = data.get("reference_id")
        provider = data.get("provider", "relworx")
        description = "Deposit to Tondeka Digital"
        missing_fields = []
        if amount is None:
            missing_fields.append({"amount": "Missing required field"})
        if phone_number is None:
            missing_fields.append({"phone_number": "Missing required field"})
        if missing_fields:
            return jsonify({"error": missing_fields}), 400
        amount = float(amount)
        # Validate and format phone number using phonenumbers
        try:
            parsed_number = phonenumbers.parse(phone_number, None)
            if not phonenumbers.is_valid_number(parsed_number):
                return jsonify({"error": [{"phone_number": "Invalid phone number format."}]}), 400
            formatted_phone = phonenumbers.format_number(parsed_number, phonenumbers.PhoneNumberFormat.E164)
        except Exception as e:
            return jsonify({"error": [{"phone_number": f"Phone number parsing failed: {str(e)}"}]}), 400
        if amount < 500:
            return jsonify({"error": [{"amount": "Minimum deposit amount is 500"}]}), 400
        elif amount > 5_000_000:
            return jsonify({"error": [{"amount": "Maximum deposit amount is 5,000,000"}]}), 400
        # Validate phone number with Relworx if provider is relworx
        if provider == "relworx":
            client = RelworxApiClient()
            try:
                validation_resp = client.validate_msisdn(formatted_phone)
                if not validation_resp.get("success", True):
                    return jsonify({"error": [{"phone_number": "Invalid phone number."}]}), 400
            except Exception as e:
                return jsonify({"error": [{"phone_number": f"Phone number validation failed: {str(e)}"}]}), 400
        now = datetime.datetime.utcnow().isoformat()
        account = get_account_by_user_id(user_id, db.connection.session)
        if not account:
            return jsonify({"error": [{"account": "Account not found."}]}), 401

        existing = db.connection.session.query(Transaction).filter_by(
                reference_id=reference_id, type=TransactionType.DEPOSIT).first()
        if existing:
            return jsonify({"error": [{"reference_id": "Deposit transaction already exists for this reference_id."}]}), 409
        tx_hash = transaction_hash(user_id, amount, description, provider, account.id, now)
        metadata = {"hash": tx_hash, "phone_number": formatted_phone}
        # Validate metadata for provider BEFORE creating the transaction
        # try:
        #     validated_metadata = validate_and_serialize_metadata(provider, metadata)
        # except ValidationError as e:
        #     error_details = [
        #         {".".join(str(loc) for loc in err["loc"]): err["msg"]}
        #         for err in e.errors()
        #     ]
        #     return jsonify({"error": error_details}), 400
        # except Exception as e:
        #     return jsonify({"error": [{"metadata": f"Metadata validation failed: {str(e)}"}]}), 400
        transaction = Transaction(
            account_id=account.id,
            reference_id=reference_id,
            amount=amount,
            type=TransactionType.DEPOSIT,
            status=TransactionStatus.PENDING,
            description=description,
            provider=PaymentProvider(provider) if provider else None,
            provider_reference=None,
            metadata_json=metadata
        )
        db.connection.session.add(transaction)
        db.connection.session.commit()
        message = {
            "user_id": user_id,
            "amount": amount,
            "reference_id": reference_id,
            "description": description,
            "provider": provider,
            "phone_number": formatted_phone,
        }
        producer = get_kafka_producer()
        producer.send(WALLET_DEPOSIT_TOPIC, message)
        return jsonify({"message": "Deposit request is being processed.", "tx_reference": tx_hash}), 201
    except Exception as e:
        return jsonify({"error": [{"exception": str(e)}]}), 400

# --- /wallet/withdraw endpoint ---
@app.route("/wallet/withdraw", methods=["POST"])
@token_required
def wallet_withdraw():
    try:
        user_id = g.user.id
        data = request.get_json()
        amount = data.get("amount")
        reference_id = data.get("reference_id")
        phone_number = data.get("phone_number")
        provider = data.get("provider", "relworx")
        description = data.get("description", "Withdrawal from TOI BETS")
        missing_fields = []
        if amount is None:
            missing_fields.append({"amount": "Missing required field"})
        if reference_id is None:
            missing_fields.append({"reference_id": "Missing required field"})
        if phone_number is None:
            missing_fields.append({"phone_number": "Missing required field"})
        if missing_fields:
            return jsonify({"error": missing_fields}), 400
        amount = float(amount)
        try:
            parsed_number = phonenumbers.parse(phone_number, None)
            if not phonenumbers.is_valid_number(parsed_number):
                return jsonify({"error": [{"phone_number": "Invalid phone number format."}]}), 400
            formatted_phone = phonenumbers.format_number(parsed_number, phonenumbers.PhoneNumberFormat.E164)
        except Exception as e:
            return jsonify({"error": [{"phone_number": f"Phone number parsing failed: {str(e)}"}]}), 400
        session = db.connection.session
        account = get_account_by_user_id(user_id, session)
        if not account:
            return jsonify({"error": [{"account": "Account not found."}]}), 401
        # Check for duplicate
        existing = session.query(Transaction).filter_by(reference_id=reference_id, type=TransactionType.WITHDRAWAL).first()
        if existing:
            return jsonify({"error": [{"reference_id": "Withdrawal transaction already exists for this reference_id."}]}), 409
        # Reservation logic: check available balance and lock amount atomically
        from decimal import Decimal
        try:
            session.refresh(account, with_for_update=True)
            available = float(account.balance) - float(account.locked_amount)
            if available < amount:
                return jsonify({"error": [{"amount": "Insufficient available balance."}]}), 400
            account.locked_amount += Decimal(amount)
            # session.add(account)
            metadata = {"reference": reference_id, "phone_number": formatted_phone, "amount": amount, "description": description}
            tx = Transaction(
                account_id=account.id,
                reference_id=reference_id,
                amount=amount,
                type=TransactionType.WITHDRAWAL,
                status=TransactionStatus.PENDING,
                description=description,
                provider=PaymentProvider(provider) if provider else None,
                provider_reference=None,
                metadata_json=metadata
            )
            session.add(tx)
        except Exception as e:
            session.rollback()
            return jsonify({"error": [{"exception": f"Reservation failed: {str(e)}"}]}), 400
        session.commit()
        # Enqueue the withdrawal request to Kafka for async processing
        message = {
            "user_id": user_id,
            "amount": amount,
            "reference_id": reference_id,
            "description": description,
            "provider": provider,
            "phone_number": formatted_phone,
            "metadata": metadata
        }
        producer = get_kafka_producer()
        producer.send(WALLET_WITHDRAW_TOPIC, message)
        return jsonify({"message": "Withdrawal request is being processed.", "tx_reference": reference_id}), 201
    except Exception as e:
        return jsonify({"error": [{"exception": str(e)}]}), 400

@app.route("/wallet/transfer", methods=["POST"])
@token_required
def wallet_transfer():
    try:
        from_user_id = g.user.id
        data = request.get_json()
        to_user_id = int(data.get("to"))
        amount = float(data.get("amount"))
        reference_id = data.get("reference_id")
        description = data.get("description")
        txs = transfer(from_user_id, to_user_id, amount, reference_id, description, db.connection.session)
        return jsonify([model_to_dict(tx) for tx in txs]), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/wallet/transactions", methods=["GET"])
@token_required
def wallet_transactions():
    try:
        user_id = g.user.id
        limit = int(request.args.get("limit", 20))
        offset = int(request.args.get("offset", 0))
        txs = get_transaction_history(user_id, db.connection.session, limit=limit, offset=offset)
        return jsonify([model_to_dict(tx) for tx in txs]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/wallet/balance', methods=['GET'])
@token_required
def wallet_balance():
    # Always use authenticated user
    user_id = None
    if hasattr(g, 'user') and g.user is not None:
        user_id = g.user.id
    if not user_id:
        return jsonify({"error": "User not authenticated"}), 401
    try:
        balance = get_balance(user_id, db.connection.session)
        return jsonify({"success": True, "balance": balance["balance"], "available_balance": balance["available_balance"]})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/wallet/reserve', methods=['POST'])
@token_required
def wallet_reserve():
    app.logger.info("Wallet reserve request")
    user_id = g.user.id
    data = request.get_json()
    amount = float(data.get('amount'))
    reference = data.get('reference')
    if not amount or not reference:
        return jsonify({"success": False, "error": "Missing amount or reference"}), 400
    session = db.connection.session
    try:
        # Idempotency check
        existing = session.query(Reservation).filter_by(
            user_id=user_id, reference=reference, type=ReservationType.RESERVE
        ).first()
        if existing:
            if existing.status == "success":
                return jsonify({"success": True}), 200
            else:
                return jsonify({"success": False, "error": "Previous reservation failed"}), 400
        # Get user's default currency
        user = session.query(User).filter_by(id=user_id).first()
        if not user or not user.default_currency:
            status = "failed"
            session.add(Reservation(user_id=user_id, reference=reference, amount=amount, type=ReservationType.RESERVE, status=status))
            app.logger.info(f"No default currency set for user {user_id}")
            session.commit()
            return jsonify({"success": False, "error": "No default currency set for user"}), 404
        # Find the user's account for the default currency
        account = session.query(Account).filter_by(user_id=user_id, currency=user.default_currency).with_for_update().first()
        if not account:
            status = "failed"
            session.add(Reservation(user_id=user_id, reference=reference, amount=amount, type=ReservationType.RESERVE, status=status))
            app.logger.info(f"No account found for user {user_id} with currency {user.default_currency}")
            session.commit()
            return jsonify({"success": False, "error": "No wallet/account found for user's default currency"}), 404
        if account.available_balance() < amount:
            status = "failed"
            session.add(Reservation(user_id=user_id, reference=reference, amount=amount, type=ReservationType.RESERVE, status=status))
            app.logger.info(f"Insufficient funds for user {user_id}")
            session.commit()
            return jsonify({"success": False, "error": "Insufficient funds"}), 400
        account.locked_amount += Decimal(amount)
        session.add(account)
        session.add(Reservation(user_id=user_id, reference=reference, amount=amount, type=ReservationType.RESERVE, status="success"))
        session.commit()
        return jsonify({"success": True}), 200
    except Exception as e:
        session.rollback()
        app.logger.info(f"Exception during wallet reserve: {e!r}")
        app.logger.error(traceback.format_exc())
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/wallet/release', methods=['POST'])
@token_required
def wallet_release():
    user_id = g.user.id
    data = request.get_json()
    amount = float(data.get('amount'))
    reference = data.get('reference')
    if not amount or not reference:
        return jsonify({"success": False, "error": "Missing amount or reference"}), 400
    session = db.connection.session
    try:
        with session.begin():
            # Idempotency check
            existing = session.query(Reservation).filter_by(
                user_id=user_id, reference=reference, type=ReservationType.RELEASE
            ).first()
            if existing:
                if existing.status == "success":
                    return jsonify({"success": True}), 200
                else:
                    return jsonify({"success": False, "error": "Previous release failed"}), 400
            account = session.query(Account).filter_by(user_id=user_id).with_for_update().first()
            if not account:
                status = "failed"
                session.add(Reservation(user_id=user_id, reference=reference, amount=amount, type=ReservationType.RELEASE, status=status))
                return jsonify({"success": False, "error": "Account not found"}), 404
            if account.locked_amount < amount:
                status = "failed"
                session.add(Reservation(user_id=user_id, reference=reference, amount=amount, type=ReservationType.RELEASE, status=status))
                return jsonify({"success": False, "error": "Not enough locked funds to release"}), 400
            account.locked_amount -= amount
            session.add(account)
            session.add(Reservation(user_id=user_id, reference=reference, amount=amount, type=ReservationType.RELEASE, status="success"))
        return jsonify({"success": True}), 200
    except Exception as e:
        session.rollback()
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/admin/wallets/<int:user_id>', methods=['GET'])
@token_required
@is_admin
def admin_get_user_wallet(user_id):
    session = db.connection.session
    app.logger.info(f"Getting wallet for user {user_id}")
    try:
        account = get_account_by_user_id(user_id, session)
        if not account:
            app.logger.info(f"Account not found for user {user_id}")
            print(f"Account not found for user {user_id}")
            return jsonify({'error': 'Account not found for user'}), 404
        balance = get_balance(user_id, session)
        transactions = get_transaction_history(user_id, session, limit=10, offset=0)
        return jsonify({
            'account': model_to_dict(account),
            'balance': balance,
            'transactions': [model_to_dict(tx) for tx in transactions]
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/admin/wallets/<int:user_id>/create', methods=['POST'])
@token_required
@is_admin
def create_wallet(user_id):
    data = request.get_json() or {}
    currency = data.get("currency")
    label = data.get("label", "main")
    if not currency:
        return jsonify({"error": "currency is required"}), 400
    account_number = generate_unique_account_number(db.connection.session, length=10)
    wallet = Account(
        user_id=user_id,
        currency=currency,
        balance=0.0,
        label=label,
        account_number=account_number
    )
    db.connection.session.add(wallet)
    db.connection.session.commit()
    return jsonify({
        "account_number": wallet.account_number,
        "user_id": wallet.user_id,
        "currency": wallet.currency,
        "balance": wallet.balance,
        "label": wallet.label
    }), 201

@app.route('/admin/wallets/<int:user_id>/credit', methods=['POST'])
@token_required
@is_admin
def admin_credit_user(user_id):
    """
    Credit a user's wallet. If 'account_number' is provided in the POST body, credit that specific account for the user.
    Otherwise, credit the first account found for the user.
    """
    data = request.get_json()
    amount = Decimal(str(data['amount']))
    reference = data.get('reference', 'admin_credit')
    note = data.get('note', '')
    account_number = data.get('account_number')
    session = db.connection.session
    try:
        if account_number:
            account = session.query(Account).filter_by(user_id=user_id, account_number=account_number).first()
            if not account:
                return jsonify({'error': f'Account with account_number {account_number} not found for user {user_id}'}), 404
        else:
            account = get_account_by_user_id(user_id, session)
            if not account:
                return jsonify({'error': 'Account not found'}), 404
        account.balance += amount
        # Optionally log transaction here
        session.commit()
        return jsonify({'message': f'Credited {amount} to user {user_id} (account_number: {account.account_number})', 'account': model_to_dict(account)}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/admin/wallets/<int:user_id>/debit', methods=['POST'])
@token_required
@is_admin
def admin_debit_user(user_id):
    """
    Debit a user's wallet. If 'account_number' is provided in the POST body, debit that specific account for the user.
    Otherwise, debit the first account found for the user.
    """
    data = request.get_json()
    amount = Decimal(str(data['amount']))
    reference = data.get('reference', 'admin_debit')
    note = data.get('note', '')
    account_number = data.get('account_number')
    session = db.connection.session
    try:
        if account_number:
            account = session.query(Account).filter_by(user_id=user_id, account_number=account_number).first()
            if not account:
                return jsonify({'error': f'Account with account_number {account_number} not found for user {user_id}'}), 404
        else:
            account = get_account_by_user_id(user_id, session)
            if not account:
                return jsonify({'error': 'Account not found'}), 404
        if account.available_balance() < amount:
            return jsonify({'error': 'Insufficient funds'}), 400
        account.balance -= amount
        # Optionally log transaction here
        session.commit()
        return jsonify({'message': f'Debited {amount} from user {user_id} (account_number: {account.account_number})', 'account': model_to_dict(account)}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/admin/wallets/transfer', methods=['POST'])
@token_required
@is_admin
def admin_transfer_between_users():
    data = request.get_json()
    from_account_number = data['from_account_number']
    to_account_number = data['to_account_number']
    amount = Decimal(str(data['amount']))
    reference = data.get('reference', 'admin_transfer')
    note = data.get('note', '')
    session = db.connection.session
    try:
        from_account = session.query(Account).filter_by(account_number=from_account_number).first()
        to_account = session.query(Account).filter_by(account_number=to_account_number).first()
        if not from_account or not to_account:
            return jsonify({'error': 'Account not found'}), 404
        if from_account.currency != to_account.currency:
            return jsonify({'error': 'Cannot transfer between accounts with different currencies.'}), 400
        if from_account.available_balance() < amount:
            return jsonify({'error': 'Insufficient funds'}), 400
        from_account.balance -= amount
        # from_account.available_balance -= amount
        to_account.balance += amount
        # to_account.available_balance += amount
        # Optionally log transaction here
        session.commit()
        return jsonify({'message': f'Transferred {amount} from account {from_account_number} to account {to_account_number}', 'from_account': model_to_dict(from_account), 'to_account': model_to_dict(to_account)}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/admin/wallets/<int:user_id>/accounts', methods=['GET'])
@token_required
@is_admin
def admin_get_all_user_wallets(user_id):
    session = db.connection.session
    app.logger.info(f"Getting all wallets for user {user_id}")
    try:
        accounts = session.query(Account).filter_by(user_id=user_id).all()
        if not accounts:
            app.logger.info(f"No accounts found for user {user_id}")
            return jsonify({'error': 'No accounts found for user'}), 404
        result = []
        for account in accounts:
            # Get balance for this account
            balance = {
                'balance': float(account.balance),
                'available_balance': float(account.balance) - float(account.locked_amount)
            }
            # Get recent transactions for this account
            transactions = session.query(db.wallet.Transaction) \
                .filter(db.wallet.Transaction.account_id == account.id) \
                .order_by(db.wallet.Transaction.created_at.desc()) \
                .limit(10).all()
            result.append({
                'account': model_to_dict(account),
                'balance': balance,
                'transactions': [model_to_dict(tx) for tx in transactions]
            })
        return jsonify({'accounts': result}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/admin/wallets/<account_number>/lock', methods=['POST'])
@token_required
@is_admin
def admin_lock_funds(account_number):
    data = request.get_json()
    amount = Decimal(str(data['amount']))
    reference = data.get('reference', '')
    session = db.connection.session
    try:
        account = session.query(Account).filter_by(account_number=account_number).first()
        if not account:
            return jsonify({'error': 'Account not found'}), 404
        # Check for existing reservation with same reference
        existing = session.query(Reservation).filter_by(
            user_id=account.user_id, reference=reference, type=ReservationType.RESERVE
        ).first()
        if existing:
            if existing.status == "success":
                return jsonify({'message': 'Funds already locked for this reference', 'reservation': model_to_dict(existing)}), 200
            else:
                return jsonify({'error': 'Previous reservation failed'}), 400
        if account.available_balance() < amount:
            return jsonify({'error': 'Insufficient available funds'}), 400
        account.locked_amount += amount
        reservation = Reservation(
            user_id=account.user_id,
            reference=reference,
            amount=amount,
            type=ReservationType.RESERVE,
            status="success"
        )
        session.add(account)
        session.add(reservation)
        session.commit()
        return jsonify({'message': f'Locked {amount} in account {account_number}', 'account': model_to_dict(account), 'reservation': model_to_dict(reservation)}), 200
    except Exception as e:
        session.rollback()
        return jsonify({'error': str(e)}), 400

@app.route('/admin/transactions', methods=['GET'])
@token_required
@is_admin
def admin_list_transactions():
    session = db.connection.session
    try:
        limit = int(request.args.get("limit", 20))
        offset = int(request.args.get("offset", 0))
        transactions = get_all_transactions(session, limit=limit, offset=offset)
        return jsonify(transactions), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.teardown_request
def remove_session(exception=None):
    session = db.connection.session
    if exception:
        try:
            session.rollback()
        except Exception:
            pass
    else:
        try:
            session.commit()
        except Exception:
            pass
    try:
        session.remove()
    except Exception:
        pass


def verify_relworx_signature(request, webhook_key, url="https://8678e0da3e7a.ngrok-free.app/api/v1/webhook/relworx/request-payment"):
    # url = request.url
    # url = "https://8678e0da3e7a.ngrok-free.app/api/v1/webhook/relworx/request-payment"
    signature_header = request.headers.get("Relworx-Signature")
    if not signature_header:
        app.logger.error(f"Missing signature header for {url}")
        return False, "Missing signature header"
    try:
        parts = dict(item.split("=") for item in signature_header.split(","))
        timestamp = parts["t"]
        signature = parts["v"]
    except Exception:
        app.logger.error(f"Invalid signature header format for {url}")
        return False, "Invalid signature header format"
    data = request.get_json(force=True)
    params = {
        "status": data.get("status"),
        "customer_reference": data.get("customer_reference"),
        "internal_reference": data.get("internal_reference"),
    }
    signed_data = url + timestamp
    for key in sorted(params.keys()):
        signed_data += str(key) + str(params[key])
    computed_signature = hmac.new(
        webhook_key.encode(),
        signed_data.encode(),
        hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(computed_signature, signature):
        app.logger.error(f"Invalid signature for {url}")
        return False, "Invalid signature"
    return True, data

def mark_transaction_failed_by_internal_reference(internal_reference, error_reason=None):
    from db.connection import session
    from db.wallet import Transaction, TransactionStatus
    tx = session.query(Transaction).filter_by(provider_reference=internal_reference).first()
    if tx and tx.status != TransactionStatus.FAILED:
        tx.status = TransactionStatus.FAILED
        if error_reason:
            meta = tx.metadata_json or {}
            meta['error'] = error_reason
            tx.metadata_json = meta
        session.commit()

@app.route("/webhook/relworx/request-payment", methods=["POST"])
def relworx_request_payment_webhook():
    """
    Webhook endpoint for Relworx request payment status updates.
    Updates the deposit transaction status and metadata, and credits the wallet on success.
    """
    webhook_key = os.environ.get("RELWORX_WEBHOOK_KEY")
    data = request.get_json(force=True)
    internal_reference = data.get("internal_reference")
    if not webhook_key:
        if internal_reference:
            mark_transaction_failed_by_internal_reference(internal_reference, "Webhook key not configured")
        return jsonify({"error": "Webhook key not configured"}), 500
    app_host = config("APP_HOST")
    url = f"{app_host}/api/v1/webhook/relworx/request-payment"
    valid, result = verify_relworx_signature(request, webhook_key, url)
    if not valid:
        app.logger.error(f"Invalid signature for relworx request payment webhook: {result}")
        if internal_reference:
            mark_transaction_failed_by_internal_reference(internal_reference, result)
        return jsonify({"error": result}), 400
    data = result
    # --- Business logic ---
    from db.connection import session
    tx = session.query(Transaction).filter_by(provider_reference=internal_reference, type=TransactionType.DEPOSIT).first()
    if not tx:
        app.logger.error(
            f"Transaction not found for internal reference: {internal_reference}")
        return jsonify({"error": "Transaction not found"}), 404
    # Only credit if status is changing from PENDING to COMPLETED
    if tx.status == TransactionStatus.PENDING and data.get("status") == "success":
        account = session.query(Account).filter_by(id=tx.account_id).with_for_update().first()
        if account:
            account.balance += Decimal(str(tx.amount))
            # session.add(account)
        tx.status = TransactionStatus.COMPLETED
        transaction_id = tx.reference_id
        status = tx.status.value
        notify_transaction_update(transaction_id, status)
    elif data.get("status") == "success":
        # Already completed, do nothing
        pass
    else:
        tx.status = TransactionStatus.FAILED
        transaction_id = tx.reference_id
        status = tx.status.value
        notify_transaction_update(transaction_id, status)
    # Merge webhook data into metadata_json
    meta = tx.metadata_json or {}
    meta.update(data)
    # try:
    #     validated_metadata = validate_and_serialize_metadata(tx.provider.value if tx.provider else "relworx", meta)
    # except Exception as e:
    #     app.logger.error(f"Metadata validation failed: {str(e)}")
    #     return jsonify({"error": f"Metadata validation failed: {str(e)}"}), 400
    tx.metadata_json = meta
    session.commit()
    return jsonify({"status": "ok"}), 200

@app.route("/webhook/relworx/send-payment", methods=["POST"])
def relworx_send_payment_webhook():
    """
    Webhook endpoint for Relworx send payment (withdrawal) status updates.
    Updates the withdrawal transaction status and metadata.
    """
    webhook_key = os.environ.get("RELWORX_WEBHOOK_KEY")
    data = request.get_json(force=True)
    internal_reference = data.get("internal_reference")
    if not webhook_key:
        if internal_reference:
            mark_transaction_failed_by_internal_reference(internal_reference, "Webhook key not configured")
        return jsonify({"error": "Webhook key not configured"}), 500
    app_host = config("APP_HOST")
    url = f"{app_host}/api/v1/webhook/relworx/send-payment"
    valid, result = verify_relworx_signature(request, webhook_key, url)
    if not valid:
        if internal_reference:
            mark_transaction_failed_by_internal_reference(internal_reference, result)
        return jsonify({"error": result}), 400
    data = result
    # --- Business logic ---
    from db.connection import session
    from decimal import Decimal
    tx = session.query(Transaction).filter_by(provider_reference=internal_reference, type=TransactionType.WITHDRAWAL).first()
    if not tx:
        return jsonify({"error": "Transaction not found"}), 404
    account = session.query(Account).filter_by(id=tx.account_id).with_for_update().first()
    # Update status based on webhook
    if data.get("status") == "success":
        if tx.status == TransactionStatus.PENDING:
            if account:
                account.locked_amount -= Decimal(str(tx.amount))
                account.balance -= Decimal(str(tx.amount))
                # session.add(account)
            tx.status = TransactionStatus.COMPLETED
            transaction_id = tx.reference_id
            status = tx.status.value
            notify_transaction_update(transaction_id, status)
    else:  # failure or any non-success
        if tx.status == TransactionStatus.PENDING:
            if account:
                account.locked_amount -= Decimal(str(tx.amount))
                account.balance += Decimal(str(tx.amount))
                # session.add(account)
            tx.status = TransactionStatus.FAILED
            transaction_id = tx.reference_id
            status = tx.status.value
            notify_transaction_update(transaction_id, status)
    # Merge webhook data into metadata_json
    meta = tx.metadata_json or {}
    meta.update(data)
    try:
        validated_metadata = validate_and_serialize_metadata(tx.provider.value if tx.provider else "relworx", meta)
    except Exception as e:
        return jsonify({"error": f"Metadata validation failed: {str(e)}"}), 400
    tx.metadata_json = validated_metadata
    session.commit()
    return jsonify({"status": "ok"}), 200

# schemas_bp = Blueprint('/schemas', __name__)

@app.route('/payment-providers/schemas', methods=['GET'])
def get_provider_schemas():
    """
    Returns the JSON schema for each payment provider's metadata.
    """
    return jsonify({
        provider: model.schema() for provider, model in PROVIDER_METADATA_MODELS.items()
    })

@app.route("/test/transaction-status", methods=["POST"])
def test_transaction_status():
    data = request.get_json() or {}
    transaction_id = data.get("transaction_id", "test-tx-123")
    status = data.get("status", "pending")
    notify_transaction_update(transaction_id, status)
    return jsonify({"message": "Dummy transaction sent", "data": {"transaction_id": transaction_id, "status": status}}), 200

@app.route("/admin/create-crypto-addresses/<int:user_id>", methods=["POST"])
@token_required
@is_admin
def create_crypto_addresses_for_user(user_id):
    """
    Manually create crypto addresses for an existing user.
    This is useful for users who were registered before mnemonics were configured.
    """
    from db.connection import session
    from shared.crypto import cryptos
    
    try:
        # Check if user exists
        user = session.query(User).filter_by(id=user_id).first()
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Get crypto wallet classes
        crypto_wallet_classes = {
            "BTC": BTC,
            "ETH": ETH,
            "BNB": BNB,
            "WORLD": WORLD,
            "OPTIMISM": OPTIMISM,
            "LTC": LTC,
            "BCH": BCH,
            "GRS": GRS,
            "TRX": TRX
        }
        
        created_addresses = []
        
        # Get all crypto currencies from cryptos.py
        for crypto in cryptos.accounts:
            symbol = crypto["symbol"]
            is_chain = crypto.get("is_chain", False)
            parent_chain = crypto.get("parent_chain")
            
            # Only create addresses for chains (not tokens)
            if not is_chain:
                continue
                
            # Check if wallet class exists
            if symbol not in crypto_wallet_classes:
                continue
                
            # Check if crypto account exists
            crypto_account = session.query(Account).filter_by(
                user_id=user_id,
                currency=symbol,
                account_type=AccountType.CRYPTO
            ).first()
            
            if not crypto_account:
                app.logger.warning(f"[Admin] No crypto account found for {symbol} user {user_id}")
                continue
            
            # Check if address already exists
            existing_address = session.query(CryptoAddress).filter_by(
                account_id=crypto_account.id
            ).first()
            
            if existing_address:
                app.logger.info(f"[Admin] Address already exists for {symbol} user {user_id}")
                continue
            
            try:
                wallet_class = crypto_wallet_classes[symbol]
                wallet = wallet_class()
                
                # Get mnemonic from config
                mnemonic_key = f"{symbol}_MNEMONIC"
                mnemonic = config(mnemonic_key, default=None)
                
                if mnemonic:
                    wallet = wallet.from_mnemonic(mnemonic=mnemonic)
                    index = crypto_account.id - 1
                    
                    # Generate new address
                    address_gen, priv_key, pub_key = wallet.new_address(index=index)
                    
                    # Create crypto address record
                    crypto_address = CryptoAddress(
                        account_id=crypto_account.id,
                        address=address_gen,
                        label=symbol,
                        is_active=True,
                        currency_code=symbol,
                        address_type="hd_wallet"
                    )
                    session.add(crypto_address)
                    created_addresses.append({
                        "symbol": symbol,
                        "address": address_gen,
                        "account_id": crypto_account.id
                    })
                    app.logger.info(f"[Admin] Created {symbol} address for user {user_id}: {address_gen}")
                else:
                    app.logger.warning(f"[Admin] No mnemonic configured for {symbol}")
                    
            except Exception as e:
                app.logger.error(f"[Admin] Failed to create {symbol} address for user {user_id}: {e}")
                continue
        
        session.commit()
        return jsonify({
            "message": f"Created {len(created_addresses)} crypto addresses for user {user_id}",
            "addresses": created_addresses
        }), 200
        
    except Exception as e:
        session.rollback()
        app.logger.error(f"[Admin] Error creating crypto addresses for user {user_id}: {e}")
        return jsonify({"error": str(e)}), 500

# Register the blueprint with the app
# app.register_blueprint(schemas_bp)
app.register_blueprint(blockcypher_webhook)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000, debug=True)
