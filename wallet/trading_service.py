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
    Account, Transaction, Trade, TradeStatus, TradeType, PaymentMethod, TransactionType, CryptoAddress, AccountType, Reservation, ReservationType, PaymentProvider, TransactionStatus, 
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
            from reserve_service import ReserveService
            self.reserve_service = ReserveService(session)
    
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
        from decimal import Decimal
        crypto_amount_smallest = AmountConverter.to_smallest_units(Decimal(str(crypto_amount)), crypto_currency)
        fiat_amount_smallest = AmountConverter.to_smallest_units(Decimal(str(fiat_amount)), fiat_currency)
        fee_amount_smallest = AmountConverter.to_smallest_units(Decimal(str(fee_amount)), fiat_currency)
            
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
    
    def get_quote_for_crypto_amount(
        self,
        crypto_currency: str,
        fiat_currency: str,
        crypto_amount: float,
        payment_method: PaymentMethod
    ) -> Dict:
        """Get quote for buying specified crypto amount - returns total fiat cost including fees"""
        
        # Get current price
        price = self.get_crypto_price(crypto_currency, fiat_currency)
        
        # Calculate fees based on payment method
        fee_percentage = self._get_fee_percentage(payment_method)
        
        # Calculate costs
        gross_fiat = crypto_amount * price  # Base cost without fees
        fee_amount = gross_fiat * fee_percentage  # Fee amount
        total_fiat_cost = gross_fiat + fee_amount  # Total user pays
        
        # Convert to smallest units for precision
        crypto_amount_smallest = AmountConverter.to_smallest_units(crypto_amount, crypto_currency)
        gross_fiat_smallest = AmountConverter.to_smallest_units(gross_fiat, fiat_currency)
        fee_amount_smallest = AmountConverter.to_smallest_units(fee_amount, fiat_currency)
        total_fiat_smallest = AmountConverter.to_smallest_units(total_fiat_cost, fiat_currency)
        
        return {
            "crypto_currency": crypto_currency.upper(),
            "crypto_amount": crypto_amount,
            "crypto_amount_smallest_unit": crypto_amount_smallest,
            "fiat_currency": fiat_currency.upper(),
            "gross_fiat_cost": gross_fiat,
            "gross_fiat_cost_smallest_unit": gross_fiat_smallest,
            "fee_amount": fee_amount,
            "fee_amount_smallest_unit": fee_amount_smallest,
            "total_fiat_cost": total_fiat_cost,
            "total_fiat_cost_smallest_unit": total_fiat_smallest,
            "exchange_rate": price,
            "fee_percentage": fee_percentage,
            "payment_method": payment_method.value
        }
    
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
        
        # Check reserve sufficiency before creating trade
        if hasattr(self, 'reserve_service') and trade_type == TradeType.BUY:
            from db.wallet import AccountType
            # For buy trades, check if we have enough crypto in reserves
            amounts = self.calculate_trade_amounts(
                crypto_currency, fiat_currency, amount, trade_type, payment_method
            )
            crypto_amount_needed = amounts["crypto_amount"]
            
            reserve_check = self.reserve_service.check_reserve_sufficiency(
                crypto_currency, crypto_amount_needed, AccountType.CRYPTO, "trading"
            )
            
            if not reserve_check["is_sufficient"]:
                raise ValueError(f"Insufficient liquidity reserves for {crypto_currency}. Available: {reserve_check['available_amount']}, Required: {reserve_check['required_amount']}")
        
        # Get or create user account for the crypto currency
        account = session.query(Account).filter(
            Account.user_id == user_id,
            Account.currency == crypto_currency
        ).first()
        
        if not account:
            # Fail if user doesn't have required crypto account
            error_msg = f"User {user_id} does not have a {crypto_currency} account. Account must be created before trading."
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Calculate amounts (reuse if already calculated above)
        if 'amounts' not in locals():
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
            # Also store in payment_metadata for compatibility
            if not trade.payment_metadata:
                trade.payment_metadata = {}
            trade.payment_metadata.update({
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
            # Get phone number from payment metadata
            phone_number = None
            if trade.payment_metadata and 'phone_number' in trade.payment_metadata:
                phone_number = trade.payment_metadata['phone_number']
            
            if not phone_number:
                raise ValueError("Phone number required for mobile money payment")
            
            # Use existing Relworx request_payment method (same as deposit)
            reference_id = f"TRADE_{trade.id}"
            description = f"Buy {trade.crypto_currency} - DT Exchange"
            
            response = self.relworx_client.request_payment(
                reference=reference_id,
                msisdn=phone_number,
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
            current_balance = account.crypto_balance_smallest_unit or 0
            account.crypto_balance_smallest_unit = current_balance + trade.crypto_amount_smallest_unit
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
            
            # Send WebSocket notification for trade completion
            logger.info(f"🔔 About to send trade completion notification for trade {trade.id}")
            self._send_trade_completion_notification(trade)
            
            logger.info(f"✅ Completed buy trade {trade.id}: {AmountConverter.format_display_amount(trade.crypto_amount_smallest_unit, trade.crypto_currency)}")
            return True
            
        except Exception as e:
            logger.error(f"Error completing buy trade {trade.id}: {e}")
            raise
    
    def _complete_sell_trade(self, trade: Trade, session: Session) -> bool:
        """Complete sell trade - user sells crypto, receives fiat via mobile money"""
        reservation_ref = None
        try:
            # Get user's crypto account
            account = session.query(Account).filter_by(id=trade.account_id).first()
            if not account:
                raise ValueError(f"Account {trade.account_id} not found")
            
            # Get available balance in smallest units for unified precision
            available_balance = account.crypto_balance_smallest_unit or 0

            logger.info(f"Available balance: {available_balance}")
            logger.info(f"Trade crypto amount: {trade.crypto_amount_smallest_unit}")
            
            if available_balance < trade.crypto_amount_smallest_unit:
                raise ValueError(f"Insufficient crypto balance: ACCOUNT ID: {trade.account_id}  {available_balance} < {trade.crypto_amount_smallest_unit}")
            
            # Step 1: Create reservation to lock funds (don't debit balance yet)
            reservation_ref = self._create_sell_trade_reservation(trade, account, session)
            
            # Update trade status to processing
            trade.status = TradeStatus.PROCESSING
            session.commit()  # Commit reservation first
            
            # Step 2: Initiate mobile money payout via Relworx
            if trade.payment_method == PaymentMethod.MOBILE_MONEY:
                payout_success = self._initiate_mobile_money_payout(trade, session)
                if not payout_success:
                    # Cancel reservation and fail trade
                    self._cancel_sell_trade_reservation(reservation_ref, account, session)
                    trade.status = TradeStatus.FAILED
                    session.commit()
                    logger.error(f"❌ Mobile money payout failed for trade {trade.id}, reservation cancelled")
                    return False
            
            # Step 3: Keep trade in PROCESSING - finalization happens via webhook
            # Don't finalize here - wait for webhook confirmation
            
            session.commit()
            
            logger.info(f"✅ Completed sell trade {trade.id}: {AmountConverter.format_display_amount(trade.crypto_amount_smallest_unit, trade.crypto_currency)}")
            return True
            
        except Exception as e:
            logger.error(f"Error completing sell trade {trade.id}: {e}")
            # If we have a reservation, cancel it on error
            if reservation_ref:
                try:
                    self._cancel_sell_trade_reservation(reservation_ref, account, session)
                except Exception as cancel_error:
                    logger.error(f"Failed to cancel reservation {reservation_ref}: {cancel_error}")
            raise
    
    def _create_sell_trade_reservation(self, trade: Trade, account: Account, session: Session) -> str:
        """Create a reservation to lock funds for sell trade"""
        import time
        reservation_ref = f"sell_trade_{trade.id}_{int(time.time() * 1000)}"
        
        # Lock the amount in the account
        current_locked = account.crypto_locked_amount_smallest_unit or 0
        account.crypto_locked_amount_smallest_unit = current_locked + trade.crypto_amount_smallest_unit
        
        # Create reservation record
        reservation = Reservation(
            user_id=account.user_id,
            reference=reservation_ref,
            amount=float(trade.crypto_amount),
            type=ReservationType.RESERVE,
            status="active"
        )
        
        session.add(reservation)
        logger.info(f"🔒 Created sell trade reservation: {reservation_ref} for {AmountConverter.format_display_amount(trade.crypto_amount_smallest_unit, trade.crypto_currency)}")
        
        return reservation_ref
    
    def _cancel_sell_trade_reservation(self, reservation_ref: str, account: Account, session: Session):
        """Cancel a sell trade reservation and unlock funds"""
        if not reservation_ref:
            return
            
        # Find and update the reservation
        reservation = session.query(Reservation).filter_by(
            reference=reservation_ref,
            type=ReservationType.RESERVE,
            status="active"
        ).first()
        
        if reservation:
            # Unlock the funds
            current_locked = account.crypto_locked_amount_smallest_unit or 0
            amount_to_unlock = int(reservation.amount * (10 ** 8))  # Convert back to smallest units
            new_locked = current_locked - amount_to_unlock
            if new_locked < 0:
                new_locked = 0
            account.crypto_locked_amount_smallest_unit = new_locked
            
            # Mark reservation as cancelled
            reservation.status = "cancelled"
            
            logger.info(f"🔓 Cancelled sell trade reservation: {reservation_ref}")
        else:
            logger.warning(f"Reservation {reservation_ref} not found for cancellation")
    
    def _finalize_sell_trade(self, trade: Trade, account: Account, reservation_ref: str, session: Session):
        """Finalize sell trade - debit balance, credit reserve, complete reservation"""
        logger.info(f"🔄 Finalizing sell trade {trade.id}: debiting {AmountConverter.format_display_amount(trade.crypto_amount_smallest_unit, trade.crypto_currency)}")
        
        # Debit user's crypto balance
        total_balance = account.crypto_balance_smallest_unit or 0
        locked_amount = account.crypto_locked_amount_smallest_unit or 0
        available_balance = total_balance - locked_amount
        new_total_balance = total_balance - trade.crypto_amount_smallest_unit
        logger.info(f"💰 Total balance: {total_balance}, Locked: {locked_amount}, Available: {available_balance}")
        logger.info(f"💰 New total balance: {total_balance} -> {new_total_balance} (debiting {trade.crypto_amount_smallest_unit})")
        account.crypto_balance_smallest_unit = new_total_balance
        account.balance = float(account.balance) - float(trade.crypto_amount)  # Backward compatibility
        
        # Unlock the reserved funds
        current_locked = account.crypto_locked_amount_smallest_unit or 0
        new_locked = current_locked - trade.crypto_amount_smallest_unit
        logger.info(f"🔓 Locked amount: {current_locked} -> {new_locked} (unlocking {trade.crypto_amount_smallest_unit})")
        account.crypto_locked_amount_smallest_unit = new_locked
        
        # Credit crypto to reserve account
        self._adjust_reserve_balance(trade.crypto_currency, trade.crypto_amount_smallest_unit, session)
        
        # Complete the reservation
        if reservation_ref:
            reservation = session.query(Reservation).filter_by(
                reference=reservation_ref,
                type=ReservationType.RESERVE,
                status="active"
            ).first()
            
            if reservation:
                reservation.status = "completed"
                logger.info(f"✅ Completed sell trade reservation: {reservation_ref}")
        
        # Create accounting entries
        if self.session and hasattr(self, 'accounting_service'):
            self._create_sell_trade_accounting_entry(trade, account)
        
        # Update trade status
        trade.status = TradeStatus.COMPLETED
        trade.completed_at = datetime.datetime.utcnow()
        
        # Send WebSocket notification for trade completion
        logger.info(f"🔔 About to send trade completion notification for trade {trade.id}")
        self._send_trade_completion_notification(trade)
    
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
            # Don't fail the trade for accounting errors
            pass
    
    def _send_trade_completion_notification(self, trade: Trade):
        """Send trade completion notification via Redis pub/sub"""
        try:
            import redis
            import json
            import os
            
            # Get Redis connection details
            redis_host = os.environ.get('REDIS_HOST', 'redis')
            redis_port = int(os.environ.get('REDIS_PORT', 6379))
            redis_password = os.environ.get('REDIS_PASSWORD', None)
            redis_db = int(os.environ.get('REDIS_DB', 0))

            redis_kwargs = {
                "host": redis_host,
                "port": redis_port,
                "db": redis_db,
                "socket_connect_timeout": 5,
                "socket_timeout": 5,
                "retry_on_timeout": True
            }
            if redis_password:
                redis_kwargs["password"] = redis_password

            r = redis.Redis(**redis_kwargs)
            
            # Prepare notification data
            notification_data = {
                'type': 'trade_status_update',
                'trade_id': trade.id,
                'data': {
                    'status': 'completed',
                    'message': f'Trade #{trade.id} completed successfully',
                    'trade_type': trade.trade_type.value if hasattr(trade.trade_type, 'value') else str(trade.trade_type),
                    'crypto_currency': trade.crypto_currency,
                    'crypto_amount': float(trade.crypto_amount),
                    'fiat_amount': float(trade.fiat_amount),
                    'completed_at': trade.completed_at.isoformat() if trade.completed_at else None
                },
                'timestamp': trade.completed_at.isoformat() if trade.completed_at else None
            }
            
            logger.info(f"🔔 PUBLISHING trade completion to Redis channel 'trade_updates' for trade {trade.id}")
            logger.info(f"🔔 Notification data: {notification_data}")
            
            # Publish to Redis channel
            message = json.dumps(notification_data)
            result = r.publish('trade_updates', message)
            
            logger.info(f"✅ PUBLISHED trade completion notification for trade {trade.id} to {result} subscribers")
                
        except Exception as e:
            logger.error(f"💥 ERROR publishing trade completion notification for trade {trade.id}: {e}")
            # Don't fail the trade for notification errors
    
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
                current_balance = int(reserve_account.crypto_balance_smallest_unit or 0)
                amount_int = int(amount_smallest_unit)
                new_balance = current_balance + amount_int
                
                if new_balance < 0:
                    logger.warning(f"Reserve balance for {currency} would go negative: {new_balance}")
                
                reserve_account.crypto_balance_smallest_unit = new_balance
                reserve_account.balance = float(reserve_account.balance or 0) + (float(amount_smallest_unit) / (10 ** 8))  # Assuming 8 decimal places
                
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
            # Get phone number from payment metadata
            phone_number = None
            if trade.payment_metadata and 'phone_number' in trade.payment_metadata:
                phone_number = trade.payment_metadata['phone_number']
            
            if not phone_number:
                raise ValueError("Phone number required for mobile money payout")
            
            reference_id = f"PAYOUT_{trade.id}"
            description = f"Sell {trade.crypto_currency} payout - DT Exchange"
            
            # Use Relworx to send money to user
            response = self.relworx_client.send_payment(
                reference=reference_id,
                msisdn=phone_number,
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
            
            # Get or create reserve account
            from reserve_service import ReserveService
            reserve_service = ReserveService(session)
            reserve_account = reserve_service.get_reserve_account(trade.crypto_currency, AccountType.CRYPTO)
            
            if not reserve_account:
                raise ValueError(f"Failed to create reserve account for {trade.crypto_currency}")
            
            # Get or create fee collection account
            fee_account = session.query(Account).filter(
                Account.currency == trade.fee_currency,
                Account.account_type == AccountType.FIAT,
                Account.label == "fee_collection"
            ).first()
            
            if not fee_account:
                # Create fee collection account if it doesn't exist
                from db.utils import generate_unique_account_number
                import os
                system_user_id = int(os.getenv("WALLET_SYSTEM_USER_ID", "1"))
                fee_account = Account(
                    user_id=system_user_id,
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
            # Format amounts for better display
            crypto_display = AmountConverter.format_display_amount(trade.crypto_amount_smallest_unit, trade.crypto_currency)
            fiat_display = AmountConverter.format_display_amount(trade.fiat_amount_smallest_unit, trade.fiat_currency)
            
            crypto_transaction = Transaction(
                account_id=user_crypto_account.id,
                reference_id=f"BUY_{trade.id}",
                amount=trade.crypto_amount,
                amount_smallest_unit=trade.crypto_amount_smallest_unit,
                type=TransactionType.BUY_CRYPTO,
                status=TransactionStatus.COMPLETED,
                description=f"Bought {crypto_display} for {fiat_display}",
                trade_id=trade.id
            )
            
            # Create fiat transaction (user to reserve)
            fiat_transaction = Transaction(
                account_id=reserve_account.id,
                reference_id=f"BUY_FIAT_{trade.id}",
                amount=trade.fiat_amount - trade.fee_amount,  # Net amount after fee
                amount_smallest_unit=trade.fiat_amount_smallest_unit - trade.fee_amount_smallest_unit,
                type=TransactionType.BUY_CRYPTO,
                status=TransactionStatus.COMPLETED,
                description=f"Payment for {crypto_display}",
                trade_id=trade.id
            )
            
            # Create fee transaction (to fee collection account)
            fee_transaction = Transaction(
                account_id=fee_account.id,
                reference_id=f"FEE_{trade.id}",
                amount=trade.fee_amount,
                amount_smallest_unit=trade.fee_amount_smallest_unit,
                type=TransactionType.BUY_CRYPTO,
                status=TransactionStatus.COMPLETED,
                description=f"Trading fee for {crypto_display}",
                trade_id=trade.id,
                metadata_json={"fee_type": "trading_fee", "trade_id": trade.id}
            )
            
            session.add(crypto_transaction)
            session.add(fiat_transaction)
            session.add(fee_transaction)
            
            # Update balances using unified precision system
            user_crypto_account.balance = float(user_crypto_account.balance or 0) + float(trade.crypto_amount)
            user_crypto_account.crypto_balance_smallest_unit = (
                user_crypto_account.crypto_balance_smallest_unit or 0
            ) + trade.crypto_amount_smallest_unit
            
            reserve_account.balance = float(reserve_account.balance or 0) - float(trade.crypto_amount)
            reserve_account.crypto_balance_smallest_unit = (
                reserve_account.crypto_balance_smallest_unit or 0
            ) - trade.crypto_amount_smallest_unit
            
            # Update fee collection account
            fee_account.balance = float(fee_account.balance or 0) + float(trade.fee_amount)
            
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
                import os
                system_user_id = int(os.getenv("WALLET_SYSTEM_USER_ID", "1"))
                fee_account = Account(
                    user_id=system_user_id,
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
            user_crypto_account.balance = float(user_crypto_account.balance or 0) - float(trade.crypto_amount)
            user_crypto_account.crypto_balance_smallest_unit = (
                user_crypto_account.crypto_balance_smallest_unit or 0
            ) - trade.crypto_amount_smallest_unit
            
            # Credit crypto reserve
            crypto_reserve.balance = float(crypto_reserve.balance or 0) + float(trade.crypto_amount)
            crypto_reserve.crypto_balance_smallest_unit = (
                crypto_reserve.crypto_balance_smallest_unit or 0
            ) + trade.crypto_amount_smallest_unit
            
            # Update fiat balances (net amount after fee)
            net_fiat_amount = float(trade.fiat_amount) - float(trade.fee_amount)
            net_fiat_smallest = trade.fiat_amount_smallest_unit - trade.fee_amount_smallest_unit
            
            # Debit fiat reserve
            fiat_reserve.balance = float(fiat_reserve.balance or 0) - float(trade.fiat_amount)
            
            # Credit user's fiat account (net amount)
            user_fiat_account.balance = float(user_fiat_account.balance or 0) + net_fiat_amount
            
            # Update fee collection account
            fee_account.balance = float(fee_account.balance or 0) + float(trade.fee_amount)
            
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
                "trade_type": trade.trade_type.value,  # Convert enum to string
                "payment_method": trade.payment_method.value,  # Convert enum to string
                "amount": float(trade.fiat_amount),
                "currency": trade.fiat_currency
            }
            
            self.kafka_producer.send("trades", message)
            
        except Exception as e:
            logger.error(f"Error sending trade to Kafka: {e}")
    
    def _send_trade_completion_notification_kafka(self, trade: Trade):
        """Send trade completion notification via Kafka (legacy)"""
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
