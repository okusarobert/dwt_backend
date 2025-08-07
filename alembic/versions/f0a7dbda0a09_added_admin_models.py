"""added admin models

Revision ID: f0a7dbda0a09
Revises: ad43b406e01b
Create Date: 2025-07-16 19:53:50.362397

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# Add this import
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'f0a7dbda0a09'
down_revision: Union[str, None] = 'ad43b406e01b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create the ENUM type
    account_type_enum = postgresql.ENUM('FIAT', 'CRYPTO', name='accounttype')
    account_type_enum.create(op.get_bind())

    # 2. Add the column using the new ENUM type
    op.add_column('accounts', sa.Column('account_type', sa.Enum(
        'FIAT', 'CRYPTO', name='accounttype'), nullable=True))


def downgrade() -> None:
    # 1. Drop the column first
    op.drop_column('accounts', 'account_type')

    # 2. Drop the ENUM type
    account_type_enum = postgresql.ENUM('FIAT', 'CRYPTO', name='accounttype')
    account_type_enum.drop(op.get_bind())
