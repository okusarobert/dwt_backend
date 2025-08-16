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
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # Check if ENUM type exists
    res = bind.execute(sa.text("SELECT 1 FROM pg_type WHERE typname = 'accounttype'")).scalar()
    if not res:
        account_type_enum = postgresql.ENUM('FIAT', 'CRYPTO', name='accounttype')
        account_type_enum.create(bind)

    # Check if column exists
    columns = [col['name'] for col in inspector.get_columns('accounts')]
    if 'account_type' not in columns:
        op.add_column('accounts', sa.Column('account_type', sa.Enum(
            'FIAT', 'CRYPTO', name='accounttype'), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # Check if column exists before dropping
    columns = [col['name'] for col in inspector.get_columns('accounts')]
    if 'account_type' in columns:
        op.drop_column('accounts', 'account_type')

    # Check if ENUM type exists before dropping
    res = bind.execute(sa.text("SELECT 1 FROM pg_type WHERE typname = 'accounttype'")).scalar()
    if res:
        account_type_enum = postgresql.ENUM('FIAT', 'CRYPTO', name='accounttype')
        account_type_enum.drop(bind)
