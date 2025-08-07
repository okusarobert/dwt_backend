#!/usr/bin/env python3
import sys
import os
sys.path.append('/app')

from db.connection import session
from db.wallet import CryptoAddress, Account, AccountType
from shared.crypto.HD import BTC
from decouple import config
from db.utils import generate_unique_account_number

def create_btc_addresses_for_user(user_id):
    """Create BTC testnet addresses for a user"""

    btc_account = session.query(Account).filter_by(
        user_id=user_id,
        currency='BTC',
        account_type=AccountType.CRYPTO
    ).first()

    if not btc_account:
        print(f"Creating BTC account for user {user_id}")
        account_number = generate_unique_account_number(session, length=10)
        btc_account = Account(
            user_id=user_id,
            balance=0,
            locked_amount=0,
            currency='BTC',
            account_type=AccountType.CRYPTO,
            account_number=account_number,
            label='BTC Wallet'
        )
        session.add(btc_account)
        session.flush()
        print(f"Created BTC account with ID: {btc_account.id}")

    mnemonic = config('BTC_MNEMONIC', default=None)
    if not mnemonic:
        print("No BTC_MNEMONIC configured")
        return

    wallet = BTC()
    wallet = wallet.from_mnemonic(mnemonic=mnemonic)

    index = btc_account.id - 1
    address_gen, priv_key, pub_key = wallet.new_address(index=index)

    print(f"Generated BTC testnet address: {address_gen}")

    crypto_address = CryptoAddress(
        account_id=btc_account.id,
        address=address_gen,
        label='BTC',
        is_active=True,
        currency_code='BTC',
        address_type="hd_wallet"
    )

    session.add(crypto_address)
    session.commit()

    print(f"Successfully created BTC testnet address for user {user_id}")

if __name__ == "__main__":
    create_btc_addresses_for_user(16) 