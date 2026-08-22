"""update meeting response status enum

Revision ID: 676a00a8686f
Revises: d0905189bdb2
Create Date: 2026-08-20 14:08:41.418941

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '676a00a8686f'
down_revision: Union[str, Sequence[str], None] = 'd0905189bdb2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.execute(
        "ALTER TYPE meetingresponsestatus RENAME VALUE 'ACCEPTED' TO 'CONFIRMED'"
    )
    op.execute(
        "ALTER TYPE meetingresponsestatus RENAME VALUE 'DECLINED' TO 'REJECTED'"
    )


def downgrade():
    op.execute(
        "ALTER TYPE meetingresponsestatus RENAME VALUE 'CONFIRMED' TO 'ACCEPTED'"
    )
    op.execute(
        "ALTER TYPE meetingresponsestatus RENAME VALUE 'REJECTED' TO 'DECLINED'"
    )
