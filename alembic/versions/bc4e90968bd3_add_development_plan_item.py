"""add development plan item

Revision ID: bc4e90968bd3
Revises: 7944f2536463
Create Date: 2026-08-21 00:35:55.685461

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bc4e90968bd3'
down_revision: Union[str, Sequence[str], None] = '7944f2536463'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
