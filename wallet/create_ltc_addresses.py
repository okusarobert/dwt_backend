#!/usr/bin/env python3
import sys
import os
sys.path.append('/app')

from db.connection import session
from db.wallet import CryptoAddress, Account, AccountType
from shared.crypto.HD import LTC
from decouple import config
from db.utils import generate_unique_account_number

def create_ltc_addresses_for_user(user_id):
    """Create LTC testnet addresses for a user"""
    
    # Get LTC account for the user
    ltc_account = session.query(Account).filter_by(
        user_id=user_id,
        currency='LTC',
        account_type=AccountType.CRYPTO
    ).first()
    
    if not ltc_account:
        print(f"Creating LTC account for user {user_id}")
        # Create LTC account
        account_number = generate_unique_account_number(session, length=10)
        ltc_account = Account(
            user_id=user_id,
            balance=0,
            locked_amount=0,
            currency='LTC',
            account_type=AccountType.CRYPTO,
            account_number=account_number,
            label='LTC Wallet'
        )
        session.add(ltc_account)
        session.flush()  # Get the ID without committing
        print(f"Created LTC account with ID: {ltc_account.id}")
    
    # Get mnemonic
    mnemonic = config('LTC_MNEMONIC', default=None)
    if not mnemonic:
        print("No LTC_MNEMONIC configured")
        return
    
    # Create wallet and generate address
    wallet = LTC()
    wallet = wallet.from_mnemonic(mnemonic=mnemonic)
    
    # Generate new address
    index = ltc_account.id - 1
    address_gen, priv_key, pub_key = wallet.new_address(index=index)
    
    print(f"Generated LTC testnet address: {address_gen}")
    
    # Create crypto address record
    crypto_address = CryptoAddress(
        account_id=ltc_account.id,
        address=address_gen,
        label='LTC',
        is_active=True,
        currency_code='LTC',
        address_type="hd_wallet"
    )
    
    session.add(crypto_address)
    session.commit()
    
    print(f"Successfully created LTC testnet address for user {user_id}")

if __name__ == "__main__":
    create_ltc_addresses_for_user(15) 