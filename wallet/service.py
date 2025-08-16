from db import Account, Transaction, User
from db.connection import session
from db.wallet import TransactionType, TransactionStatus
from sqlalchemy.orm import Session
from typing import Optional, List
import uuid
from shared.kafka_producer import get_kafka_producer
from db.utils import model_to_dict, generate_random_digits
try:
    from lib.payment_metadata import PROVIDER_METADATA_MODELS
except ImportError:
    # Fallback for testing environments
    PROVIDER_METADATA_MODELS = {}
from db.wallet import PaymentProvider
from shared.currency_precision import AmountConverter
from shared.trading_accounting import TradingAccountingService
from db.accounting import JournalEntry, LedgerTransaction, AccountingAccount
import logging

logger = logging.getLogger(__name__)


def get_account_by_user_id(user_id: int, currency: str, session: Session) -> Optional[Account]:
    """
    Fetch an account for a given user ID.
    """
    return session.query(Account).filter(Account.user_id == user_id, Account.currency == currency).first()


def create_account(user_id: int, session: Session) -> Account:
    """
    Create a new account for a user.
    Raises an exception if the account already exists.
    """
    user = session.query(User).filter_by(id=user_id).first()
    if not user:
        return None
    existing = get_account_by_user_id(user_id, "UGX", session)
    if existing:
        raise ValueError(f"Account already exists for user_id={user_id}")
    account_number = f"{generate_random_digits(10)}"
    account = Account(user_id=user_id, balance=0, locked_amount=0,
                      account_number=account_number, currency=user.default_currency)
    session.add(account)
    session.commit()
    session.refresh(account)
    return account


def create_account_for_user(user_id, session):
    user = session.query(User).filter_by(id=user_id).first()
    if not user:
        return None
    # Check if account already exists
    account = session.query(Account).filter_by(user_id=user_id).first()
    if account:
        return account
    # Create new account
    account_number = f"{generate_random_digits(10)}"
    account = Account(user_id=user_id, balance=0, available_balance=0, account_number=account_number, currency=user.default_currency)
    session.add(account)
    session.commit()
    return account


def get_balance(user_id: int, session: Session) -> dict:
    """
    Return the available and total balance for a user.
    Returns a dict with 'balance' and 'available_balance'.
    Raises an exception if the account does not exist.
    """
    account = get_account_by_user_id(user_id, "UGX", session)
    if not account:
        raise ValueError(f"Account does not exist for user_id={user_id}")
    return {
        "balance": float(account.balance),
        "available_balance": account.available_balance()
    }


def validate_and_serialize_metadata(provider: str, metadata: dict) -> dict:
    """
    Validate and serialize provider-specific metadata using the registered pydantic model.
    Returns a dict suitable for storage in metadata_json.
    """
    model = PROVIDER_METADATA_MODELS.get(provider)
    if model:
        return model(**metadata).dict()
    return metadata  # fallback: store as-is


def deposit(user_id: int, amount: float, reference_id: Optional[str], description: Optional[str], session: Session, provider: Optional[str] = None, provider_reference: Optional[str] = None, metadata: Optional[dict] = None) -> Transaction:
    """
    Add funds to a user's account and create a transaction with unified precision and accounting integration.
    Supports provider-specific metadata and provider tracking.
    """
    if not reference_id:
        raise ValueError("reference_id is required for idempotency")
    try:
        if amount <= 0:
            raise ValueError("Deposit amount must be positive")
        account = session.query(Account).filter(Account.user_id == user_id).with_for_update().first()
        if not account:
            raise ValueError(f"Account does not exist for user_id={user_id}")
        
        # Idempotency check
        existing_tx = session.query(Transaction).filter_by(
            account_id=account.id,
            reference_id=reference_id,
            type=TransactionType.DEPOSIT
        ).first()
        if existing_tx:
            return existing_tx
        
        # Get currency from account
        currency = account.currency or "UGX"
        
        # Convert to smallest units using unified converter
        amount_smallest_unit = AmountConverter.to_smallest_units(amount, currency)
        
        validated_metadata = None
        if provider and metadata:
            validated_metadata = validate_and_serialize_metadata(provider, metadata)
        
        # Update account balance using smallest units
        current_balance = account.balance_smallest_unit or 0
        account.balance_smallest_unit = current_balance + amount_smallest_unit
        account.balance = float(account.balance) + float(amount)  # Keep for backward compatibility
        
        transaction = Transaction(
            account_id=account.id,
            reference_id=reference_id,
            amount=amount,
            amount_smallest_unit=amount_smallest_unit,  # Unified field
            type=TransactionType.DEPOSIT,
            status=TransactionStatus.COMPLETED,
            description=description,
            provider=PaymentProvider(provider) if provider else None,
            provider_reference=provider_reference,
            metadata_json=validated_metadata,
        )
        session.add(transaction)
        
        # Create accounting journal entry
        try:
            _create_accounting_entry(transaction, account, session, False)  # False = deposit
        except Exception as e:
            logger.error(f"⚠️ Failed to create accounting entry for deposit: {e}")
        
        session.flush()
        session.refresh(transaction)
        
        logger.info(f"💾 Created deposit with unified system: {AmountConverter.format_display_amount(amount_smallest_unit, currency)}")
        return transaction
    except Exception as e:
        session.rollback()
        raise


