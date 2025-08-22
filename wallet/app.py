from flask import Flask, Blueprint, request, jsonify, g
from db.utils import token_required, model_to_dict, ensure_kafka_topic, is_admin, generate_unique_account_number
from flasgger import Swagger
import db.connection
from service import (
    create_account, get_balance, deposit, withdraw, transfer, get_transaction_history, process_credit_message,
    get_account_by_user_id, create_account_for_user, get_all_transactions
)
from trading_service import TradingService
from portfolio_service import get_dashboard_summary
import threading
import os
import json
from confluent_kafka import Consumer
from db.wallet import TransactionType, Reservation, ReservationType, Transaction, PaymentProvider, TransactionStatus, AccountType, PortfolioSnapshot, Trade, TradeType, TradeStatus, PaymentMethod, Voucher, VoucherStatus
from db import Account
import logging
import datetime
import time
from sqlalchemy.orm import Session
from decimal import Decimal
import traceback
from db import User
import hmac
import hashlib
from lib.payment_metadata import PROVIDER_METADATA_MODELS
from lib.relworx_client import RelworxApiClient
from shared.kafka_producer import get_kafka_producer
from shared.fiat.forex_service import forex_service
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
from shared.crypto.price_cache_service import get_price_cache_service, get_cached_prices, refresh_cached_prices
from shared.crypto.price_refresh_service import start_price_refresh_service
from blockcypher_webhook import blockcypher_webhook
from solana_webhook import solana_webhook
from shared.crypto.clients.btc import BTCWallet,BitcoinConfig
from shared.crypto.clients.tron import TronWallet, TronWalletConfig

app = Flask(__name__)

Swagger(app)

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
KAFKA_CREDIT_TOPIC = os.getenv("KAFKA_CREDIT_TOPIC", "wallet-credit-requests")
USER_REGISTERED_TOPIC = os.getenv("USER_REGISTERED_TOPIC", "user.registered")
WALLET_DEPOSIT_TOPIC = os.getenv(
    "WALLET_DEPOSIT_TOPIC", "wallet-deposit-requests")
WALLET_WITHDRAW_TOPIC = os.getenv(
    "WALLET_WITHDRAW_TOPIC", "wallet-withdraw-requests")

# Initialize trading service
trading_service = TradingService()

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

# Trading Endpoints

@app.route('/api/trading/prices', methods=['GET'])
@token_required
def get_trading_crypto_prices(current_user):
    """Get current crypto prices in UGX"""
    try:
        # Get all supported cryptocurrencies with UGX prices
        cryptocurrencies = ['BTC', 'ETH', 'SOL', 'BNB', 'USDT', 'ADA', 'MATIC']
        prices = {}
        
        for crypto in cryptocurrencies:
            try:
                usd_price = trading_service.get_crypto_price(crypto, 'USD')
                ugx_price = trading_service.get_crypto_price(crypto, 'UGX')
                
                prices[crypto] = {
                    'price_ugx': ugx_price,
                    'price_usd': usd_price,
                    'change_24h': 0,  # TODO: Implement 24h change
                    'last_updated': datetime.datetime.utcnow().isoformat()
                }
            except Exception as e:
                app.logger.warning(f"Failed to get price for {crypto}: {e}")
                continue
        
        return jsonify(prices)
    except Exception as e:
        app.logger.error(f"Error getting crypto prices: {e}")
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/trading/exchange-rate/<from_currency>/<to_currency>', methods=['GET'])
@token_required
def get_exchange_rate(current_user, from_currency, to_currency):
    """Get live exchange rate between two currencies"""
    try:
        trading_service = TradingService()
        rate = trading_service.get_exchange_rate(from_currency, to_currency)
        
        return jsonify({
            "success": True,
            "from_currency": from_currency,
            "to_currency": to_currency,
            "rate": rate
        })
    except Exception as e:
        app.logger.error(f"Error getting exchange rate: {e}")
        return jsonify({"success": False, "error": str(e)}), 400

# Wallet Crypto Management Endpoints
# ---------------------------------------------


@app.route('/wallet/crypto/<crypto>/deposit/address', methods=['POST'])
@token_required
def generate_deposit_address(current_user, crypto):
    """Generate a deposit address for the specified cryptocurrency"""
    try:
        crypto = crypto.upper()
        session = db.connection.get_session()
        
        # Validate supported crypto
        supported_cryptos = ['BTC', 'ETH', 'SOL', 'BNB', 'USDT', 'TRX', 'LTC']
        if crypto not in supported_cryptos:
            return jsonify({"success": False, "error": f"Unsupported cryptocurrency: {crypto}"}), 400
        
        # Check if user already has a deposit address for this crypto
        existing_address = session.query(CryptoAddress).filter(
            CryptoAddress.user_id == current_user.id,
            CryptoAddress.currency == crypto,
            CryptoAddress.address_type == 'deposit'
        ).first()
        
        if existing_address:
            return jsonify({
                "success": True,
                "address": existing_address.address,
                "memo": existing_address.memo,
                "currency": crypto
            })
        
        # Generate new address based on crypto type
        if crypto == 'BTC':
            btc_wallet = BTC()
            address = btc_wallet.create_address()
        elif crypto == 'ETH':
            eth_wallet = ETH()
            address = eth_wallet.create_address()
        elif crypto == 'TRX':
            trx_wallet = TRX()
            address = trx_wallet.create_address()
        elif crypto == 'BNB':
            bnb_wallet = BNB()
            address = bnb_wallet.create_address()
        elif crypto == 'LTC':
            ltc_wallet = LTC()
            address = ltc_wallet.create_address()
        else:
            # For other cryptos, use a placeholder address generation
            # In production, implement proper wallet generation for each crypto
            address = f"generated_{crypto.lower()}_address_{current_user.id}"
        
        # Save the address to database
        crypto_address = CryptoAddress(
            user_id=current_user.id,
            currency=crypto,
            address=address,
            address_type='deposit',
            is_active=True
        )
        
        session.add(crypto_address)
        session.commit()
        
        return jsonify({
            "success": True,
            "address": address,
            "currency": crypto
        })
        
    except Exception as e:
        app.logger.error(f"Error generating deposit address for {crypto}: {e}")
        if 'session' in locals():
            session.rollback()
        return jsonify({"success": False, "error": str(e)}), 400
    finally:
        if 'session' in locals():
            session.close()

@app.route('/wallet/crypto/<crypto>/withdraw', methods=['POST'])
@token_required
def withdraw_crypto(current_user, crypto):
    """Withdraw cryptocurrency to an external address"""
    try:
        crypto = crypto.upper()
        data = request.get_json()
        
        if not data:
            return jsonify({"success": False, "error": "No data provided"}), 400
        
        amount = data.get('amount')
        address = data.get('address')
        
        if not amount or not address:
            return jsonify({"success": False, "error": "Amount and address are required"}), 400
        
        # Validate supported crypto
        supported_cryptos = ['BTC', 'ETH', 'SOL', 'BNB', 'USDT', 'TRX', 'LTC']
        if crypto not in supported_cryptos:
            return jsonify({"success": False, "error": f"Unsupported cryptocurrency: {crypto}"}), 400
        
        session = db.connection.get_session()
        
        # Get user's crypto account
        crypto_account = session.query(Account).filter(
            Account.user_id == current_user.id,
            Account.account_type == AccountType.CRYPTO,
            Account.currency == crypto
        ).first()
        
        if not crypto_account:
            return jsonify({"success": False, "error": f"No {crypto} account found"}), 400
        
        # Convert amount to smallest units
        if crypto == 'BTC' or crypto == 'LTC':
            amount_smallest_units = int(float(amount) * 100_000_000)  # to satoshis
        elif crypto == 'ETH' or crypto == 'BNB':
            amount_smallest_units = int(float(amount) * 10**18)  # to wei
        elif crypto == 'SOL':
            amount_smallest_units = int(float(amount) * 10**9)  # to lamports
        elif crypto == 'USDT' or crypto == 'TRX':
            amount_smallest_units = int(float(amount) * 10**6)  # to micro units
        else:
            amount_smallest_units = int(float(amount) * 10**8)  # default 8 decimals
        
        # Check sufficient balance
        if crypto_account.balance_smallest_unit < amount_smallest_units:
            return jsonify({"success": False, "error": "Insufficient balance"}), 400
        
        # Create withdrawal transaction
        transaction = Transaction(
            user_id=current_user.id,
            account_id=crypto_account.id,
            transaction_type=TransactionType.WITHDRAWAL,
            amount_smallest_unit=amount_smallest_units,
            currency=crypto,
            status=TransactionStatus.PENDING,
            reference_id=f"withdraw_{crypto.lower()}_{current_user.id}_{int(time.time())}",
            metadata={
                "withdrawal_address": address,
                "crypto_currency": crypto,
                "amount_crypto": amount
            }
        )
        
        session.add(transaction)
        
        # Update account balance
        crypto_account.balance_smallest_unit -= amount_smallest_units
        
        session.commit()
        
        # In production, here you would:
        # 1. Queue the withdrawal for processing
        # 2. Send to blockchain network
        # 3. Update transaction status based on blockchain confirmation
        
        app.logger.info(f"Withdrawal initiated: {amount} {crypto} to {address} for user {current_user.id}")
        
        return jsonify({
            "success": True,
            "message": f"Withdrawal of {amount} {crypto} initiated successfully",
            "transaction_id": transaction.reference_id
        })
        
    except Exception as e:
        app.logger.error(f"Error withdrawing {crypto}: {e}")
        if 'session' in locals():
            session.rollback()
        return jsonify({"success": False, "error": str(e)}), 400
    finally:
        if 'session' in locals():
            session.close()


# ---------------------------------------------
# Admin: User Management
# ---------------------------------------------

@app.route('/api/admin/users', methods=['GET'])
@app.route('/api/v1/admin/users', methods=['GET'])
@app.route('/api/v1/api/admin/users', methods=['GET'])
@token_required
@is_admin
def admin_list_users(current_user):
    """List users with optional filters and pagination"""
    try:
        session = db.connection.session
        q = session.query(User)

        # Filters
        search = request.args.get('q') or request.args.get('query')
        role = request.args.get('role')
        blocked = request.args.get('blocked')
        deleted = request.args.get('deleted')

        if search:
            like = f"%{search}%"
            q = q.filter(
                (User.email.ilike(like)) |
                (User.first_name.ilike(like)) |
                (User.last_name.ilike(like)) |
                (User.phone_number.ilike(like))
            )

        if role:
            try:
                q = q.filter(User.role == db.models.UserRole(role))
            except Exception:
                return jsonify({"success": False, "error": "Invalid role"}), 400

        if blocked is not None:
            if blocked.lower() in ("true", "1"): q = q.filter(User.blocked.is_(True))
            if blocked.lower() in ("false", "0"): q = q.filter(User.blocked.is_(False))

        if deleted is not None:
            if deleted.lower() in ("true", "1"): q = q.filter(User.deleted.is_(True))
            if deleted.lower() in ("false", "0"): q = q.filter(User.deleted.is_(False))

        # Pagination
        try:
            page = int(request.args.get('page', 1))
            page_size = int(request.args.get('page_size', 25))
            if page_size > 200: page_size = 200
            if page < 1: page = 1
        except ValueError:
            page, page_size = 1, 25

        total = q.count()
        users = q.order_by(User.id.desc()).offset((page-1)*page_size).limit(page_size).all()

        def serialize(u: User):
            d = model_to_dict(u)
            # Ensure enum -> value
            try:
                if isinstance(u.role, enum.Enum):
                    d['role'] = u.role.value
            except Exception:
                pass
            return d

        return jsonify({
            "success": True,
            "data": [serialize(u) for u in users],
            "pagination": {"page": page, "page_size": page_size, "total": total}
        })
    except Exception as e:
        app.logger.error(f"admin_list_users error: {e}")
        return jsonify({"success": False, "error": str(e)}), 400


@app.route('/api/admin/users/<int:user_id>', methods=['GET'])
@app.route('/api/v1/admin/users/<int:user_id>', methods=['GET'])
@app.route('/api/v1/api/admin/users/<int:user_id>', methods=['GET'])
@token_required
@is_admin
def admin_get_user(current_user, user_id: int):
    try:
        session = db.connection.session
        u = session.query(User).get(user_id)
        if not u:
            return jsonify({"success": False, "error": "User not found"}), 404
        d = model_to_dict(u)
        try:
            if isinstance(u.role, enum.Enum):
                d['role'] = u.role.value
        except Exception:
            pass
        return jsonify({"success": True, "data": d})
    except Exception as e:
        app.logger.error(f"admin_get_user error: {e}")
        return jsonify({"success": False, "error": str(e)}), 400


