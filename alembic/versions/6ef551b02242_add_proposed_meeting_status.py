"""add proposed meeting status

Revision ID: 6ef551b02242
Revises: 36e44fb3f99b
Create Date: 2026-08-20 13:22:14.801235

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6ef551b02242'
down_revision: Union[str, Sequence[str], None] = '36e44fb3f99b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TYPE meetingstatus ADD VALUE 'PROPOSED'"
    )


def downgrade() -> None:
    pass