def withdraw(user_id: int, amount: float, reference_id: Optional[str], description: Optional[str], session: Session, provider: Optional[str] = None, provider_reference: Optional[str] = None, metadata: Optional[dict] = None) -> Transaction:
    """
    Withdraw funds from a user's account and create a transaction with unified precision and accounting integration.
    Supports provider-specific metadata and provider tracking.
    """
    if not reference_id:
        raise ValueError("reference_id is required for idempotency")
    try:
        if amount <= 0:
            raise ValueError("Withdrawal amount must be positive")
        account = session.query(Account).filter(Account.user_id == user_id).with_for_update().first()
        if not account:
            raise ValueError(f"Account does not exist for user_id={user_id}")
        
        # Idempotency check
        existing_tx = session.query(Transaction).filter_by(
            account_id=account.id,
            reference_id=reference_id,
            type=TransactionType.WITHDRAWAL
        ).first()
        if existing_tx:
            return existing_tx
        
        # Get currency from account
        currency = account.currency or "UGX"
        
        # Convert to smallest units using unified converter
        amount_smallest_unit = AmountConverter.to_smallest_units(amount, currency)
        
        if account.available_balance() < amount:
            raise ValueError("Insufficient available balance")
        
        validated_metadata = None
        if provider and metadata:
            validated_metadata = validate_and_serialize_metadata(provider, metadata)
        
        # Update account balance using smallest units
        current_balance = account.balance_smallest_unit or 0
        account.balance_smallest_unit = current_balance - amount_smallest_unit
        account.balance = float(account.balance) - float(amount)  # Keep for backward compatibility
        
        transaction = Transaction(
            account_id=account.id,
            reference_id=reference_id,
            amount=amount,
            amount_smallest_unit=amount_smallest_unit,  # Unified field
            type=TransactionType.WITHDRAWAL,
            status=TransactionStatus.COMPLETED,
            description=description,
            provider=PaymentProvider(provider) if provider else None,
            provider_reference=provider_reference,
            metadata_json=validated_metadata,
        )
        session.add(transaction)
        
        # Create accounting journal entry
        try:
            _create_accounting_entry(transaction, account, session, True)  # True = withdrawal
        except Exception as e:
            logger.error(f"⚠️ Failed to create accounting entry for withdrawal: {e}")
        
        session.flush()
        session.refresh(transaction)
        
        logger.info(f"💾 Created withdrawal with unified system: {AmountConverter.format_display_amount(amount_smallest_unit, currency)}")
        return transaction
    except Exception as e:
        session.rollback()
        raise


