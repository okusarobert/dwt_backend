"""
Trading Accounting Integration Module

This module provides functions to create proper double-entry journal entries
for all trading operations, ensuring full integration with the accounting system.
"""

from decimal import Decimal
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from db.accounting import AccountingAccount, JournalEntry, LedgerTransaction, AccountType
from shared.currency_precision import AmountConverter
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class TradingAccountingService:
    """Service for creating accounting entries for trading operations"""
    
    def __init__(self, session: Session):
        self.session = session
        self._account_cache = {}
    
    def get_account_by_name(self, name: str) -> Optional[AccountingAccount]:
        """Get accounting account by name with caching"""
        if name not in self._account_cache:
            account = self.session.query(AccountingAccount).filter(
                AccountingAccount.name == name
            ).first()
            self._account_cache[name] = account
        return self._account_cache[name]
    
    def create_buy_trade_journal_entry(
        self,
        trade_id: int,
        user_id: int,
        crypto_currency: str,
        crypto_amount_smallest_unit: int,
        fiat_currency: str,
        fiat_amount_smallest_unit: int,
        fee_amount_smallest_unit: int,
        fee_currency: str
    ) -> JournalEntry:
        """
        Create journal entry for a crypto buy trade.
        
        For a BUY trade:
        - Debit: Crypto Asset Account (increase crypto holdings)
        - Debit: Trading Fee Expense (record fee as expense)
        - Credit: Cash/Fiat Account (decrease fiat balance)
        """
        
        # Get required accounts
        crypto_account = self.get_account_by_name(f"Crypto Assets - {crypto_currency}")
        fiat_account = self.get_account_by_name(f"Cash - {fiat_currency}")
        fee_expense_account = self.get_account_by_name("Trading Expenses")
        
        if not all([crypto_account, fiat_account, fee_expense_account]):
            raise ValueError("Required trading accounts not found in chart of accounts")
        
        # Convert amounts for description
        crypto_display = AmountConverter.format_display_amount(crypto_amount_smallest_unit, crypto_currency)
        fiat_display = AmountConverter.format_display_amount(fiat_amount_smallest_unit, fiat_currency)
        
        # Create journal entry
        journal_entry = JournalEntry(
            description=f"Buy {crypto_display} for {fiat_display} (Trade #{trade_id})"
        )
        self.session.add(journal_entry)
        self.session.flush()  # Get the ID
        
        # Create ledger transactions using smallest units
        ledger_transactions = [
            # Debit crypto asset account (increase crypto holdings)
            LedgerTransaction(
                journal_entry_id=journal_entry.id,
                account_id=crypto_account.id,
                debit_smallest_unit=crypto_amount_smallest_unit,
                credit_smallest_unit=0
            ),
            # Debit trading fee expense
            LedgerTransaction(
                journal_entry_id=journal_entry.id,
                account_id=fee_expense_account.id,
                debit_smallest_unit=fee_amount_smallest_unit,
                credit_smallest_unit=0
            ),
            # Credit fiat account (decrease fiat balance)
            LedgerTransaction(
                journal_entry_id=journal_entry.id,
                account_id=fiat_account.id,
                debit_smallest_unit=0,
                credit_smallest_unit=fiat_amount_smallest_unit + fee_amount_smallest_unit
            )
        ]
        
        for lt in ledger_transactions:
            self.session.add(lt)
        
        journal_entry.ledger_transactions = ledger_transactions
        return journal_entry
    
    def create_sell_trade_journal_entry(
        self,
        trade_id: int,
        user_id: int,
        crypto_currency: str,
        crypto_amount_smallest_unit: int,
        fiat_currency: str,
        fiat_amount_smallest_unit: int,
        fee_amount_smallest_unit: int,
        fee_currency: str
    ) -> JournalEntry:
        """
        Create journal entry for a crypto sell trade.
        
        For a SELL trade:
        - Debit: Cash/Fiat Account (increase fiat balance)
        - Debit: Trading Fee Expense (record fee as expense)
        - Credit: Crypto Asset Account (decrease crypto holdings)
        """
        
        # Get required accounts
        crypto_account = self.get_account_by_name(f"Crypto Assets - {crypto_currency}")
        fiat_account = self.get_account_by_name(f"Cash - {fiat_currency}")
        fee_expense_account = self.get_account_by_name("Trading Expenses")
        
        if not all([crypto_account, fiat_account, fee_expense_account]):
            raise ValueError("Required trading accounts not found in chart of accounts")
        
        # Convert amounts for description
        crypto_display = AmountConverter.format_display_amount(crypto_amount_smallest_unit, crypto_currency)
        fiat_display = AmountConverter.format_display_amount(fiat_amount_smallest_unit, fiat_currency)
        
        # Create journal entry
        journal_entry = JournalEntry(
            description=f"Sell {crypto_display} for {fiat_display} (Trade #{trade_id})"
        )
        self.session.add(journal_entry)
        self.session.flush()  # Get the ID
        
        # Create ledger transactions using smallest units
        ledger_transactions = [
            # Debit fiat account (increase fiat balance)
            LedgerTransaction(
                journal_entry_id=journal_entry.id,
                account_id=fiat_account.id,
                debit_smallest_unit=fiat_amount_smallest_unit - fee_amount_smallest_unit,
                credit_smallest_unit=0
            ),
            # Debit trading fee expense
            LedgerTransaction(
                journal_entry_id=journal_entry.id,
                account_id=fee_expense_account.id,
                debit_smallest_unit=fee_amount_smallest_unit,
                credit_smallest_unit=0
            ),
            # Credit crypto asset account (decrease crypto holdings)
            LedgerTransaction(
                journal_entry_id=journal_entry.id,
                account_id=crypto_account.id,
                debit_smallest_unit=0,
                credit_smallest_unit=crypto_amount_smallest_unit
            )
        ]
        
        for lt in ledger_transactions:
            self.session.add(lt)
        
        journal_entry.ledger_transactions = ledger_transactions
        return journal_entry
    
    def create_trade_fee_revenue_entry(
        self,
        trade_id: int,
        fee_amount_smallest_unit: int,
        fee_currency: str
    ) -> JournalEntry:
        """
        Create journal entry for trading fee revenue (platform's perspective).
        
        - Debit: Cash Account (increase platform's cash)
        - Credit: Trading Fee Revenue (record revenue)
        """
        
        cash_account = self.get_account_by_name(f"Cash - {fee_currency}")
        revenue_account = self.get_account_by_name("Trading Fee Revenue")
        
        if not all([cash_account, revenue_account]):
            raise ValueError("Required revenue accounts not found")
        
        fee_display = AmountConverter.format_display_amount(fee_amount_smallest_unit, fee_currency)
        
        journal_entry = JournalEntry(
            description=f"Trading fee revenue from Trade #{trade_id}: {fee_display}"
        )
        self.session.add(journal_entry)
        self.session.flush()
        
        ledger_transactions = [
            # Debit cash account (platform receives fee)
            LedgerTransaction(
                journal_entry_id=journal_entry.id,
                account_id=cash_account.id,
                debit_smallest_unit=fee_amount_smallest_unit,
                credit_smallest_unit=0
            ),
            # Credit revenue account
            LedgerTransaction(
                journal_entry_id=journal_entry.id,
                account_id=revenue_account.id,
                debit_smallest_unit=0,
                credit_smallest_unit=fee_amount_smallest_unit
            )
        ]
        
        for lt in ledger_transactions:
            self.session.add(lt)
        
        journal_entry.ledger_transactions = ledger_transactions
        return journal_entry
    
    def process_trade_accounting(
        self,
        trade_data: Dict
    ) -> List[JournalEntry]:
        """
        Process all accounting entries for a completed trade.
        Returns list of created journal entries.
        """
        
        journal_entries = []
        
        # Create main trade entry
        if trade_data['trade_type'] == 'buy':
            main_entry = self.create_buy_trade_journal_entry(
                trade_id=trade_data['id'],
                user_id=trade_data['user_id'],
                crypto_currency=trade_data['crypto_currency'],
                crypto_amount=trade_data['crypto_amount'],
                fiat_currency=trade_data['fiat_currency'],
                fiat_amount=trade_data['fiat_amount'],
                fee_amount=trade_data['fee_amount'],
                fee_currency=trade_data['fee_currency']
            )
        else:  # sell
            main_entry = self.create_sell_trade_journal_entry(
                trade_id=trade_data['id'],
                user_id=trade_data['user_id'],
                crypto_currency=trade_data['crypto_currency'],
                crypto_amount=trade_data['crypto_amount'],
                fiat_currency=trade_data['fiat_currency'],
                fiat_amount=trade_data['fiat_amount'],
                fee_amount=trade_data['fee_amount'],
                fee_currency=trade_data['fee_currency']
            )
        
        journal_entries.append(main_entry)
        
        # Create fee revenue entry (platform's perspective)
        if trade_data['fee_amount'] > 0:
            fee_entry = self.create_trade_fee_revenue_entry(
                trade_id=trade_data['id'],
                fee_amount=trade_data['fee_amount'],
                fee_currency=trade_data['fee_currency']
            )
            journal_entries.append(fee_entry)
        
        return journal_entries


