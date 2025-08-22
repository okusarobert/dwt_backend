"""
Trading Service for Crypto Buy/Sell Operations
Handles multiple payment methods: Mobile Money, Bank Deposit, Vouchers
"""

import logging
import uuid
import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from db.connection import get_session
from db.wallet import (
    Trade, TradeType, TradeStatus, PaymentMethod, PaymentProvider,
    Transaction, TransactionType, TransactionStatus, Account,
    Voucher, VoucherStatus
)
from db.models import User
from shared.crypto.price_cache_service import get_cached_prices
from lib.relworx_client import RelworxApiClient
from shared.kafka_producer import get_kafka_producer
from shared.currency_precision import AmountConverter
from shared.trading_accounting import TradingAccountingService
from shared.fiat.forex_service import forex_service
from db.accounting import JournalEntry, LedgerTransaction, AccountingAccount
import json

logger = logging.getLogger(__name__)

class TradingService:
    def __init__(self, session: Session = None):
        self.relworx_client = RelworxApiClient()
        self.kafka_producer = get_kafka_producer()
        self.session = session
        if session:
            self.accounting_service = TradingAccountingService(session)
    
    def get_exchange_rate(self, from_currency: str, to_currency: str) -> float:
        """Get exchange rate between two currencies"""
        return forex_service.get_exchange_rate(from_currency, to_currency)
        
    def get_crypto_price(self, crypto_currency: str, fiat_currency: str = "USD") -> float:
        """Get current crypto price with proper fiat conversion"""
        try:
            prices = get_cached_prices()
            
            # The cache stores prices with just the symbol key (e.g., "BTC")
            # All cached prices are in USD by default
            crypto_symbol = crypto_currency.upper()
            
            if crypto_symbol in prices and prices[crypto_symbol] is not None:
                usd_price = float(prices[crypto_symbol])
                
                if fiat_currency.upper() == "USD":
                    return usd_price
                
                # Convert USD price to target fiat currency
                exchange_rate = forex_service.get_exchange_rate("USD", fiat_currency)
                converted_price = usd_price * exchange_rate
                
                logger.debug(f"Converted {crypto_currency} price: ${usd_price} USD -> {converted_price} {fiat_currency} (rate: {exchange_rate})")
                return converted_price
                
            raise ValueError(f"Price not found for {crypto_currency}")
        except Exception as e:
            logger.error(f"Error getting crypto price: {e}")
            raise
    
    def calculate_trade_amounts(
        self, 
        crypto_currency: str, 
        fiat_currency: str,
        amount: float,
        trade_type: TradeType,
        payment_method: PaymentMethod
    ) -> Dict:
        """Calculate trade amounts including fees"""
        
        # Get current price
        price = self.get_crypto_price(crypto_currency, fiat_currency)
        
        # Calculate fees based on payment method
        fee_percentage = self._get_fee_percentage(payment_method)
        
        if trade_type == TradeType.BUY:
            # User is buying crypto with fiat
            fiat_amount = amount
            fee_amount = fiat_amount * fee_percentage
            net_fiat = fiat_amount - fee_amount
            crypto_amount = net_fiat / price
            
        else:  # SELL
            # User is selling crypto for fiat
            crypto_amount = amount
            gross_fiat = crypto_amount * price
            fee_amount = gross_fiat * fee_percentage
            fiat_amount = gross_fiat - fee_amount
            
        # Convert to smallest units using unified precision system
        crypto_amount_smallest = AmountConverter.to_smallest_units(crypto_amount, crypto_currency)
        fiat_amount_smallest = AmountConverter.to_smallest_units(fiat_amount, fiat_currency)
        fee_amount_smallest = AmountConverter.to_smallest_units(fee_amount, fiat_currency)
            
        return {
            "crypto_amount": crypto_amount,
            "crypto_amount_smallest_unit": crypto_amount_smallest,
            "fiat_amount": fiat_amount,
            "fiat_amount_smallest_unit": fiat_amount_smallest,
            "fee_amount": fee_amount,
            "fee_amount_smallest_unit": fee_amount_smallest,
            "exchange_rate": price,
            "fee_percentage": fee_percentage
        }
    
    def _get_fee_percentage(self, payment_method: PaymentMethod) -> float:
        """Get fee percentage based on payment method"""
        # All payment methods now have 1% fee
        return 0.01  # 1%
    
    def create_trade(
        self,
        user_id: int,
        trade_type: TradeType,
        crypto_currency: str,
        fiat_currency: str,
        amount: float,
        payment_method: PaymentMethod,
        payment_details: Dict,
        session: Session
    ) -> Trade:
        """Create a new trade"""
        
        # Get or create user account for the crypto currency
        account = session.query(Account).filter(
            Account.user_id == user_id,
            Account.currency == crypto_currency
        ).first()
        
        if not account:
            # Auto-create crypto account for the user
            from service import generate_random_digits
            from db.wallet import AccountType
            
            account_number = f"{generate_random_digits(10)}"
            account = Account(
                user_id=user_id,
                currency=crypto_currency,
                account_type=AccountType.CRYPTO,
                balance=0.0,
                locked_amount=0.0,
                account_number=account_number,
                label=f"{crypto_currency} Account"
            )
            session.add(account)
            session.flush()  # Get the account ID without committing
            logger.info(f"Auto-created {crypto_currency} account for user {user_id}")
        
        # Calculate amounts
        amounts = self.calculate_trade_amounts(
            crypto_currency, fiat_currency, amount, trade_type, payment_method
        )
        
        # Create trade with unified precision system
        trade = Trade(
            user_id=user_id,
            account_id=account.id,
            trade_type=trade_type,  # Store enum object, not .value
            status=TradeStatus.PENDING,  # Store enum object, not .value
            crypto_currency=crypto_currency.upper(),
            crypto_amount=amounts["crypto_amount"],
            crypto_amount_smallest_unit=amounts["crypto_amount_smallest_unit"],
            fiat_currency=fiat_currency.upper(),
            fiat_amount=amounts["fiat_amount"],
            fiat_amount_smallest_unit=amounts["fiat_amount_smallest_unit"],
            exchange_rate=amounts["exchange_rate"],
            fee_amount=amounts["fee_amount"],
            fee_amount_smallest_unit=amounts["fee_amount_smallest_unit"],
            fee_currency=fiat_currency.upper(),
            payment_method=payment_method,  # Store enum object, not .value
            precision_config={
                "crypto_currency": crypto_currency,
                "fiat_currency": fiat_currency,
                "fee_currency": fiat_currency
            },
            description=f"{trade_type.value.title()} {amounts['crypto_amount']} {crypto_currency} with {payment_method.value}",
            trade_metadata=payment_details
        )
        
        # Set payment-specific details (only for fields that exist in database)
        if payment_method == PaymentMethod.VOUCHER:
            trade.voucher_id = payment_details.get("voucher_id")
        elif payment_method == PaymentMethod.MOBILE_MONEY:
            trade.payment_provider = PaymentProvider.RELWORX
            # Store mobile money details in both metadata and dedicated fields
            trade.mobile_money_provider = payment_details.get("provider")
            if not trade.trade_metadata:
                trade.trade_metadata = {}
            trade.trade_metadata.update({
                "phone_number": payment_details.get("phone_number"),
                "provider": payment_details.get("provider")
            })
        elif payment_method == PaymentMethod.BANK_DEPOSIT:
            # Store bank details in both metadata and dedicated fields
            trade.bank_name = payment_details.get("bank_name")
            trade.account_name = payment_details.get("account_name")
            trade.account_number = payment_details.get("account_number")
            trade.deposit_reference = payment_details.get("deposit_reference")
            if not trade.trade_metadata:
                trade.trade_metadata = {}
            trade.trade_metadata.update({
                "bank_name": payment_details.get("bank_name"),
                "account_name": payment_details.get("account_name"),
                "account_number": payment_details.get("account_number"),
                "deposit_reference": payment_details.get("deposit_reference")
            })
        
        session.add(trade)
        session.commit()
        
        # Send to Kafka for processing
        self._send_trade_to_kafka(trade)
        
        logger.info(f"Created trade {trade.id} for user {user_id}")
        return trade
    
    def process_mobile_money_payment(self, trade: Trade, session: Session) -> bool:
        """Process mobile money payment using existing Relworx deposit logic"""
        try:
            if not trade.phone_number:
                raise ValueError("Phone number required for mobile money payment")
            
            # Use existing Relworx request_payment method (same as deposit)
            reference_id = f"TRADE_{trade.id}"
            description = f"Buy {trade.crypto_currency} - DT Exchange"
            
            response = self.relworx_client.request_payment(
                reference=reference_id,
                msisdn=trade.phone_number,
                amount=float(trade.fiat_amount),
                description=description
            )
            
            if response:
                trade.payment_reference = response.get("internal_reference")
                trade.payment_status = "pending"
                trade.status = TradeStatus.PAYMENT_PENDING
                trade.trade_metadata = trade.trade_metadata or {}
                trade.trade_metadata.update(response)
                session.commit()
                
                logger.info(f"Mobile money payment initiated for trade {trade.id}")
                return True
            else:
                logger.error(f"Failed to initiate mobile money payment for trade {trade.id}")
                return False
                
        except Exception as e:
            logger.error(f"Error processing mobile money payment: {e}")
            trade.status = TradeStatus.FAILED
            trade.trade_metadata = trade.trade_metadata or {}
            trade.trade_metadata['error'] = f"Payment initiation failed: {str(e)}"
            session.commit()
            return False
    
    def process_voucher_payment(self, trade: Trade, voucher_code: str, session: Session) -> bool:
        """Process voucher payment"""
        try:
            # Validate voucher
            voucher = session.query(Voucher).filter(
                Voucher.code == voucher_code,
                Voucher.status == VoucherStatus.ACTIVE
            ).first()
            
            if not voucher:
                raise ValueError("Invalid or expired voucher")
            
            if voucher.currency != trade.fiat_currency:
                raise ValueError(f"Voucher currency {voucher.currency} doesn't match trade currency {trade.fiat_currency}")
            
            if voucher.amount < trade.fiat_amount:
                raise ValueError("Voucher amount insufficient")
            
            # Mark voucher as used
            voucher.status = VoucherStatus.USED
            voucher.user_id = trade.user_id
            voucher.used_at = datetime.datetime.utcnow()
            
            # Update trade
            trade.voucher_id = voucher.id
            trade.payment_status = "completed"
            trade.payment_received_at = datetime.datetime.utcnow()
            trade.status = TradeStatus.PAYMENT_RECEIVED
            
            session.commit()
            
            logger.info(f"Voucher payment completed for trade {trade.id}")
            return True
            
        except Exception as e:
            logger.error(f"Error processing voucher payment: {e}")
            return False
    
    def complete_trade(self, trade: Trade, session: Session) -> bool:
        """Complete trade and create accounting entries with unified precision"""
        try:
            if trade.trade_type == TradeType.BUY:
                return self._complete_buy_trade(trade, session)
            else:
                return self._complete_sell_trade(trade, session)
        except Exception as e:
            logger.error(f"Error completing trade {trade.id}: {e}")
            trade.status = TradeStatus.FAILED
            session.commit()
            return False
    
    def _complete_buy_trade(self, trade: Trade, session: Session) -> bool:
        """Complete buy trade - user pays fiat, receives crypto"""
        try:
            # Get user's crypto account
            account = session.query(Account).filter_by(id=trade.account_id).first()
            if not account:
                raise ValueError(f"Account {trade.account_id} not found")
            
            # Credit user's crypto balance using unified precision
            current_balance = account.balance_smallest_unit or 0
            account.balance_smallest_unit = current_balance + trade.crypto_amount_smallest_unit
            account.balance = float(account.balance) + float(trade.crypto_amount)  # Backward compatibility
            
            # Debit crypto from reserve account (we gave crypto to user)
            self._adjust_reserve_balance(trade.crypto_currency, -trade.crypto_amount_smallest_unit, session)
            
            # Update trade status
            trade.status = TradeStatus.COMPLETED
            trade.completed_at = datetime.datetime.utcnow()
            
            # Create accounting entries
            if self.session and hasattr(self, 'accounting_service'):
                self._create_buy_trade_accounting_entry(trade, account)
            
            session.commit()
            
            logger.info(f"✅ Completed buy trade {trade.id}: {AmountConverter.format_display_amount(trade.crypto_amount_smallest_unit, trade.crypto_currency)}")
            return True
            
        except Exception as e:
            logger.error(f"Error completing buy trade {trade.id}: {e}")
            raise
    
    def _complete_sell_trade(self, trade: Trade, session: Session) -> bool:
        """Complete sell trade - user sells crypto, receives fiat via mobile money"""
        try:
            # Get user's crypto account
            account = session.query(Account).filter_by(id=trade.account_id).first()
            if not account:
                raise ValueError(f"Account {trade.account_id} not found")
            
            # Check sufficient balance
            available_balance = account.balance_smallest_unit or 0
            if available_balance < trade.crypto_amount_smallest_unit:
                raise ValueError("Insufficient crypto balance")
            
            # Debit user's crypto balance using unified precision
            account.balance_smallest_unit = available_balance - trade.crypto_amount_smallest_unit
            account.balance = float(account.balance) - float(trade.crypto_amount)  # Backward compatibility
            
            # Credit crypto to reserve account (we received crypto from user)
            self._adjust_reserve_balance(trade.crypto_currency, trade.crypto_amount_smallest_unit, session)
            
            # Update trade status
            trade.status = TradeStatus.PROCESSING_PAYOUT
            
            # Create accounting entries (debit user crypto, credit reserve)
            if self.session and hasattr(self, 'accounting_service'):
                self._create_sell_trade_accounting_entry(trade, account)
            
            # Initiate mobile money payout via Relworx
            if trade.payment_method == PaymentMethod.MOBILE_MONEY:
                payout_success = self._initiate_mobile_money_payout(trade, session)
                if not payout_success:
                    # Rollback balance change and reserve adjustment
                    account.balance_smallest_unit = available_balance
                    account.balance = float(account.balance) + float(trade.crypto_amount)
                    self._adjust_reserve_balance(trade.crypto_currency, -trade.crypto_amount_smallest_unit, session)
                    trade.status = TradeStatus.FAILED
                    session.commit()
                    return False
            
            session.commit()
            
            logger.info(f"✅ Processing sell trade {trade.id}: {AmountConverter.format_display_amount(trade.crypto_amount_smallest_unit, trade.crypto_currency)}")
            return True
            
        except Exception as e:
            logger.error(f"Error completing sell trade {trade.id}: {e}")
            raise
    
    def _create_buy_trade_accounting_entry(self, trade: Trade, account: Account):
        """Create accounting entry for buy trade"""
        try:
            # Format amount for description
            crypto_amount_display = AmountConverter.format_display_amount(trade.crypto_amount_smallest_unit, trade.crypto_currency)
            fiat_amount_display = AmountConverter.format_display_amount(trade.fiat_amount_smallest_unit, trade.fiat_currency)
            
            description = f"Buy trade: {crypto_amount_display} for {fiat_amount_display} (Trade #{trade.id})"
            
            # Create journal entry
            journal_entry = self.accounting_service.create_journal_entry(
                description=description,
                reference_id=f"TRADE_BUY_{trade.id}",
                metadata={
                    "trade_id": trade.id,
                    "trade_type": "buy",
                    "user_id": trade.user_id,
                    "crypto_currency": trade.crypto_currency,
                    "fiat_currency": trade.fiat_currency
                }
            )
            
            # Get accounting accounts
            crypto_asset_account = self.accounting_service.get_or_create_account(f"Crypto Assets - {trade.crypto_currency}")
            user_liability_account = self.accounting_service.get_or_create_account(f"User Liabilities - {trade.crypto_currency}")
            
            # Debit: Crypto Assets (increase asset)
            # Credit: User Liabilities (increase liability to user)
            self.accounting_service.create_ledger_transactions(
                journal_entry.id,
                [
                    (crypto_asset_account.id, trade.crypto_amount_smallest_unit, 0),  # Debit crypto assets
                    (user_liability_account.id, 0, trade.crypto_amount_smallest_unit)  # Credit user liabilities
                ]
            )
            
            logger.info(f"💰 Created buy trade accounting entry: {description}")
            
        except Exception as e:
            logger.error(f"Error creating buy trade accounting entry: {e}")
            raise
    
    def _create_sell_trade_accounting_entry(self, trade: Trade, account: Account):
        """Create accounting entry for sell trade"""
        try:
            # Format amount for description
            crypto_amount_display = AmountConverter.format_display_amount(trade.crypto_amount_smallest_unit, trade.crypto_currency)
            fiat_amount_display = AmountConverter.format_display_amount(trade.fiat_amount_smallest_unit, trade.fiat_currency)
            
            description = f"Sell trade: {crypto_amount_display} for {fiat_amount_display} (Trade #{trade.id})"
            
            # Create journal entry
            journal_entry = self.accounting_service.create_journal_entry(
                description=description,
                reference_id=f"TRADE_SELL_{trade.id}",
                metadata={
                    "trade_id": trade.id,
                    "trade_type": "sell",
                    "user_id": trade.user_id,
                    "crypto_currency": trade.crypto_currency,
                    "fiat_currency": trade.fiat_currency
                }
            )
            
            # Get accounting accounts
            user_liability_account = self.accounting_service.get_or_create_account(f"User Liabilities - {trade.crypto_currency}")
            crypto_reserve_account = self.accounting_service.get_or_create_account(f"Crypto Reserves - {trade.crypto_currency}")
            
            # Debit: User Liabilities (decrease liability to user)
            # Credit: Crypto Reserves (increase reserve for payout)
            self.accounting_service.create_ledger_transactions(
                journal_entry.id,
                [
                    (user_liability_account.id, trade.crypto_amount_smallest_unit, 0),  # Debit user liabilities
                    (crypto_reserve_account.id, 0, trade.crypto_amount_smallest_unit)  # Credit crypto reserves
                ]
            )
            
            logger.info(f"💸 Created sell trade accounting entry: {description}")
            
        except Exception as e:
            logger.error(f"Error creating sell trade accounting entry: {e}")
            raise
    
    def _adjust_reserve_balance(self, currency: str, amount_smallest_unit: int, session: Session):
        """Adjust reserve account balance for trading operations"""
        try:
            from reserve_service import ReserveService
            from db.wallet import AccountType
            
            reserve_service = ReserveService(session)
            reserve_account = reserve_service.get_reserve_account(currency, AccountType.CRYPTO)
            
            if not reserve_account:
                logger.warning(f"No reserve account found for {currency}, creating one")
                reserve_account = reserve_service.get_reserve_account(currency, AccountType.CRYPTO)
            
            if reserve_account:
                # Update reserve balance using unified precision
                current_balance = reserve_account.balance_smallest_unit or 0
                new_balance = current_balance + amount_smallest_unit
                
                if new_balance < 0:
                    logger.warning(f"Reserve balance for {currency} would go negative: {new_balance}")
                
                reserve_account.balance_smallest_unit = new_balance
                reserve_account.balance = float(reserve_account.balance or 0) + (amount_smallest_unit / (10 ** 8))  # Assuming 8 decimal places
                
                action = "credited" if amount_smallest_unit > 0 else "debited"
                logger.info(f"💰 Reserve {action}: {AmountConverter.format_display_amount(abs(amount_smallest_unit), currency)} {currency}")
            else:
                logger.error(f"Failed to get or create reserve account for {currency}")
                
        except Exception as e:
            logger.error(f"Error adjusting reserve balance for {currency}: {e}")
            raise
    
    def _initiate_mobile_money_payout(self, trade: Trade, session: Session) -> bool:
        """Initiate mobile money payout via Relworx"""
        try:
            if not trade.phone_number:
                raise ValueError("Phone number required for mobile money payout")
            
            reference_id = f"PAYOUT_{trade.id}"
            description = f"Sell {trade.crypto_currency} payout - DT Exchange"
            
            # Use Relworx to send money to user
            response = self.relworx_client.send_payment(
                reference=reference_id,
                msisdn=trade.phone_number,
                amount=float(trade.fiat_amount),
                description=description
            )
            
            if response:
                trade.payout_reference = response.get("internal_reference")
                trade.payout_status = "pending"
                trade.trade_metadata = trade.trade_metadata or {}
                trade.trade_metadata.update(response)
                
                logger.info(f"Mobile money payout initiated for trade {trade.id}")
                return True
            else:
                logger.error(f"Failed to initiate mobile money payout for trade {trade.id}")
                return False
                
        except Exception as e:
            logger.error(f"Error initiating mobile money payout: {e}")
            return False
    
    def process_bank_deposit_payment(self, trade: Trade, session: Session) -> bool:
        """Process bank deposit payment"""
        try:
            # Generate deposit reference
            deposit_ref = f"DEP_{trade.id}_{uuid.uuid4().hex[:8].upper()}"
            
            # Update trade with deposit details
            trade.deposit_reference = deposit_ref
            trade.payment_status = "pending"
            trade.status = TradeStatus.PAYMENT_PENDING
            
            session.commit()
            
            logger.info(f"Bank deposit payment initiated for trade {trade.id}")
            return True
            
        except Exception as e:
            logger.error(f"Error processing bank deposit payment: {e}")
            return False
    
    def execute_trade(self, trade: Trade, session: Session) -> bool:
        """Execute a trade by transferring assets (renamed to avoid duplication)"""
        try:
            # Create transactions
            if trade.trade_type == TradeType.BUY:
                # User buys crypto: debit fiat, credit crypto
                success = self._execute_buy_trade(trade, session)
            else:
                # User sells crypto: debit crypto, credit fiat
                success = self._execute_sell_trade(trade, session)
            
            if success:
                trade.status = TradeStatus.COMPLETED
                trade.completed_at = datetime.datetime.utcnow()
                session.commit()
                
                # Send success notification
                self._send_trade_completion_notification(trade)
                
                logger.info(f"Trade {trade.id} completed successfully")
                return True
            else:
                trade.status = TradeStatus.FAILED
                session.commit()
                return False
                
        except Exception as e:
            logger.error(f"Error completing trade {trade.id}: {e}")
            trade.status = TradeStatus.FAILED
            session.commit()
            return False
    
    def _execute_buy_trade(self, trade: Trade, session: Session) -> bool:
        """Execute buy trade: transfer crypto from reserve to user and collect fees"""
        try:
            # Get user's crypto account
            user_crypto_account = session.query(Account).filter(
                Account.user_id == trade.user_id,
                Account.currency == trade.crypto_currency,
                Account.account_type == AccountType.CRYPTO
            ).first()
            
            if not user_crypto_account:
                raise ValueError(f"User crypto account not found for {trade.crypto_currency}")
            
            # Get reserve account
            reserve_account = session.query(Account).filter(
                Account.currency == trade.crypto_currency,
                Account.account_type == AccountType.CRYPTO,
                Account.label == "reserve"
            ).first()
            
            if not reserve_account:
                raise ValueError(f"Reserve account not found for {trade.crypto_currency}")
            
            # Get or create fee collection account
            fee_account = session.query(Account).filter(
                Account.currency == trade.fee_currency,
                Account.account_type == AccountType.FIAT,
                Account.label == "fee_collection"
            ).first()
            
            if not fee_account:
                # Create fee collection account if it doesn't exist
                from db.utils import generate_unique_account_number
                fee_account = Account(
                    user_id=1,  # Admin user ID
                    balance=0,
                    locked_amount=0,
                    currency=trade.fee_currency,
                    account_type=AccountType.FIAT,
                    account_number=generate_unique_account_number(session, length=10),
                    label="fee_collection"
                )
                session.add(fee_account)
                session.flush()  # Get the ID
            
            # Create crypto transaction (reserve to user)
            crypto_transaction = Transaction(
                account_id=user_crypto_account.id,
                reference_id=f"BUY_{trade.id}",
                amount=trade.crypto_amount,
                type=TransactionType.BUY_CRYPTO,
                status=TransactionStatus.COMPLETED,
                description=f"Buy {trade.crypto_currency}",
                trade_id=trade.id
            )
            
            # Create fiat transaction (user to reserve)
            fiat_transaction = Transaction(
                account_id=reserve_account.id,
                reference_id=f"BUY_FIAT_{trade.id}",
                amount=trade.fiat_amount - trade.fee_amount,  # Net amount after fee
                type=TransactionType.BUY_CRYPTO,
                status=TransactionStatus.COMPLETED,
                description=f"Payment for {trade.crypto_currency}",
                trade_id=trade.id
            )
            
            # Create fee transaction (to fee collection account)
            fee_transaction = Transaction(
                account_id=fee_account.id,
                reference_id=f"FEE_{trade.id}",
                amount=trade.fee_amount,
                type=TransactionType.BUY_CRYPTO,
                status=TransactionStatus.COMPLETED,
                description=f"Trading fee for {trade.crypto_currency} {trade.trade_type.value}",
                trade_id=trade.id,
                metadata_json={"fee_type": "trading_fee", "trade_id": trade.id}
            )
            
            session.add(crypto_transaction)
            session.add(fiat_transaction)
            session.add(fee_transaction)
            
            # Update balances using unified precision system
            user_crypto_account.balance = float(user_crypto_account.balance or 0) + trade.crypto_amount
            user_crypto_account.crypto_balance_smallest_unit = (
                user_crypto_account.crypto_balance_smallest_unit or 0
            ) + trade.crypto_amount_smallest_unit
            
            reserve_account.balance = float(reserve_account.balance or 0) - trade.crypto_amount
            reserve_account.crypto_balance_smallest_unit = (
                reserve_account.crypto_balance_smallest_unit or 0
            ) - trade.crypto_amount_smallest_unit
            
            # Update fee collection account
            fee_account.balance = (fee_account.balance or 0) + trade.fee_amount
            
            # Link transactions to trade
            trade.crypto_transaction_id = crypto_transaction.id
            trade.fiat_transaction_id = fiat_transaction.id
            
            session.commit()
            logger.info(f"Fee collected: {trade.fee_amount} {trade.fee_currency} for trade {trade.id}")
            return True
            
        except Exception as e:
            logger.error(f"Error executing buy trade: {e}")
            session.rollback()
            return False
    
    def _execute_sell_trade(self, trade: Trade, session: Session) -> bool:
        """Execute sell trade: transfer crypto from user to reserve, fiat to user and collect fees"""
        try:
            # Get user's crypto account
            user_crypto_account = session.query(Account).filter(
                Account.user_id == trade.user_id,
                Account.currency == trade.crypto_currency,
                Account.account_type == AccountType.CRYPTO
            ).first()
            
            if not user_crypto_account:
                raise ValueError(f"User crypto account not found for {trade.crypto_currency}")
            
            # Get reserve accounts
            crypto_reserve = session.query(Account).filter(
                Account.currency == trade.crypto_currency,
                Account.account_type == AccountType.CRYPTO,
                Account.label == "reserve"
            ).first()
            
            fiat_reserve = session.query(Account).filter(
                Account.currency == trade.fiat_currency,
                Account.account_type == AccountType.FIAT,
                Account.label == "reserve"
            ).first()
            
            if not crypto_reserve or not fiat_reserve:
                raise ValueError("Reserve accounts not found")
            
            # Get or create fee collection account
            fee_account = session.query(Account).filter(
                Account.currency == trade.fee_currency,
                Account.account_type == AccountType.FIAT,
                Account.label == "fee_collection"
            ).first()
            
            if not fee_account:
                # Create fee collection account if it doesn't exist
                from db.utils import generate_unique_account_number
                fee_account = Account(
                    user_id=1,  # Admin user ID
                    balance=0,
                    locked_amount=0,
                    currency=trade.fee_currency,
                    account_type=AccountType.FIAT,
                    account_number=generate_unique_account_number(session, length=10),
                    label="fee_collection"
                )
                session.add(fee_account)
                session.flush()  # Get the ID
            
            # Create crypto transaction (user to reserve)
            crypto_transaction = Transaction(
                account_id=crypto_reserve.id,
                reference_id=f"SELL_{trade.id}",
                amount=trade.crypto_amount,
                type=TransactionType.SELL_CRYPTO,
                status=TransactionStatus.COMPLETED,
                description=f"Sell {trade.crypto_currency}",
                trade_id=trade.id
            )
            
            # Get user's fiat account for the payout
            user_fiat_account = session.query(Account).filter(
                Account.user_id == trade.user_id,
                Account.currency == trade.fiat_currency,
                Account.account_type == AccountType.FIAT
            ).first()
            
            if not user_fiat_account:
                # Auto-create fiat account if it doesn't exist
                from service import generate_random_digits
                account_number = f"{generate_random_digits(10)}"
                user_fiat_account = Account(
                    user_id=trade.user_id,
                    currency=trade.fiat_currency,
                    account_type=AccountType.FIAT,
                    balance=0.0,
                    locked_amount=0.0,
                    account_number=account_number,
                    label=f"{trade.fiat_currency} Account"
                )
                session.add(user_fiat_account)
                session.flush()
            
            # Create fiat transaction (reserve to user - net amount after fee)
            fiat_transaction = Transaction(
                account_id=user_fiat_account.id,  # Correct: fiat goes to user's fiat account
                reference_id=f"SELL_FIAT_{trade.id}",
                amount=trade.fiat_amount - trade.fee_amount,  # Net amount after fee
                amount_smallest_unit=trade.fiat_amount_smallest_unit - trade.fee_amount_smallest_unit,
                type=TransactionType.SELL_CRYPTO,
                status=TransactionStatus.COMPLETED,
                description=f"Payment for {trade.crypto_currency}",
                trade_id=trade.id
            )
            
            # Create fee transaction (to fee collection account)
            fee_transaction = Transaction(
                account_id=fee_account.id,
                reference_id=f"FEE_{trade.id}",
                amount=trade.fee_amount,
                type=TransactionType.SELL_CRYPTO,
                status=TransactionStatus.COMPLETED,
                description=f"Trading fee for {trade.crypto_currency} {trade.trade_type.value}",
                trade_id=trade.id,
                metadata_json={"fee_type": "trading_fee", "trade_id": trade.id}
            )
            
            session.add(crypto_transaction)
            session.add(fiat_transaction)
            session.add(fee_transaction)
            
            # Update balances using unified precision system
            # Debit user's crypto
            user_crypto_account.balance = float(user_crypto_account.balance or 0) - trade.crypto_amount
            user_crypto_account.crypto_balance_smallest_unit = (
                user_crypto_account.crypto_balance_smallest_unit or 0
            ) - trade.crypto_amount_smallest_unit
            
            # Credit crypto reserve
            crypto_reserve.balance = float(crypto_reserve.balance or 0) + trade.crypto_amount
            crypto_reserve.crypto_balance_smallest_unit = (
                crypto_reserve.crypto_balance_smallest_unit or 0
            ) + trade.crypto_amount_smallest_unit
            
            # Update fiat balances (net amount after fee)
            net_fiat_amount = trade.fiat_amount - trade.fee_amount
            net_fiat_smallest = trade.fiat_amount_smallest_unit - trade.fee_amount_smallest_unit
            
            # Debit fiat reserve
            fiat_reserve.balance = (fiat_reserve.balance or 0) - trade.fiat_amount
            
            # Credit user's fiat account (net amount)
            user_fiat_account.balance = (user_fiat_account.balance or 0) + net_fiat_amount
            
            # Update fee collection account
            fee_account.balance = (fee_account.balance or 0) + trade.fee_amount
            
            # Link transactions to trade
            trade.crypto_transaction_id = crypto_transaction.id
            trade.fiat_transaction_id = fiat_transaction.id
            
            session.commit()
            logger.info(f"Fee collected: {trade.fee_amount} {trade.fee_currency} for trade {trade.id}")
            return True
            
        except Exception as e:
            logger.error(f"Error executing sell trade: {e}")
            session.rollback()
            return False
    
    def _send_trade_to_kafka(self, trade: Trade):
        """Send trade to Kafka for processing"""
        try:
            message = {
                "trade_id": trade.id,
                "user_id": trade.user_id,
                "trade_type": trade.trade_type,  # Already a string value
                "payment_method": trade.payment_method,  # Already a string value
                "amount": float(trade.fiat_amount),
                "currency": trade.fiat_currency
            }
            
            self.kafka_producer.send("trades", message)
            
        except Exception as e:
            logger.error(f"Error sending trade to Kafka: {e}")
    
    def _send_trade_completion_notification(self, trade: Trade):
        """Send trade completion notification"""
        try:
            message = {
                "trade_id": trade.id,
                "user_id": trade.user_id,
                "trade_type": trade.trade_type,  # Already a string value
                "crypto_amount": float(trade.crypto_amount),
                "crypto_currency": trade.crypto_currency,
                "fiat_amount": float(trade.fiat_amount),
                "fiat_currency": trade.fiat_currency,
                "status": "completed"
            }
            
            self.kafka_producer.send("trade-notifications", message)
            
        except Exception as e:
            logger.error(f"Error sending trade notification: {e}")
    
    def get_user_trades(self, user_id: int, session: Session, limit: int = 50) -> List[Trade]:
        """Get user's trade history"""
        return session.query(Trade).filter(
            Trade.user_id == user_id
        ).order_by(Trade.created_at.desc()).limit(limit).all()
    
    def get_trade_by_id(self, trade_id: int, user_id: int, session: Session) -> Optional[Trade]:
        """Get specific trade by ID"""
        return session.query(Trade).filter(
            Trade.id == trade_id,
            Trade.user_id == user_id
        ).first()
    
    def cancel_trade(self, trade: Trade, session: Session) -> bool:
        """Cancel a pending trade"""
        try:
            if trade.status not in [TradeStatus.PENDING, TradeStatus.PAYMENT_PENDING]:
                raise ValueError("Cannot cancel trade in current status")
            
            trade.status = TradeStatus.CANCELLED
            trade.cancelled_at = datetime.datetime.utcnow()
            session.commit()
            
            logger.info(f"Trade {trade.id} cancelled")
            return True
            
        except Exception as e:
            logger.error(f"Error cancelling trade: {e}")
            return False
