"""add review pending competency cycle status

Revision ID: 7944f2536463
Revises: c97a91d76dfc
Create Date: 2026-08-20 23:44:50.335523

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7944f2536463'
down_revision: Union[str, Sequence[str], None] = 'c97a91d76dfc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.execute(
        "ALTER TYPE competencycyclestatus ADD VALUE IF NOT EXISTS 'REVIEW_PENDING'"
    )

def downgrade() -> None:
    """Downgrade schema."""
    pass