@app.route('/api/admin/users/<int:user_id>', methods=['PATCH'])
@app.route('/api/v1/admin/users/<int:user_id>', methods=['PATCH'])
@app.route('/api/v1/api/admin/users/<int:user_id>', methods=['PATCH'])
@token_required
@is_admin
def admin_update_user(current_user, user_id: int):
    """Update user fields: first_name, last_name, phone_number, role, country, blocked, deleted, default_currency"""
    try:
        session = db.connection.session
        u = session.query(User).get(user_id)
        if not u:
            return jsonify({"success": False, "error": "User not found"}), 404
        data = request.get_json() or {}

        # Simple field updates
        for f in ["first_name", "last_name", "phone_number", "country", "default_currency"]:
            if f in data and isinstance(data[f], str):
                setattr(u, f, data[f])

        # Booleans
        if "blocked" in data:
            u.blocked = bool(data["blocked"])
        if "deleted" in data:
            u.deleted = bool(data["deleted"])

        # Role
        if "role" in data and data["role"]:
            try:
                u.role = db.models.UserRole(data["role"])  # type: ignore
            except Exception:
                return jsonify({"success": False, "error": "Invalid role"}), 400

        session.commit()

        d = model_to_dict(u)
        try:
            if isinstance(u.role, enum.Enum):
                d['role'] = u.role.value
        except Exception:
            pass
        return jsonify({"success": True, "data": d})
    except Exception as e:
        app.logger.error(f"admin_update_user error: {e}")
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/trading/calculate', methods=['POST'])
@token_required
def calculate_trade(current_user):
    """Calculate trade amounts including fees"""
    try:
        data = request.get_json()
        
        crypto_currency = data.get('crypto_currency', 'BTC')
        fiat_currency = data.get('fiat_currency', 'USD')
        amount = float(data.get('amount', 0))
        trade_type = TradeType(data.get('trade_type', 'buy'))
        payment_method = PaymentMethod(data.get('payment_method', 'mobile_money'))
        
        amounts = trading_service.calculate_trade_amounts(
            crypto_currency, fiat_currency, amount, trade_type, payment_method
        )
        
        return jsonify({
            "success": True,
            "crypto_amount": amounts.get('crypto_amount', 0),
            "fiat_amount": amounts.get('fiat_amount', 0),
            "exchange_rate": amounts.get('exchange_rate', 0),
            "fee_amount": amounts.get('fee_amount', 0),
            "total_cost": amounts.get('total_cost'),
            "net_proceeds": amounts.get('net_proceeds')
        })
    except Exception as e:
        app.logger.error(f"Error calculating trade: {e}")
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/trading/buy', methods=['POST'])
@token_required
def buy_crypto(current_user):
    """Buy crypto with fiat payment"""
    try:
        data = request.get_json()
        
        crypto_currency = data.get('crypto_currency', 'BTC')
        fiat_currency = data.get('fiat_currency', 'USD')
        amount = float(data.get('amount', 0))
        payment_method = PaymentMethod(data.get('payment_method', 'mobile_money'))
        payment_details = data.get('payment_details', {})
        
        session = db.connection.get_session()
        
        # Create trade
        trade = trading_service.create_trade(
            user_id=current_user.id,
            trade_type=TradeType.BUY,
            crypto_currency=crypto_currency,
            fiat_currency=fiat_currency,
            amount=amount,
            payment_method=payment_method,
            payment_details=payment_details,
            session=session
        )
        
        # Process payment based on method
        if payment_method == PaymentMethod.MOBILE_MONEY:
            success = trading_service.process_mobile_money_payment(trade, session)
        elif payment_method == PaymentMethod.VOUCHER:
            voucher_code = payment_details.get('voucher_code')
            success = trading_service.process_voucher_payment(trade, voucher_code, session)
        elif payment_method == PaymentMethod.BANK_DEPOSIT:
            success = trading_service.process_bank_deposit_payment(trade, session)
        else:
            success = False
        
        if success:
            return jsonify({
                "success": True,
                "data": {
                    "trade_id": trade.id,
                    "status": trade.status.value,
                    "payment_reference": trade.payment_reference,
                    "amount": float(trade.fiat_amount),
                    "crypto_amount": float(trade.crypto_amount),
                    "fee_amount": float(trade.fee_amount)
                }
            })
        else:
            return jsonify({"success": False, "error": "Failed to process payment"}), 400
            
    except Exception as e:
        app.logger.error(f"Error buying crypto: {e}")
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/trading/sell', methods=['POST'])
@token_required
def sell_crypto(current_user):
    """Sell crypto for fiat payment"""
    try:
        data = request.get_json()
        
        crypto_currency = data.get('crypto_currency', 'BTC')
        fiat_currency = data.get('fiat_currency', 'USD')
        amount = float(data.get('amount', 0))
        payment_method = PaymentMethod(data.get('payment_method', 'mobile_money'))
        payment_details = data.get('payment_details', {})
        
        session = db.connection.get_session()
        
        # Create trade
        trade = trading_service.create_trade(
            user_id=current_user.id,
            trade_type=TradeType.SELL,
            crypto_currency=crypto_currency,
            fiat_currency=fiat_currency,
            amount=amount,
            payment_method=payment_method,
            payment_details=payment_details,
            session=session
        )
        
        # For sell orders, we can complete immediately if user has sufficient balance
        success = trading_service.complete_trade(trade, session)
        
        if success:
            return jsonify({
                "success": True,
                "data": {
                    "trade_id": trade.id,
                    "status": trade.status.value,
                    "amount": float(trade.crypto_amount),
                    "fiat_amount": float(trade.fiat_amount),
                    "fee_amount": float(trade.fee_amount)
                }
            })
        else:
            return jsonify({"success": False, "error": "Insufficient balance or trade failed"}), 400
            
    except Exception as e:
        app.logger.error(f"Error selling crypto: {e}")
        app.logger.error(traceback.format_exc())
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/trading/trades', methods=['GET'])
@token_required
def get_user_trades(current_user):
    """Get user's trade history"""
    try:
        user_id = current_user.id
        
        # Get pagination parameters
        limit = request.args.get('limit', 10, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        # Get optional filters
        status = request.args.get('status')
        trade_type = request.args.get('trade_type')
        
        session = db.connection.session
        query = session.query(Trade).filter(Trade.user_id == user_id)
        
        # Apply filters
        if status:
            query = query.filter(Trade.status == TradeStatus(status))
        if trade_type:
            query = query.filter(Trade.trade_type == TradeType(trade_type))
        
        # Apply pagination and ordering
        trades = query.order_by(Trade.created_at.desc()).offset(offset).limit(limit).all()
        
        # Convert to dict format
        trades_data = []
        for trade in trades:
            trades_data.append({
                'id': trade.id,
                'trade_type': trade.trade_type.value,
                'crypto_currency': trade.crypto_currency,
                'fiat_currency': trade.fiat_currency,
                'crypto_amount': float(trade.crypto_amount),
                'fiat_amount': float(trade.fiat_amount),
                'exchange_rate': float(trade.exchange_rate),
                'fee_amount': float(trade.fee_amount),
                'status': trade.status.value,
                'payment_method': trade.payment_method.value,
                'created_at': trade.created_at.isoformat(),
                'updated_at': trade.updated_at.isoformat()
            })
        
        return jsonify({
            "success": True,
            "trades": trades_data,
            "pagination": {
                "limit": limit,
                "offset": offset,
                "total": len(trades_data)
            }
        })
    except Exception as e:
        app.logger.error(f"Error getting user trades: {e}")
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/trading/history', methods=['GET'])
@token_required
def get_trading_history(current_user):
    """Get trading history (alias for trades endpoint)"""
    try:
        user_id = current_user.id
        
        # Get pagination parameters
        limit = request.args.get('limit', 10, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        # Get optional filters
        status = request.args.get('status')
        trade_type = request.args.get('trade_type')
        
        session = db.connection.session
        
        # Use specific column selection to avoid missing column errors
        query = session.query(
            Trade.id,
            Trade.trade_type,
            Trade.crypto_currency,
            Trade.fiat_currency,
            Trade.crypto_amount,
            Trade.fiat_amount,
            Trade.exchange_rate,
            Trade.fee_amount,
            Trade.status,
            Trade.payment_method,
            Trade.created_at,
            Trade.updated_at
        ).filter(Trade.user_id == user_id)
        
        # Apply filters
        if status:
            query = query.filter(Trade.status == TradeStatus(status))
        if trade_type:
            query = query.filter(Trade.trade_type == TradeType(trade_type))
        
        # Apply pagination and ordering
        trades = query.order_by(Trade.created_at.desc()).offset(offset).limit(limit).all()
        
        # Convert to dict format
        trades_data = []
        for trade in trades:
            trades_data.append({
                'id': trade.id,
                'trade_type': trade.trade_type.value,
                'crypto_currency': trade.crypto_currency,
                'fiat_currency': trade.fiat_currency,
                'crypto_amount': float(trade.crypto_amount),
                'fiat_amount': float(trade.fiat_amount),
                'exchange_rate': float(trade.exchange_rate),
                'fee_amount': float(trade.fee_amount) if trade.fee_amount else 0.0,
                'status': trade.status.value,
                'payment_method': trade.payment_method.value,
                'created_at': trade.created_at.isoformat(),
                'updated_at': trade.updated_at.isoformat()
            })
        
        return jsonify({
            "success": True,
            "trades": trades_data,
            "pagination": {
                "limit": limit,
                "offset": offset,
                "total": len(trades_data)
            }
        })
    except Exception as e:
        app.logger.error(f"Error getting trading history: {e}")
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/trading/trades/<int:trade_id>', methods=['GET'])
@token_required
def get_trade_details(current_user, trade_id):
    """Get specific trade details"""
    try:
        session = db.connection.get_session()
        trade = trading_service.get_trade_by_id(trade_id, current_user.id, session)
        
        if not trade:
            return jsonify({"success": False, "error": "Trade not found"}), 404
        
        trade_data = {
            "id": trade.id,
            "trade_type": trade.trade_type.value,
            "status": trade.status.value,
            "crypto_currency": trade.crypto_currency,
            "crypto_amount": float(trade.crypto_amount),
            "fiat_currency": trade.fiat_currency,
            "fiat_amount": float(trade.fiat_amount),
            "exchange_rate": float(trade.exchange_rate),
            "fee_amount": float(trade.fee_amount) if trade.fee_amount else 0,
            "payment_method": trade.payment_method.value,
            "payment_reference": trade.payment_reference,
            "payment_status": trade.payment_status,
            "created_at": trade.created_at.isoformat(),
            "completed_at": trade.completed_at.isoformat() if trade.completed_at else None,
                            "payment_details": trade.trade_metadata
        }
        
        return jsonify({
            "success": True,
            "data": trade_data
        })
    except Exception as e:
        app.logger.error(f"Error getting trade details: {e}")
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/trading/trades/<int:trade_id>/cancel', methods=['POST'])
@token_required
def cancel_trade(current_user, trade_id):
    """Cancel a pending trade"""
    try:
        session = db.connection.get_session()
        trade = trading_service.get_trade_by_id(trade_id, current_user.id, session)
        
        if not trade:
            return jsonify({"success": False, "error": "Trade not found"}), 404
        
        success = trading_service.cancel_trade(trade, session)
        
        if success:
            return jsonify({
                "success": True,
                "message": "Trade cancelled successfully"
            })
        else:
            return jsonify({"success": False, "error": "Cannot cancel trade in current status"}), 400
            
    except Exception as e:
        app.logger.error(f"Error cancelling trade: {e}")
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/trading/vouchers/validate', methods=['POST'])
@token_required
def validate_voucher(current_user):
    """Validate a voucher code"""
    try:
        data = request.get_json()
        voucher_code = data.get('voucher_code')
        currency = data.get('currency', 'USD')
        
        if not voucher_code:
            return jsonify({"success": False, "error": "Voucher code required"}), 400
        
        session = db.connection.get_session()
        voucher = session.query(Voucher).filter(
            Voucher.code == voucher_code,
            Voucher.status == VoucherStatus.ACTIVE,
            Voucher.currency == currency
        ).first()
        
        if not voucher:
            return jsonify({"success": False, "error": "Invalid or expired voucher"}), 400
        
        return jsonify({
            "success": True,
            "data": {
                "voucher_id": voucher.id,
                "amount": float(voucher.amount),
                "currency": voucher.currency,
                "voucher_type": voucher.voucher_type.value
            }
        })
    except Exception as e:
        app.logger.error(f"Error validating voucher: {e}")
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/trading/payment-methods', methods=['GET'])
@token_required
def get_payment_methods(current_user):
    """Get available payment methods"""
    try:
        payment_methods = [
            {
                "method": "mobile_money",
                "name": "Mobile Money",
                "description": "Pay with MTN, Airtel, or other mobile money",
                "currencies": ["UGX", "USD"],
                "fee_percentage": 1.0,
                "processing_time": "Instant"
            },
            {
                "method": "bank_deposit",
                "name": "Bank Deposit",
                "description": "Deposit to our bank account",
                "currencies": ["UGX", "USD"],
                "fee_percentage": 1.0,
                "processing_time": "1-2 hours"
            },
            {
                "method": "voucher",
                "name": "Voucher",
                "description": "Use UGX or USD vouchers",
                "currencies": ["UGX", "USD"],
                "fee_percentage": 1.0,
                "processing_time": "Instant"
            }
        ]
        
        return jsonify({
            "success": True,
            "data": payment_methods
        })
    except Exception as e:
        app.logger.error(f"Error getting payment methods: {e}")
        return jsonify({"success": False, "error": str(e)}), 400

# Webhook for Relworx mobile money payments
@app.route('/api/webhooks/relworx', methods=['POST'])
def relworx_webhook():
    """Handle Relworx mobile money payment webhooks with signature verification"""
    try:
        data = request.get_json()
        app.logger.info(f"Received Relworx webhook: {data}")
        
        # Verify webhook signature
        signature = request.headers.get('X-Relworx-Signature')
        webhook_secret = config('RELWORX_WEBHOOK_SECRET', default=None)
        
        if webhook_secret and signature:
            # Verify webhook signature
            import hmac
            import hashlib
            
            # Create expected signature
            payload = request.get_data()
            expected_signature = hmac.new(
                webhook_secret.encode('utf-8'),
                payload,
                hashlib.sha256
            ).hexdigest()
            
            # Compare signatures
            if not hmac.compare_digest(signature, expected_signature):
                app.logger.error(f"Invalid webhook signature: {signature}")
                return jsonify({"success": False, "error": "Invalid signature"}), 401
        elif webhook_secret:
            app.logger.warning("Webhook secret configured but no signature provided")
            return jsonify({"success": False, "error": "Missing signature"}), 401
        
        reference = data.get('reference')
        status = data.get('status')
        amount = data.get('amount')
        
        if not reference or not status:
            return jsonify({"success": False, "error": "Missing required fields"}), 400
        
        # Extract trade ID from reference
        if reference.startswith('TRADE_'):
            trade_id = int(reference.split('_')[1])
            
            session = db.connection.get_session()
            trade = session.query(Trade).filter(Trade.id == trade_id).first()
            
            if trade:
                if status == 'success':
                    trade.payment_status = 'completed'
                    trade.payment_received_at = datetime.datetime.utcnow()
                    trade.status = TradeStatus.PAYMENT_RECEIVED
                    
                    # Complete the trade with unified precision and accounting
                    from wallet.trading_service import TradingService
                    trading_service = TradingService(session)
                    success = trading_service.complete_trade(trade, session)
                    
                    if success:
                        from shared.currency_precision import AmountConverter
                        crypto_display = AmountConverter.format_display_amount(trade.crypto_amount_smallest_unit, trade.crypto_currency)
                        fiat_display = AmountConverter.format_display_amount(trade.fiat_amount_smallest_unit, trade.fiat_currency)
                        app.logger.info(f"✅ Trade {trade_id} completed via Relworx: {crypto_display} for {fiat_display}")
                    else:
                        app.logger.error(f"❌ Failed to complete trade {trade_id}")
                        
                elif status == 'failed':
                    trade.payment_status = 'failed'
                    trade.status = TradeStatus.FAILED
                    app.logger.error(f"❌ Trade {trade_id} payment failed via Relworx")
                    
                session.commit()
        
        # Handle sell trade payout confirmations
        elif reference.startswith('PAYOUT_'):
            trade_id = int(reference.split('_')[1])
            
            session = db.connection.get_session()
            trade = session.query(Trade).filter(Trade.id == trade_id).first()
            
            if trade:
                if status == 'success':
                    trade.payout_status = 'completed'
                    trade.status = TradeStatus.COMPLETED
                    trade.completed_at = datetime.datetime.utcnow()
                    
                    from shared.currency_precision import AmountConverter
                    fiat_display = AmountConverter.format_display_amount(trade.fiat_amount_smallest_unit, trade.fiat_currency)
                    app.logger.info(f"✅ Sell trade {trade_id} payout completed via Relworx: {fiat_display}")
                    
                elif status == 'failed':
                    trade.payout_status = 'failed'
                    trade.status = TradeStatus.FAILED
                    app.logger.error(f"❌ Sell trade {trade_id} payout failed via Relworx")
                    
                session.commit()
        
        return jsonify({"success": True})
        
    except Exception as e:
        app.logger.error(f"Error processing Relworx webhook: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

# Webhook for Buy Trade Completion
@app.route('/api/webhooks/buy-complete', methods=['POST'])
def buy_complete_webhook():
    """Handle buy trade completion webhooks with signature verification"""
    try:
        data = request.get_json()
        app.logger.info(f"Received buy completion webhook: {data}")
        
        # Verify webhook signature
        signature = request.headers.get('X-Buy-Webhook-Signature')
        webhook_secret = config('BUY_WEBHOOK_SECRET', default=None)
        
        if webhook_secret and signature:
            # Verify webhook signature
            import hmac
            import hashlib
            
            # Create expected signature
            payload = request.get_data()
            expected_signature = hmac.new(
                webhook_secret.encode('utf-8'),
                payload,
                hashlib.sha256
            ).hexdigest()
            
            # Compare signatures
            if not hmac.compare_digest(signature, expected_signature):
                app.logger.error(f"Invalid buy webhook signature: {signature}")
                return jsonify({"success": False, "error": "Invalid signature"}), 401
        elif webhook_secret:
            app.logger.warning("Buy webhook secret configured but no signature provided")
            return jsonify({"success": False, "error": "Missing signature"}), 401
        
        trade_id = data.get('trade_id')
        status = data.get('status')
        crypto_amount = data.get('crypto_amount')
        transaction_hash = data.get('transaction_hash')
        
        if not trade_id or not status:
            return jsonify({"success": False, "error": "Missing required fields"}), 400
        
        session = db.connection.get_session()
        trade = session.query(Trade).filter(Trade.id == trade_id).first()
        
        if trade:
            if status == 'completed':
                trade.status = TradeStatus.COMPLETED
                trade.completed_at = datetime.datetime.utcnow()
                trade.trade_metadata = trade.trade_metadata or {}
                trade.trade_metadata['crypto_transaction_hash'] = transaction_hash
                trade.trade_metadata['webhook_received_at'] = datetime.datetime.utcnow().isoformat()
                
                # Update crypto transaction if exists
                if trade.crypto_transaction_id:
                    crypto_transaction = session.query(Transaction).filter(
                        Transaction.id == trade.crypto_transaction_id
                    ).first()
                    if crypto_transaction:
                        crypto_transaction.metadata_json = crypto_transaction.metadata_json or {}
                        crypto_transaction.metadata_json['blockchain_hash'] = transaction_hash
                        crypto_transaction.metadata_json['webhook_processed'] = True
                
                app.logger.info(f"Buy trade {trade_id} completed via webhook")
                
            elif status == 'failed':
                trade.status = TradeStatus.FAILED
                trade.trade_metadata = trade.trade_metadata or {}
                trade.trade_metadata['webhook_error'] = data.get('error_message', 'Unknown error')
                trade.trade_metadata['webhook_received_at'] = datetime.datetime.utcnow().isoformat()
                
                app.logger.error(f"Buy trade {trade_id} failed via webhook: {data.get('error_message')}")
            
            session.commit()
            
            # Send notification via Kafka
            notification_data = {
                'user_id': trade.user_id,
                'trade_id': trade.id,
                'status': status,
                'trade_type': 'buy',
                'crypto_amount': crypto_amount,
                'crypto_currency': trade.crypto_currency
            }
            
            try:
                from shared.kafka_producer import send_kafka_message
                send_kafka_message('trade-notifications', notification_data)
            except Exception as e:
                app.logger.error(f"Failed to send trade notification: {e}")
        
        return jsonify({"success": True})
        
    except Exception as e:
        app.logger.error(f"Error processing buy completion webhook: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

# Webhook for Sell Trade Completion
@app.route('/api/webhooks/sell-complete', methods=['POST'])
def sell_complete_webhook():
    """Handle sell trade completion webhooks with signature verification"""
    try:
        data = request.get_json()
        app.logger.info(f"Received sell completion webhook: {data}")
        
        # Verify webhook signature
        signature = request.headers.get('X-Sell-Webhook-Signature')
        webhook_secret = config('SELL_WEBHOOK_SECRET', default=None)
        
        if webhook_secret and signature:
            # Verify webhook signature
            import hmac
            import hashlib
            
            # Create expected signature
            payload = request.get_data()
            expected_signature = hmac.new(
                webhook_secret.encode('utf-8'),
                payload,
                hashlib.sha256
            ).hexdigest()
            
            # Compare signatures
            if not hmac.compare_digest(signature, expected_signature):
                app.logger.error(f"Invalid sell webhook signature: {signature}")
                return jsonify({"success": False, "error": "Invalid signature"}), 401
        elif webhook_secret:
            app.logger.warning("Sell webhook secret configured but no signature provided")
            return jsonify({"success": False, "error": "Missing signature"}), 401
        
        trade_id = data.get('trade_id')
        status = data.get('status')
        fiat_amount = data.get('fiat_amount')
        payment_reference = data.get('payment_reference')
        
        if not trade_id or not status:
            return jsonify({"success": False, "error": "Missing required fields"}), 400
        
        session = db.connection.get_session()
        trade = session.query(Trade).filter(Trade.id == trade_id).first()
        
        if trade:
            if status == 'completed':
                trade.status = TradeStatus.COMPLETED
                trade.completed_at = datetime.datetime.utcnow()
                trade.payment_reference = payment_reference
                trade.trade_metadata = trade.trade_metadata or {}
                trade.trade_metadata['webhook_received_at'] = datetime.datetime.utcnow().isoformat()
                trade.trade_metadata['payment_processed'] = True
                
                # Update fiat transaction if exists
                if trade.fiat_transaction_id:
                    fiat_transaction = session.query(Transaction).filter(
                        Transaction.id == trade.fiat_transaction_id
                    ).first()
                    if fiat_transaction:
                        fiat_transaction.metadata_json = fiat_transaction.metadata_json or {}
                        fiat_transaction.metadata_json['payment_reference'] = payment_reference
                        fiat_transaction.metadata_json['webhook_processed'] = True
                
                app.logger.info(f"Sell trade {trade_id} completed via webhook")
                
            elif status == 'failed':
                trade.status = TradeStatus.FAILED
                trade.trade_metadata = trade.trade_metadata or {}
                trade.trade_metadata['webhook_error'] = data.get('error_message', 'Unknown error')
                trade.trade_metadata['webhook_received_at'] = datetime.datetime.utcnow().isoformat()
                
                app.logger.error(f"Sell trade {trade_id} failed via webhook: {data.get('error_message')}")
            
            session.commit()
            
            # Send notification via Kafka
            notification_data = {
                'user_id': trade.user_id,
                'trade_id': trade.id,
                'status': status,
                'trade_type': 'sell',
                'fiat_amount': fiat_amount,
                'fiat_currency': trade.fiat_currency
            }
            
            try:
                from shared.kafka_producer import send_kafka_message
                send_kafka_message('trade-notifications', notification_data)
            except Exception as e:
                app.logger.error(f"Failed to send trade notification: {e}")
        
        return jsonify({"success": True})
        
    except Exception as e:
        app.logger.error(f"Error processing sell completion webhook: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

# Webhook for Trade Status Updates
@app.route('/api/webhooks/trade-status', methods=['POST'])
def trade_status_webhook():
    """Handle general trade status update webhooks with signature verification"""
    try:
        data = request.get_json()
        app.logger.info(f"Received trade status webhook: {data}")
        
        # Verify webhook signature
        signature = request.headers.get('X-Trade-Webhook-Signature')
        webhook_secret = config('TRADE_WEBHOOK_SECRET', default=None)
        
        if webhook_secret and signature:
            # Verify webhook signature
            import hmac
            import hashlib
            
            # Create expected signature
            payload = request.get_data()
            expected_signature = hmac.new(
                webhook_secret.encode('utf-8'),
                payload,
                hashlib.sha256
            ).hexdigest()
            
            # Compare signatures
            if not hmac.compare_digest(signature, expected_signature):
                app.logger.error(f"Invalid trade webhook signature: {signature}")
                return jsonify({"success": False, "error": "Invalid signature"}), 401
        elif webhook_secret:
            app.logger.warning("Trade webhook secret configured but no signature provided")
            return jsonify({"success": False, "error": "Missing signature"}), 401
        
        trade_id = data.get('trade_id')
        new_status = data.get('status')
        metadata = data.get('metadata', {})
        
        if not trade_id or not new_status:
            return jsonify({"success": False, "error": "Missing required fields"}), 400
        
        session = db.connection.get_session()
        trade = session.query(Trade).filter(Trade.id == trade_id).first()
        
        if trade:
            # Update trade status
            if hasattr(TradeStatus, new_status.upper()):
                trade.status = TradeStatus[new_status.upper()]
            else:
                app.logger.warning(f"Invalid trade status: {new_status}")
                return jsonify({"success": False, "error": "Invalid status"}), 400
            
            # Update metadata
            trade.trade_metadata = trade.trade_metadata or {}
            trade.trade_metadata.update(metadata)
            trade.trade_metadata['webhook_received_at'] = datetime.datetime.utcnow().isoformat()
            
            # Set completion timestamp if status is completed
            if new_status == 'completed':
                trade.completed_at = datetime.datetime.utcnow()
            
            session.commit()
            
            app.logger.info(f"Trade {trade_id} status updated to {new_status} via webhook")
            
            # Send notification via Kafka
            notification_data = {
                'user_id': trade.user_id,
                'trade_id': trade.id,
                'status': new_status,
                'trade_type': trade.trade_type.value,
                'metadata': metadata
            }
            
            try:
                from shared.kafka_producer import send_kafka_message
                send_kafka_message('trade-notifications', notification_data)
            except Exception as e:
                app.logger.error(f"Failed to send trade notification: {e}")
        
        return jsonify({"success": True})
        
    except Exception as e:
        app.logger.error(f"Error processing trade status webhook: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

def start_merged_consumer():
    from db.connection import get_session
    logger = setup_logging()
    consumer = Consumer({
        'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS,
        'group.id': 'wallet-merged-consumer',
        'session.timeout.ms': 6000,
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
                            btc_config = BitcoinConfig.testnet()
                            btc_wallet = BTCWallet(user_id=user_id,btc_config=btc_config, session=session, logger=logger)
                            btc_wallet.create_wallet()
                            session.commit()
                        # btc_wallet.create_address()

                        # Create crypto wallet for ETH
                        existing_account_eth = session.query(Account).filter_by(
                            user_id=user_id,
                            currency="ETH",
                            account_type=AccountType.CRYPTO
                        ).first()
                        if not existing_account_eth:
                            from shared.crypto.clients.eth import ETHWallet, EthereumConfig

                            eth_config = EthereumConfig.testnet(
                                config('ALCHEMY_API_KEY', default=''))
                            eth_wallet = ETHWallet(
                                user_id=user_id,
                                eth_config=eth_config,
                                session=session,
                                logger=app.logger
                            )
                            eth_wallet.create_wallet()
                            eth_wallet.create_usdt_account()
                            eth_wallet.create_usdc_account()
                            session.commit()
                            logger.info(f"[Wallet] Created ETH account for user {user_id}")
                        # Create crypto wallet for SOL
                        existing_account_sol = session.query(Account).filter_by(
                            user_id=user_id,
                            currency="SOL",
                            account_type=AccountType.CRYPTO
                        ).first()
                        if not existing_account_sol:
                            from shared.crypto.clients.sol import SOLWallet, SolanaConfig

                            sol_config = SolanaConfig.testnet(
                                config('ALCHEMY_API_KEY', default=''))
                            sol_wallet = SOLWallet(
                                user_id=user_id,
                                sol_config=sol_config,
                                session=session,
                                logger=app.logger
                            )
                            sol_wallet.create_wallet()
                            session.commit()
                            logger.info(f"[Wallet] Created SOL account for user {user_id}")
                                
                        # Create crypto wallet for TRX
                        existing_account_trx = session.query(Account).filter_by(
                            user_id=user_id,
                            currency="TRX",
                            account_type=AccountType.CRYPTO
                        ).first()
                        if not existing_account_trx:
                            trx_api_key = config('TRON_API_KEY', default='')
                            if not trx_api_key:
                                logger.warning(f"[Wallet] TRON_API_KEY not configured; skipping TRX wallet creation for user {user_id}")
                            else:
                                trx_config = TronWalletConfig.testnet(trx_api_key)
                                trx_wallet = TronWallet(user_id=user_id, tron_config=trx_config, session=session, logger=logger)
                                trx_wallet.create_wallet()
                                trx_wallet.create_usdt_account()
                                session.commit()
                                logger.info(f"[Wallet] Created TRX account for user {user_id}")

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
                account = get_account_by_user_id(user_id, "UGX",db.connection.session)
                amount = data.get('amount')
                reference_id = data.get('reference_id')
                description = data.get('description')
                provider = data.get('provider')
                phone_number = data.get('phone_number')
                session = get_session()
                transaction = session.query(Transaction).filter_by(
                                        reference_id=reference_id).first()
                if not transaction:
                    logger.error(f"[Wallet] Transaction not found for reference_id: {reference_id}")
                    continue

                if provider == "relworx":
                    try:
                        client = RelworxApiClient()
                        resp = client.request_payment(reference_id, phone_number, amount, description)
                        logger.info(f"[Wallet] relworx response: {resp}")
                        provider_reference = resp.get('internal_reference')
                        transaction.provider_reference = provider_reference
                        session.commit()

                    except Exception as e:
                        transaction.status = TransactionStatus.FAILED
                        error = {"error": "Could not request payment"}
                        transaction.metadata_json = error | transaction.metadata_json
                        session.commit()
                        logger.error(f"[Wallet] Could not request payment for user {user_id}: {e!r}")
                    finally:
                        session.close()

            elif topic == WALLET_WITHDRAW_TOPIC:
                user_id = data.get('user_id')
                amount = data.get('amount')
                reference_id = data.get('reference_id')
                description = data.get('description')
                provider = data.get('provider', 'relworx')
                phone_number = data.get('phone_number')
                metadata = data.get('metadata', {})
                # Only query for the transaction (do not create)
                session = get_session()
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
            logger.error(f"[Wallet] Failed to process message: {e}")
            logger.error(traceback.format_exc())
            # Do not commit offset so message can be retried
        finally:
            session.close()

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

# Start the price refresh service in a background thread
threading.Thread(target=start_price_refresh_service, daemon=True).start()


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
                            btc_config = BitcoinConfig.testnet()
                            btc_wallet = BTCWallet(user_id=user_id,btc_config=btc_config, session=session, logger=logger)
                            btc_wallet.create_wallet()
                            session.commit()
                        # btc_wallet.create_address()

                        # Create crypto wallet for ETH
                        existing_account_eth = session.query(Account).filter_by(
                            user_id=user_id,
                            currency="ETH",
                            account_type=AccountType.CRYPTO
                        ).first()
                        if not existing_account_eth:
                            from shared.crypto.clients.eth import ETHWallet, EthereumConfig

                            eth_config = EthereumConfig.testnet(
                                config('ALCHEMY_API_KEY', default=''))
                            eth_wallet = ETHWallet(
                                user_id=user_id,
                                eth_config=eth_config,
                                session=session,
                                logger=app.logger
                            )
                            eth_wallet.create_wallet()
                            eth_wallet.create_usdt_account()
                            eth_wallet.create_usdc_account()
                            session.commit()
                            logger.info(f"[Wallet] Created ETH account for user {user_id}")
                        # Create crypto wallet for SOL
                        existing_account_sol = session.query(Account).filter_by(
                            user_id=user_id,
                            currency="SOL",
                            account_type=AccountType.CRYPTO
                        ).first()
                        if not existing_account_sol:
                            from shared.crypto.clients.sol import SOLWallet, SolanaConfig

                            sol_config = SolanaConfig.testnet(
                                config('ALCHEMY_API_KEY', default=''))
                            sol_wallet = SOLWallet(
                                user_id=user_id,
                                sol_config=sol_config,
                                session=session,
                                logger=app.logger
                            )
                            sol_wallet.create_wallet()
                            session.commit()
                            logger.info(f"[Wallet] Created SOL account for user {user_id}")
                                
                        # Create crypto wallet for TRX
                        existing_account_trx = session.query(Account).filter_by(
                            user_id=user_id,
                            currency="TRX",
                            account_type=AccountType.CRYPTO
                        ).first()
                        if not existing_account_trx:
                            trx_api_key = config('TRON_API_KEY', default='')
                            if not trx_api_key:
                                logger.warning(f"[Wallet] TRON_API_KEY not configured; skipping TRX wallet creation for user {user_id}")
                            else:
                                trx_config = TronWalletConfig.testnet(trx_api_key)
                                trx_wallet = TronWallet(user_id=user_id, tron_config=trx_config, session=session, logger=logger)
                                trx_wallet.create_wallet()
                                trx_wallet.create_usdt_account()
                                session.commit()
                                logger.info(f"[Wallet] Created TRX account for user {user_id}")

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
                account = get_account_by_user_id(user_id, "UGX",db.connection.session)
                amount = data.get('amount')
                reference_id = data.get('reference_id')
                description = data.get('description')
                provider = data.get('provider')
                phone_number = data.get('phone_number')
                session = get_session()
                transaction = session.query(Transaction).filter_by(
                                        reference_id=reference_id).first()
                if not transaction:
                    logger.error(f"[Wallet] Transaction not found for reference_id: {reference_id}")
                    continue

                if provider == "relworx":
                    try:
                        client = RelworxApiClient()
                        resp = client.request_payment(reference_id, phone_number, amount, description)
                        logger.info(f"[Wallet] relworx response: {resp}")
                        provider_reference = resp.get('internal_reference')
                        transaction.provider_reference = provider_reference
                        session.commit()

                    except Exception as e:
                        transaction.status = TransactionStatus.FAILED
                        error = {"error": "Could not request payment"}
                        transaction.metadata_json = error | transaction.metadata_json
                        session.commit()
                        logger.error(f"[Wallet] Could not request payment for user {user_id}: {e!r}")
                    finally:
                        session.close()

            elif topic == WALLET_WITHDRAW_TOPIC:
                user_id = data.get('user_id')
                amount = data.get('amount')
                reference_id = data.get('reference_id')
                description = data.get('description')
                provider = data.get('provider', 'relworx')
                phone_number = data.get('phone_number')
                metadata = data.get('metadata', {})
                # Only query for the transaction (do not create)
                session = get_session()
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
            logger.error(f"[Wallet] Failed to process message: {e}")
            logger.error(traceback.format_exc())
            # Do not commit offset so message can be retried
        finally:
            session.close()

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

# Start the price refresh service in a background thread
threading.Thread(target=start_price_refresh_service, daemon=True).start()

# Periodic SOL finality checker
def start_solana_finality_checker():
    from db.connection import get_session
    from db.wallet import Transaction, Account, TransactionStatus, TransactionType
    from shared.currency_precision import AmountConverter
    from service import confirm_crypto_withdrawal
    from solana_webhook import _update_tx_confirmations_and_credit
    import time
    logger = app.logger
    poll_seconds = int(os.getenv("SOL_FINALITY_POLL_SECS", "20"))
    
    while True:
        logger.info(f"🔍 SOL finality checker running every {poll_seconds} seconds")
        session = None
        try:
            session = get_session()
            
            # Get pending SOL transactions (both deposits and withdrawals)
            pending = (
                session.query(Transaction)
                .join(Account, Transaction.account_id == Account.id)
                .filter(
                    Transaction.status == TransactionStatus.AWAITING_CONFIRMATION,
                    Transaction.blockchain_txid.isnot(None),
                    Account.currency == "SOL",
                )
                .all()
            )
            
            logger.info(f"Found {len(pending)} pending SOL transactions")
            
            for tx in pending:
                try:
                    tx_hash = tx.blockchain_txid
                    tx_type = tx.type
                    amount_lamports = tx.amount_smallest_unit or 0
                    formatted_amount = AmountConverter.format_display_amount(amount_lamports, "SOL")
                    
                    logger.info(f"🔍 Checking SOL {tx_type.value if tx_type else 'transaction'}: {formatted_amount} (hash: {tx_hash[:8]}...)")
                    
                    if tx_type == TransactionType.WITHDRAWAL:
                        # For withdrawals, use the unified confirmation system
                        success = confirm_crypto_withdrawal(tx_hash, session)
                        if success:
                            logger.info(f"✅ Confirmed SOL withdrawal: {formatted_amount}")
                        else:
                            logger.debug(f"⏳ SOL withdrawal still pending: {formatted_amount}")
                    else:
                        # For deposits, use the existing webhook system
                        _update_tx_confirmations_and_credit(
                            tx_hash,
                            required_confirmations=tx.required_confirmations or 32,
                            tx_type=tx_type
                        )
                        
                except Exception as tx_error:
                    logger.error(f"❌ Error updating SOL transaction {tx.id}: {tx_error}")
                    # Rollback the session to clear any failed transaction state
                    if session:
                        try:
                            session.rollback()
                        except Exception as rollback_error:
                            logger.error(f"Error rolling back session: {rollback_error}")
                            
        except Exception as e:
            logger.error(f"❌ SOL finality checker error: {e}")
            if session:
                try:
                    session.rollback()
                except Exception as rollback_error:
                    logger.error(f"Error rolling back session: {rollback_error}")
        finally:
            if session:
                try:
                    session.close()
                except Exception as close_error:
                    logger.error(f"Error closing session: {close_error}")
                    
        time.sleep(poll_seconds)

threading.Thread(target=start_solana_finality_checker, daemon=True).start()


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


def notify_ethereum_address_created(address: str, currency_code: str, account_id: int, user_id: int):
    """Notify about new Ethereum address creation via Kafka"""
    try:
        producer = get_kafka_producer()
        producer.send("ethereum-address-events", {
            "event_type": "ethereum_address_created",
            "address_data": {
                "address": address,
                "currency_code": currency_code,
                "account_id": account_id,
                "user_id": user_id,
                "timestamp": datetime.datetime.utcnow().isoformat()
            }
        })
        app.logger.info(f"📨 Sent Ethereum address creation event for {address}")
    except Exception as e:
        app.logger.error(f"Failed to notify Ethereum address creation: {e}")

@app.route("/health", methods=["GET"])
@token_required
def health():
    return {"status": "ok"}, 200

@app.route("/wallet/account", methods=["POST"])
@token_required
def wallet_create_account():
    session = None
    try:
        user_id = g.user.id
        session = db.connection.get_session()
        account = create_account(user_id, session)
        return jsonify(model_to_dict(account)), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    finally:
        if session:
            session.close()

@app.route("/wallet/balance", methods=["GET"])
@token_required
def wallet_get_balance():
    session = None
    try:
        user_id = g.user.id
        session = db.connection.get_session()
        balance = get_balance(user_id, session)
        return jsonify(balance), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    finally:
        if session:
            session.close()

@app.route("/wallet/deposit", methods=["POST"])
@token_required
def wallet_deposit():
    session = None
    try:
        user_id = g.user.id
        data = request.get_json()
        phone_number = data.get("phone_number")
        amount = data.get("amount")
        reference_id = data.get("reference_id")
        provider = data.get("provider", "relworx")
        description = "Deposit to Digital Tondeka"
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
        session = db.connection.get_session()
        account = get_account_by_user_id(user_id, "UGX", session)
        if not account:
            return jsonify({"error": [{"account": "Account not found."}]}), 401

        existing = session.query(Transaction).filter_by(
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
            metadata_json=metadata,
            amount_smallest_unit=amount * 10**2,
            precision_config={
                "currency": "UGX",
                "decimals": 2,
                "smallest_units": "cents",
                "parent_currency": "UGX",
            }
        )
        session.add(transaction)
        session.commit()
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
    finally:
        if session:
            session.close()

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
        description = data.get("description", "Withdrawal from Digital Tondeka")
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
        account = get_account_by_user_id(user_id, "UGX",session)
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
            app.logger.info(f"[WALLET] Available balance: {available}, amount: {amount} for user {user_id}")
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
                metadata_json=metadata,
                amount_smallest_unit=amount * 10**2,
                precision_config={
                    "currency": "UGX",
                    "decimals": 2,
                    "smallest_units": "cents",
                    "parent_currency": "UGX",
                }
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

@app.route("/wallet/withdraw/ethereum", methods=["POST"])
@token_required
def wallet_withdraw_ethereum():
    """
    Withdraw Ethereum to an external address
    
    Request body:
    {
        "to_address": "0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6",
        "amount": 0.01,
        "reference_id": "eth_withdraw_123",
        "description": "ETH withdrawal",
        "gas_limit": 21000
    }
    """
    try:
        user_id = g.user.id
        data = request.get_json()
        
        # Validate required fields
        to_address = data.get("to_address")
        amount = data.get("amount")
        reference_id = data.get("reference_id")
        description = data.get("description", "Ethereum withdrawal")
        gas_limit = data.get("gas_limit", 21000)
        token_contract = data.get("token_contract")
        token_symbol = (data.get("token_symbol") or "").upper() if data.get("token_symbol") else None
        token_decimals = data.get("token_decimals")
        
        missing_fields = []
        if not to_address:
            missing_fields.append({"to_address": "Missing required field"})
        if amount is None:
            missing_fields.append({"amount": "Missing required field"})
        if not reference_id:
            missing_fields.append({"reference_id": "Missing required field"})
        
        if missing_fields:
            return jsonify({"error": missing_fields}), 400
        
        # Validate amount
        try:
            amount = float(amount)
            if amount <= 0:
                return jsonify({"error": [{"amount": "Amount must be greater than 0"}]}), 400
        except (ValueError, TypeError):
            return jsonify({"error": [{"amount": "Invalid amount format"}]}), 400
        
        # Validate Ethereum address
        if not to_address.startswith("0x") or len(to_address) != 42:
            return jsonify({"error": [{"to_address": "Invalid Ethereum address format"}]}), 400
        
        session = db.connection.session
        
        # Get user's ETH account (for gas and native withdrawals)
        eth_account = session.query(Account).filter_by(
            user_id=user_id,
            currency="ETH",
            account_type=AccountType.CRYPTO
        ).first()
        
        if not eth_account:
            return jsonify({"error": [{"account": "No ETH account found for user"}]}), 404
        
        # Check for duplicate transaction
        existing = session.query(Transaction).filter_by(
            reference_id=reference_id,
            type=TransactionType.WITHDRAWAL
        ).first()
        
        if existing:
            return jsonify({"error": [{"reference_id": "Withdrawal transaction already exists for this reference_id"}]}), 409
        
        # Import unified precision system
        from shared.currency_precision import AmountConverter
        
        # Determine if ERC20 or native ETH
        is_erc20 = bool(token_contract)
        if is_erc20:
            if not token_symbol:
                return jsonify({"error": [{"token_symbol": "token_symbol required for ERC20 withdrawal"}]}), 400
            token_accounts = session.query(Account).filter(
                Account.user_id == user_id,
                Account.account_type == AccountType.CRYPTO,
                Account.currency == token_symbol,
            ).all()
            token_account = next((a for a in token_accounts if (a.precision_config or {}).get("parent_currency", "").upper() == "ETH"), None)
            if not token_account:
                return jsonify({"error": [{"account": f"No {token_symbol} (ETH) account found for user"}]}), 404
            
            # Use unified precision system for ERC20 tokens
            try:
                amount_smallest = AmountConverter.to_smallest_units(amount, token_symbol)
            except:
                # Fallback to legacy calculation
                decimals = int(token_decimals if token_decimals is not None else (token_account.precision_config or {}).get("decimals", 18))
                amount_smallest = int(amount * (10 ** decimals))
            
            # Check balance using unified system
            if hasattr(token_account, 'balance_smallest_unit'):
                available_smallest = (token_account.balance_smallest_unit or 0)
            else:
                available_smallest = (token_account.crypto_balance_smallest_unit or 0)
                
            if available_smallest < amount_smallest:
                available_display = AmountConverter.format_display_amount(available_smallest, token_symbol)
                return jsonify({"error": [{"amount": f"Insufficient balance. Available: {available_display}"}]}), 400
        else:
            # Use unified precision system for ETH
            amount_smallest = AmountConverter.to_smallest_units(amount, "ETH")
            
            # Check balance using unified system
            if hasattr(eth_account, 'balance_smallest_unit'):
                available_balance_smallest = (eth_account.balance_smallest_unit or 0)
            else:
                available_balance_smallest = (eth_account.crypto_balance_smallest_unit or 0)
                
            if available_balance_smallest < amount_smallest:
                available_display = AmountConverter.format_display_amount(available_balance_smallest, "ETH")
                return jsonify({"error": [{"amount": f"Insufficient balance. Available: {available_display}"}]}), 400
        
        # Initialize ETH wallet
        from shared.crypto.clients.eth import ETHWallet, EthereumConfig
        
        api_key = config('ALCHEMY_API_KEY', default='')
        if not api_key:
            return jsonify({"error": [{"system": "Ethereum API key not configured"}]}), 500
        
        eth_config = EthereumConfig.testnet(api_key)  # Use testnet for safety
        eth_wallet = ETHWallet(
            user_id=user_id,
            eth_config=eth_config,
            session=session,
            logger=app.logger
        )
        eth_wallet.account_id = eth_account.id
        
        # Send transaction
        try:
            if is_erc20:
                tx_info = eth_wallet.send_erc20_transfer(token_contract, to_address, float(amount), int(token_decimals if token_decimals is not None else (token_account.precision_config or {}).get("decimals", 18)))
            else:
                tx_info = eth_wallet.send_transaction(to_address, amount, gas_limit)
        except Exception as e:
            return jsonify({"error": [{"transaction": f"Failed to send transaction: {str(e)}"}]}), 500
        
        # Lock the amount and create transaction record using unified system
        try:
            if is_erc20:
                session.refresh(token_account, with_for_update=True)
                # Use unified balance fields if available, fallback to legacy
                if hasattr(token_account, 'locked_amount_smallest_unit') and hasattr(token_account, 'balance_smallest_unit'):
                    token_account.locked_amount_smallest_unit = (token_account.locked_amount_smallest_unit or 0) + amount_smallest
                    token_account.balance_smallest_unit = (token_account.balance_smallest_unit or 0) - amount_smallest
                else:
                    token_account.crypto_locked_amount_smallest_unit = (token_account.crypto_locked_amount_smallest_unit or 0) + amount_smallest
                    token_account.crypto_balance_smallest_unit = (token_account.crypto_balance_smallest_unit or 0) - amount_smallest
            else:
                session.refresh(eth_account, with_for_update=True)
                # Use unified balance fields if available, fallback to legacy
                if hasattr(eth_account, 'locked_amount_smallest_unit') and hasattr(eth_account, 'balance_smallest_unit'):
                    eth_account.locked_amount_smallest_unit = (eth_account.locked_amount_smallest_unit or 0) + amount_smallest
                    eth_account.balance_smallest_unit = (eth_account.balance_smallest_unit or 0) - amount_smallest
                else:
                    eth_account.crypto_locked_amount_smallest_unit = (eth_account.crypto_locked_amount_smallest_unit or 0) + amount_smallest
                    eth_account.crypto_balance_smallest_unit = (eth_account.crypto_balance_smallest_unit or 0) - amount_smallest
            # Create reservation for the withdrawal amount
            import time
            reservation_reference = f"eth_withdrawal_{int(time.time() * 1000)}_{reference_id}"
            
            reservation = Reservation(
                user_id=user_id,
                reference=reservation_reference,
                amount=amount,  # Store in ETH for consistency
                type=ReservationType.RESERVE,
                status="active"
            )
            
            # Create transaction record
            metadata = {
                "to_address": to_address,
                "gas_limit": gas_limit,
                "estimated_cost_eth": tx_info.get("estimated_cost_eth", 0),
                "transaction_params": tx_info.get("transaction_params", {}),
                "transaction_hash": tx_info.get("transaction_hash"),
                "from_address": tx_info.get("from_address").lower(),
                "block_number": 0,
                "reservation_reference": reservation_reference,
            }
            
            tx = Transaction(
                account_id=(token_account.id if is_erc20 else eth_account.id),
                reference_id=reference_id,
                amount=amount,  # Keep for backward compatibility
                amount_smallest_unit=amount_smallest,  # Unified field for precision
                currency=(token_symbol if is_erc20 else "ETH"),  # Unified currency field
                type=TransactionType.WITHDRAWAL,
                status=TransactionStatus.AWAITING_CONFIRMATION,
                address=tx_info.get("from_address", "").lower(),
                description=(description if not is_erc20 else f"{token_symbol} withdrawal"),
                provider=PaymentProvider.CRYPTO,
                provider_reference=tx_info.get("transaction_hash"),
                blockchain_txid=tx_info.get("transaction_hash"),  # Store hash in blockchain_txid for eth_monitor
                metadata_json=(
                    {
                        **metadata,
                        "token_contract": token_contract,
                        "token_symbol": token_symbol,
                    }
                    if is_erc20
                    else metadata
                )
            )
            
            session.add(reservation)
            session.add(tx)
            session.commit()
            
            app.logger.info(f"💰 ETH withdrawal sent: {amount} ETH to {to_address}")
            app.logger.info(f"   User: {user_id}, Reference: {reference_id}")
            app.logger.info(f"   Transaction Hash: {tx_info.get('transaction_hash')}")
            app.logger.info(f"   Estimated cost: {tx_info.get('estimated_cost_eth', 0)} ETH")
            app.logger.info(f"   Reservation: {reservation_reference}")
            
            return jsonify({
                "message": "Ethereum withdrawal sent successfully",
                "transaction_info": {
                    "reference_id": reference_id,
                    "amount_eth": amount,
                    "to_address": to_address,
                    "transaction_hash": tx_info.get("transaction_hash"),
                    "estimated_cost_eth": tx_info.get("estimated_cost_eth", 0),
                    "status": "sent",
                    "reservation_reference": reservation_reference
                }
            }), 201
            
        except Exception as e:
            session.rollback()
            app.logger.error(f"❌ ETH withdrawal failed: {e}")
            return jsonify({"error": [{"system": f"Failed to process withdrawal: {str(e)}"}]}), 500
            
    except Exception as e:
        app.logger.error(f"❌ ETH withdrawal endpoint error: {e}")
        return jsonify({"error": [{"system": str(e)}]}), 500

@app.route("/wallet/withdraw/solana", methods=["POST"])
@token_required
def wallet_withdraw_solana():
    """
    Withdraw Solana to an external address
    
    Request body:
    {
        "to_address": "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM",
        "amount": 0.01,
        "reference_id": "sol_withdraw_123",
        "description": "SOL withdrawal",
        "priority_fee": 5000
    }
    """
    try:
        user_id = g.user.id
        data = request.get_json()
        
        # Validate required fields
        to_address = data.get("to_address")
        amount = data.get("amount")
        reference_id = data.get("reference_id")
        description = data.get("description", "Solana withdrawal")
        priority_fee = data.get("priority_fee", 5000)
        
        missing_fields = []
        if not to_address:
            missing_fields.append({"to_address": "Missing required field"})
        if amount is None:
            missing_fields.append({"amount": "Missing required field"})
        if not reference_id:
            missing_fields.append({"reference_id": "Missing required field"})
        
        if missing_fields:
            return jsonify({"error": missing_fields}), 400
        
        # Validate amount
        try:
            amount = float(amount)
            if amount <= 0:
                return jsonify({"error": [{"amount": "Amount must be greater than 0"}]}), 400
        except (ValueError, TypeError):
            return jsonify({"error": [{"amount": "Invalid amount format"}]}), 400
        
        # Validate Solana address
        if not to_address or len(to_address) != 44:  # Solana addresses are 44 characters
            return jsonify({"error": [{"to_address": "Invalid Solana address format"}]}), 400
        
        session = db.connection.session
        
        # Get user's SOL account
        sol_account = session.query(Account).filter_by(
            user_id=user_id,
            currency="SOL",
            account_type=AccountType.CRYPTO
        ).first()
        
        if not sol_account:
            return jsonify({"error": [{"account": "No SOL account found for user"}]}), 404
        
        # Check for duplicate transaction
        existing = session.query(Transaction).filter_by(
            reference_id=reference_id,
            type=TransactionType.WITHDRAWAL
        ).first()
        
        if existing:
            return jsonify({"error": [{"reference_id": "Withdrawal transaction already exists for this reference_id"}]}), 409
        
        # Import unified precision system
        from shared.currency_precision import AmountConverter
        
        # Use unified precision system for SOL
        amount_smallest = AmountConverter.to_smallest_units(amount, "SOL")
        
        # Check balance using unified system
        if hasattr(sol_account, 'balance_smallest_unit'):
            available_balance_smallest = (sol_account.balance_smallest_unit or 0)
        else:
            available_balance_smallest = (sol_account.crypto_balance_smallest_unit or 0)
        
        app.logger.info(f"SOL withdrawal: {AmountConverter.format_display_amount(amount_smallest, 'SOL')}")
        
        if available_balance_smallest < amount_smallest:
            available_display = AmountConverter.format_display_amount(available_balance_smallest, "SOL")
            return jsonify({"error": [{"amount": f"Insufficient balance. Available: {available_display}"}]}), 400
        
        # Initialize SOL wallet
        from shared.crypto.clients.sol import SOLWallet, SolanaConfig
        
        api_key = config('ALCHEMY_API_KEY', default='')
        if not api_key:
            return jsonify({"error": [{"system": "Solana API key not configured"}]}), 500
        
        sol_config = SolanaConfig.testnet(api_key)  # Use testnet for safety
        sol_wallet = SOLWallet(
            user_id=user_id,
            sol_config=sol_config,
            session=session,
            logger=app.logger
        )
        sol_wallet.account_id = sol_account.id
        
        # Send transaction
        try:
            tx_info = sol_wallet.send_transaction(to_address, amount, priority_fee)
        except Exception as e:
            return jsonify({"error": [{"transaction": f"Failed to send transaction: {str(e)}"}]}), 500
        
        # Lock the amount and create transaction record using unified system
        try:
            session.refresh(sol_account, with_for_update=True)
            # Use unified balance fields if available, fallback to legacy
            if hasattr(sol_account, 'locked_amount_smallest_unit') and hasattr(sol_account, 'balance_smallest_unit'):
                sol_account.locked_amount_smallest_unit = (sol_account.locked_amount_smallest_unit or 0) + amount_smallest
                sol_account.balance_smallest_unit = (sol_account.balance_smallest_unit or 0) - amount_smallest
            else:
                sol_account.crypto_locked_amount_smallest_unit = (sol_account.crypto_locked_amount_smallest_unit or 0) + amount_smallest
                sol_account.crypto_balance_smallest_unit = (sol_account.crypto_balance_smallest_unit or 0) - amount_smallest
            
            # Create reservation for the withdrawal amount
            import time
            reservation_reference = f"sol_withdrawal_{int(time.time() * 1000)}_{reference_id}"
            
            reservation = Reservation(
                user_id=user_id,
                reference=reservation_reference,
                amount=amount,  # Store in SOL for consistency
                type=ReservationType.RESERVE,
                status="active"
            )
            
            # Create transaction record
            metadata = {
                "to_address": to_address,
                "priority_fee": priority_fee,
                "estimated_cost_sol": tx_info.get("estimated_cost_sol", 0),
                "transaction_params": tx_info.get("transaction_params", {}),
                "transaction_hash": tx_info.get("transaction_hash"),
                "from_address": tx_info.get("from_address").lower(),
                "block_number": 0,
                "reservation_reference": reservation_reference,
            }
            
            tx = Transaction(
                account_id=sol_account.id,
                reference_id=reference_id,
                amount=amount,  # Keep for backward compatibility
                amount_smallest_unit=amount_smallest,  # Unified field for precision
                currency="SOL",  # Unified currency field
                type=TransactionType.WITHDRAWAL,
                status=TransactionStatus.AWAITING_CONFIRMATION,
                address=tx_info.get("from_address", "").lower(),
                description=description,
                provider=PaymentProvider.CRYPTO,
                provider_reference=tx_info.get("transaction_hash"),
                blockchain_txid=tx_info.get("transaction_hash"),  # Store hash in blockchain_txid for monitoring
                confirmations=0,  # Start with 0 confirmations
                required_confirmations=32,  # Solana typically needs 32 confirmations for finality
                metadata_json=metadata
            )
            
            session.add(reservation)
            session.add(tx)
            session.commit()
            
            app.logger.info(f"💰 SOL withdrawal sent: {amount} SOL to {to_address}")
            app.logger.info(f"   User: {user_id}, Reference: {reference_id}")
            app.logger.info(f"   Transaction Hash: {tx_info.get('transaction_hash')}")
            app.logger.info(f"   Estimated cost: {tx_info.get('estimated_cost_sol', 0)} SOL")
            app.logger.info(f"   Reservation: {reservation_reference}")
            
            return jsonify({
                "message": "Solana withdrawal sent successfully",
                "transaction_info": {
                    "reference_id": reference_id,
                    "amount_sol": amount,
                    "to_address": to_address,
                    "transaction_hash": tx_info.get("transaction_hash"),
                    "estimated_cost_sol": tx_info.get("estimated_cost_sol", 0),
                    "status": "sent",
                    "reservation_reference": reservation_reference
                }
            }), 201
            
        except Exception as e:
            session.rollback()
            app.logger.error(f"❌ SOL withdrawal failed: {e}")
            return jsonify({"error": [{"system": f"Failed to process withdrawal: {str(e)}"}]}), 500
            
    except Exception as e:
        app.logger.error(f"❌ SOL withdrawal endpoint error: {e}")
        return jsonify({"error": [{"system": str(e)}]}), 500

@app.route("/wallet/withdraw/solana/status/<reference_id>", methods=["GET"])
@token_required
def wallet_withdraw_solana_status(reference_id):
    """
    Get the status of a Solana withdrawal transaction
    
    Returns:
    {
        "reference_id": "sol_withdraw_123",
        "status": "sent|confirmed|failed",
        "transaction_hash": "5GRcJvEm2nepdhEkWgp49sKWt8x87dkHVmcci1Ta9mCSreAxQctcyVnHV9NvT7GiKmk6MDgbiriqne3RpuVuamLt",
        "amount_sol": 0.01,
        "to_address": "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM",
        "confirmations": 15,
        "required_confirmations": 15,
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z"
    }
    """
    try:
        user_id = g.user.id
        session = db.connection.session
        
        # Get the transaction
        transaction = session.query(Transaction).filter_by(
            reference_id=reference_id,
            type=TransactionType.WITHDRAWAL,
            account_id=session.query(Account).filter_by(
                user_id=user_id,
                currency="SOL",
                account_type=AccountType.CRYPTO
            ).first().id
        ).first()
        
        if not transaction:
            return jsonify({"error": "Transaction not found"}), 404
        
        # Get reservation if it exists
        reservation = None
        if transaction.metadata_json and transaction.metadata_json.get("reservation_reference"):
            reservation = session.query(Reservation).filter_by(
                reference=transaction.metadata_json["reservation_reference"]
            ).first()
        
        # Format response
        response_data = {
            "reference_id": transaction.reference_id,
            "status": transaction.status.value,
            "transaction_hash": transaction.blockchain_txid,
            "amount_sol": transaction.amount,
            "to_address": transaction.metadata_json.get("to_address") if transaction.metadata_json else None,
            "confirmations": transaction.confirmations or 0,
            "required_confirmations": transaction.required_confirmations or 15,
            "created_at": transaction.created_at.isoformat() if transaction.created_at else None,
            "updated_at": transaction.updated_at.isoformat() if transaction.updated_at else None,
            "description": transaction.description,
            "estimated_cost_sol": transaction.metadata_json.get("estimated_cost_sol", 0) if transaction.metadata_json else 0
        }
        
        if reservation:
            response_data["reservation"] = {
                "reference": reservation.reference,
                "status": reservation.status,
                "amount": reservation.amount
            }
        
        return jsonify(response_data), 200
        
    except Exception as e:
        app.logger.error(f"❌ SOL withdrawal status endpoint error: {e}")
        return jsonify({"error": str(e)}), 500

def release_withdrawal_reservation(transaction_hash: str, user_id: int, amount: float):
    """
    Release the reservation for a confirmed withdrawal transaction
    """
    try:
        session = db.connection.session
        
        # Find the transaction
        transaction = session.query(Transaction).filter_by(
            blockchain_txid=transaction_hash,
            type=TransactionType.WITHDRAWAL
        ).first()
        
        if not transaction:
            app.logger.warning(f"Withdrawal transaction {transaction_hash} not found")
            return False
        
        # Get the reservation reference from metadata
        reservation_ref = transaction.metadata_json.get("reservation_reference")
        if not reservation_ref:
            app.logger.warning(f"No reservation reference found for transaction {transaction_hash}")
            return False
        
        # Find and update the reservation
        reservation = session.query(Reservation).filter_by(
            user_id=user_id,
            reference=reservation_ref,
            type=ReservationType.RESERVE
        ).first()
        
        if not reservation:
            app.logger.warning(f"Reservation {reservation_ref} not found")
            return False
        
        # Create release reservation
        release_ref = f"eth_withdrawal_release_{int(time.time() * 1000)}_{transaction_hash[:8]}"
        release_reservation = Reservation(
            user_id=user_id,
            reference=release_ref,
            amount=amount,
            type=ReservationType.RELEASE,
            status="completed"
        )
        
        # Update original reservation status
        reservation.status = "completed"
        
        session.add(release_reservation)
        session.commit()
        
        app.logger.info(f"✅ Released withdrawal reservation: {reservation_ref}")
        app.logger.info(f"   Transaction: {transaction_hash}")
        app.logger.info(f"   Amount: {amount} ETH")
        
        return True
        
    except Exception as e:
        app.logger.error(f"❌ Error releasing withdrawal reservation: {e}")
        session.rollback()
        return False


@app.route("/wallet/reservations/<reference_id>", methods=["GET"])
@token_required
def wallet_get_reservation_status(reference_id):
    """
    Get the status of a reservation
    """
    try:
        user_id = g.user.id
        session = db.connection.session
        
        # Get the reservation
        reservation = session.query(Reservation).filter_by(
            user_id=user_id,
            reference=reference_id
        ).first()
        
        if not reservation:
            return jsonify({"error": [{"reservation": "Reservation not found"}]}), 404
        
        return jsonify({
            "reservation": {
                "reference": reservation.reference,
                "amount": reservation.amount,
                "type": reservation.type.value,
                "status": reservation.status,
                "created_at": reservation.created_at.isoformat() if reservation.created_at else None
            }
        }), 200
        
    except Exception as e:
        app.logger.error(f"❌ Error getting reservation status: {e}")
        return jsonify({"error": [{"system": str(e)}]}), 500


@app.route("/wallet/reservations", methods=["GET"])
@token_required
def wallet_list_reservations():
    """
    List all reservations for the authenticated user
    """
    try:
        user_id = g.user.id
        session = db.connection.session
        
        # Get all reservations for the user
        reservations = session.query(Reservation).filter_by(
            user_id=user_id
        ).order_by(Reservation.created_at.desc()).all()
        
        reservation_list = []
        for reservation in reservations:
            reservation_list.append({
                "reference": reservation.reference,
                "amount": reservation.amount,
                "type": reservation.type.value,
                "status": reservation.status,
                "created_at": reservation.created_at.isoformat() if reservation.created_at else None
            })
        
        return jsonify({
            "reservations": reservation_list,
            "count": len(reservation_list)
        }), 200
        
    except Exception as e:
        app.logger.error(f"❌ Error listing reservations: {e}")
        return jsonify({"error": [{"system": str(e)}]}), 500


@app.route("/wallet/withdraw/ethereum/status/<reference_id>", methods=["GET"])
@token_required
def wallet_withdraw_ethereum_status(reference_id):
    """
    Check the status of an Ethereum withdrawal transaction
    """
    try:
        user_id = g.user.id
        session = db.connection.session
        
        # Get the transaction
        transaction = session.query(Transaction).filter_by(
            reference_id=reference_id,
            type=TransactionType.WITHDRAWAL,
            account_id=session.query(Account).filter_by(user_id=user_id, currency="ETH").first().id
        ).first()
        
        if not transaction:
            return jsonify({"error": [{"transaction": "Transaction not found"}]}), 404
        
        # Get transaction status from blockchain
        tx_hash = transaction.provider_reference
        if not tx_hash:
            return jsonify({
                "status": "prepared",
                "reference_id": reference_id,
                "message": "Transaction prepared but not yet sent to blockchain"
            }), 200
        
        # Initialize ETH wallet to check status
        from shared.crypto.clients.eth import ETHWallet, EthereumConfig
        
        api_key = config('ALCHEMY_API_KEY', default='')
        if not api_key:
            return jsonify({"error": [{"system": "Ethereum API key not configured"}]}), 500
        
        eth_config = EthereumConfig.testnet(api_key)
        eth_wallet = ETHWallet(
            user_id=user_id,
            eth_config=eth_config,
            session=session,
            logger=app.logger
        )
        
        # Get transaction status
        status_info = eth_wallet.get_transaction_status(tx_hash)
        
        if status_info:
            return jsonify({
                "reference_id": reference_id,
                "tx_hash": tx_hash,
                "status": status_info.get("status"),
                "block_number": status_info.get("block_number"),
                "gas_used": status_info.get("gas_used"),
                "receipt": status_info.get("receipt")
            }), 200
        else:
            return jsonify({
                "reference_id": reference_id,
                "tx_hash": tx_hash,
                "status": "pending",
                "message": "Transaction not yet confirmed on blockchain"
            }), 200
            
    except Exception as e:
        app.logger.error(f"❌ ETH withdrawal status check error: {e}")
        return jsonify({"error": [{"system": str(e)}]}), 500

@app.route("/wallet/transfer", methods=["POST"])
@token_required
def wallet_transfer():
    """
    Enhanced transfer endpoint with currency support, email lookup, and idempotency
    Requires: currency, to_email, amount, reference_id
    Optional: description
    """
    try:
        from_user_id = g.user.id
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['currency', 'to_email', 'amount', 'reference_id']
        for field in required_fields:
            if not data.get(field):
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
        currency = data.get("currency").upper()
        to_email = data.get("to_email").lower()
        amount = float(data.get("amount"))
        reference_id = data.get("reference_id")
        description = data.get("description")
        
        # Validate amount
        if amount <= 0:
            return jsonify({"error": "Amount must be greater than 0"}), 400
        
        # Validate reference_id format (should be non-empty string)
        if not reference_id or not isinstance(reference_id, str) or len(reference_id.strip()) == 0:
            return jsonify({"error": "reference_id must be a non-empty string"}), 400
        
        # Use enhanced transfer service
        from transfer_service import transfer_between_users
        
        result = transfer_between_users(
            session=db.connection.session,
            from_user_id=from_user_id,
            to_email=to_email,
            amount=amount,
            currency=currency,
            reference_id=reference_id,
            description=description
        )
        
        return jsonify(result), 201
        
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        app.logger.error(f"Transfer failed: {str(e)}")
        return jsonify({"error": "Transfer failed. Please try again."}), 500

@app.route("/wallet/transactions", methods=["GET"])
@token_required
def wallet_transactions():
    try:
        user_id = g.user.id
        limit = min(int(request.args.get("limit", 20)), 100)  # Cap limit at 100
        offset = max(int(request.args.get("offset", 0)), 0)  # Ensure offset is non-negative
        page = max(int(request.args.get("page", 1)), 1)  # Page number (1-based)
        
        # Filter parameters
        currency = request.args.get("currency", None)
        status = request.args.get("status", None)
        tx_type = request.args.get("type", None)
        date_from = request.args.get("date_from", None)
        date_to = request.args.get("date_to", None)
        search = request.args.get("search", None)
        
        # Sorting parameters
        sort_by = request.args.get("sort_by", "created_at")
        sort_order = request.args.get("sort_order", "desc")
        
        # Calculate offset from page if provided
        if request.args.get("page"):
            offset = (page - 1) * limit
        
        # Build base query
        session = db.connection.session
        base_query = session.query(Transaction).join(
            Account, Transaction.account_id == Account.id
        ).filter(Account.user_id == user_id)
        
        # Apply filters
        if currency:
            base_query = base_query.filter(Account.currency == currency.upper())
        
        if status:
            base_query = base_query.filter(Transaction.status == status.upper())
        
        if tx_type:
            base_query = base_query.filter(Transaction.type == tx_type.lower())
        
        if date_from:
            try:
                from datetime import datetime
                date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
                base_query = base_query.filter(Transaction.created_at >= date_from_obj)
            except ValueError:
                pass  # Invalid date format, ignore filter
        
        if date_to:
            try:
                from datetime import datetime, timedelta
                date_to_obj = datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1)
                base_query = base_query.filter(Transaction.created_at < date_to_obj)
            except ValueError:
                pass  # Invalid date format, ignore filter
        
        if search:
            search_term = f"%{search}%"
            base_query = base_query.filter(
                db.or_(
                    Transaction.description.ilike(search_term),
                    Transaction.blockchain_txid.ilike(search_term),
                    Transaction.address.ilike(search_term)
                )
            )
        
        # Get total count for pagination
        total_count = base_query.count()
        
        # Apply sorting
        if sort_by == "amount":
            if sort_order == "asc":
                base_query = base_query.order_by(Transaction.amount.asc())
            else:
                base_query = base_query.order_by(Transaction.amount.desc())
        elif sort_by == "status":
            if sort_order == "asc":
                base_query = base_query.order_by(Transaction.status.asc())
            else:
                base_query = base_query.order_by(Transaction.status.desc())
        else:  # Default to created_at
            if sort_order == "asc":
                base_query = base_query.order_by(Transaction.created_at.asc())
            else:
                base_query = base_query.order_by(Transaction.created_at.desc())
        
        # Apply pagination
        txs = base_query.offset(offset).limit(limit).all()
        
        # Calculate pagination metadata
        total_pages = (total_count + limit - 1) // limit
        has_next = offset + limit < total_count
        has_prev = offset > 0
        
        # Build pagination links
        base_url = request.base_url
        params = request.args.copy()
        
        pagination_links = {
            "first": f"{base_url}?{dict(params, page=1, offset=0)}",
            "last": f"{base_url}?{dict(params, page=total_pages, offset=(total_pages-1)*limit)}",
        }
        
        if has_prev:
            prev_page = max(1, page - 1)
            prev_offset = max(0, offset - limit)
            pagination_links["prev"] = f"{base_url}?{dict(params, page=prev_page, offset=prev_offset)}"
        
        if has_next:
            next_page = page + 1
            next_offset = offset + limit
            pagination_links["next"] = f"{base_url}?{dict(params, page=next_page, offset=next_offset)}"
        
        # Enhanced transaction serialization with currency info
        transactions_data = []
        for tx in txs:
            tx_dict = model_to_dict(tx)
            # Add currency from the related account
            currency = tx.account.currency if tx.account else None
            tx_dict['currency'] = currency
            
            # Fix amount display using unified system for crypto currencies
            if currency and tx.amount_smallest_unit is not None:
                try:
                    from shared.currency_precision import AmountConverter
                    # Use proper amount conversion for display
                    proper_amount = AmountConverter.from_smallest_units(tx.amount_smallest_unit, currency)
                    tx_dict['amount'] = float(proper_amount)
                    # Also add formatted amount for display
                    tx_dict['formatted_amount'] = AmountConverter.format_display_amount(tx.amount_smallest_unit, currency)
                except Exception as e:
                    logger.warning(f"Failed to convert amount for currency {currency}: {e}")
            
            transactions_data.append(tx_dict)
        
        response_data = {
            "transactions": transactions_data,
            "pagination": {
                "page": page,
                "limit": limit,
                "offset": offset,
                "total_count": total_count,
                "total_pages": total_pages,
                "has_next": has_next,
                "has_prev": has_prev,
                "links": pagination_links
            }
        }
        
        return jsonify(response_data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/wallet/transactions/<int:transaction_id>", methods=["GET"])
@token_required
def get_transaction_details(transaction_id):
    try:
        user_id = g.user.id
        session = db.connection.session
        
        # Debug: Check if transaction exists at all
        transaction_exists = session.query(Transaction).filter(Transaction.id == transaction_id).first()
        app.logger.debug(f"DEBUG: Transaction {transaction_id} exists: {transaction_exists is not None}")
        
        if transaction_exists:
            app.logger.debug(f"DEBUG: Transaction {transaction_id} account_id: {transaction_exists.account_id}")
            # Check if account belongs to user
            account = session.query(Account).filter(Account.id == transaction_exists.account_id).first()
            if account:
                app.logger.debug(f"DEBUG: Account {account.id} belongs to user {account.user_id}, current user: {user_id}")
        
        # Get transaction with account details
        transaction = session.query(Transaction).join(
            Account, Transaction.account_id == Account.id
        ).filter(
            Transaction.id == transaction_id,
            Account.user_id == user_id
        ).first()
        
        if not transaction:
            return jsonify({
                "error": "Transaction not found or you don't have permission to view it",
                "debug": {
                    "transaction_id": transaction_id,
                    "user_id": user_id,
                    "transaction_exists": transaction_exists is not None
                }
            }), 404
        
        # Get account details
        account = session.query(Account).filter(Account.id == transaction.account_id).first()
        
        # Enhanced transaction serialization with currency info
        transaction_dict = model_to_dict(transaction)
        currency = transaction.account.currency if transaction.account else None
        transaction_dict['currency'] = currency
        
        # Fix amount display using unified system for crypto currencies
        if currency and transaction.amount_smallest_unit is not None:
            try:
                from shared.currency_precision import AmountConverter
                # Use proper amount conversion for display
                proper_amount = AmountConverter.from_smallest_units(transaction.amount_smallest_unit, currency)
                transaction_dict['amount'] = float(proper_amount)
                # Also add formatted amount for display
                transaction_dict['formatted_amount'] = AmountConverter.format_display_amount(transaction.amount_smallest_unit, currency)
            except Exception as e:
                logger.warning(f"Failed to convert amount for currency {currency}: {e}")
        
        response_data = {
            "transaction": {
                **transaction_dict,
                "account": {
                    "id": account.id,
                    "currency": account.currency,
                    "account_type": account.account_type.value if account.account_type else None
                } if account else None
            }
        }
        
        return jsonify(response_data), 200
    except Exception as e:
        app.logger.error(f"ERROR: Exception in get_transaction_details: {str(e)}")
        return jsonify({"error": str(e)}), 400

@app.route("/wallet/pnl", methods=["GET"])
@token_required
def get_user_pnl():
    """Get user PnL based on actual transaction costs from ledger"""
    try:
        from pnl_service import WalletPnLService
        
        user_id = g.user.id
        currency = request.args.get('currency')
        period_days = int(request.args.get('period_days', 1))
        
        result = WalletPnLService.get_user_pnl(user_id, currency, period_days)
        
        if result['success']:
            return jsonify(result['data']), 200
        else:
            return jsonify({"error": result['error']}), 400
            
    except Exception as e:
        app.logger.error(f"Error in get_user_pnl: {str(e)}")
        return jsonify({"error": str(e)}), 400

@app.route("/wallet/portfolio-summary", methods=["GET"])
@token_required
def get_portfolio_summary():
    """Get portfolio summary with accurate PnL based on cost basis"""
    try:
        from pnl_service import WalletPnLService
        
        user_id = g.user.id
        result = WalletPnLService.get_portfolio_summary(user_id)
        
        if result['success']:
            return jsonify(result['data']), 200
        else:
            return jsonify({"error": result['error']}), 400
            
    except Exception as e:
        app.logger.error(f"Error in get_portfolio_summary: {str(e)}")
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
        account = get_account_by_user_id(user_id, "UGX", session)
        if not account:
            app.logger.info(f"Account not found for user {user_id}")
            print(f"Account not found for user {user_id}")
            return jsonify({'error': 'Account not found for user'}), 404
        balance = get_balance(user_id, session)
        transactions = get_transaction_history(user_id, "UGX", session, limit=10, offset=0)
        
        # Fix transaction amounts using unified system
        transactions_data = []
        for tx in transactions:
            tx_dict = model_to_dict(tx)
            currency = tx.account.currency if tx.account else None
            if currency and tx.amount_smallest_unit is not None:
                try:
                    from shared.currency_precision import AmountConverter
                    proper_amount = AmountConverter.from_smallest_units(tx.amount_smallest_unit, currency)
                    tx_dict['amount'] = float(proper_amount)
                    tx_dict['formatted_amount'] = AmountConverter.format_display_amount(tx.amount_smallest_unit, currency)
                except Exception as e:
                    logger.warning(f"Failed to convert amount for currency {currency}: {e}")
            transactions_data.append(tx_dict)
        
        return jsonify({
            'account': model_to_dict(account),
            'balance': balance,
            'transactions': transactions_data
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
            account = get_account_by_user_id(user_id, "UGX", session)
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
            account = get_account_by_user_id(user_id, "UGX", session)
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
    """
    Admin transfer between user accounts with idempotency support
    """
    try:
        data = request.get_json()
        from_account_number = data.get('from_account_number')
        to_account_number = data.get('to_account_number')
        amount = float(data.get('amount', 0))
        reference_id = data.get('reference_id')  # For idempotency
        note = data.get('note', '')
        
        if not all([from_account_number, to_account_number, amount]):
            return jsonify({'error': 'Missing required fields: from_account_number, to_account_number, amount'}), 400
        
        if amount <= 0:
            return jsonify({'error': 'Amount must be greater than 0'}), 400
        
        session = db.connection.session
        
        # Get accounts
        from_account = session.query(Account).filter_by(account_number=from_account_number).first()
        to_account = session.query(Account).filter_by(account_number=to_account_number).first()
        
        if not from_account or not to_account:
            return jsonify({'error': 'Account not found'}), 404
        
        if from_account.currency != to_account.currency:
            return jsonify({'error': 'Cannot transfer between accounts with different currencies.'}), 400
        
        # Use the transfer service for consistency and idempotency
        from transfer_service import TransferService
        
        # Create a custom transfer service for admin transfers
        transfer_service = TransferService(session)
        
        # Check idempotency if reference_id is provided
        if reference_id:
            existing_transaction = transfer_service._get_existing_transaction_by_reference(reference_id)
            if existing_transaction:
                app.logger.info(f"Admin transfer idempotency: Found existing transaction with reference_id {reference_id}")
                return jsonify({
                    'message': 'Transfer already processed with this reference_id',
                    'status': 'idempotent',
                    'transaction_id': existing_transaction.id,
                    'reference_id': reference_id,
                    'from_account': model_to_dict(from_account),
                    'to_account': model_to_dict(to_account)
                }), 200
        
        # Validate sufficient balance
        if from_account.available_balance() < amount:
            return jsonify({'error': 'Insufficient funds'}), 400
        
        # Create transfer transaction
        transaction = transfer_service._create_transfer_transaction(
            from_account, to_account, amount, from_account.currency, 
            reference_id, note or f"Admin transfer from {from_account_number} to {to_account_number}"
        )
        
        # Update account balances
        transfer_service._update_account_balances(from_account, to_account, amount, from_account.currency)
        
        # Create ledger entries
        transfer_service._create_ledger_entries(transaction, from_account, to_account, amount, from_account.currency)
        
        # Commit all changes
        session.commit()
        
        app.logger.info(f"Admin transfer completed: {amount} {from_account.currency} from account {from_account_number} to {to_account_number}")
        
        return jsonify({
            'message': f'Transferred {amount} {from_account.currency} from account {from_account_number} to account {to_account_number}',
            'transaction_id': transaction.id,
            'reference_id': reference_id,
            'from_account': model_to_dict(from_account),
            'to_account': model_to_dict(to_account),
            'status': 'completed'
        }), 200
        
    except Exception as e:
        session.rollback() if 'session' in locals() else None
        app.logger.error(f"Admin transfer failed: {str(e)}")
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
            
            # Fix transaction amounts using unified system
            transactions_data = []
            for tx in transactions:
                tx_dict = model_to_dict(tx)
                currency = tx.account.currency if tx.account else None
                if currency and tx.amount_smallest_unit is not None:
                    try:
                        from shared.currency_precision import AmountConverter
                        proper_amount = AmountConverter.from_smallest_units(tx.amount_smallest_unit, currency)
                        tx_dict['amount'] = float(proper_amount)
                        tx_dict['formatted_amount'] = AmountConverter.format_display_amount(tx.amount_smallest_unit, currency)
                    except Exception as e:
                        logger.warning(f"Failed to convert amount for currency {currency}: {e}")
                transactions_data.append(tx_dict)
            
            result.append({
                'account': model_to_dict(account),
                'balance': balance,
                'transactions': transactions_data
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


# --- Crypto Price Endpoints ---

@app.route('/wallet/prices', methods=['GET'])
# @token_required
def get_crypto_prices():
    """Get cached crypto prices for all supported symbols."""
    try:
        symbols = request.args.getlist('symbols')
        force_refresh = request.args.get('refresh', 'false').lower() == 'true'
        auto_populate = request.args.get('populate', 'false').lower() == 'true'
        
        if symbols:
            # Get prices for specific symbols
            if force_refresh:
                prices = refresh_cached_prices(symbols)
            else:
                prices = get_cached_prices(symbols)
        else:
            # Get all cached prices
            service = get_price_cache_service()
            
            # If auto_populate is enabled and no prices exist, populate cache first
            if auto_populate:
                cached_prices = service.get_cached_prices()
                if all(price is None for price in cached_prices.values()):
                    app.logger.info("Auto-populating empty cache with initial prices")
                    try:
                        # Set a timeout for the API call to prevent hanging
                        import signal
                        
                        def timeout_handler(signum, frame):
                            raise TimeoutError("API call timed out")
                        
                        # Set a 10-second timeout
                        signal.signal(signal.SIGALRM, timeout_handler)
                        signal.alarm(10)
                        
                        try:
                            service.refresh_prices()
                        finally:
                            signal.alarm(0)  # Cancel the alarm
                    except (TimeoutError, Exception) as e:
                        app.logger.warning(f"Failed to auto-populate cache: {e}")
                        app.logger.info("Returning empty prices - will populate on next background refresh")
            
            prices = service.get_all_prices(force_refresh=force_refresh)
        
        return jsonify({
            'success': True,
            'prices': prices,
            'timestamp': datetime.datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        app.logger.error(f"Failed to get crypto prices: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/wallet/prices/test-populate', methods=['POST'])
def test_populate_cache():
    """Test endpoint to populate cache with mock data (for development/testing)."""
    try:
        service = get_price_cache_service()
        
        # Check if Alchemy API is configured
        if not service.alchemy_api:
            return jsonify({
                'success': False,
                'error': 'Alchemy API not configured. Please set ALCHEMY_API_KEY environment variable.'
            }), 500
        
        # Try to populate cache with real prices
        app.logger.info("Test populating cache with real prices from Alchemy API")
        prices = service.refresh_prices()
        
        if prices:
            successful_refreshes = sum(1 for price in prices.values() if price is not None)
            total_symbols = len(prices)
            
            return jsonify({
                'success': True,
                'message': f'Successfully populated cache with {successful_refreshes}/{total_symbols} prices',
                'prices': prices,
                'timestamp': datetime.datetime.utcnow().isoformat()
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to fetch prices from Alchemy API'
            }), 500
        
    except Exception as e:
        app.logger.error(f"Failed to test populate cache: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/wallet/prices/<symbol>', methods=['GET'])
@token_required
def get_crypto_price(symbol):
    """Get cached price for a specific crypto symbol."""
    try:
        force_refresh = request.args.get('refresh', 'false').lower() == 'true'
        
        service = get_price_cache_service()
        price = service.get_price_with_fallback(symbol.upper(), force_refresh)
        
        if price is not None:
            return jsonify({
                'success': True,
                'symbol': symbol.upper(),
                'price': price,
                'currency': 'USD',
                'timestamp': datetime.datetime.utcnow().isoformat()
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': f'Price not available for {symbol}'
            }), 404
            
    except Exception as e:
        app.logger.error(f"Failed to get price for {symbol}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/wallet/prices/refresh', methods=['POST'])
@token_required
@is_admin
def refresh_crypto_prices():
    """Force refresh all crypto prices from Alchemy API."""
    try:
        symbols = request.args.getlist('symbols')
        
        service = get_price_cache_service()
        if symbols:
            prices = service.refresh_prices(symbols)
        else:
            prices = service.refresh_prices()
        
        return jsonify({
            'success': True,
            'message': f'Refreshed prices for {len(prices)} symbols',
            'prices': prices,
            'timestamp': datetime.datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        app.logger.error(f"Failed to refresh crypto prices: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/wallet/prices/refresh-expired', methods=['POST'])
@token_required
@is_admin
def refresh_expired_crypto_prices():
    """Refresh only expired crypto prices from Alchemy API."""
    try:
        service = get_price_cache_service()
        prices = service.refresh_expired_prices()
        
        return jsonify({
            'success': True,
            'message': f'Refreshed {len(prices)} expired prices',
            'prices': prices,
            'timestamp': datetime.datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        app.logger.error(f"Failed to refresh expired crypto prices: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/wallet/prices/status', methods=['GET'])
@token_required
@is_admin
def get_price_cache_status():
    """Get status information about the price cache service."""
    try:
        service = get_price_cache_service()
        status = service.get_cache_status()
        
        return jsonify({
            'success': True,
            'status': status
        }), 200
        
    except Exception as e:
        app.logger.error(f"Failed to get price cache status: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/wallet/prices/symbols', methods=['POST'])
@token_required
@is_admin
def manage_price_symbols():
    """Add or remove symbols from the price cache service."""
    try:
        data = request.get_json() or {}
        action = data.get('action')  # 'add' or 'remove'
        symbols = data.get('symbols', [])
        
        if not action or not symbols:
            return jsonify({
                'success': False,
                'error': 'Action and symbols are required'
            }), 400
        
        service = get_price_cache_service()
        results = {}
        
        if action == 'add':
            for symbol in symbols:
                results[symbol] = service.add_symbol(symbol)
        elif action == 'remove':
            for symbol in symbols:
                results[symbol] = service.remove_symbol(symbol)
        else:
            return jsonify({
                'success': False,
                'error': 'Invalid action. Use "add" or "remove"'
            }), 500
        
        return jsonify({
            'success': True,
            'action': action,
            'results': results,
            'timestamp': datetime.datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        app.logger.error(f"Failed to manage price symbols: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/wallet/prices/background-service', methods=['POST'])
@token_required
@is_admin
def control_background_price_service():
    """Control the background price refresh service."""
    try:
        data = request.get_json() or {}
        action = data.get('action')  # 'refresh-expired', 'force-refresh-all', 'status'
        
        if not action:
            return jsonify({
                'success': False,
                'error': 'Action is required'
            }), 400
        
        from shared.crypto.price_refresh_service import get_price_refresh_service
        service = get_price_refresh_service()
        
        if action == 'refresh-expired':
            prices = service.refresh_now()
            message = f"Background service refreshed {len(prices)} expired prices"
        elif action == 'force-refresh-all':
            prices = service.force_refresh_all()
            message = f"Background service force refreshed {len(prices)} prices"
        elif action == 'status':
            status = service.get_status()
            return jsonify({
                'success': True,
                'action': action,
                'status': status
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': f'Invalid action: {action}'
            }), 400
        
        return jsonify({
            'success': True,
            'action': action,
            'message': message,
            'prices': prices,
            'timestamp': datetime.datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        app.logger.error(f"Failed to control background price service: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# Portfolio and Ledger Endpoints - Removed duplicate route


@app.route('/wallet/portfolio/analysis/<period>', methods=['GET'])
@token_required
def get_portfolio_analysis(period):
    """Get portfolio analysis for specified period (24h, 7d, 30d, 90d)"""
    try:
        from wallet.portfolio_service import get_portfolio_analysis as analyze_portfolio
        
        result = analyze_portfolio(db.connection.session, g.user.id, period)
        return jsonify(result), 200
        
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        app.logger.error(f"Failed to get portfolio analysis: {str(e)}")
        return jsonify({"error": "Failed to get portfolio analysis"}), 500


@app.route('/wallet/portfolio/ledger', methods=['GET'])
@token_required
def get_ledger_history():
    """Get ledger history for authenticated user with optional filters"""
    try:
        from wallet.portfolio_service import get_ledger_history as get_user_ledger
        
        # Get query parameters
        currency = request.args.get('currency')
        limit = int(request.args.get('limit', 100))
        
        # Validate limit
        if limit > 1000:
            limit = 1000
        
        result = get_user_ledger(db.connection.session, g.user.id, currency, limit)
        return jsonify(result), 200
        
    except Exception as e:
        app.logger.error(f"Failed to get ledger history: {str(e)}")
        return jsonify({"error": "Failed to get ledger history"}), 500


@app.route('/wallet/portfolio/snapshot/<snapshot_type>', methods=['GET'])
@token_required
def get_portfolio_snapshot(snapshot_type):
    """Get specific portfolio snapshot (daily, weekly, monthly)"""
    try:
        from wallet.portfolio_service import PortfolioService
        from db.wallet import PortfolioSnapshot
        from sqlalchemy import and_
        from datetime import date, timedelta
        
        service = PortfolioService(db.connection.session)
        
        # Get current date
        today = date.today()
        
        if snapshot_type == 'daily':
            snapshot_date = today
        elif snapshot_type == 'weekly':
            # Start of current week
            snapshot_date = today - timedelta(days=today.weekday())
        elif snapshot_type == 'monthly':
            # Start of current month
            snapshot_date = today.replace(day=1)
        else:
            return jsonify({"error": "Invalid snapshot type. Use: daily, weekly, or monthly"}), 400
        
        # Get current portfolio data
        current_portfolio = service._calculate_current_portfolio(g.user.id)
        
        # Check if snapshot already exists
        snapshot = db.connection.session.query(PortfolioSnapshot).filter(
            and_(
                PortfolioSnapshot.user_id == g.user.id,
                PortfolioSnapshot.snapshot_type == snapshot_type,
                PortfolioSnapshot.snapshot_date == snapshot_date
            )
        ).first()
        
        # Create new snapshot if it doesn't exist
        if not snapshot:
            snapshot = PortfolioSnapshot(
                user_id=g.user.id,
                snapshot_type=snapshot_type,
                snapshot_date=snapshot_date,
                total_value_usd=current_portfolio.get('total_value_usd', 0.0),
                total_change_24h=current_portfolio.get('total_change_24h', 0.0),
                total_change_7d=current_portfolio.get('total_change_7d', 0.0),
                total_change_30d=current_portfolio.get('total_change_30d', 0.0),
                change_percent_24h=current_portfolio.get('change_percent_24h', 0.0),
                change_percent_7d=current_portfolio.get('change_percent_7d', 0.0),
                change_percent_30d=current_portfolio.get('change_percent_30d', 0.0),
                currency_count=current_portfolio.get('currency_count', 0),
                asset_details=current_portfolio.get('asset_details', {}),
                created_at=datetime.datetime.utcnow(),
                updated_at=datetime.datetime.utcnow()
            )
            db.connection.session.add(snapshot)
            db.connection.session.commit()
        
        if snapshot:
            result = {
                "snapshot_type": snapshot.snapshot_type,
                "snapshot_date": snapshot.snapshot_date.isoformat(),
                "total_value_usd": float(snapshot.total_value_usd),
                "total_change_24h": float(snapshot.total_change_24h) if snapshot.total_change_24h else 0.0,
                "total_change_7d": float(snapshot.total_change_7d) if snapshot.total_change_7d else 0.0,
                "total_change_30d": float(snapshot.total_change_30d) if snapshot.total_change_30d else 0.0,
                "change_percent_24h": float(snapshot.change_percent_24h) if snapshot.change_percent_24h else 0.0,
                "change_percent_7d": float(snapshot.change_percent_7d) if snapshot.change_percent_7d else 0.0,
                "change_percent_30d": float(snapshot.change_percent_30d) if snapshot.change_percent_30d else 0.0,
                "currency_count": snapshot.currency_count,
                "asset_details": snapshot.asset_details or {}
            }
            return jsonify(result), 200
        else:
            return jsonify({"error": "Failed to create snapshot"}), 500
        
    except Exception as e:
        app.logger.error(f"Failed to get portfolio snapshot: {str(e)}")
        return jsonify({"error": "Failed to get portfolio snapshot"}), 500

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
        session.close()
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

# Old Relworx deposit/withdrawal webhooks removed - these don't serve the trading purpose
# Trading webhooks are handled by /api/webhooks/relworx endpoint above

# Old Relworx deposit/withdrawal webhooks removed - now handled via trading system

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
                # Special handling for Ethereum addresses to use the ETH client's create_address method
                if symbol.upper() == "ETH":
                    # Use the ETH client directly for automatic Kafka notification
                    from shared.crypto.clients.eth import ETHWallet, EthereumConfig
                    
                    eth_config = EthereumConfig.mainnet(config('ALCHEMY_API_KEY', default=''))
                    eth_wallet = ETHWallet(
                        user_id=user_id,
                         eth_config=eth_config,
                        session=session,
                        logger=app.logger
                    )
                    eth_wallet.account_id = crypto_account.id
                    
                    # This will automatically create the address and send Kafka notification
                    eth_wallet.create_address(notify=True)
                    
                    # Get the created address from the database
                    created_address = session.query(CryptoAddress).filter_by(
                        account_id=crypto_account.id,
                        currency_code=symbol
                    ).first()
                    
                    if created_address:
                        created_addresses.append({
                            "symbol": symbol,
                            "address": created_address.address,
                            "account_id": crypto_account.id
                        })
                        app.logger.info(f"[Admin] Created {symbol} address for user {user_id}: {created_address.address}")
                    else:
                        app.logger.error(f"[Admin] Failed to retrieve created {symbol} address for user {user_id}")
                        
                else:
                    # Use the generic approach for other cryptocurrencies
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

@app.route("/wallet/sol/register-webhook", methods=["POST"])
@token_required
def register_solana_address_with_webhook():
    """Register a Solana address with Alchemy webhook for monitoring"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        address = data.get("address")
        if not address:
            return jsonify({"error": "Address is required"}), 400
        
        # Get the authenticated user
        user_id = g.user.id
        
        # Get database session
        from db.connection import get_session
        session = get_session()
        
        # Get the user's Solana account
        crypto_account = session.query(Account).filter_by(
            user_id=user_id,
            currency_code="SOL"
        ).first()
        
        if not crypto_account:
            return jsonify({"error": "No Solana account found for user"}), 404
        
        # Verify the address belongs to this user
        crypto_address = session.query(CryptoAddress).filter_by(
            account_id=crypto_account.id,
            address=address,
            currency_code="SOL"
        ).first()
        
        if not crypto_address:
            return jsonify({"error": "Address not found or does not belong to user"}), 404
        
        # Create Solana wallet instance and register with webhook
        from shared.crypto.clients.sol import SOLWallet, SolanaConfig
        from decouple import config
        
        alchemy_api_key = config('ALCHEMY_API_KEY', default=None)
        if not alchemy_api_key:
            return jsonify({"error": "ALCHEMY_API_KEY not configured"}), 500
        
        # Use testnet for now (can be made configurable)
        sol_config = SolanaConfig.testnet(alchemy_api_key)
        wallet = SOLWallet(user_id, sol_config, session, app.logger)
        wallet.account_id = crypto_account.id
        
        # Register the address with webhook
        success = wallet.register_address_with_webhook(address)
        
        if success:
            return jsonify({
                "message": "Address registered with webhook successfully",
                "address": address,
                "status": "registered"
            }), 200
        else:
            return jsonify({
                "error": "Failed to register address with webhook",
                "address": address,
                "status": "failed"
            }), 500
            
    except Exception as e:
        app.logger.error(f"Error registering Solana address with webhook: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/wallet/sol/register-all-webhooks", methods=["POST"])
@token_required
def register_all_solana_addresses_with_webhook():
    """Register all Solana addresses for the user with Alchemy webhook"""
    try:
        # Get the authenticated user
        user_id = g.user.id
        
        # Get database session
        from db.connection import get_session
        session = get_session()
        
        # Get the user's Solana account
        crypto_account = session.query(Account).filter_by(
            user_id=user_id,
            currency_code="SOL"
        ).first()
        
        if not crypto_account:
            return jsonify({"error": "No Solana account found for user"}), 404
        
        # Create Solana wallet instance
        from shared.crypto.clients.sol import SOLWallet, SolanaConfig
        from decouple import config
        
        alchemy_api_key = config('ALCHEMY_API_KEY', default=None)
        if not alchemy_api_key:
            return jsonify({"error": "ALCHEMY_API_KEY not configured"}), 500
        
        # Use testnet for now (can be made configurable)
        sol_config = SolanaConfig.testnet(alchemy_api_key)
        wallet = SOLWallet(user_id, sol_config, session, app.logger)
        wallet.account_id = crypto_account.id
        
        # Register all addresses with webhook
        results = wallet.register_all_addresses_with_webhook()
        
        return jsonify({
            "message": "Webhook registration completed",
            "results": results
        }), 200
            
    except Exception as e:
        app.logger.error(f"Error registering all Solana addresses with webhook: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/wallet/sol/unregister-webhook", methods=["POST"])
@token_required
def unregister_solana_address_from_webhook():
    """Unregister a Solana address from Alchemy webhook monitoring"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        address = data.get("address")
        if not address:
            return jsonify({"error": "Address is required"}), 400
        
        # Get the authenticated user
        user_id = g.user.id
        
        # Get database session
        from db.connection import get_session
        session = get_session()
        
        # Get the user's Solana account
        crypto_account = session.query(Account).filter_by(
            user_id=user_id,
            currency_code="SOL"
        ).first()
        
        if not crypto_account:
            return jsonify({"error": "No Solana account found for user"}), 404
        
        # Verify the address belongs to this user
        crypto_address = session.query(CryptoAddress).filter_by(
            account_id=crypto_account.id,
            address=address,
            currency_code="SOL"
        ).first()
        
        if not crypto_address:
            return jsonify({"error": "Address not found or does not belong to user"}), 400
        
        # Create Solana wallet instance and unregister from webhook
        from shared.crypto.clients.sol import SOLWallet, SolanaConfig
        from decouple import config
        
        alchemy_api_key = config('ALCHEMY_API_KEY', default=None)
        if not alchemy_api_key:
            return jsonify({"error": "ALCHEMY_API_KEY not configured"}), 500
        
        # Use testnet for now (can be made configurable)
        sol_config = SolanaConfig.testnet(alchemy_api_key)
        wallet = SOLWallet(user_id, sol_config, session, app.logger)
        wallet.account_id = crypto_account.id
        
        # Unregister the address from webhook
        success = wallet.unregister_address_from_webhook(address)
        
        if success:
            return jsonify({
                "message": "Address unregistered from webhook successfully",
                "address": address,
                "status": "unregistered"
            }), 200
        else:
            return jsonify({
                "error": "Failed to unregister address from webhook",
                "address": address,
                "status": "failed"
            }), 500
            
    except Exception as e:
        app.logger.error(f"Error unregistering Solana address from webhook: {e}")
        return jsonify({"error": str(e)}), 500

# Register the blueprint with the app
# app.register_blueprint(schemas_bp)
app.register_blueprint(blockcypher_webhook)
app.register_blueprint(solana_webhook)

@app.route("/wallet/withdraw/tron", methods=["POST"])
@token_required
def wallet_withdraw_tron():
    """
    Withdraw TRX to an external Tron address
    {
        "to_address": "T...",
        "amount": 1.0,
        "reference_id": "trx_withdraw_123",
        "description": "TRX withdrawal"
    }
    """
    try:
        user_id = g.user.id
        data = request.get_json() or {}
        to_address = data.get("to_address")
        amount = data.get("amount")
        reference_id = data.get("reference_id")
        description = data.get("description", "TRX withdrawal")
        token_contract = data.get("token_contract")
        token_symbol = data.get("token_symbol")  # e.g., USDT
        token_decimals = data.get("token_decimals")  # optional override

        missing_fields = []
        if not to_address:
            missing_fields.append({"to_address": "Missing required field"})
        if amount is None:
            missing_fields.append({"amount": "Missing required field"})
        if not reference_id:
            missing_fields.append({"reference_id": "Missing required field"})
        if missing_fields:
            return jsonify({"error": missing_fields}), 400

        # Basic Tron address validation
        if not to_address.startswith("T") or len(to_address) != 34:
            return jsonify({"error": [{"to_address": "Invalid Tron address format"}]}), 400

        try:
            amount = float(amount)
            if amount <= 0:
                return jsonify({"error": [{"amount": "Amount must be greater than 0"}]}), 400
        except (ValueError, TypeError):
            return jsonify({"error": [{"amount": "Invalid amount format"}]}), 400

        session = db.connection.session

        # Get user's TRX account
        trx_account = session.query(Account).filter_by(
            user_id=user_id,
            currency="TRX",
            account_type=AccountType.CRYPTO
        ).first()
        if not trx_account:
            return jsonify({"error": [{"account": "No TRX account found for user"}]}), 404

        # Duplicate transaction check
        existing = session.query(Transaction).filter_by(
            reference_id=reference_id,
            type=TransactionType.WITHDRAWAL
        ).first()
        if existing:
            return jsonify({"error": [{"reference_id": "Withdrawal transaction already exists for this reference_id"}]}), 409

        # If token_contract is provided, this is a TRC20 withdrawal using the token account
        is_trc20 = bool(token_contract)
        if is_trc20:
            # Find the user's token account for this symbol on TRX network
            token_symbol = (token_symbol or "USDT").upper()
            token_account = (
                session.query(Account)
                .filter(
                    Account.user_id == user_id,
                    Account.account_type == AccountType.CRYPTO,
                    Account.currency == token_symbol,
                ).all()
            )
            token_account = next(
                (acc for acc in token_account if (acc.precision_config or {}).get("parent_currency", "").upper() == "TRX"),
                None,
            )
            if not token_account:
                return jsonify({"error": [{"account": f"No {token_symbol} (TRX) account found for user"}]}), 404

            cfg = token_account.precision_config or {}
            decimals = int(token_decimals if token_decimals is not None else cfg.get("decimals", 6))
            amount_smallest = int(amount * (10 ** decimals))
            available_smallest = (token_account.crypto_balance_smallest_unit or 0)
            if available_smallest < amount_smallest:
                return jsonify({"error": [{"amount": f"Insufficient balance. Available: {available_smallest / (10 ** decimals)} {token_symbol}"}]}), 400
        else:
            # Native TRX
            available_balance_smallest = (trx_account.crypto_balance_smallest_unit or 0)
            amount_smallest = int(amount * 1_000_000)
            if available_balance_smallest < amount_smallest:
                available_balance_trx = available_balance_smallest / 1_000_000
                return jsonify({"error": [{"amount": f"Insufficient balance. Available: {available_balance_trx} TRX"}]}), 400

        # Initialize TRX wallet
        trx_api_key = config('TRON_API_KEY', default='')
        if not trx_api_key:
            return jsonify({"error": [{"system": "TRON_API_KEY not configured"}]}), 500
        trx_config = TronWalletConfig.testnet(trx_api_key)
        trx_wallet = TronWallet(
            user_id=user_id,
            tron_config=trx_config,
            session=session,
            logger=app.logger
        )
        trx_wallet.account_id = trx_account.id

        # Send transaction (TRX or TRC20)
        try:
            if is_trc20:
                tx_info = trx_wallet.send_trc20_transfer(
                    contract_address=token_contract,
                    to_address=to_address,
                    amount_standard=float(amount),
                    decimals=int(token_decimals if token_decimals is not None else (token_account.precision_config or {}).get("decimals", 6)),
                )
            else:
                tx_info = trx_wallet.send_transaction(to_address, float(amount))
        except Exception as e:
            app.logger.error(f"Failed to send transaction: {e}")
            return jsonify({"error": [{"transaction": f"Failed to send transaction: {str(e)}"}]}), 500

        # Lock the amount and create transaction record
        try:
            if is_trc20:
                session.refresh(token_account, with_for_update=True)
                token_account.crypto_locked_amount_smallest_unit = (token_account.crypto_locked_amount_smallest_unit or 0) + amount_smallest
                token_account.crypto_balance_smallest_unit = (token_account.crypto_balance_smallest_unit or 0) - amount_smallest
            else:
                session.refresh(trx_account, with_for_update=True)
                trx_account.crypto_locked_amount_smallest_unit = (trx_account.crypto_locked_amount_smallest_unit or 0) + amount_smallest
                trx_account.crypto_balance_smallest_unit = (trx_account.crypto_balance_smallest_unit or 0) - amount_smallest

            reservation_reference = f"trx_withdrawal_{int(time.time() * 1000)}_{reference_id}"
            reservation = Reservation(
                user_id=user_id,
                reference=reservation_reference,
                amount=amount,
                type=ReservationType.RESERVE,
                status="active"
            )

            metadata = {
                "to_address": to_address,
                "transaction_hash": tx_info.get("transaction_hash"),
                "from_address": tx_info.get("from_address"),
                "block_number": 0,
                "reservation_reference": reservation_reference,
            }

            tx = Transaction(
                account_id=(token_account.id if is_trc20 else trx_account.id),
                reference_id=reference_id,
                amount=amount,
                amount_smallest_unit=amount_smallest,
                precision_config=(
                    {
                        "currency": token_symbol,
                        "decimals": int(token_decimals if token_decimals is not None else (token_account.precision_config or {}).get("decimals", 6)),
                        "smallest_unit": "units",
                        "parent_currency": "TRX",
                    }
                    if is_trc20
                    else {
                        "currency": "TRX",
                        "decimals": 6,
                        "smallest_unit": "sun",
                    }
                ),
                type=TransactionType.WITHDRAWAL,
                status=TransactionStatus.AWAITING_CONFIRMATION,
                address=tx_info.get("from_address", ""),
                description=(description if not is_trc20 else f"{token_symbol} withdrawal"),
                provider=PaymentProvider.CRYPTO,
                provider_reference=tx_info.get("transaction_hash"),
                blockchain_txid=tx_info.get("transaction_hash"),
                confirmations=0,
                required_confirmations=20,
                metadata_json=(
                    {
                        **metadata,
                        "token_contract": token_contract,
                        "token_symbol": token_symbol,
                    }
                    if is_trc20
                    else metadata
                )
            )

            session.add(reservation)
            session.add(tx)
            session.commit()

            return jsonify({
                "message": ("TRC20 withdrawal sent successfully" if is_trc20 else "TRX withdrawal sent successfully"),
                "transaction_info": {
                    "reference_id": reference_id,
                    "amount": amount,
                    "to_address": to_address,
                    "transaction_hash": tx_info.get("transaction_hash"),
                    "status": "sent",
                    "reservation_reference": reservation_reference
                }
            }), 201
        except Exception as e:
            session.rollback()
            app.logger.error(f"❌ TRX withdrawal failed: {e}")
            return jsonify({"error": [{"system": f"Failed to process withdrawal: {str(e)}"}]}), 500

    except Exception as e:
        app.logger.error(f"❌ TRX withdrawal endpoint error: {e}")
        return jsonify({"error": [{"system": str(e)}]}), 500

# ============================================================================
# SWAP ENDPOINTS
# ============================================================================

@app.route("/wallet/swap/calculate", methods=["POST"])
@token_required
def calculate_swap():
    """
    Calculate swap amounts with real-time pricing and slippage protection
    """
    try:
        from_user_id = g.user.id
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['from_currency', 'to_currency', 'from_amount']
        for field in required_fields:
            if not data.get(field):
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
        from_currency = data.get("from_currency").upper()
        to_currency = data.get("to_currency").upper()
        from_amount = float(data.get("from_amount"))
        slippage_tolerance = float(data.get("slippage_tolerance", 0.01))  # Default 1%
        
        # Validate amount
        if from_amount <= 0:
            return jsonify({"error": "Amount must be greater than 0"}), 400
        
        # Use swap service
        from swap_service import SwapService
        
        swap_service = SwapService(db.connection.session)
        
        try:
            calculation = swap_service.calculate_swap_amounts(
                from_currency, to_currency, from_amount, slippage_tolerance
            )
            
            return jsonify({
                "success": True,
                "calculation": calculation
            }), 200
            
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        except Exception as e:
            app.logger.error(f"Error calculating swap: {e}")
            return jsonify({"error": "Failed to calculate swap amounts"}), 500
            
    except Exception as e:
        app.logger.error(f"Error in swap calculation endpoint: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route("/wallet/swap/execute", methods=["POST"])
@token_required
def execute_swap():
    """
    Execute a crypto-to-crypto swap
    """
    try:
        from_user_id = g.user.id
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['from_currency', 'to_currency', 'from_amount', 'reference_id']
        for field in required_fields:
            if not data.get(field):
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
        from_currency = data.get("from_currency").upper()
        to_currency = data.get("to_currency").upper()
        from_amount = float(data.get("from_amount"))
        reference_id = data.get("reference_id")
        slippage_tolerance = float(data.get("slippage_tolerance", 0.01))  # Default 1%
        
        # Validate amount
        if from_amount <= 0:
            return jsonify({"error": "Amount must be greater than 0"}), 400
        
        # Validate reference_id format
        if not reference_id or not isinstance(reference_id, str) or len(reference_id.strip()) == 0:
            return jsonify({"error": "reference_id must be a non-empty string"}), 400
        
        # Use swap service
        from swap_service import SwapService
        
        swap_service = SwapService(db.connection.session)
        
        try:
            result = swap_service.execute_swap(
                user_id=from_user_id,
                from_currency=from_currency,
                to_currency=to_currency,
                from_amount=from_amount,
                reference_id=reference_id,
                slippage_tolerance=slippage_tolerance
            )
            
            return jsonify(result), 201
            
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        except Exception as e:
            app.logger.error(f"Error executing swap: {e}")
            return jsonify({"error": "Failed to execute swap"}), 500
            
    except Exception as e:
        app.logger.error(f"Error in swap execution endpoint: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route("/wallet/swap/history", methods=["GET"])
@token_required
def get_swap_history():
    """
    Get user's swap history
    """
    try:
        from_user_id = g.user.id
        limit = request.args.get("limit", 50, type=int)
        
        # Use swap service
        from swap_service import SwapService
        
        swap_service = SwapService(db.connection.session)
        
        try:
            history = swap_service.get_swap_history(from_user_id, limit)
            
            return jsonify({
                "success": True,
                "swaps": history
            }), 200
            
        except Exception as e:
            app.logger.error(f"Error getting swap history: {e}")
            return jsonify({"error": "Failed to get swap history"}), 500
            
    except Exception as e:
        app.logger.error(f"Error in swap history endpoint: {e}")
        return jsonify({"error": "Internal server error"}), 500

# ============================================================================
# RESERVE MANAGEMENT ENDPOINTS
# ============================================================================

@app.route("/wallet/reserves/status", methods=["GET"])
@token_required
# @is_admin
def get_reserve_status():
    """
    Get status of all system reserves (Admin only)
    """
    try:
        from reserve_service import ReserveService
        
        reserve_service = ReserveService(db.connection.session)
        
        try:
            reserves = reserve_service.get_all_reserves()
            
            return jsonify({
                "success": True,
                "reserves": reserves
            }), 200
            
        except Exception as e:
            app.logger.error(f"Error getting reserve status: {e}")
            return jsonify({"error": "Failed to get reserve status"}), 500
            
    except Exception as e:
        app.logger.error(f"Error in reserve status endpoint: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route("/wallet/reserves/<currency>/<account_type>/balance", methods=["GET"])
@token_required
@is_admin
def get_reserve_balance(currency: str, account_type: str):
    """
    Get balance of a specific reserve (Admin only)
    """
    try:
        from reserve_service import ReserveService
        from db.wallet import AccountType
        
        # Validate account type
        try:
            account_type_enum = AccountType(account_type.upper())
        except ValueError as e:
            app.logger.error(f"Invalid account type: {account_type}, {e!r}")
            return jsonify({"error": f"Invalid account type: {account_type}"}), 400
        
        reserve_service = ReserveService(db.connection.session)
        
        try:
            balance = reserve_service.get_reserve_balance(currency.upper(), account_type_enum)
            
            return jsonify({
                "success": True,
                "balance": balance
            }), 200
            
        except Exception as e:
            app.logger.error(f"Error getting reserve balance: {e}")
            return jsonify({"error": "Failed to get reserve balance"}), 500
            
    except Exception as e:
        app.logger.error(f"Error in reserve balance endpoint: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route("/wallet/reserves/<currency>/<account_type>/topup", methods=["POST"])
@token_required
@is_admin
def top_up_reserve(currency: str, account_type: str):
    """
    Top up a reserve with additional funds (Admin only)
    """
    try:
        from reserve_service import ReserveService
        from db.wallet import AccountType
        
        # Validate account type
        try:
            account_type_enum = AccountType(account_type.upper())
        except ValueError:
            return jsonify({"error": f"Invalid account type: {account_type}"}), 400
        
        data = request.get_json()
        amount = float(data.get("amount", 0))
        source_reference = data.get("source_reference")
        
        if amount <= 0:
            return jsonify({"error": "Amount must be greater than 0"}), 400
        
        reserve_service = ReserveService(db.connection.session)
        
        try:
            result = reserve_service.top_up_reserve(
                currency.upper(), amount, account_type_enum, source_reference
            )
            
            if result["success"]:
                return jsonify(result), 200
            else:
                return jsonify(result), 400
                
        except Exception as e:
            app.logger.error(f"Error topping up reserve: {e}")
            return jsonify({"error": "Failed to top up reserve"}), 500
            
    except Exception as e:
        app.logger.error(f"Error in reserve topup endpoint: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route("/wallet/reserves/<currency>/<account_type>/withdraw", methods=["POST"])
@token_required
@is_admin
def withdraw_from_reserve(currency: str, account_type: str):
    """
    Withdraw funds from a reserve (Admin only)
    """
    try:
        from reserve_service import ReserveService
        from db.wallet import AccountType
        
        # Validate account type
        try:
            account_type_enum = AccountType(account_type.upper())
        except ValueError:
            return jsonify({"error": f"Invalid account type: {account_type}"}), 400
        
        data = request.get_json()
        amount = float(data.get("amount", 0))
        destination_reference = data.get("destination_reference")
        
        if amount <= 0:
            return jsonify({"error": "Amount must be greater than 0"}), 400
        
        reserve_service = ReserveService(db.connection.session)
        
        try:
            result = reserve_service.withdraw_from_reserve(
                currency.upper(), amount, account_type_enum, destination_reference
            )
            
            if result["success"]:
                return jsonify(result), 200
            else:
                return jsonify(result), 400
                
        except Exception as e:
            app.logger.error(f"Error withdrawing from reserve: {e}")
            return jsonify({"error": "Failed to withdraw from reserve"}), 500
            
    except Exception as e:
        app.logger.error(f"Error in reserve withdrawal endpoint: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route("/wallet/reserves/analytics", methods=["GET"])
@token_required
@is_admin
def get_reserve_analytics():
    """
    Get analytics about reserve usage over time (Admin only)
    """
    try:
        from reserve_service import ReserveService
        
        period_days = request.args.get("period_days", 30, type=int)
        
        if period_days <= 0 or period_days > 365:
            return jsonify({"error": "Period must be between 1 and 365 days"}), 400
        
        reserve_service = ReserveService(db.connection.session)
        
        try:
            analytics = reserve_service.get_reserve_analytics(period_days)
            
            return jsonify({
                "success": True,
                "analytics": analytics
            }), 200
            
        except Exception as e:
            app.logger.error(f"Error getting reserve analytics: {e}")
            return jsonify({"error": "Failed to get reserve analytics"}), 500
            
    except Exception as e:
        app.logger.error(f"Error in reserve analytics endpoint: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route("/wallet/reserves/cache/clear", methods=["POST"])
@token_required
@is_admin
def clear_reserve_cache():
    """
    Clear reserve service cache (Admin only)
    """
    try:
        from reserve_service import ReserveService
        
        reserve_service = ReserveService(db.connection.session)
        
        try:
            reserve_service.clear_cache()
            
            return jsonify({
                "success": True,
                "message": "Reserve cache cleared successfully"
            }), 200
            
        except Exception as e:
            app.logger.error(f"Error clearing reserve cache: {e}")
            return jsonify({"error": "Failed to clear reserve cache"}), 500
            
    except Exception as e:
        app.logger.error(f"Error in reserve cache clear endpoint: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/api/wallet/crypto/balances', methods=['GET'])
@token_required
def get_crypto_balances(current_user):
    """Get user's aggregated crypto balances across all supported cryptocurrencies with multi-chain support"""
    try:
        session = db.connection.get_session()
        
        # Import the balance aggregation service
        from shared.balance_aggregation import BalanceAggregationService
        
        # Initialize the balance aggregation service
        balance_service = BalanceAggregationService(session)
        
        # Get aggregated balances
        aggregated_balances = balance_service.get_user_aggregated_balances(current_user.id)
        
        # Get current crypto prices
        try:
            cached_prices = get_cached_prices()
        except:
            cached_prices = {}
        
        # Calculate portfolio value
        portfolio_value = balance_service.get_portfolio_value(current_user.id, cached_prices, 'UGX')
        
        # Format response for UI compatibility
        balances = {}
        
        for currency, balance_info in aggregated_balances.items():
            # Get primary address for this currency (first available address)
            primary_address = None
            primary_memo = None
            
            if balance_info['addresses']:
                primary_addr = balance_info['addresses'][0]
                primary_address = primary_addr['address']
                primary_memo = primary_addr.get('memo')
            
            # Build balance entry with aggregated information
            balance_entry = {
                'balance': balance_info['total_balance'],
                'address': primary_address,
                'memo': primary_memo,
                'chains': balance_info['chains'],  # Show breakdown by chain
                'all_addresses': balance_info['addresses']  # All addresses across chains
            }
            
            # Add price and value information if available
            if currency in cached_prices and cached_prices[currency] is not None:
                price_usd = cached_prices[currency]
                try:
                    usd_to_ugx_rate = forex_service.get_exchange_rate('usd', 'ugx')
                except Exception:
                    usd_to_ugx_rate = 3700  # Fallback rate
                price_ugx = price_usd * usd_to_ugx_rate
                
                balance_entry.update({
                    'price_usd': price_usd,
                    'price_ugx': price_ugx,
                    'value_usd': balance_info['total_balance'] * price_usd,
                    'value_ugx': balance_info['total_balance'] * price_ugx
                })
            
            balances[currency] = balance_entry
        
        # Add any missing supported currencies with zero balance for UI consistency
        supported_cryptos = ['BTC', 'ETH', 'SOL', 'BNB', 'USDT', 'USDC', 'TRX', 'LTC']
        for crypto in supported_cryptos:
            if crypto not in balances:
                balances[crypto] = {
                    'balance': 0.0,
                    'address': None,
                    'memo': None,
                    'chains': {},
                    'all_addresses': []
                }
        
        return jsonify({
            "success": True,
            "balances": balances,
            "total_value_usd": portfolio_value['total_value_usd'],
            "total_value_ugx": portfolio_value['total_value_target'],
            "portfolio_breakdown": portfolio_value['currencies'],
            "aggregation_summary": balance_service.get_balance_summary(current_user.id)
        })
        
    except Exception as e:
        app.logger.error(f"Error getting aggregated crypto balances: {e}")
        app.logger.error(traceback.format_exc())
        return jsonify({"success": False, "error": str(e)}), 400
    finally:
        if 'session' in locals():
            session.close()

@app.route('/api/wallet/crypto/balances/detailed', methods=['GET'])
@token_required
def get_detailed_crypto_balances(current_user):
    """Get detailed aggregated crypto balances with full multi-chain breakdown"""
    try:
        session = db.connection.get_session()
        
        # Import the balance aggregation service
        from shared.balance_aggregation import BalanceAggregationService
        
        # Initialize the balance aggregation service
        balance_service = BalanceAggregationService(session)
        
        # Get aggregated balances
        aggregated_balances = balance_service.get_user_aggregated_balances(current_user.id)
        
        # Get current crypto prices
        try:
            cached_prices = get_cached_prices()
        except:
            cached_prices = {}
        
        # Calculate portfolio value
        portfolio_value = balance_service.get_portfolio_value(current_user.id, cached_prices, 'UGX')
        
        # Get balance summary
        balance_summary = balance_service.get_balance_summary(current_user.id)
        
        return jsonify({
            "success": True,
            "aggregated_balances": aggregated_balances,
            "portfolio_value": portfolio_value,
            "balance_summary": balance_summary,
            "multi_chain_details": {
                currency: {
                    "total_balance": info['total_balance'],
                    "chain_breakdown": info['chains'],
                    "addresses_by_chain": info['addresses']
                }
                for currency, info in aggregated_balances.items()
                if len(info['chains']) > 1  # Only show multi-chain tokens
            }
        })
        
    except Exception as e:
        app.logger.error(f"Error getting detailed crypto balances: {e}")
        app.logger.error(traceback.format_exc())
        return jsonify({"success": False, "error": str(e)}), 400
    finally:
        if 'session' in locals():
            session.close()

@app.route('/api/v1/wallet/dashboard/summary', methods=['GET'])
@token_required
def dashboard_summary():
    """
    Get a summary of the user's portfolio for the dashboard.
    """
    session = db.connection.session
    try:
        current_user = g.user
        summary = get_dashboard_summary(session, current_user.id)
        return jsonify({"success": True, "data": summary}), 200
    except Exception as e:
        # g.user might not be available on exception, so we can't log the user ID here.
        app.logger.error(f"Error getting dashboard summary: {e}")
        return jsonify({"error": "Failed to retrieve dashboard summary"}), 500
    finally:
        session.close()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000, debug=True)
