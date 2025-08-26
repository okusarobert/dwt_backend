"""merge_currency_heads

Revision ID: ffda88480694
Revises: f181afaca3c1, add_currency_mgmt_tables
Create Date: 2025-08-25 19:43:59.850569

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ffda88480694'
down_revision: Union[str, None] = ('f181afaca3c1', 'add_currency_mgmt_tables')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
