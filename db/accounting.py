import enum
from sqlalchemy import (
    event,
    select,
    Column,
    Integer,
    String,
    Numeric,
    DateTime,
    Enum,
    ForeignKey,
    Boolean
)
from decimal import Decimal
from sqlalchemy.orm import relationship, validates, Mapped, mapped_column, sessionmaker
from typing import List
from .base import Base, Timestamped

class AccountType(enum.Enum):
    ASSET = "ASSET"
    LIABILITY = "LIABILITY"
    EQUITY = "EQUITY"
    INCOME = "INCOME"
    EXPENSE = "EXPENSE"

class AccountingAccount(Timestamped):
    __tablename__ = "chart_of_accounts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    type: Mapped[AccountType] = mapped_column(Enum(AccountType), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="USD")
    parent_id: Mapped[int] = mapped_column(Integer, ForeignKey("chart_of_accounts.id"), nullable=True)
    is_system_account: Mapped[bool] = mapped_column(Boolean, default=False)
    balance: Mapped[Decimal] = mapped_column(Numeric(20, 8), default=Decimal("0.0"))

    children = relationship("AccountingAccount", back_populates="parent")
    parent = relationship("AccountingAccount", remote_side=[id], back_populates="children")

class JournalEntry(Timestamped):
    __tablename__ = "journal_entries"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    description: Mapped[str] = mapped_column(String(255), nullable=False)

    ledger_transactions = relationship("LedgerTransaction", back_populates="journal_entry", cascade="all, delete-orphan")

@event.listens_for(JournalEntry, 'before_insert')
@event.listens_for(JournalEntry, 'before_update')
def validate_journal_entry_balance(mapper, connection, target):
    total_debits = sum(lt.debit for lt in target.ledger_transactions)
    total_credits = sum(lt.credit for lt in target.ledger_transactions)

    if total_debits != total_credits:
        raise ValueError("Debits and credits must be balanced.")


class LedgerTransaction(Timestamped):
    __tablename__ = "ledger_transactions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    journal_entry_id: Mapped[int] = mapped_column(Integer, ForeignKey("journal_entries.id"), nullable=False)
    account_id: Mapped[int] = mapped_column(Integer, ForeignKey("chart_of_accounts.id"), nullable=False)
    debit: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False, default=Decimal("0.0"))
    credit: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False, default=Decimal("0.0"))

    journal_entry = relationship("JournalEntry", back_populates="ledger_transactions")
    account = relationship("AccountingAccount")

@event.listens_for(LedgerTransaction, 'after_insert')
def receive_after_insert(mapper, connection, target):
    """
    Listen for new LedgerTransaction objects and update the corresponding Account balance atomically.
    """
    Session = sessionmaker(bind=connection)
    session = Session()
    try:
        account = session.query(AccountingAccount).filter(AccountingAccount.id == target.account_id).with_for_update().one()
        if account.type in (AccountType.ASSET, AccountType.EXPENSE):
            account.balance += target.debit - target.credit
        else:
            account.balance += target.credit - target.debit
        session.commit()
    finally:
        session.close()