def transfer(from_user_id: int, to_user_id: int, amount: float, reference_id: Optional[str], description: Optional[str], session: Session) -> List[Transaction]:
    """
    Move funds from one user's account to another, with two transactions (debit and credit) using unified precision and accounting integration.
    Ensures atomicity and idempotency (by reference_id).
    Returns a list of the two transactions.
    Raises an exception if any check fails.
    """
    if not reference_id:
        raise ValueError("reference_id is required for idempotency")
    try:
        if amount <= 0:
            raise ValueError("Transfer amount must be positive")
        if from_user_id == to_user_id:
            raise ValueError("Cannot transfer to the same user")
        
        # Always lock in order of user_id to avoid deadlocks
        user_ids = sorted([from_user_id, to_user_id])
        accounts = session.query(Account).filter(Account.user_id.in_(user_ids)).with_for_update().all()
        from_account = next((a for a in accounts if a.user_id == from_user_id), None)
        to_account = next((a for a in accounts if a.user_id == to_user_id), None)
        
        if not from_account:
            raise ValueError(f"Sender account does not exist for user_id={from_user_id}")
        if not to_account:
            raise ValueError(f"Recipient account does not exist for user_id={to_user_id}")
        
        # Ensure both accounts use same currency
        from_currency = from_account.currency or "UGX"
        to_currency = to_account.currency or "UGX"
        if from_currency != to_currency:
            raise ValueError(f"Cannot transfer between different currencies: {from_currency} -> {to_currency}")
        
        # Idempotency check (debit)
        existing_debit = session.query(Transaction).filter_by(
            account_id=from_account.id,
            reference_id=reference_id,
            type=TransactionType.TRANSFER
        ).first()
        # Idempotency check (credit)
        existing_credit = session.query(Transaction).filter_by(
            account_id=to_account.id,
            reference_id=reference_id,
            type=TransactionType.TRANSFER
        ).first()
        if existing_debit and existing_credit:
            return [existing_debit, existing_credit]
        
        if from_account.available_balance() < amount:
            raise ValueError("Insufficient available balance for transfer")
        
        # Convert to smallest units using unified converter
        amount_smallest_unit = AmountConverter.to_smallest_units(amount, from_currency)
        
        # Update account balances using smallest units
        from_current_balance = from_account.balance_smallest_unit or 0
        to_current_balance = to_account.balance_smallest_unit or 0
        
        from_account.balance_smallest_unit = from_current_balance - amount_smallest_unit
        to_account.balance_smallest_unit = to_current_balance + amount_smallest_unit
        
        # Keep backward compatibility
        from_account.balance = float(from_account.balance) - float(amount)
        to_account.balance = float(to_account.balance) + float(amount)
        
        debit_tx = Transaction(
            account_id=from_account.id,
            reference_id=reference_id,
            amount=amount,
            amount_smallest_unit=amount_smallest_unit,  # Unified field
            type=TransactionType.TRANSFER,
            status=TransactionStatus.COMPLETED,
            description=f"Transfer to user {to_user_id}: {description}" if description else f"Transfer to user {to_user_id}",
            metadata_json={"transfer_type": "debit", "counterpart_user_id": to_user_id, "currency": from_currency, "unified_system": True}
        )
        credit_tx = Transaction(
            account_id=to_account.id,
            reference_id=reference_id,
            amount=amount,
            amount_smallest_unit=amount_smallest_unit,  # Unified field
            type=TransactionType.TRANSFER,
            status=TransactionStatus.COMPLETED,
            description=f"Transfer from user {from_user_id}: {description}" if description else f"Transfer from user {from_user_id}",
            metadata_json={"transfer_type": "credit", "counterpart_user_id": from_user_id, "currency": to_currency, "unified_system": True}
        )
        
        session.add(debit_tx)
        session.add(credit_tx)
        
        # Create accounting journal entries for both sides of the transfer
        try:
            _create_transfer_accounting_entries(debit_tx, credit_tx, from_account, to_account, session)
        except Exception as e:
            logger.error(f"⚠️ Failed to create accounting entries for transfer: {e}")
        
        session.flush()
        session.refresh(debit_tx)
        session.refresh(credit_tx)
        
        logger.info(f"💾 Created transfer with unified system: {AmountConverter.format_display_amount(amount_smallest_unit, from_currency)} from user {from_user_id} to user {to_user_id}")
        return [debit_tx, credit_tx]
    except Exception as e:
        session.rollback()
        raise


