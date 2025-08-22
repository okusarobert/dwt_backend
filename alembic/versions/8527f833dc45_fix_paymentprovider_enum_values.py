"""fix_paymentprovider_enum_values

Revision ID: 8527f833dc45
Revises: 3681d240347a
Create Date: 2025-08-18 16:26:48.910343

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8527f833dc45'
down_revision: Union[str, None] = '3681d240347a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop and recreate the paymentprovider enum to ensure clean mapping
    # Handle all tables that use the paymentprovider enum with safe column checks
    
    # Check if columns exist before trying to manipulate them
    connection = op.get_bind()
    
    # Check if payment_provider column exists in trades table
    trades_has_payment_provider = connection.execute("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'trades' AND column_name = 'payment_provider'
        );
    """).scalar()
    
    # Check if provider column exists in transactions table
    transactions_has_provider = connection.execute("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'transactions' AND column_name = 'provider'
        );
    """).scalar()
    
    # 1. Handle trades table if column exists
    if trades_has_payment_provider:
        op.execute("ALTER TABLE trades ADD COLUMN payment_provider_temp VARCHAR(32);")
        op.execute("UPDATE trades SET payment_provider_temp = payment_provider::text;")
        op.execute("ALTER TABLE trades DROP COLUMN payment_provider;")
    
    # 2. Handle transactions table if column exists
    if transactions_has_provider:
        op.execute("ALTER TABLE transactions ADD COLUMN provider_temp VARCHAR(32);")
        op.execute("UPDATE transactions SET provider_temp = provider::text;")
        op.execute("ALTER TABLE transactions DROP COLUMN provider;")
    
    # 3. Drop the old enum type
    op.execute("DROP TYPE IF EXISTS paymentprovider CASCADE;")
    
    # 4. Create new enum type with correct lowercase values matching Python enum
    op.execute("""
        CREATE TYPE paymentprovider AS ENUM (
            'relworx', 'mpesa', 'crypto', 'bank', 'blockbrite', 
            'voucher', 'mobile_money', 'bank_deposit'
        );
    """)
    
    # 5. Add columns back with the new enum type
    op.execute("ALTER TABLE trades ADD COLUMN payment_provider paymentprovider;")
    op.execute("ALTER TABLE transactions ADD COLUMN provider paymentprovider;")
    
    # 6. Convert old uppercase values to new lowercase values for trades (if data existed)
    if trades_has_payment_provider:
        op.execute("""
            UPDATE trades SET payment_provider = 
            CASE 
                WHEN payment_provider_temp = 'RELWORX' THEN 'relworx'::paymentprovider
                WHEN payment_provider_temp = 'MPESA' THEN 'mpesa'::paymentprovider
                WHEN payment_provider_temp = 'CRYPTO' THEN 'crypto'::paymentprovider
                WHEN payment_provider_temp = 'BANK' THEN 'bank'::paymentprovider
                WHEN payment_provider_temp = 'BLOCKBRITE' THEN 'blockbrite'::paymentprovider
                WHEN payment_provider_temp = 'VOUCHER' THEN 'voucher'::paymentprovider
                WHEN payment_provider_temp = 'MOBILE_MONEY' THEN 'mobile_money'::paymentprovider
                WHEN payment_provider_temp = 'BANK_DEPOSIT' THEN 'bank_deposit'::paymentprovider
                ELSE NULL
            END;
        """)
        op.execute("ALTER TABLE trades DROP COLUMN payment_provider_temp;")
    
    # 7. Convert old uppercase values to new lowercase values for transactions (if data existed)
    if transactions_has_provider:
        op.execute("""
            UPDATE transactions SET provider = 
            CASE 
                WHEN provider_temp = 'RELWORX' THEN 'relworx'::paymentprovider
                WHEN provider_temp = 'MPESA' THEN 'mpesa'::paymentprovider
                WHEN provider_temp = 'CRYPTO' THEN 'crypto'::paymentprovider
                WHEN provider_temp = 'BANK' THEN 'bank'::paymentprovider
                WHEN provider_temp = 'BLOCKBRITE' THEN 'blockbrite'::paymentprovider
                WHEN provider_temp = 'VOUCHER' THEN 'voucher'::paymentprovider
                WHEN provider_temp = 'MOBILE_MONEY' THEN 'mobile_money'::paymentprovider
                WHEN provider_temp = 'BANK_DEPOSIT' THEN 'bank_deposit'::paymentprovider
                ELSE NULL
            END;
        """)
        op.execute("ALTER TABLE transactions DROP COLUMN provider_temp;")


def downgrade() -> None:
    # This is a destructive migration, downgrade would require recreating the old state
    pass
