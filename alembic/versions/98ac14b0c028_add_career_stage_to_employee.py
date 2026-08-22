"""add career stage to employee

Revision ID: 98ac14b0c028
Revises: 1d22af6b6f1c
Create Date: 2026-08-19 01:24:29.915047

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '98ac14b0c028'
down_revision: Union[str, Sequence[str], None] = '1d22af6b6f1c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    career_stage = sa.Enum(
        "PRE_ONBOARDING",
        "ONBOARDING",
        "POST_ONBOARDING",
        "EXITED",
        "INACTIVE",
        name="careerstage",
    )

    career_stage.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "employees",
        sa.Column(
            "career_stage",
            career_stage,
            nullable=True,
        ),
    )

    op.execute(
        """
        UPDATE employees
        SET career_stage = 'PRE_ONBOARDING'
        WHERE career_stage IS NULL
        """
    )

    op.alter_column(
        "employees",
        "career_stage",
        nullable=False,
    )


def downgrade() -> None:
    op.drop_column("employees", "career_stage")

    career_stage = sa.Enum(
        "PRE_ONBOARDING",
        "ONBOARDING",
        "POST_ONBOARDING",
        "EXITED",
        "INACTIVE",
        name="careerstage",
    )

    career_stage.drop(op.get_bind(), checkfirst=True)


