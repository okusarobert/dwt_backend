from db import Account, Transaction, User
from db.connection import session
from db.wallet import TransactionType, TransactionStatus
from sqlalchemy.orm import Session
from typing import Optional, List
import uuid
from shared.kafka_producer import get_kafka_producer
from db.utils import model_to_dict, generate_random_digits
from lib.payment_metadata import PROVIDER_METADATA_MODELS
from db.wallet import PaymentProvider


def get_account_by_user_id(user_id: int, session: Session) -> Optional[Account]:
    """
    Fetch an account for a given user ID.
    """
    return session.query(Account).filter(Account.user_id == user_id).first()


def create_account(user_id: int, session: Session) -> Account:
    """
    Create a new account for a user.
    Raises an exception if the account already exists.
    """
    user = session.query(User).filter_by(id=user_id).first()
    if not user:
        return None
    existing = get_account_by_user_id(user_id, session)
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
    account = get_account_by_user_id(user_id, session)
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
    Add funds to a user's account and create a transaction.
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
        validated_metadata = None
        if provider and metadata:
            validated_metadata = validate_and_serialize_metadata(provider, metadata)
        account.balance = float(account.balance) + float(amount)
        transaction = Transaction(
            account_id=account.id,
            reference_id=reference_id,
            amount=amount,
            type=TransactionType.DEPOSIT,
            status=TransactionStatus.COMPLETED,
            description=description,
            provider=PaymentProvider(provider) if provider else None,
            provider_reference=provider_reference,
            metadata_json=validated_metadata,
        )
        session.add(transaction)
        session.flush()
        session.refresh(transaction)
        return transaction
    except Exception as e:
        session.rollback()
        raise


def withdraw(user_id: int, amount: float, reference_id: Optional[str], description: Optional[str], session: Session, provider: Optional[str] = None, provider_reference: Optional[str] = None, metadata: Optional[dict] = None) -> Transaction:
    """
    Withdraw funds from a user's account and create a transaction.
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
        if account.available_balance() < amount:
            raise ValueError("Insufficient available balance")
        validated_metadata = None
        if provider and metadata:
            validated_metadata = validate_and_serialize_metadata(provider, metadata)
        account.balance = float(account.balance) - float(amount)
        transaction = Transaction(
            account_id=account.id,
            reference_id=reference_id,
            amount=amount,
            type=TransactionType.WITHDRAWAL,
            status=TransactionStatus.COMPLETED,
            description=description,
            provider=PaymentProvider(provider) if provider else None,
            provider_reference=provider_reference,
            metadata_json=validated_metadata,
        )
        session.add(transaction)
        session.flush()
        session.refresh(transaction)
        return transaction
    except Exception as e:
        session.rollback()
        raise


def transfer(from_user_id: int, to_user_id: int, amount: float, reference_id: Optional[str], description: Optional[str], session: Session) -> List[Transaction]:
    """
    Move funds from one user's account to another, with two transactions (debit and credit).
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
        from_account.balance = float(from_account.balance) - float(amount)
        to_account.balance = float(to_account.balance) + float(amount)
        debit_tx = Transaction(
            account_id=from_account.id,
            reference_id=reference_id,
            amount=amount,
            type=TransactionType.TRANSFER,
            status=TransactionStatus.COMPLETED,
            description=f"Transfer to user {to_user_id}: {description}" if description else f"Transfer to user {to_user_id}",
            metadata=None
        )
        credit_tx = Transaction(
            account_id=to_account.id,
            reference_id=reference_id,
            amount=amount,
            type=TransactionType.TRANSFER,
            status=TransactionStatus.COMPLETED,
            description=f"Transfer from user {from_user_id}: {description}" if description else f"Transfer from user {from_user_id}",
            metadata=None
        )
        session.add(debit_tx)
        session.add(credit_tx)
        session.flush()
        session.refresh(debit_tx)
        session.refresh(credit_tx)
        return [debit_tx, credit_tx]
    except Exception as e:
        session.rollback()
        raise


def get_transaction_history(user_id: int, session: Session, limit: int = 20, offset: int = 0) -> List[Transaction]:
    """
    List recent transactions for a user, paginated by limit and offset.
    Raises an exception if the account does not exist.
    """
    account = get_account_by_user_id(user_id, session)
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
