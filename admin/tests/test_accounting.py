import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from decimal import Decimal

from db.base import Base
from db.accounting import AccountingAccount, AccountType, JournalEntry, LedgerTransaction

@pytest.fixture(scope="module")
def engine():
    return create_engine("sqlite:///:memory:")

@pytest.fixture(scope="module")
def tables(engine):
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)

@pytest.fixture(scope="function")
def db_session(engine, tables):
    connection = engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection)
    session = Session()
    yield session
    session.close()
    transaction.rollback()
    connection.close()

def test_balanced_journal_entry(db_session):
    # Setup accounts
    cash_account = AccountingAccount(name="Cash", type=AccountType.ASSET, currency="USD", balance=Decimal('1000.00'))
    revenue_account = AccountingAccount(name="Revenue", type=AccountType.INCOME, currency="USD", balance=Decimal('0.00'))
    db_session.add_all([cash_account, revenue_account])
    db_session.commit()

    # Create journal entry
    journal_entry = JournalEntry(description="Test Sale")
    journal_entry.ledger_transactions.append(
        LedgerTransaction(account_id=cash_account.id, debit=Decimal('100.00'), credit=Decimal('0.00'))
    )
    journal_entry.ledger_transactions.append(
        LedgerTransaction(account_id=revenue_account.id, debit=Decimal('0.00'), credit=Decimal('100.00'))
    )

    db_session.add(journal_entry)
    db_session.commit()

    # Verify balances
    assert cash_account.balance == Decimal('1100.00')
    assert revenue_account.balance == Decimal('100.00')

def test_unbalanced_journal_entry(db_session):
    cash_account = AccountingAccount(name="Cash", type=AccountType.ASSET, currency="USD")
    db_session.add(cash_account)
    db_session.commit()

    journal_entry = JournalEntry(description="Unbalanced Entry")
    journal_entry.ledger_transactions.append(
        LedgerTransaction(account_id=cash_account.id, debit=Decimal('100.00'), credit=Decimal('0.00'))
    )
    journal_entry.ledger_transactions.append(
        LedgerTransaction(account_id=cash_account.id, debit=Decimal('0.00'), credit=Decimal('50.00')) # Unbalanced
    )

    with pytest.raises(ValueError, match="Debits and credits must be balanced."):
        db_session.add(journal_entry)
        db_session.commit()

def test_atomic_balance_updates(db_session):
    asset_account = AccountingAccount(name="Accounts Receivable", type=AccountType.ASSET, currency="USD", balance=Decimal('0.00'))
    liability_account = AccountingAccount(name="Accounts Payable", type=AccountType.LIABILITY, currency="USD", balance=Decimal('0.00'))
    expense_account = AccountingAccount(name="Office Supplies", type=AccountType.EXPENSE, currency="USD", balance=Decimal('0.00'))
    income_account = AccountingAccount(name="Sales Revenue", type=AccountType.INCOME, currency="USD", balance=Decimal('0.00'))
    equity_account = AccountingAccount(name="Owner's Equity", type=AccountType.EQUITY, currency="USD", balance=Decimal('1000.00'))
    cash_account = AccountingAccount(name="Cash", type=AccountType.ASSET, currency="USD", balance=Decimal('1000.00'))
    db_session.add_all([asset_account, liability_account, expense_account, income_account, equity_account, cash_account])
    db_session.commit()

    # Test Asset/Expense account logic (Debit increases balance)
    # Correctly balanced entry
    journal_entry = JournalEntry(description="Asset and Expense Test Balanced")
    journal_entry.ledger_transactions.append(LedgerTransaction(account_id=asset_account.id, debit=Decimal('200.00'), credit=Decimal('0.00'))) 
    journal_entry.ledger_transactions.append(LedgerTransaction(account_id=cash_account.id, debit=Decimal('0.00'), credit=Decimal('200.00'))) 
    db_session.add(journal_entry)
    db_session.commit()

    assert asset_account.balance == Decimal('200.00')
    assert cash_account.balance == Decimal('800.00')

    # Test Liability/Income/Equity account logic (Credit increases balance)
    journal_entry2 = JournalEntry(description="Liability, Income, and Equity Test")
    journal_entry2.ledger_transactions.append(LedgerTransaction(account_id=liability_account.id, debit=Decimal('0.00'), credit=Decimal('300'))) 
    journal_entry2.ledger_transactions.append(LedgerTransaction(account_id=income_account.id, debit=Decimal('0.00'), credit=Decimal('150'))) 
    journal_entry2.ledger_transactions.append(LedgerTransaction(account_id=equity_account.id, debit=Decimal('0.00'), credit=Decimal('500'))) 
    journal_entry2.ledger_transactions.append(LedgerTransaction(account_id=cash_account.id, debit=Decimal('950'), credit=Decimal('0.00'))) 
    db_session.add(journal_entry2)
    db_session.commit()
    assert liability_account.balance == Decimal('300.00')
    assert income_account.balance == Decimal('150.00')
    assert equity_account.balance == Decimal('1500.00')
    assert cash_account.balance == Decimal('1750.00')
