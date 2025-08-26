import enum
import datetime
from .base import Base, Timestamped
from .unified_amounts import UnifiedAmountMixin, UnifiedBalanceMixin
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
    Boolean,
    BigInteger
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

class TransactionType(enum.Enum):
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    SWAP = "swap"
    TRANSFER = "transfer"
    BUY_CRYPTO = "buy_crypto"
    SELL_CRYPTO = "sell_crypto"

class TransactionStatus(enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REVERSED = "reversed"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    PROCESSING = "processing"
    CANCELLED = "cancelled"

class PaymentProvider(enum.Enum):
    RELWORX = "relworx"
    MPESA = "mpesa"
    CRYPTO = "crypto"
    BANK = "bank"
    BLOCKBRITE = "blockbrite"
    VOUCHER = "voucher"
    MOBILE_MONEY = "mobile_money"
    BANK_DEPOSIT = "bank_deposit"

class PaymentMethod(enum.Enum):
    MOBILE_MONEY = "mobile_money"
    BANK_DEPOSIT = "bank_deposit"
    VOUCHER = "voucher"
    CRYPTO = "crypto"

class VoucherType(enum.Enum):
    UGX = "UGX"
    USD = "USD"

class VoucherStatus(enum.Enum):
    ACTIVE = "active"
    USED = "used"
    EXPIRED = "expired"
    CANCELLED = "cancelled"

class TradeType(enum.Enum):
    BUY = "buy"
    SELL = "sell"

class TradeStatus(enum.Enum):
    PENDING = "pending"
    PAYMENT_PENDING = "payment_pending"
    PAYMENT_RECEIVED = "payment_received"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"

class AccountType(enum.Enum):
    FIAT = "FIAT"
    CRYPTO = "CRYPTO"

class Account(Timestamped):
    __tablename__ = "accounts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Legacy balance columns (required by database schema)
    balance: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    locked_amount: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    
    # Legacy crypto amounts (kept for backward compatibility)
    crypto_balance_smallest_unit: Mapped[int | None] = mapped_column(Numeric(78, 0), nullable=True)
    crypto_locked_amount_smallest_unit: Mapped[int | None] = mapped_column(Numeric(78, 0), nullable=True)
    
    # Precision configuration for this account
    precision_config: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    
    # Currency field (matches database schema)
    currency: Mapped[str] = mapped_column(String(16), nullable=False)
    
    account_type: Mapped[AccountType] = mapped_column(Enum(AccountType, values_callable=lambda obj: [e.value for e in obj]), nullable=False, default=AccountType.FIAT)
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
    trades = relationship("Trade", back_populates="account")

    user = relationship("User", back_populates="accounts")
    
    def available_balance(self) -> float:
        """Get available balance (balance - locked_amount)"""
        return float(self.balance - self.locked_amount)
    
    def _convert_smallest_to_standard(self, smallest_units: int) -> float:
        """Convert smallest units to standard currency units"""
        from shared.currency_precision import AmountConverter
        if smallest_units is None:
            return 0.0
        try:
            return float(AmountConverter.from_smallest_units(smallest_units, self.currency))
        except Exception:
            # Fallback for unsupported currencies - assume 8 decimal places
            return float(smallest_units / 100_000_000)

class Voucher(Timestamped):
    """Voucher system for UGX and USD payments"""
    __tablename__ = "vouchers"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(16), unique=True, nullable=False, index=True)
    amount: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)  # UGX or USD
    voucher_type: Mapped[VoucherType] = mapped_column(Enum(VoucherType), nullable=False)
    status: Mapped[VoucherStatus] = mapped_column(Enum(VoucherStatus), nullable=False, default=VoucherStatus.ACTIVE)
    user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    used_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    expires_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    
    user = relationship("User")
    
    __table_args__ = (
        Index('idx_voucher_code_status', 'code', 'status'),
        Index('idx_voucher_user_status', 'user_id', 'status'),
    )

