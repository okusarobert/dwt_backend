"""added private key

Revision ID: 60cafc119eef
Revises: e2f84217a6be
Create Date: 2025-08-04 15:10:18.354974

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '60cafc119eef'
down_revision: Union[str, None] = 'e2f84217a6be'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # Idempotent alterations for 'accounts' table
    op.alter_column('accounts', 'account_type',
               existing_type=postgresql.ENUM('FIAT', 'CRYPTO', name='accounttype'),
               nullable=False)
    op.alter_column('accounts', 'user_id',
               existing_type=sa.INTEGER(),
               nullable=False)

    # Idempotent additions for 'crypto_addresses' table
    crypto_columns = [c['name'] for c in inspector.get_columns('crypto_addresses')]
    if 'private_key' not in crypto_columns:
        op.add_column('crypto_addresses', sa.Column('private_key', sa.String(length=256), nullable=True))
    if 'public_key' not in crypto_columns:
        op.add_column('crypto_addresses', sa.Column('public_key', sa.String(length=256), nullable=True))

    op.alter_column('crypto_addresses', 'memo',
               existing_type=sa.VARCHAR(length=128),
               type_=sa.String(length=256),
               existing_nullable=True)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    op.alter_column('crypto_addresses', 'memo',
               existing_type=sa.String(length=256),
               type_=sa.VARCHAR(length=128),
               existing_nullable=True)

    # Idempotent drops for 'crypto_addresses' table
    crypto_columns = [c['name'] for c in inspector.get_columns('crypto_addresses')]
    if 'public_key' in crypto_columns:
        op.drop_column('crypto_addresses', 'public_key')
    if 'private_key' in crypto_columns:
        op.drop_column('crypto_addresses', 'private_key')

    # Idempotent alterations for 'accounts' table
    op.alter_column('accounts', 'user_id',
               existing_type=sa.INTEGER(),
               nullable=True)
    op.alter_column('accounts', 'account_type',
               existing_type=postgresql.ENUM('FIAT', 'CRYPTO', name='accounttype'),
               nullable=True)
