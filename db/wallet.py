import enum
import datetime
from .base import Base, Timestamped
from sqlalchemy import (
    Column,
    Integer,
    String,
    Numeric,
    DateTime,
    Enum,
    ForeignKey,
    JSON,
    Float,
    UniqueConstraint,
    Index,
    Boolean
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

class TransactionType(enum.Enum):
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    SWAP = "swap"
    TRANSFER = "transfer"

class TransactionStatus(enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REVERSED = "reversed"
    AWAITING_CONFIRMATION = "awaiting_confirmation"  # new status for crypto

class PaymentProvider(enum.Enum):
    RELWORX = "relworx"
    MPESA = "mpesa"
    CRYPTO  = "crypto"
    BANK = "bank"
    BLOCKBRITE = "blockbrite"
    # Add more providers as needed

class AccountType(enum.Enum):
    FIAT = "FIAT"
    CRYPTO = "CRYPTO"

class Account(Timestamped):
    __tablename__ = "accounts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    balance: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    locked_amount: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    # currency_id = Column(Integer, ForeignKey("currencies.id"), nullable=True, index=True)
    currency: Mapped[str | None] = mapped_column(String(16), nullable=True, index=True)  # replaced by currency_id
    account_type: Mapped[AccountType] = mapped_column(Enum(AccountType), nullable=False, default=AccountType.FIAT)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey(
        "users.id", ondelete="CASCADE"), nullable=False, index=True)
    account_number: Mapped[str] = mapped_column(String(10), unique=True, index=True, nullable=False)
    label: Mapped[str | None] = mapped_column(String(32), index=True, nullable=True)

    transactions = relationship(
        "Transaction",
        back_populates="account",
        cascade="all, delete-orphan",
        foreign_keys="[Transaction.account_id]"
    )
    crypto_addresses = relationship(
        "CryptoAddress", back_populates="account", cascade="all, delete-orphan"
    )

    user = relationship("User", back_populates="accounts")
    def available_balance(self) -> float:
        return float(self.balance) - float(self.locked_amount)

    # __table_args__ = (
    #     UniqueConstraint('user_id', 'currency_id', name='uq_accounts_user_currency'),
    # )

class Transaction(Timestamped):
    __tablename__ = "transactions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(Integer, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    reference_id: Mapped[str] = mapped_column(String(64), nullable=True, index=True)
    amount: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    type: Mapped[TransactionType] = mapped_column(Enum(TransactionType), nullable=False)
    status: Mapped[TransactionStatus] = mapped_column(Enum(TransactionStatus), nullable=False, default=TransactionStatus.PENDING)
    description: Mapped[str] = mapped_column(String(255), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=True)
    provider: Mapped[PaymentProvider | None] = mapped_column(Enum(PaymentProvider), nullable=True, doc="Payment provider for this transaction")
    provider_reference: Mapped[str | None] = mapped_column(String(128), nullable=True, doc="Provider's transaction/reference ID")
    # Crypto-specific fields
    blockchain_txid = Column(String(128), nullable=True, index=True)
    confirmations = Column(Integer, nullable=True)
    required_confirmations = Column(Integer, nullable=True, default=3)
    address = Column(String(128), nullable=True)  # crypto address involved
    # Fee support
    fee_amount = Column(Numeric(15, 8), nullable=True)
    fee_currency_id = Column(Integer, ForeignKey("currencies.id"), nullable=True)
    fee_account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True)
    # created_at: Mapped[datetime.datetime] = mapped_column(DateTime, index=True, nullable=False)

    account = relationship(
        "Account",
        back_populates="transactions",
        foreign_keys=[account_id]
    )
    fee_account = relationship(
        "Account",
        foreign_keys=[fee_account_id]
    )

    __table_args__ = (
        Index("ix_transactions_account_reference_type", "account_id", "reference_id", "type"),
    )

class Swap(Timestamped):
    __tablename__ = "swaps"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    from_account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    to_account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    from_amount = Column(Numeric(20, 8), nullable=False)
    to_amount = Column(Numeric(20, 8), nullable=False)
    rate = Column(Float, nullable=False)
    fee_amount = Column(Numeric(20, 8), nullable=True)
    fee_currency_id = Column(Integer, ForeignKey("currencies.id"), nullable=True)
    status = Column(String(16), default="pending")
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=True)
    # Add relationships as needed

class ReservationType(enum.Enum):
    RESERVE = "reserve"
    RELEASE = "release"

class Reservation(Timestamped):
    __tablename__ = "reservations"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False, index=True)
    reference = Column(String(64), nullable=False)
    amount = Column(Float, nullable=False)
    type = Column(Enum(ReservationType), nullable=False)
    status = Column(String(16), nullable=False)
    # created_at = Column(DateTime, default=datetime.datetime.utcnow)

    __table_args__ = (UniqueConstraint('user_id', 'reference', 'type', name='_user_ref_type_uc'),)

class CryptoAddress(Timestamped):
    __tablename__ = "crypto_addresses"
    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True)
    address = Column(String(128), nullable=False, unique=True)
    label = Column(String(64), nullable=True)
    is_active = Column(Boolean, default=True)
    memo = Column(String(256), nullable=True)  # For coins like XRP/XLM
    address_type = Column(String(32), nullable=True)  # e.g., 'legacy', 'segwit', 'erc20', etc.
    version = Column(String(16), nullable=True)  # For versioning address formats
    # currency_id = Column(Integer, ForeignKey("currencies.id"), nullable=True)  # Uncomment when Currency model is added
    currency_code = Column(String(120), nullable=False)
    private_key = Column(String(256), nullable=True)
    public_key = Column(String(256), nullable=True)
    webhook_ids = Column(JSON, nullable=True)  # BlockCypher webhook subscription IDs as JSON array

    account = relationship("Account", back_populates="crypto_addresses")
    __table_args__ = (UniqueConstraint('account_id', 'address', name='uq_account_address'),)
