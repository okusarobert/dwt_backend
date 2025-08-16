#!/usr/bin/env python3
"""
Create ERC-20 token accounts (USDT, USDC) for Ethereum for existing users.

Behavior
- For every user that has an ETH `Account` (CRYPTO), create missing token `Account`s
  for USDT and USDC with `precision_config.parent_currency='ETH'`.
- Idempotent: skips if the token account already exists for the user.
- Does NOT create new `CryptoAddress` rows (tokens reuse the user's ETH address).

Usage
- All users with ETH accounts:
    python wallet/create_eth_erc20_accounts.py
- Single user:
    python wallet/create_eth_erc20_accounts.py --user-id 123
"""

from __future__ import annotations

import argparse
from typing import Iterable, Optional

from db.connection import session
from db.wallet import Account, AccountType
from db.utils import generate_unique_account_number


TOKENS = [
    {"symbol": "USDT", "decimals": 6},
    {"symbol": "USDC", "decimals": 6},
]


def get_eth_user_ids(target_user_id: Optional[int] = None) -> Iterable[int]:
    """Return user_id(s) that have at least one ETH CRYPTO account."""
    query = session.query(Account.user_id).filter(
        Account.account_type == AccountType.CRYPTO,
        Account.currency == "ETH",
    )
    if target_user_id is not None:
        query = query.filter(Account.user_id == target_user_id)
    # Distinct user_ids
    return {row.user_id for row in query.all()}


def token_account_exists(user_id: int, symbol: str) -> bool:
    """Check if the user already has the token account on ETH parent chain."""
    existing = (
        session.query(Account)
        .filter(
            Account.user_id == user_id,
            Account.account_type == AccountType.CRYPTO,
            Account.currency == symbol.upper(),
        )
        .all()
    )
    for acc in existing:
        cfg = acc.precision_config or {}
        if str(cfg.get("parent_currency", "")).upper() == "ETH":
            return True
    return False


def create_token_account(user_id: int, symbol: str, decimals: int) -> Optional[int]:
    """Create a token Account row for the user. Returns new account id or None."""
    try:
        account = Account(
            user_id=user_id,
            balance=0,
            locked_amount=0,
            currency=symbol.upper(),
            account_type=AccountType.CRYPTO,
            account_number=generate_unique_account_number(session=session, length=10),
            label=f"{symbol.upper()} Account",
            precision_config={
                "currency": symbol.upper(),
                "decimals": int(decimals),
                "smallest_unit": "units",
                "parent_currency": "ETH",
            },
        )
        session.add(account)
        session.commit()
        session.refresh(account)
        print(f"[OK] Created {symbol.upper()} account (id={account.id}) for user {user_id}")
        return account.id
    except Exception as e:
        session.rollback()
        print(f"[ERR] Failed to create {symbol.upper()} account for user {user_id}: {e}")
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Create USDT/USDC ERC-20 accounts for Ethereum")
    parser.add_argument("--user-id", type=int, help="Process only this user id", default=None)
    args = parser.parse_args()

    target_users = get_eth_user_ids(args.user_id)
    if not target_users:
        print("No users with ETH accounts found for the given filter.")
        return

    created = 0
    skipped = 0
    for uid in sorted(target_users):
        for tok in TOKENS:
            symbol = tok["symbol"].upper()
            decimals = int(tok["decimals"])  # type: ignore[arg-type]
            if token_account_exists(uid, symbol):
                print(f"[SKIP] {symbol} account already exists for user {uid}")
                skipped += 1
                continue
            if create_token_account(uid, symbol, decimals):
                created += 1

    print(f"Done. Created={created}, Skipped={skipped}")


if __name__ == "__main__":
    main()