def _create_accounting_entry(transaction: Transaction, account: Account, session: Session, is_withdrawal: bool):
    """
    Create accounting journal entry for wallet deposits and withdrawals.
    For deposits: Debit Cash/Bank, Credit User Liability
    For withdrawals: Debit User Liability, Credit Cash/Bank
    """
    try:
        amount_smallest_unit = transaction.amount_smallest_unit
        currency = account.currency or "UGX"
        
        # Format amount for description
        formatted_amount = AmountConverter.format_display_amount(amount_smallest_unit, currency)
        
        if is_withdrawal:
            description = f"Wallet withdrawal: {formatted_amount} for user {account.user_id}"
            debit_account = f"User Liabilities - {currency}"
            credit_account = f"Cash/Bank - {currency}"
        else:
            description = f"Wallet deposit: {formatted_amount} for user {account.user_id}"
            debit_account = f"Cash/Bank - {currency}"
            credit_account = f"User Liabilities - {currency}"
        
        # Use TradingAccountingService to create the journal entry
        accounting_service = TradingAccountingService(session)
        accounting_service.create_journal_entry(
            description=description,
            debit_account_name=debit_account,
            credit_account_name=credit_account,
            amount_smallest_unit=amount_smallest_unit,
            currency=currency,
            reference_id=transaction.reference_id,
            metadata={
                "transaction_id": transaction.id,
                "account_id": account.id,
                "user_id": account.user_id,
                "transaction_type": transaction.type.value if transaction.type else None,
                "unified_system": True
            }
        )
        logger.info(f"✅ Created accounting entry for {'withdrawal' if is_withdrawal else 'deposit'}: {formatted_amount}")
    except Exception as e:
        logger.error(f"⚠️ Failed to create accounting entry for {'withdrawal' if is_withdrawal else 'deposit'}: {e}")


def _create_crypto_withdrawal_accounting_entry(transaction: Transaction, account: Account, session: Session):
    """
    Create accounting journal entry for confirmed crypto withdrawals.
    Debit: User Liabilities - {Currency} (decrease liability)
    Credit: Crypto Assets - {Currency} (decrease asset)
    
    This should only be called AFTER the withdrawal is confirmed on blockchain.
    """
    try:
        amount_smallest_unit = transaction.amount_smallest_unit
        currency = transaction.currency or account.currency or "ETH"
        
        # Format amount for description
        formatted_amount = AmountConverter.format_display_amount(amount_smallest_unit, currency)
        
        description = f"Confirmed crypto withdrawal: {formatted_amount} for user {account.user_id}"
        
        # Use TradingAccountingService to create the journal entry
        accounting_service = TradingAccountingService(session)
        accounting_service.create_journal_entry(
            description=description,
            debit_account_name=f"User Liabilities - {currency}",
            credit_account_name=f"Crypto Assets - {currency}",
            amount_smallest_unit=amount_smallest_unit,
            currency=currency,
            reference_id=transaction.reference_id,
            metadata={
                "transaction_id": transaction.id,
                "account_id": account.id,
                "user_id": account.user_id,
                "blockchain_txid": transaction.blockchain_txid,
                "address": transaction.address,
                "transaction_type": transaction.type.value if transaction.type else None,
                "unified_system": True,
                "confirmation_type": "crypto_withdrawal"
            }
        )
        logger.info(f"✅ Created crypto withdrawal accounting entry: {formatted_amount}")
    except Exception as e:
        logger.error(f"⚠️ Failed to create crypto withdrawal accounting entry: {e}")


