"""fix_tradetype_enum_values

Revision ID: d57ed0c3f961
Revises: 5908c6093a07
Create Date: 2025-08-18 15:30:30.450362

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd57ed0c3f961'
down_revision: Union[str, None] = '5908c6093a07'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add uppercase enum values to match what the application is using
    op.execute("ALTER TYPE tradetype ADD VALUE IF NOT EXISTS 'SELL'")
    op.execute("ALTER TYPE tradetype ADD VALUE IF NOT EXISTS 'BUY'")


def downgrade() -> None:
    # Note: PostgreSQL doesn't support removing enum values directly
    # This would require recreating the enum type
    pass
