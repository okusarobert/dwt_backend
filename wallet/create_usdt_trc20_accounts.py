#!/usr/bin/env python3
"""
Create USDT (TRC-20) accounts for existing users on TRON (parent_currency=TRX).

Usage:
  python wallet/create_usdt_trc20_accounts.py               # process all users with TRX accounts
  python wallet/create_usdt_trc20_accounts.py --user-id 123  # process a single user

Notes:
- Does NOT create new crypto addresses (TRC-20 uses the same TRX address).
- Skips users who already have a USDT account with precision_config.parent_currency == 'TRX'.
"""

import argparse
import sys
from typing import Optional

from db.connection import session
from db.wallet import Account, AccountType
from db.utils import generate_unique_account_number


USDT_SYMBOL = "USDT"
TRX_PARENT = "TRX"


def has_trx_account(user_id: int) -> bool:
    return (
        session.query(Account)
        .filter(
            Account.user_id == user_id,
            Account.account_type == AccountType.CRYPTO,
            Account.currency == TRX_PARENT,
        )
        .first()
        is not None
    )


def find_trc20_usdt_account(user_id: int) -> Optional[Account]:
    accounts = (
        session.query(Account)
        .filter(
            Account.user_id == user_id,
            Account.account_type == AccountType.CRYPTO,
            Account.currency == USDT_SYMBOL,
        )
        .all()
    )
    for acc in accounts:
        cfg = acc.precision_config or {}
        if str(cfg.get("parent_currency", "")).upper() == TRX_PARENT:
            return acc
    return None


def create_trc20_usdt_account(user_id: int) -> Optional[Account]:
    """Create a USDT TRC-20 account for the user if missing (parent_currency=TRX)."""
    # Verify parent TRX account exists
    if not has_trx_account(user_id):
        print(f"[skip] User {user_id} has no TRX account")
        return None

    existing = find_trc20_usdt_account(user_id)
    if existing:
        print(f"[exists] User {user_id} already has USDT (TRX) account id={existing.id}")
        return existing

    try:
        account = Account(
            user_id=user_id,
            balance=0,
            locked_amount=0,
            currency=USDT_SYMBOL,
            account_type=AccountType.CRYPTO,
            account_number=generate_unique_account_number(session=session, length=10),
            label="USDT Account (TRX)",
            precision_config={
                "currency": USDT_SYMBOL,
                "decimals": 6,
                "smallest_unit": "units",
                "parent_currency": TRX_PARENT,
            },
        )
        session.add(account)
        session.commit()
        session.refresh(account)
        print(f"[created] User {user_id} USDT (TRX) account id={account.id}")
        return account
    except Exception as e:
        session.rollback()
        print(f"[error] Failed to create USDT (TRX) account for user {user_id}: {e}")
        return None


def process_all_users(target_user_id: Optional[int] = None) -> None:
    if target_user_id is not None:
        create_trc20_usdt_account(target_user_id)
        return

    # Process all users who have a TRX account
    users_with_trx = (
        session.query(Account.user_id)
        .filter(
            Account.account_type == AccountType.CRYPTO,
            Account.currency == TRX_PARENT,
        )
        .distinct()
        .all()
    )

    count_created = 0
    for (user_id,) in users_with_trx:
        acc = create_trc20_usdt_account(user_id)
        if acc is not None:
            count_created += 1

    print(f"Done. Created/verified USDT (TRX) accounts for {len(users_with_trx)} user(s); newly created: {count_created}")


def main():
    parser = argparse.ArgumentParser(description="Create USDT (TRC-20) accounts for existing users on TRX")
    parser.add_argument("--user-id", type=int, default=None, help="Process a single user ID")
    args = parser.parse_args()
    process_all_users(args.user_id)


if __name__ == "__main__":
    main()