def confirm_crypto_withdrawal(transaction_hash: str, session: Session) -> bool:
    """
    Confirm a crypto withdrawal transaction and create accounting entry.
    This should be called when a withdrawal transaction is confirmed on blockchain.
    
    Returns True if confirmation was successful, False otherwise.
    """
    try:
        # Find the withdrawal transaction
        tx = session.query(Transaction).filter_by(
            blockchain_txid=transaction_hash,
            type=TransactionType.WITHDRAWAL,
            status=TransactionStatus.AWAITING_CONFIRMATION
        ).first()
        
        if not tx:
            logger.warning(f"No pending withdrawal found for transaction hash: {transaction_hash}")
            return False
        
        # Get the account
        account = session.query(Account).filter_by(id=tx.account_id).first()
        if not account:
            logger.error(f"Account not found for transaction: {tx.id}")
            return False
        
        # Check blockchain confirmation status
        currency = tx.currency or account.currency or "ETH"
        is_confirmed = _check_blockchain_confirmation(transaction_hash, currency)
        
        if not is_confirmed:
            logger.debug(f"Transaction {transaction_hash[:8]}... not yet confirmed on blockchain")
            return False
        
        # Update transaction status
        tx.status = TransactionStatus.COMPLETED
        
        # Release locked funds
        amount_smallest_unit = tx.amount_smallest_unit
        if hasattr(account, 'locked_amount_smallest_unit'):
            # Use unified balance system
            account.locked_amount_smallest_unit = max(0, (account.locked_amount_smallest_unit or 0) - amount_smallest_unit)
        else:
            # Fallback to legacy crypto fields
            account.crypto_locked_amount_smallest_unit = max(0, (account.crypto_locked_amount_smallest_unit or 0) - amount_smallest_unit)
        
        # Create accounting entry for confirmed withdrawal
        _create_crypto_withdrawal_accounting_entry(tx, account, session)
        
        session.commit()
        
        formatted_amount = AmountConverter.format_display_amount(amount_smallest_unit, currency)
        logger.info(f"✅ Confirmed crypto withdrawal: {formatted_amount} (tx: {transaction_hash})")
        
        return True
        
    except Exception as e:
        session.rollback()
        logger.error(f"❌ Failed to confirm crypto withdrawal {transaction_hash}: {e}")
        return False


def _check_blockchain_confirmation(transaction_hash: str, currency: str) -> bool:
    """
    Check if a transaction is confirmed on the blockchain.
    Returns True if confirmed, False if still pending.
    """
    try:
        if currency == "SOL":
            return _check_solana_confirmation(transaction_hash)
        elif currency in ["ETH", "USDT", "USDC", "DAI"]:
            return _check_ethereum_confirmation(transaction_hash)
        else:
            logger.warning(f"Unsupported currency for confirmation check: {currency}")
            return False
    except Exception as e:
        logger.error(f"Error checking blockchain confirmation for {transaction_hash}: {e}")
        return False


def _check_solana_confirmation(transaction_hash: str) -> bool:
    """Check Solana transaction confirmation status using Alchemy API."""
    try:
        import requests
        from decouple import config
        
        api_key = config('ALCHEMY_API_KEY', default='')
        if not api_key:
            logger.error("ALCHEMY_API_KEY not configured")
            return False
        
        # Use devnet for testing, mainnet for production
        network = config('SOLANA_NETWORK', default='devnet')
        if network.upper() == 'MAINNET':
            url = f"https://solana-mainnet.g.alchemy.com/v2/{api_key}"
        else:
            url = f"https://solana-devnet.g.alchemy.com/v2/{api_key}"
        
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getSignatureStatuses",
            "params": [[transaction_hash], {"searchTransactionHistory": True}]
        }
        
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        if 'result' in data and data['result']['value'] and len(data['result']['value']) > 0:
            status = data['result']['value'][0]
            if status:
                confirmation_status = status.get('confirmationStatus')
                confirmations = status.get('confirmations')
                
                # Consider finalized or 32+ confirmations as confirmed
                if confirmation_status == 'finalized' or (isinstance(confirmations, int) and confirmations >= 32):
                    return True
        
        return False
        
    except Exception as e:
        logger.error(f"Error checking Solana confirmation for {transaction_hash}: {e}")
        return False


def _check_ethereum_confirmation(transaction_hash: str) -> bool:
    """Check Ethereum transaction confirmation status using Alchemy API."""
    try:
        import requests
        from decouple import config
        
        api_key = config('ALCHEMY_API_KEY', default='')
        if not api_key:
            logger.error("ALCHEMY_API_KEY not configured")
            return False
        
        # Use testnet for testing, mainnet for production
        network = config('ETHEREUM_NETWORK', default='sepolia')
        if network.upper() == 'MAINNET':
            url = f"https://eth-mainnet.g.alchemy.com/v2/{api_key}"
        else:
            url = f"https://eth-sepolia.g.alchemy.com/v2/{api_key}"
        
        # Get transaction receipt
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "eth_getTransactionReceipt",
            "params": [transaction_hash]
        }
        
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        if 'result' in data and data['result']:
            receipt = data['result']
            block_number = receipt.get('blockNumber')
            
            if block_number:
                # Get current block number
                current_block_payload = {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "eth_blockNumber",
                    "params": []
                }
                
                current_response = requests.post(url, json=current_block_payload, timeout=10)
                current_response.raise_for_status()
                
                current_data = current_response.json()
                if 'result' in current_data:
                    current_block = int(current_data['result'], 16)
                    tx_block = int(block_number, 16)
                    confirmations = current_block - tx_block + 1
                    
                    # Consider 12+ confirmations as confirmed for Ethereum
                    return confirmations >= 12
        
        return False
        
    except Exception as e:
        logger.error(f"Error checking Ethereum confirmation for {transaction_hash}: {e}")
        return False


