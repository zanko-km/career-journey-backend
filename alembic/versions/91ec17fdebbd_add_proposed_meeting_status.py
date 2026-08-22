"""add proposed meeting status

Revision ID: 91ec17fdebbd
Revises: 942d67b6f66e
Create Date: 2026-08-20 13:29:06.934412

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '91ec17fdebbd'
down_revision: Union[str, Sequence[str], None] = '942d67b6f66e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TYPE meetingstatus ADD VALUE 'PROPOSED'"
    )


def downgrade() -> None:
    pass