class Trade(Timestamped):
    """Crypto trading system with multiple payment methods"""
    __tablename__ = "trades"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Trade details
    trade_type: Mapped[TradeType] = mapped_column(Enum(TradeType, values_callable=lambda obj: [e.value for e in obj]), nullable=False)
    status: Mapped[TradeStatus] = mapped_column(Enum(TradeStatus, values_callable=lambda obj: [e.value for e in obj]), nullable=False, default=TradeStatus.PENDING)
    
    # User and account
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    account_id: Mapped[int] = mapped_column(Integer, ForeignKey("accounts.id"), nullable=False, index=True)
    
    # Crypto details
    crypto_currency: Mapped[str] = mapped_column(String(10), nullable=False)  # BTC, ETH, etc.
    crypto_amount: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)
    
    # Fiat details
    fiat_currency: Mapped[str] = mapped_column(String(3), nullable=False)  # UGX, USD, etc.
    fiat_amount: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    
    # Exchange rate and fees
    exchange_rate: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)
    fee_amount: Mapped[float] = mapped_column(Numeric(15, 2), nullable=True)
    fee_currency: Mapped[str] = mapped_column(String(3), nullable=True)
    
    # Unified amount fields for precision system
    crypto_amount_smallest_unit: Mapped[int | None] = mapped_column(Numeric(78, 0), nullable=True)
    fiat_amount_smallest_unit: Mapped[int | None] = mapped_column(Numeric(78, 0), nullable=True)
    fee_amount_smallest_unit: Mapped[int | None] = mapped_column(Numeric(78, 0), nullable=True)
    precision_config: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    
    # Payment method
    payment_method: Mapped[PaymentMethod] = mapped_column(Enum(PaymentMethod, values_callable=lambda obj: [e.value for e in obj]), nullable=False)
    payment_provider: Mapped[PaymentProvider | None] = mapped_column(Enum(PaymentProvider, values_callable=lambda obj: [e.value for e in obj]), nullable=True)
    
    # Payment details
    payment_reference: Mapped[str | None] = mapped_column(String(128), nullable=True)
    payment_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    payment_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    
    # Voucher details (if applicable)
    voucher_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("vouchers.id"), nullable=True)
    
    # Additional payment detail fields (now exist in database)
    mobile_money_provider: Mapped[str | None] = mapped_column(String(32), nullable=True)
    bank_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    account_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    account_number: Mapped[str | None] = mapped_column(String(32), nullable=True)
    deposit_reference: Mapped[str | None] = mapped_column(String(64), nullable=True)
    
    # Transaction references
    crypto_transaction_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("transactions.id"), nullable=True)
    fiat_transaction_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("transactions.id"), nullable=True)
    
    # Metadata
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    trade_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    
    # Timestamps
    payment_received_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    cancelled_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User")
    account = relationship("Account", back_populates="trades")
    voucher = relationship("Voucher")
    crypto_transaction = relationship("Transaction", foreign_keys=[crypto_transaction_id])
    fiat_transaction = relationship("Transaction", foreign_keys=[fiat_transaction_id])
    
    __table_args__ = (
        Index('idx_trade_user_status', 'user_id', 'status'),
        Index('idx_trade_type_status', 'trade_type', 'status'),
        Index('idx_trade_payment_method', 'payment_method', 'status'),
        Index('idx_trade_created_at', 'created_at'),
    )

class Transaction(Timestamped):
    __tablename__ = "transactions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(Integer, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    reference_id: Mapped[str] = mapped_column(String(64), nullable=True, index=True)
    
    # Legacy amount field (kept for backward compatibility)
    amount: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    
    # Unified amount field (currency comes from related account)
    amount_smallest_unit: Mapped[int] = mapped_column(Numeric(78, 0), nullable=False, default=0)
    
    # Legacy precision config (kept for backward compatibility)
    precision_config: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    
    type: Mapped[TransactionType] = mapped_column(Enum(TransactionType), nullable=False)
    status: Mapped[TransactionStatus] = mapped_column(Enum(TransactionStatus), nullable=False, default=TransactionStatus.PENDING)
    description: Mapped[str] = mapped_column(String(255), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=True)
    provider: Mapped[PaymentProvider | None] = mapped_column(Enum(PaymentProvider, values_callable=lambda obj: [e.value for e in obj]), nullable=True, doc="Payment provider for this transaction")
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
    # Trade reference
    trade_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("trades.id"), nullable=True)
    # Journal entry reference for accounting
    journal_entry_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    account = relationship(
        "Account",
        back_populates="transactions",
        foreign_keys=[account_id]
    )
    
    @property
    def currency(self):
        """Get currency from the related account"""
        return self.account.currency if self.account else None
    
    fee_account = relationship(
        "Account",
        foreign_keys=[fee_account_id]
    )
    trade = relationship("Trade", foreign_keys=[trade_id])

    __table_args__ = (
        Index("ix_transactions_account_reference_type", "account_id", "reference_id", "type"),
    )
    
    # Legacy compatibility methods
    def get_amount_smallest_unit(self) -> int:
        """Legacy method - now uses unified system"""
        return int(self.amount_smallest_unit or 0)
    
    def get_amount_standard(self) -> float:
        """Legacy method - now uses unified system"""
        return float(self.amount)

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