def _create_transfer_accounting_entries(debit_tx: Transaction, credit_tx: Transaction, from_account: Account, to_account: Account, session: Session):
    """
    Create accounting journal entries for user-to-user transfers.
    This is an internal liability transfer between users, so no cash accounts are affected.
    Debit: From User Liability (decrease sender's liability)
    Credit: To User Liability (increase recipient's liability)
    """
    currency = from_account.currency or "UGX"
    amount_smallest_unit = debit_tx.amount_smallest_unit
    
    # Format amount for description
    formatted_amount = AmountConverter.format_display_amount(amount_smallest_unit, currency)
    
    description = f"User transfer: {formatted_amount} from user {from_account.user_id} to user {to_account.user_id}"
    
    # Use TradingAccountingService to create the journal entry
    accounting_service = TradingAccountingService(session)
    accounting_service.create_journal_entry(
        description=description,
        debit_account_name=f"User Liabilities - {currency} (User {from_account.user_id})",
        credit_account_name=f"User Liabilities - {currency} (User {to_account.user_id})",
        amount_smallest_unit=amount_smallest_unit,
        currency=currency,
        reference_id=debit_tx.reference_id,
        metadata={
            "debit_transaction_id": debit_tx.id,
            "credit_transaction_id": credit_tx.id,
            "from_account_id": from_account.id,
            "to_account_id": to_account.id,
            "from_user_id": from_account.user_id,
            "to_user_id": to_account.user_id,
            "transfer_type": "user_to_user",
            "unified_system": True
        }
    )


def get_transaction_history(user_id: int, currency: str,  session: Session, limit: int = 20, offset: int = 0) -> List[Transaction]:
    """
    List recent transactions for a user, paginated by limit and offset.
    Raises an exception if the account does not exist.
    """
    account = get_account_by_user_id(user_id, currency, session)
    if not account:
        raise ValueError(f"Account does not exist for user_id={user_id}")
    transactions = (
        session.query(Transaction)
        .filter(Transaction.account_id == account.id)
        .order_by(Transaction.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return transactions


def process_credit_message(user_id: int, amount: float, reference_id: str, description: str, session: Session) -> Transaction:
    """
    Process a credit request for a user (from a message queue).
    Uses deposit() logic, ensures idempotency by reference_id.
    Returns the created or existing Transaction.
    """
    return deposit(user_id, amount, reference_id, description, session)


def get_all_transactions(session: Session, limit: int = 20, offset: int = 0):
    """
    List all transactions in the system, paginated.
    Returns a list of dicts, each containing transaction, account, and user info.
    """
    query = (
        session.query(Transaction, Account, User)
        .join(Account, Transaction.account_id == Account.id)
        .join(User, Account.user_id == User.id)
        .order_by(Transaction.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    results = []
    for tx, account, user in query.all():
        tx_dict = model_to_dict(tx)
        account_dict = model_to_dict(account)
        user_dict = model_to_dict(user)
        results.append({
            "transaction": tx_dict,
            "account": account_dict,
            "user": {
                "id": user_dict["id"],
                "first_name": user_dict["first_name"],
                "last_name": user_dict["last_name"],
                "email": user_dict["email"],
                "role": user_dict["role"],
            }
        })
    return results

# Example usage for future wallet events:
# kafka_producer = get_kafka_producer()
# kafka_producer.send('wallet-events', {'user_id': user_id, 'event': 'deposit', ...})
