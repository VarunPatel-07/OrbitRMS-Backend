"""automated-migration

Revision ID: 7dd193befc52
Revises: 882a5873813a
Create Date: 2026-06-08
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7dd193befc52"
down_revision: Union[str, None] = "882a5873813a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Step 1: Add columns as nullable first
    op.add_column(
        "client_inquires_data",
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )

    op.add_column(
        "client_inquires_data",
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )

    # Step 2: Fill existing rows
    op.execute(
        """
        UPDATE client_inquires_data
        SET 
            created_at = NOW(),
            updated_at = NOW()
        WHERE created_at IS NULL OR updated_at IS NULL
    """
    )

    # Step 3: Make columns NOT NULL
    op.alter_column(
        "client_inquires_data",
        "created_at",
        existing_type=sa.DateTime(),
        nullable=False,
    )

    op.alter_column(
        "client_inquires_data",
        "updated_at",
        existing_type=sa.DateTime(),
        nullable=False,
    )


def downgrade() -> None:
    op.drop_column("client_inquires_data", "updated_at")
    op.drop_column("client_inquires_data", "created_at")
