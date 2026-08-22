"""align escalation fields and recovery terminal statuses

Revision ID: bb0e5c2bf726
Revises: de07a8c7b9f1
Create Date: 2026-08-22
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "bb0e5c2bf726"
down_revision: Union[str, Sequence[str], None] = "de07a8c7b9f1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "escalations",
        sa.Column(
            "priority",
            sa.String(length=20),
            nullable=False,
            server_default="medium",
        ),
    )
    op.execute(
        sa.text(
            "UPDATE recovery_cases SET status = 'recovered' "
            "WHERE status = 'resolved'"
        )
    )
    op.execute(
        sa.text(
            "UPDATE recovery_cases SET stage = 'recovered' "
            "WHERE stage = 'completed'"
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE recovery_cases SET status = 'resolved' "
            "WHERE status = 'recovered'"
        )
    )
    op.execute(
        sa.text(
            "UPDATE recovery_cases SET stage = 'completed' "
            "WHERE stage = 'recovered'"
        )
    )
    op.drop_column("escalations", "priority")
