import logging
import os
import random
import string
from typing import Dict, Optional, List, Tuple
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_DOWN
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from db.wallet import Account, Transaction, TransactionType, TransactionStatus, AccountType
import time
import json
from shared.crypto.price_cache_service import get_price_cache_service
from shared.fiat.fiat_fx_service import get_fiat_fx_service

logger = logging.getLogger(__name__)

class ReserveService:
    """
    Service for managing system reserves for swaps and trading operations
    Maintains liquidity pools for immediate execution
    """
    
    def __init__(self, session: Session):
        self.session = session
        # System user to own reserve accounts; must exist in users table
        self.system_user_id = int(os.getenv("WALLET_SYSTEM_USER_ID", "1"))
        self.reserve_accounts = {}  # Cache for reserve account lookups
        self.reserve_cache = {}
        self.cache_ttl = 30  # 30 seconds cache
        
    def get_reserve_account(self, currency: str, account_type: AccountType) -> Optional[Account]:
        """Get or create reserve account for a specific currency and type"""
        cache_key = f"{currency}_{account_type.value}"
        
        if cache_key in self.reserve_accounts:
            return self.reserve_accounts[cache_key]
        
        # Look for existing reserve account
        account = self.session.query(Account).filter(
            and_(
                Account.currency == currency.upper(),
                Account.account_type == account_type,
                Account.label == f"RESERVE_{currency}_{account_type.value}"
            )
        ).first()
        
        if not account:
            # Determine precision for crypto accounts
            precision_cfg = None
            if account_type == AccountType.CRYPTO:
                curr = currency.upper()
                decimals_by_currency = {
                    "BTC": 8,
                    "ETH": 18,
                    "USDC": 6,
                    "USDT": 6,
                    "SOL": 9,
                    "TRX": 6,
                }
                if curr in decimals_by_currency:
                    precision_cfg = {"decimals": decimals_by_currency[curr]}
            # Create new reserve account
            account = Account(
                currency=currency.upper(),
                account_type=account_type,
                user_id=self.system_user_id,  # System user ID
                account_number=self._generate_reserve_account_number(currency, account_type),
                label=f"RESERVE_{currency}_{account_type.value}",
                balance=0.0 if account_type == AccountType.FIAT else 0.0,
                crypto_balance_smallest_unit=0 if account_type == AccountType.CRYPTO else None,
                crypto_locked_amount_smallest_unit=0 if account_type == AccountType.CRYPTO else None,
                precision_config=precision_cfg
            )
            
            self.session.add(account)
            self.session.flush()
            logger.info(f"Created reserve account for {currency} {account_type.value}")
        
        self.reserve_accounts[cache_key] = account
        return account
    
    def get_reserve_balance(self, currency: str, account_type: AccountType) -> Dict:
        """Get current reserve balance and status"""
        cache_key = f"balance_{currency}_{account_type.value}"
        
        # Check cache first
        if cache_key in self.reserve_cache:
            cache_time, data = self.reserve_cache[cache_key]
            if time.time() - cache_time < self.cache_ttl:
                return data
        
        account = self.get_reserve_account(currency, account_type)
        
        if account_type == AccountType.CRYPTO:
            available_balance = account.available_balance()
            total_balance = float(account._convert_smallest_to_standard(account.crypto_balance_smallest_unit or 0))
            locked_balance = float(account._convert_smallest_to_standard(account.crypto_locked_amount_smallest_unit or 0))
        else:
            available_balance = account.available_balance()
            total_balance = float(account.balance)
            locked_balance = float(account.locked_amount)
        
        # Calculate utilization percentage
        utilization = (locked_balance / total_balance * 100) if total_balance > 0 else 0
        
        # Determine reserve status
        if utilization >= 90:
            status = "critical"
        elif utilization >= 75:
            status = "warning"
        elif utilization >= 50:
            status = "moderate"
        else:
            status = "healthy"
        
        reserve_data = {
            "currency": currency,
            "account_type": account_type.value,
            "total_balance": total_balance,
            "available_balance": available_balance,
            "locked_balance": locked_balance,
            "utilization_percentage": round(utilization, 2),
            "status": status,
            "account_id": account.id,
            "account_number": account.account_number,
            "last_updated": time.time()
        }
        
        # Cache the result
        self.reserve_cache[cache_key] = (time.time(), reserve_data)
        return reserve_data
    
    def get_all_reserves(self) -> Dict:
        """Get status of all system reserves"""
        # Define supported currencies and types
        crypto_currencies = ["BTC", "ETH", "USDC", "USDT", "SOL", "TRX"]
        fiat_currencies = ["UGX", "KES", "TZS", "USD"]
        
        reserves = {
            "crypto": {},
            "fiat": {},
            "summary": {
                "total_crypto_value_usd": 0.0,
                "total_fiat_value_usd": 0.0,
                "overall_status": "healthy",
                "critical_reserves": [],
                "warning_reserves": []
            }
        }
        
        # Get crypto reserves
        for currency in crypto_currencies:
            reserve_data = self.get_reserve_balance(currency, AccountType.CRYPTO)
            reserves["crypto"][currency] = reserve_data
            
            # Add to summary
            if reserve_data["status"] == "critical":
                reserves["summary"]["critical_reserves"].append(f"{currency} (Crypto)")
            elif reserve_data["status"] == "warning":
                reserves["summary"]["warning_reserves"].append(f"{currency} (Crypto)")
        
        # Get fiat reserves
        for currency in fiat_currencies:
            reserve_data = self.get_reserve_balance(currency, AccountType.FIAT)
            reserves["fiat"][currency] = reserve_data
            
            # Add to summary
            if reserve_data["status"] == "critical":
                reserves["summary"]["critical_reserves"].append(f"{currency} (Fiat)")
            elif reserve_data["status"] == "warning":
                reserves["summary"]["warning_reserves"].append(f"{currency} (Fiat)")
        
        # Determine overall status
        if reserves["summary"]["critical_reserves"]:
            reserves["summary"]["overall_status"] = "critical"
        elif reserves["summary"]["warning_reserves"]:
            reserves["summary"]["overall_status"] = "warning"
        
        return reserves
    
    def check_reserve_sufficiency(
        self, 
        currency: str, 
        amount: float, 
        account_type: AccountType,
        operation_type: str = "swap"
    ) -> Dict:
        """
        Check if reserve has sufficient balance for an operation
        Returns detailed analysis of reserve capacity
        """
        reserve_data = self.get_reserve_balance(currency, account_type)
        
        # Calculate required amount based on operation type
        if operation_type == "swap":
            # For swaps, we need the full amount available
            required_amount = amount
            buffer_multiplier = 1.0
        elif operation_type == "trading":
            # For trading, we need amount + buffer for market volatility
            required_amount = amount
            buffer_multiplier = 1.1  # 10% buffer
        else:
            required_amount = amount
            buffer_multiplier = 1.0
        
        total_required = required_amount * buffer_multiplier
        
        # Check sufficiency
        is_sufficient = reserve_data["available_balance"] >= total_required
        remaining_after_operation = reserve_data["available_balance"] - total_required
        
        # Calculate new utilization
        new_total_balance = reserve_data["total_balance"]
        new_locked_balance = reserve_data["locked_balance"] + total_required
        new_utilization = (new_locked_balance / new_total_balance * 100) if new_total_balance > 0 else 0
        
        # Determine new status
        if new_utilization >= 90:
            new_status = "critical"
        elif new_utilization >= 75:
            new_status = "warning"
        elif new_utilization >= 50:
            new_status = "moderate"
        else:
            new_status = "healthy"
        
        return {
            "is_sufficient": is_sufficient,
            "required_amount": total_required,
            "available_amount": reserve_data["available_balance"],
            "remaining_after_operation": remaining_after_operation,
            "current_utilization": reserve_data["utilization_percentage"],
            "new_utilization": round(new_utilization, 2),
            "current_status": reserve_data["status"],
            "new_status": new_status,
            "buffer_multiplier": buffer_multiplier,
            "operation_type": operation_type,
            "reserve_data": reserve_data
        }
    
    def reserve_amount(
        self, 
        currency: str, 
        amount: float, 
        account_type: AccountType,
        reference_id: str,
        operation_type: str = "swap"
    ) -> Dict:
        """
        Reserve an amount from the system reserve
        This locks the amount for immediate use
        """
        try:
            # Check sufficiency first
            sufficiency_check = self.check_reserve_sufficiency(currency, amount, account_type, operation_type)
            
            if not sufficiency_check["is_sufficient"]:
                return {
                    "success": False,
                    "error": f"Insufficient reserve balance. Required: {sufficiency_check['required_amount']}, Available: {sufficiency_check['available_amount']}",
                    "sufficiency_check": sufficiency_check
                }
            
            account = self.get_reserve_account(currency, account_type)
            
            # Lock the amount
            if account_type == AccountType.CRYPTO:
                amount_smallest = self._convert_to_smallest_unit(amount, currency)
                account.crypto_locked_amount_smallest_unit += amount_smallest
            else:
                from decimal import Decimal
                amt_dec = Decimal(str(amount))
                current = account.locked_amount if account.locked_amount is not None else Decimal("0")
                account.locked_amount = current + amt_dec
            
            # Create reservation transaction
            transaction = Transaction(
                account_id=account.id,
                reference_id=reference_id,
                amount=amount,
                type=TransactionType.DEPOSIT,  # Using DEPOSIT for reserve operations
                status=TransactionStatus.PENDING,
                description=f"Reserve {operation_type} operation: {amount} {currency}",
                metadata_json={
                    "operation_type": "reserve_lock",
                    "original_operation": operation_type,
                    "currency": currency,
                    "account_type": account_type.value,
                    "lock_timestamp": time.time()
                }
            )
            
            self.session.add(transaction)
            self.session.commit()
            
            # Update cache
            cache_key = f"balance_{currency}_{account_type.value}"
            if cache_key in self.reserve_cache:
                del self.reserve_cache[cache_key]
            
            logger.info(f"Reserved {amount} {currency} for {operation_type} operation")
            
            return {
                "success": True,
                "reserved_amount": amount,
                "reference_id": reference_id,
                "transaction_id": transaction.id,
                "new_utilization": sufficiency_check["new_utilization"],
                "new_status": sufficiency_check["new_status"]
            }
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error reserving amount: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def release_reserve(
        self, 
        currency: str, 
        amount: float, 
        account_type: AccountType,
        reference_id: str
    ) -> Dict:
        """
        Release a previously reserved amount back to available balance
        """
        try:
            account = self.get_reserve_account(currency, account_type)
            
            # Release the lock
            if account_type == AccountType.CRYPTO:
                amount_smallest = self._convert_to_smallest_unit(amount, currency)
                account.crypto_locked_amount_smallest_unit -= amount_smallest
                if account.crypto_locked_amount_smallest_unit < 0:
                    account.crypto_locked_amount_smallest_unit = 0
            else:
                from decimal import Decimal
                amt_dec = Decimal(str(amount))
                current = account.locked_amount if account.locked_amount is not None else Decimal("0")
                new_locked = current - amt_dec
                account.locked_amount = new_locked if new_locked > 0 else Decimal("0")
            
            # Update transaction status
            transaction = self.session.query(Transaction).filter(
                Transaction.reference_id == reference_id
            ).first()
            
            if transaction:
                transaction.status = TransactionStatus.COMPLETED
                transaction.metadata_json = transaction.metadata_json or {}
                transaction.metadata_json["release_timestamp"] = time.time()
            
            self.session.commit()
            
            # Update cache
            cache_key = f"balance_{currency}_{account_type.value}"
            if cache_key in self.reserve_cache:
                del self.reserve_cache[cache_key]
            
            logger.info(f"Released reserve: {amount} {currency}")
            
            return {
                "success": True,
                "released_amount": amount,
                "reference_id": reference_id,
                "message": f"Successfully released {amount} {currency} from reserve"
            }
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error releasing reserve: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def top_up_reserve(
        self, 
        currency: str, 
        amount: float, 
        account_type: AccountType,
        source_reference: str = None
    ) -> Dict:
        """
        Top up a reserve with additional funds
        This increases the total available balance
        """
        try:
            account = self.get_reserve_account(currency, account_type)
            
            # Add to balance
            if account_type == AccountType.CRYPTO:
                amount_smallest = self._convert_to_smallest_unit(amount, currency)
                account.crypto_balance_smallest_unit += amount_smallest
            else:
                from decimal import Decimal
                amt_dec = Decimal(str(amount))
                current = account.balance if account.balance is not None else Decimal("0")
                account.balance = current + amt_dec

            # Determine smallest unit for transaction record (NOT NULL column)
            if account_type == AccountType.CRYPTO:
                tx_amount_smallest = amount_smallest
            else:
                from decimal import Decimal, ROUND_HALF_UP
                tx_amount_smallest = int((Decimal(str(amount)) * Decimal("100")).to_integral_value(rounding=ROUND_HALF_UP))

            # Create top-up transaction
            transaction = Transaction(
                account_id=account.id,
                reference_id=f"topup_{int(time.time())}_{currency}",
                amount=amount,
                amount_smallest_unit=int(tx_amount_smallest),
                type=TransactionType.DEPOSIT,
                status=TransactionStatus.COMPLETED,
                description=f"Reserve top-up: {amount} {currency}",
                metadata_json={
                    "operation_type": "reserve_topup",
                    "currency": currency,
                    "account_type": account_type.value,
                    "source_reference": source_reference,
                    "topup_timestamp": time.time()
                }
            )

            self.session.add(transaction)
            self.session.commit()
            
            # Update cache
            cache_key = f"balance_{currency}_{account_type.value}"
            if cache_key in self.reserve_cache:
                del self.reserve_cache[cache_key]
            
            logger.info(f"Topped up reserve: {amount} {currency}")
            
            return {
                "success": True,
                "topped_up_amount": amount,
                "new_total_balance": account.available_balance() + (float(account.locked_amount) if account_type == AccountType.FIAT else 0.0),
                "transaction_id": transaction.id
            }
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error topping up reserve: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def withdraw_from_reserve(
        self, 
        currency: str, 
        amount: float, 
        account_type: AccountType,
        destination_reference: str = None
    ) -> Dict:
        """
        Withdraw funds from reserve (for maintenance or rebalancing)
        """
        try:
            # Check if we have enough available balance
            reserve_data = self.get_reserve_balance(currency, account_type)
            
            if reserve_data["available_balance"] < amount:
                return {
                    "success": False,
                    "error": f"Insufficient available balance. Requested: {amount}, Available: {reserve_data['available_balance']}"
                }
            
            account = self.get_reserve_account(currency, account_type)
            
            # Deduct from balance
            if account_type == AccountType.CRYPTO:
                amount_smallest = self._convert_to_smallest_unit(amount, currency)
                account.crypto_balance_smallest_unit -= amount_smallest
                if account.crypto_balance_smallest_unit < 0:
                    account.crypto_balance_smallest_unit = 0
            else:
                from decimal import Decimal
                amt_dec = Decimal(str(amount))
                current = account.balance if account.balance is not None else Decimal("0")
                new_bal = current - amt_dec
                account.balance = new_bal if new_bal > 0 else Decimal("0")
            
            # Create withdrawal transaction
            # Determine smallest unit for transaction record (NOT NULL column)
            if account_type == AccountType.CRYPTO:
                tx_amount_smallest = amount_smallest
            else:
                from decimal import Decimal, ROUND_HALF_UP
                tx_amount_smallest = int((Decimal(str(amount)) * Decimal("100")).to_integral_value(rounding=ROUND_HALF_UP))

            transaction = Transaction(
                account_id=account.id,
                reference_id=f"withdraw_{int(time.time())}_{currency}",
                amount=amount,
                amount_smallest_unit=int(tx_amount_smallest),
                type=TransactionType.WITHDRAWAL,
                status=TransactionStatus.COMPLETED,
                description=f"Reserve withdrawal: {amount} {currency}",
                metadata_json={
                    "operation_type": "reserve_withdrawal",
                    "currency": currency,
                    "account_type": account_type.value,
                    "destination_reference": destination_reference,
                    "withdrawal_timestamp": time.time()
                }
            )
            
            self.session.add(transaction)
            self.session.commit()
            
            # Update cache
            cache_key = f"balance_{currency}_{account_type.value}"
            if cache_key in self.reserve_cache:
                del self.reserve_cache[cache_key]
            
            logger.info(f"Withdrew from reserve: {amount} {currency}")
            
            return {
                "success": True,
                "withdrawn_amount": amount,
                "new_total_balance": account.available_balance() + (float(account.locked_amount) if account_type == AccountType.FIAT else 0.0),
                "transaction_id": transaction.id
            }
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error withdrawing from reserve: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_reserve_analytics(self, period_days: int = 30) -> Dict:
        """Get analytics about reserve usage over time"""
        try:
            # Get transactions for reserve accounts
            reserve_accounts = self.session.query(Account).filter(
                Account.label.like("RESERVE_%")
            ).all()
            
            account_ids = [acc.id for acc in reserve_accounts]
            
            # Get transactions in the period
            cutoff_dt = datetime.utcnow() - timedelta(days=period_days)
            
            transactions = self.session.query(Transaction).filter(
                and_(
                    Transaction.account_id.in_(account_ids),
                    Transaction.created_at >= cutoff_dt
            )).all()
            
            # Initialize price services
            price_service = get_price_cache_service()
            fx_service = get_fiat_fx_service()
            price_cache: Dict[str, float] = {}

            # Analyze by currency and operation type
            analytics = {
                "period_days": period_days,
                "total_transactions": len(transactions),
                "by_currency": {},
                "by_operation": {
                    "reserve_lock": 0,
                    "reserve_release": 0,
                    "reserve_topup": 0,
                    "reserve_withdrawal": 0
                },
                # Daily breakdowns (ISO date -> value)
                "daily": {
                    "total": {},
                    "inflow": {},
                    "outflow": {},
                    "total_usd": {},
                    "inflow_usd": {},
                    "outflow_usd": {},
                },
                # Overall totals across period
                "totals": {
                    "volume_gross": 0.0,
                    "inflow": 0.0,
                    "outflow": 0.0,
                    "net_flow": 0.0,
                    "tx_count": len(transactions),
                    "volume_gross_usd": 0.0,
                    "inflow_usd": 0.0,
                    "outflow_usd": 0.0,
                    "net_flow_usd": 0.0,
                },
                # Snapshot of current utilization by currency
                "current_utilization": {},
            }
            
            for tx in transactions:
                metadata = tx.metadata_json or {}
                operation_type = metadata.get("operation_type", "unknown")
                currency = tx.account.currency
                acc_type = tx.account.account_type
                # Normalize amount as float in standard units
                try:
                    amt = float(tx.amount) if tx.amount is not None else 0.0
                except Exception:
                    amt = 0.0

                # Compute USD value of amount
                amt_usd = 0.0
                cur_u = (currency or "").upper()
                try:
                    if acc_type == AccountType.CRYPTO:
                        if cur_u in price_cache:
                            px = price_cache[cur_u]
                        else:
                            px = price_service.get_price_with_fallback(cur_u) or 0.0
                            price_cache[cur_u] = px
                        amt_usd = (amt * float(px)) if px else 0.0
                    else:
                        # FIAT to USD via FX service
                        amt_usd = fx_service.convert_to_usd(amt, cur_u)
                except Exception:
                    amt_usd = 0.0
                
                # Count by operation type
                if operation_type in analytics["by_operation"]:
                    analytics["by_operation"][operation_type] += 1
                
                # Count by currency
                if currency not in analytics["by_currency"]:
                    analytics["by_currency"][currency] = {
                        "total_volume": 0.0,
                        "total_volume_usd": 0.0,
                        "transaction_count": 0,
                        "operations": {},
                        "inflow": 0.0,
                        "outflow": 0.0,
                        "net_flow": 0.0,
                        "inflow_usd": 0.0,
                        "outflow_usd": 0.0,
                        "net_flow_usd": 0.0,
                    }
                
                analytics["by_currency"][currency]["total_volume"] += amt
                analytics["by_currency"][currency]["total_volume_usd"] += amt_usd
                analytics["by_currency"][currency]["transaction_count"] += 1
                
                if operation_type not in analytics["by_currency"][currency]["operations"]:
                    analytics["by_currency"][currency]["operations"][operation_type] = 0
                analytics["by_currency"][currency]["operations"][operation_type] += 1

                # Inflow/Outflow classification
                date_key = (tx.created_at.date().isoformat() if hasattr(tx, "created_at") and tx.created_at else datetime.utcnow().date().isoformat())
                if operation_type == "reserve_topup":
                    analytics["by_currency"][currency]["inflow"] += amt
                    analytics["by_currency"][currency]["inflow_usd"] += amt_usd
                    analytics["totals"]["inflow"] += amt
                    analytics["totals"]["inflow_usd"] += amt_usd
                    analytics["daily"]["inflow"][date_key] = analytics["daily"]["inflow"].get(date_key, 0.0) + amt
                    analytics["daily"]["inflow_usd"][date_key] = analytics["daily"]["inflow_usd"].get(date_key, 0.0) + amt_usd
                    analytics["daily"]["total"][date_key] = analytics["daily"]["total"].get(date_key, 0.0) + amt
                    analytics["daily"]["total_usd"][date_key] = analytics["daily"]["total_usd"].get(date_key, 0.0) + amt_usd
                elif operation_type == "reserve_withdrawal":
                    analytics["by_currency"][currency]["outflow"] += amt
                    analytics["by_currency"][currency]["outflow_usd"] += amt_usd
                    analytics["totals"]["outflow"] += amt
                    analytics["totals"]["outflow_usd"] += amt_usd
                    analytics["daily"]["outflow"][date_key] = analytics["daily"]["outflow"].get(date_key, 0.0) + amt
                    analytics["daily"]["outflow_usd"][date_key] = analytics["daily"]["outflow_usd"].get(date_key, 0.0) + amt_usd
                    analytics["daily"]["total"][date_key] = analytics["daily"]["total"].get(date_key, 0.0) + amt
                    analytics["daily"]["total_usd"][date_key] = analytics["daily"]["total_usd"].get(date_key, 0.0) + amt_usd
                else:
                    # lock/release don't change net reserves; include in gross volume only
                    analytics["totals"]["volume_gross"] += amt
                    analytics["totals"]["volume_gross_usd"] += amt_usd
                    analytics["daily"]["total"][date_key] = analytics["daily"]["total"].get(date_key, 0.0) + 0.0
                    analytics["daily"]["total_usd"][date_key] = analytics["daily"]["total_usd"].get(date_key, 0.0) + 0.0

            # Finalize aggregates
            for c, row in analytics["by_currency"].items():
                row["net_flow"] = row["inflow"] - row["outflow"]
                row["net_flow_usd"] = row["inflow_usd"] - row["outflow_usd"]
            analytics["totals"]["net_flow"] = analytics["totals"]["inflow"] - analytics["totals"]["outflow"]
            analytics["totals"]["net_flow_usd"] = analytics["totals"]["inflow_usd"] - analytics["totals"]["outflow_usd"]

            # Attach current utilization snapshot per currency
            for c in set([acc.currency for acc in reserve_accounts if acc.currency]):
                try:
                    is_crypto = any(acc.currency == c and acc.account_type == AccountType.CRYPTO for acc in reserve_accounts)
                    bal = self.get_reserve_balance(c, AccountType.CRYPTO if is_crypto else AccountType.FIAT)
                    # Compute USD balances
                    cur_u = (c or "").upper()
                    if is_crypto:
                        px = price_cache.get(cur_u)
                        if px is None:
                            px = price_service.get_price_with_fallback(cur_u) or 0.0
                            price_cache[cur_u] = px
                        total_usd = (float(bal.get("total_balance", 0.0)) * float(px)) if px else 0.0
                        available_usd = (float(bal.get("available_balance", 0.0)) * float(px)) if px else 0.0
                        locked_usd = (float(bal.get("locked_balance", 0.0)) * float(px)) if px else 0.0
                    else:
                        total_usd = fx_service.convert_to_usd(float(bal.get("total_balance", 0.0)), cur_u)
                        available_usd = fx_service.convert_to_usd(float(bal.get("available_balance", 0.0)), cur_u)
                        locked_usd = fx_service.convert_to_usd(float(bal.get("locked_balance", 0.0)), cur_u)
                    analytics["current_utilization"][c] = {
                        "status": bal.get("status"),
                        "utilization_percentage": bal.get("utilization_percentage"),
                        "total_balance": bal.get("total_balance"),
                        "available_balance": bal.get("available_balance"),
                        "locked_balance": bal.get("locked_balance"),
                        "total_balance_usd": total_usd,
                        "available_balance_usd": available_usd,
                        "locked_balance_usd": locked_usd,
                    }
                except Exception:
                    continue
            
            return analytics
            
        except Exception as e:
            logger.error(f"Error getting reserve analytics: {e}")
            return {
                "error": str(e)
            }
    
    def _generate_reserve_account_number(self, currency: str, account_type: AccountType) -> str:
        """Generate unique account number for reserve accounts
        Format: R{CUR3}{T}{RANDOM6}
        Ensures uniqueness by checking existing accounts and retrying.
        """
        prefix = f"R{currency[:3]}{account_type.value[:1]}"  # length 5
        chars = string.ascii_uppercase + string.digits
        # Try a few times with random 5-char suffix to keep total length <= 10
        for _ in range(10):
            suffix = ''.join(random.choices(chars, k=5))
            candidate = f"{prefix}{suffix}"  # total length 10
            exists = self.session.query(Account).filter(Account.account_number == candidate).first()
            if not exists:
                return candidate
        # Fallback: time-based suffix if random attempts failed
        fallback = f"{int(time.time()*1000) % 100000:05d}"
        return f"{prefix}{fallback}"
    
    def _convert_to_smallest_unit(self, amount: float, currency: str) -> int:
        """Convert amount to smallest unit"""
        precision_map = {
            "BTC": 8,   # satoshis
            "ETH": 18,  # wei
            "USDC": 6,  # 6 decimals
            "USDT": 6,  # 6 decimals
            "SOL": 9,   # lamports
            "TRX": 6,   # sun
        }
        
        precision = precision_map.get(currency.upper(), 8)
        return int(amount * (10 ** precision))
    
    def clear_cache(self):
        """Clear all cached data"""
        self.reserve_cache.clear()
        self.reserve_accounts.clear()
        logger.info("Reserve service cache cleared")
