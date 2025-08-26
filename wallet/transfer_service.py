"""
Enhanced Transfer Service with Ledger Tracking and Portfolio Management
"""
import logging
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import List, Dict, Tuple, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, func

from db.wallet import (
    Account, Transaction, TransactionType, TransactionStatus, 
    LedgerEntry, PortfolioSnapshot, CryptoPriceHistory, PaymentProvider
)
from db.models import User
from shared.crypto.price_cache_service import get_cached_prices

logger = logging.getLogger(__name__)


class TransferService:
    """Service for handling transfers with ledger tracking and portfolio management"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def transfer_between_users(
        self,
        from_user_id: int,
        to_email: str,
        amount: float,
        currency: str,
        reference_id: str = None,
        description: str = None
    ) -> Dict:
        """
        Transfer funds between users with comprehensive ledger tracking and idempotency
        
        Args:
            from_user_id: ID of the user sending funds
            to_email: Email of the user receiving funds
            amount: Amount to transfer
            currency: Currency code (e.g., 'BTC', 'ETH', 'USD')
            reference_id: Optional reference ID for idempotency and tracking
            description: Optional description of the transfer
            
        Returns:
            Dict containing transfer result and transaction details
        """
        try:
            # 0. Check for idempotency if reference_id is provided
            if reference_id:
                existing_transaction = self._get_existing_transaction_by_reference(reference_id)
                if existing_transaction:
                    logger.info(f"Idempotency: Found existing transaction with reference_id {reference_id}")
                    return self._build_idempotent_response(existing_transaction, from_user_id, to_email, amount, currency)
            
            # 1. Validate sender's wallet
            from_account = self._get_user_wallet_by_currency(from_user_id, currency)
            if not from_account:
                raise ValueError(f"Sender does not have a {currency} wallet")
            
            # 2. Validate sender has sufficient balance
            if not self._has_sufficient_balance(from_account, amount, currency):
                raise ValueError(f"Insufficient {currency} balance")
            
            # 3. Look up recipient by email
            to_user = self._get_user_by_email(to_email)
            if not to_user:
                raise ValueError(f"Recipient with email {to_email} not found")
            
            # 4. Get or create recipient's wallet for this currency
            to_account = self._get_or_create_user_wallet(to_user.id, currency)
            
            # 5. Record current prices for crypto (if applicable)
            price_usd = None
            if self._is_crypto_currency(currency):
                price_usd = self._get_current_crypto_price(currency)
                if price_usd:
                    self._record_crypto_price(currency, price_usd)
            
            # 6. Create transfer transaction
            transaction = self._create_transfer_transaction(
                from_account, to_account, amount, currency, 
                reference_id, description, price_usd
            )
            
            # 7. Update account balances
            self._update_account_balances(from_account, to_account, amount, currency)
            
            # 8. Create ledger entries
            self._create_ledger_entries(transaction, from_account, to_account, amount, currency, price_usd)
            
            # 9. Update portfolio snapshots
            self._update_portfolio_snapshots(from_user_id)
            self._update_portfolio_snapshots(to_user.id)
            
            # 10. Commit all changes
            self.session.commit()
            
            logger.info(f"Transfer completed: {amount} {currency} from user {from_user_id} to {to_email}")
            
            return {
                "success": True,
                "transaction_id": transaction.id,
                "reference_id": reference_id,
                "from_user_id": from_user_id,
                "to_user_id": to_user.id,
                "to_email": to_email,
                "amount": amount,
                "currency": currency,
                "price_usd": price_usd,
                "status": "completed"
            }
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"Transfer failed: {str(e)}")
            raise
    
    def _get_user_wallet_by_currency(self, user_id: int, currency: str) -> Optional[Account]:
        """Get user's wallet for specific currency"""
        return self.session.query(Account).filter(
            and_(
                Account.user_id == user_id,
                Account.currency == currency.upper()
            )
        ).first()
    
    def _get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email address"""
        return self.session.query(User).filter(User.email == email.lower()).first()
    
    def _get_existing_transaction_by_reference(self, reference_id: str) -> Optional[Transaction]:
        """Check if a transaction with the given reference_id already exists"""
        return self.session.query(Transaction).filter(
            Transaction.reference_id == reference_id,
            Transaction.type == TransactionType.TRANSFER
        ).first()
    
    def _build_idempotent_response(self, existing_transaction: Transaction, from_user_id: int, to_email: str, amount: float, currency: str) -> Dict:
        """Build response for idempotent transfer request"""
        # Get the recipient user from the transaction metadata
        metadata = existing_transaction.metadata_json or {}
        to_user_id = metadata.get('to_user_id')
        
        return {
            "success": True,
            "transaction_id": existing_transaction.id,
            "reference_id": existing_transaction.reference_id,
            "from_user_id": from_user_id,
            "to_user_id": to_user_id,
            "to_email": to_email,
            "amount": amount,
            "currency": currency,
            "status": "idempotent",
            "message": "Transfer already processed with this reference_id",
            "original_transaction_date": existing_transaction.created_at.isoformat() if existing_transaction.created_at else None
        }
    
    def _get_or_create_user_wallet(self, user_id: int, currency: str) -> Account:
        """Get existing wallet or create new one for user and currency"""
        wallet = self._get_user_wallet_by_currency(user_id, currency)
        if wallet:
            return wallet
        
        # Create new wallet for this currency
        account_number = self._generate_account_number()
        wallet = Account(
            user_id=user_id,
            currency=currency.upper(),
            account_number=account_number,
            balance=0.0,
            locked_amount=0.0,
            account_type=self._get_account_type(currency)
        )
        self.session.add(wallet)
        self.session.flush()  # Get the ID
        return wallet
    
    def _has_sufficient_balance(self, account: Account, amount: float, currency: str) -> bool:
        """Check if account has sufficient balance for transfer"""
        if self._is_crypto_currency(currency):
            available_balance = account.available_balance()
        else:
            available_balance = float(account.balance) - float(account.locked_amount)
        
        return available_balance >= amount
    
    def _is_crypto_currency(self, currency: str) -> bool:
        """Check if currency is crypto using admin panel"""
        from shared.currency_utils import is_currency_enabled
        return is_currency_enabled(currency.upper())
    
    def _get_account_type(self, currency: str) -> str:
        """Get account type based on currency"""
        return "CRYPTO" if self._is_crypto_currency(currency) else "FIAT"
    
    def _get_current_crypto_price(self, currency: str) -> Optional[float]:
        """Get current crypto price from cache"""
        try:
            prices = get_cached_prices()
            if currency.upper() in prices:
                return float(prices[currency.upper()]['price'])
        except Exception as e:
            logger.warning(f"Failed to get crypto price for {currency}: {e}")
        return None
    
    def _record_crypto_price(self, currency: str, price_usd: float):
        """Record crypto price in history"""
        price_record = CryptoPriceHistory(
            currency=currency.upper(),
            price_usd=Decimal(str(price_usd)),
            source="alchemy",
            price_timestamp=datetime.utcnow()
        )
        self.session.add(price_record)
    
    def _create_transfer_transaction(
        self,
        from_account: Account,
        to_account: Account,
        amount: float,
        currency: str,
        reference_id: str = None,
        description: str = None,
        price_usd: float = None
    ) -> Transaction:
        """Create transfer transaction record"""
        transaction = Transaction(
            account_id=from_account.id,
            amount=Decimal(str(amount)),
            type=TransactionType.TRANSFER,
            status=TransactionStatus.COMPLETED,
            description=description or f"Transfer to {to_account.user.email}",
            reference_id=reference_id,
            provider=PaymentProvider.CRYPTO if self._is_crypto_currency(currency) else None,
            amount_smallest_unit=0,
            metadata_json={
                "transfer_type": "user_to_user",
                "to_account_id": to_account.id,
                "to_user_id": to_account.user_id,
                "currency": currency,
                "price_usd": price_usd
            }
        )
        self.session.add(transaction)
        self.session.flush()  # Get the ID
        return transaction
    
    def _update_account_balances(self, from_account: Account, to_account: Account, amount: float, currency: str):
        """Update account balances after transfer"""
        if self._is_crypto_currency(currency):
            # For crypto, update smallest unit amounts - convert to Decimal to avoid type mismatch
            amount_smallest_unit = self._convert_to_smallest_unit(amount, currency)
            amount_smallest_unit_decimal = Decimal(str(amount_smallest_unit))
            from_account.crypto_balance_smallest_unit -= amount_smallest_unit_decimal
            to_account.crypto_balance_smallest_unit += amount_smallest_unit_decimal
        else:
            # For fiat, update standard amounts - convert to Decimal to avoid type mismatch
            amount_decimal = Decimal(str(amount))
            from_account.balance -= amount_decimal
            to_account.balance += amount_decimal
    
    def _create_ledger_entries(
        self,
        transaction: Transaction,
        from_account: Account,
        to_account: Account,
        amount: float,
        currency: str,
        price_usd: float = None
    ):
        """Create ledger entries for the transfer"""
        # Debit entry for sender
        from_balance_before = self._get_account_balance(from_account, currency)
        from_balance_after = from_balance_before - amount
        
        debit_entry = LedgerEntry(
            transaction_id=transaction.id,
            user_id=from_account.user_id,
            account_id=from_account.id,
            amount=Decimal(str(amount)),
            currency=currency.upper(),
            entry_type="debit",
            transaction_type=TransactionType.TRANSFER,
            balance_before=Decimal(str(from_balance_before)),
            balance_after=Decimal(str(from_balance_after)),
            price_usd=Decimal(str(price_usd)) if price_usd else None,
            price_timestamp=datetime.utcnow() if price_usd else None,
            description=f"Transfer to {to_account.user.email}",
            reference_id=transaction.reference_id
        )
        
        # Credit entry for recipient
        to_balance_before = self._get_account_balance(to_account, currency)
        to_balance_after = to_balance_before + amount
        
        credit_entry = LedgerEntry(
            transaction_id=transaction.id,
            user_id=to_account.user_id,
            account_id=to_account.id,
            amount=Decimal(str(amount)),
            currency=currency.upper(),
            entry_type="credit",
            transaction_type=TransactionType.TRANSFER,
            balance_before=Decimal(str(to_balance_before)),
            balance_after=Decimal(str(to_balance_after)),
            price_usd=Decimal(str(price_usd)) if price_usd else None,
            price_timestamp=datetime.utcnow() if price_usd else None,
            description=f"Transfer from {from_account.user.email}",
            reference_id=transaction.reference_id
        )
        
        self.session.add(debit_entry)
        self.session.add(credit_entry)
    
    def _get_account_balance(self, account: Account, currency: str) -> float:
        """Get current account balance for specific currency"""
        if self._is_crypto_currency(currency):
            return account.available_balance()
        else:
            return float(account.balance)
    
    def _convert_to_smallest_unit(self, amount: float, currency: str) -> int:
        """Convert standard amount to smallest unit (e.g., USD to cents, BTC to satoshis)"""
        # This is a simplified conversion - you might want to use proper precision configs
        if currency.upper() in ['BTC', 'LTC']:
            return int(amount * 100000000)  # 8 decimal places
        elif currency.upper() in ['ETH', 'BNB', 'AVAX']:
            return int(amount * 1000000000000000000)  # 18 decimal places
        elif currency.upper() in ['SOL']:
            return int(amount * 1000000000)  # 9 decimal places
        else:
            return int(amount * 100)  # Default to 2 decimal places
    
    def _generate_account_number(self) -> str:
        """Generate unique account number"""
        import random
        import string
        
        while True:
            # Generate 10-digit account number
            account_number = ''.join(random.choices(string.digits, k=10))
            
            # Check if it already exists
            existing = self.session.query(Account).filter(Account.account_number == account_number).first()
            if not existing:
                return account_number
    
    def _update_portfolio_snapshots(self, user_id: int):
        """Update portfolio snapshots for user"""
        try:
            # Get current portfolio value
            current_portfolio = self._calculate_current_portfolio(user_id)
            
            # Update daily snapshot
            self._update_snapshot(user_id, 'daily', date.today(), current_portfolio)
            
            # Update weekly snapshot (start of week)
            week_start = date.today() - timedelta(days=date.today().weekday())
            self._update_snapshot(user_id, 'weekly', week_start, current_portfolio)
            
            # Update monthly snapshot (start of month)
            month_start = date.today().replace(day=1)
            self._update_snapshot(user_id, 'monthly', month_start, current_portfolio)
            
        except Exception as e:
            logger.error(f"Failed to update portfolio snapshots for user {user_id}: {e}")
    
    def _calculate_current_portfolio(self, user_id: int) -> Dict:
        """Calculate current portfolio value and changes"""
        # Get all user accounts with balances
        accounts = self.session.query(Account).filter(Account.user_id == user_id).all()
        
        total_value_usd = 0.0
        asset_details = {}
        
        for account in accounts:
            if account.currency:
                balance = self._get_account_balance(account, account.currency)
                if balance > 0:
                    price_usd = 1.0  # Default for USD
                    if account.currency != 'USD':
                        price_usd = self._get_current_crypto_price(account.currency) or 0.0
                    
                    value_usd = balance * price_usd
                    total_value_usd += value_usd
                    
                    asset_details[account.currency] = {
                        'balance': balance,
                        'price_usd': price_usd,
                        'value_usd': value_usd
                    }
        
        # Calculate changes from previous snapshots
        changes = self._calculate_portfolio_changes(user_id, total_value_usd)
        
        return {
            'total_value_usd': total_value_usd,
            'asset_details': asset_details,
            'changes': changes
        }
    
    def _calculate_portfolio_changes(self, user_id: int, current_value: float) -> Dict:
        """Calculate portfolio changes over different time periods"""
        changes = {}
        
        # Get previous snapshots for comparison
        for period in ['daily', 'weekly', 'monthly']:
            previous_snapshot = self._get_previous_snapshot(user_id, period)
            if previous_snapshot:
                change_amount = current_value - float(previous_snapshot.total_value_usd)
                change_percent = (change_amount / float(previous_snapshot.total_value_usd)) * 100 if previous_snapshot.total_value_usd > 0 else 0
                
                changes[f'{period}_change'] = change_amount
                changes[f'{period}_change_percent'] = change_percent
            else:
                changes[f'{period}_change'] = 0.0
                changes[f'{period}_change_percent'] = 0.0
        
        return changes
    
    def _get_previous_snapshot(self, user_id: int, snapshot_type: str) -> Optional[PortfolioSnapshot]:
        """Get previous snapshot for comparison"""
        if snapshot_type == 'daily':
            previous_date = date.today() - timedelta(days=1)
        elif snapshot_type == 'weekly':
            previous_date = date.today() - timedelta(weeks=1)
        elif snapshot_type == 'monthly':
            # Get previous month
            if date.today().month == 1:
                previous_date = date.today().year - 1, 12, 1
            else:
                previous_date = date.today().replace(month=date.today().month - 1, day=1)
            previous_date = date(*previous_date)
        else:
            return None
        
        return self.session.query(PortfolioSnapshot).filter(
            and_(
                PortfolioSnapshot.user_id == user_id,
                PortfolioSnapshot.snapshot_type == snapshot_type,
                PortfolioSnapshot.snapshot_date == previous_date
            )
        ).first()
    
    def _update_snapshot(self, user_id: int, snapshot_type: str, snapshot_date: date, portfolio_data: Dict):
        """Update or create portfolio snapshot"""
        # Check if snapshot already exists for this date
        existing_snapshot = self.session.query(PortfolioSnapshot).filter(
            and_(
                PortfolioSnapshot.user_id == user_id,
                PortfolioSnapshot.snapshot_type == snapshot_type,
                PortfolioSnapshot.snapshot_date == snapshot_date
            )
        ).first()
        
        if existing_snapshot:
            # Update existing snapshot
            existing_snapshot.total_value_usd = portfolio_data['total_value_usd']
            existing_snapshot.total_change_24h = portfolio_data['changes'].get('daily_change')
            existing_snapshot.total_change_7d = portfolio_data['changes'].get('weekly_change')
            existing_snapshot.total_change_30d = portfolio_data['changes'].get('monthly_change')
            existing_snapshot.change_percent_24h = portfolio_data['changes'].get('daily_change_percent')
            existing_snapshot.change_percent_7d = portfolio_data['changes'].get('weekly_change_percent')
            existing_snapshot.change_percent_30d = portfolio_data['changes'].get('monthly_change_percent')
            existing_snapshot.currency_count = len(portfolio_data['asset_details'])
            existing_snapshot.asset_details = portfolio_data['asset_details']
        else:
            # Create new snapshot
            new_snapshot = PortfolioSnapshot(
                user_id=user_id,
                snapshot_type=snapshot_type,
                snapshot_date=snapshot_date,
                total_value_usd=portfolio_data['total_value_usd'],
                total_change_24h=portfolio_data['changes'].get('daily_change'),
                total_change_7d=portfolio_data['changes'].get('weekly_change'),
                total_change_30d=portfolio_data['changes'].get('monthly_change'),
                change_percent_24h=portfolio_data['changes'].get('daily_change_percent'),
                change_percent_7d=portfolio_data['changes'].get('weekly_change_percent'),
                change_percent_30d=portfolio_data['changes'].get('monthly_change_percent'),
                currency_count=len(portfolio_data['asset_details']),
                asset_details=portfolio_data['asset_details']
            )
            self.session.add(new_snapshot)


def transfer_between_users(
    session: Session,
    from_user_id: int,
    to_email: str,
    amount: float,
    currency: str,
    reference_id: str = None,
    description: str = None
) -> Dict:
    """Convenience function for transfers"""
    service = TransferService(session)
    return service.transfer_between_users(
        from_user_id, to_email, amount, currency, reference_id, description
    )
