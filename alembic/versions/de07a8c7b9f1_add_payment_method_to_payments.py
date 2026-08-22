"""add payment method to payments

Revision ID: de07a8c7b9f1
Revises: 5bb3c6e3bad7
Create Date: 2026-08-22
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "de07a8c7b9f1"
down_revision: Union[str, Sequence[str], None] = "5bb3c6e3bad7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Existing rows predate this field. Retain them with an explicit sentinel
    # rather than failing the migration when the column becomes required.
    op.add_column(
        "payments",
        sa.Column("payment_method", sa.String(length=50), nullable=True),
    )
    op.execute(
        sa.text(
            "UPDATE payments "
            "SET payment_method = 'unknown' "
            "WHERE payment_method IS NULL"
        )
    )
    op.alter_column("payments", "payment_method", nullable=False)


def downgrade() -> None:
    op.drop_column("payments", "payment_method")