def update_trade_with_accounting(session: Session, trade_id: int, journal_entry_id: int):
    """Update trade record with accounting information"""
    
    session.execute(
        """
        UPDATE trades 
        SET journal_entry_id = :journal_entry_id,
            accounting_processed = true,
            accounting_processed_at = NOW()
        WHERE id = :trade_id
        """,
        {'journal_entry_id': journal_entry_id, 'trade_id': trade_id}
    )


def get_trade_accounting_summary(session: Session, trade_id: int) -> Dict:
    """Get accounting summary for a specific trade"""
    
    result = session.execute(
        """
        SELECT 
            t.id,
            t.trade_type,
            t.crypto_currency,
            t.crypto_amount,
            t.fiat_currency,
            t.fiat_amount,
            t.fee_amount,
            t.accounting_processed,
            je.id as journal_entry_id,
            je.description as journal_description
        FROM trades t
        LEFT JOIN journal_entries je ON t.journal_entry_id = je.id
        WHERE t.id = :trade_id
        """,
        {'trade_id': trade_id}
    ).fetchone()
    
    if result:
        return {
            'trade_id': result.id,
            'trade_type': result.trade_type,
            'crypto_currency': result.crypto_currency,
            'crypto_amount': result.crypto_amount,
            'fiat_currency': result.fiat_currency,
            'fiat_amount': result.fiat_amount,
            'fee_amount': result.fee_amount,
            'accounting_processed': result.accounting_processed,
            'journal_entry_id': result.journal_entry_id,
            'journal_description': result.journal_description
        }
    
    return None
