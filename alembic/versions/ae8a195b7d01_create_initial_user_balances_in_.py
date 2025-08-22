"""Create initial user balances in accounting ledger

Revision ID: ae8a195b7d01
Revises: bbb8006cdaf5
Create Date: 2025-08-15 14:21:10.353675

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'ae8a195b7d01'
down_revision: Union[str, None] = 'd7d7cd31ffa4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    
    # Commit any pending enum changes first
    bind.commit()
    
    meta = sa.MetaData()
    meta.reflect(bind=bind)

    wallet_accounts = sa.Table('accounts', meta)
    accounting_accounts = sa.Table('chart_of_accounts', meta)
    journal_entries = sa.Table('journal_entries', meta)
    ledger_transactions = sa.Table('ledger_transactions', meta)

    # Create a root equity account for user balances
    equity_account_name = 'User Equity'
    equity_account_result = bind.execute(
        sa.select(accounting_accounts).where(accounting_accounts.c.name == equity_account_name)
    ).first()

    if equity_account_result:
        equity_account_id = equity_account_result.id
    else:
        insert_equity_account = bind.execute(
            accounting_accounts.insert().values(
                name=equity_account_name,
                type='EQUITY',
                currency='USD',  # Assuming a base currency, can be adjusted
                is_system_account=True
            ).returning(accounting_accounts.c.id)
        )
        equity_account_id = insert_equity_account.scalar_one()

    # Fetch all wallet accounts
    wallet_accounts_to_migrate = bind.execute(sa.select(wallet_accounts)).fetchall()

    for wallet_account in wallet_accounts_to_migrate:
        # Create a corresponding asset account in the accounting system
        asset_account_name = f'User {wallet_account.user_id} - {wallet_account.currency} Wallet'
        asset_account_result = bind.execute(
            sa.select(accounting_accounts).where(accounting_accounts.c.name == asset_account_name)
        ).first()

        if not asset_account_result:
            insert_asset_account = bind.execute(
                accounting_accounts.insert().values(
                    name=asset_account_name,
                    type='ASSET',
                    currency=wallet_account.currency,
                    is_system_account=False
                ).returning(accounting_accounts.c.id)
            )
            asset_account_id = insert_asset_account.scalar_one()

            # Create a journal entry for the initial balance
            journal_entry_id = bind.execute(
                journal_entries.insert().values(
                    description=f'Initial balance migration for user {wallet_account.user_id} - {wallet_account.currency}'
                ).returning(journal_entries.c.id)
            ).scalar_one()

            # Debit the asset account
            bind.execute(
                ledger_transactions.insert().values(
                    journal_entry_id=journal_entry_id,
                    account_id=asset_account_id,
                    debit=wallet_account.balance,
                    credit=0
                )
            )

            # Credit the equity account
            bind.execute(
                ledger_transactions.insert().values(
                    journal_entry_id=journal_entry_id,
                    account_id=equity_account_id,
                    debit=0,
                    credit=wallet_account.balance
                )
            )


def downgrade() -> None:
    bind = op.get_bind()
    meta = sa.MetaData()
    meta.reflect(bind=bind)

    journal_entries = sa.Table('journal_entries', meta)
    ledger_transactions = sa.Table('ledger_transactions', meta)
    accounting_accounts = sa.Table('chart_of_accounts', meta)

    # Find and delete the journal entries, ledger transactions, and accounts created in the upgrade
    journal_entries_to_delete = bind.execute(
        sa.select(journal_entries.c.id).where(journal_entries.c.description.like('Initial balance migration for user %'))
    ).fetchall()

    if journal_entries_to_delete:
        journal_entry_ids = [entry.id for entry in journal_entries_to_delete]
        
        # Get account_ids from ledger_transactions before deleting them
        accounts_to_delete = bind.execute(
            sa.select(ledger_transactions.c.account_id)
            .where(ledger_transactions.c.journal_entry_id.in_(journal_entry_ids))
            .distinct()
        ).fetchall()
        account_ids_to_delete = [acc.account_id for acc in accounts_to_delete]

        bind.execute(
            ledger_transactions.delete().where(ledger_transactions.c.journal_entry_id.in_(journal_entry_ids))
        )
        bind.execute(
            journal_entries.delete().where(journal_entries.c.id.in_(journal_entry_ids))
        )
        
        # Delete the created asset accounts, but not the equity account
        equity_account_name = 'User Equity'
        equity_account_id_result = bind.execute(
            sa.select(accounting_accounts.c.id).where(accounting_accounts.c.name == equity_account_name)
        ).scalar_one_or_none()
        
        if equity_account_id_result:
            account_ids_to_delete = [acc_id for acc_id in account_ids_to_delete if acc_id != equity_account_id_result]

        if account_ids_to_delete:
            bind.execute(
                accounting_accounts.delete().where(accounting_accounts.c.id.in_(account_ids_to_delete))
            )

    # Finally, delete the root equity account if it's otherwise unused
    op.execute("DELETE FROM chart_of_accounts WHERE name = 'User Equity' AND NOT EXISTS (SELECT 1 FROM ledger_transactions WHERE account_id = chart_of_accounts.id)")

