"""recreate_paymentprovider_enum_after_cleanup

Revision ID: ad16d0327ead
Revises: 8527f833dc45
Create Date: 2025-08-18 16:37:44.487530

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ad16d0327ead'
down_revision: Union[str, None] = '8527f833dc45'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Recreate PaymentProvider enum with correct lowercase values after cleanup
    op.execute("""
        CREATE TYPE paymentprovider AS ENUM (
            'relworx', 'mpesa', 'crypto', 'bank', 'blockbrite', 
            'voucher', 'mobile_money', 'bank_deposit'
        );
    """)


def downgrade() -> None:
    op.execute("DROP TYPE IF EXISTS paymentprovider CASCADE;")
