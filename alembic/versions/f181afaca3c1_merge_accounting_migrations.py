"""merge_accounting_migrations

Revision ID: f181afaca3c1
Revises: 63cbf539ec6d, create_crypto_accounts
Create Date: 2025-08-21 13:18:13.348333

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f181afaca3c1'
down_revision: Union[str, None] = ('63cbf539ec6d', 'create_crypto_accounts')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