class LedgerEntry(Timestamped):
    """Ledger entries for all financial transactions (transfers, deposits, withdrawals)"""
    __tablename__ = "ledger_entries"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Transaction reference
    transaction_id: Mapped[int] = mapped_column(Integer, ForeignKey("transactions.id"), nullable=False, index=True)
    
    # User and account details
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    account_id: Mapped[int] = mapped_column(Integer, ForeignKey("accounts.id"), nullable=False, index=True)
    
    # Amount and currency
    amount: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)  # High precision for crypto
    amount_smallest_unit: Mapped[int | None] = mapped_column(Numeric(78, 0), nullable=True)
    currency: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    
    # Entry type and direction
    entry_type: Mapped[str] = mapped_column(String(32), nullable=False)  # 'debit', 'credit'
    transaction_type: Mapped[TransactionType] = mapped_column(Enum(TransactionType), nullable=False)
    
    # Balance tracking
    balance_before: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)
    balance_after: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)
    
    # Price recording for crypto events
    price_usd: Mapped[float | None] = mapped_column(Numeric(20, 8), nullable=True)
    price_timestamp: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    
    # Metadata
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reference_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    
    # Relationships
    transaction = relationship("Transaction", foreign_keys=[transaction_id])
    user = relationship("User")
    account = relationship("Account", foreign_keys=[account_id])
    
    __table_args__ = (
        Index('idx_ledger_user_currency_created', 'user_id', 'currency', 'created_at'),
        Index('idx_ledger_transaction_type', 'transaction_type', 'created_at'),
    )


class PortfolioSnapshot(Timestamped):
    """Portfolio snapshots for historical tracking and analysis"""
    __tablename__ = "portfolio_snapshots"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # User and snapshot details
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    snapshot_type: Mapped[str] = mapped_column(String(16), nullable=False)  # 'daily', 'weekly', 'monthly'
    snapshot_date: Mapped[datetime.date] = mapped_column(DateTime, nullable=False, index=True)
    
    # Portfolio totals
    total_value_usd: Mapped[float] = mapped_column(Numeric(20, 2), nullable=False)
    total_change_24h: Mapped[float] = mapped_column(Numeric(20, 2), nullable=True)
    total_change_7d: Mapped[float] = mapped_column(Numeric(20, 2), nullable=True)
    total_change_30d: Mapped[float] = mapped_column(Numeric(20, 2), nullable=True)
    
    # Change percentages
    change_percent_24h: Mapped[float] = mapped_column(Numeric(10, 4), nullable=True)
    change_percent_7d: Mapped[float] = mapped_column(Numeric(10, 4), nullable=True)
    change_percent_30d: Mapped[float] = mapped_column(Numeric(10, 4), nullable=True)
    
    # Metadata
    currency_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    asset_details: Mapped[dict] = mapped_column(JSON, nullable=True)  # Detailed breakdown by currency
    
    # Relationships
    user = relationship("User")
    
    __table_args__ = (
        UniqueConstraint('user_id', 'snapshot_type', 'snapshot_date', name='uq_portfolio_snapshot'),
        Index('idx_portfolio_user_type_date', 'user_id', 'snapshot_type', 'snapshot_date'),
    )


class CryptoPriceHistory(Timestamped):
    """Historical crypto prices for portfolio valuation"""
    __tablename__ = "crypto_price_history"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Price details
    currency: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    price_usd: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)
    
    # Source and timestamp
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="alchemy")  # 'alchemy', 'manual', etc.
    price_timestamp: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False, index=True)
    
    # Metadata
    volume_24h: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
    market_cap: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
    
    __table_args__ = (
        Index('idx_price_currency_timestamp', 'currency', 'price_timestamp'),
        Index('idx_price_timestamp', 'price_timestamp'),
    )
