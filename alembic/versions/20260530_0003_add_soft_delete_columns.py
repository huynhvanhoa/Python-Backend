"""add soft delete columns to image assets

Revision ID: 20260530_0003
Revises: 20260530_0002
Create Date: 2026-05-30 01:00:00

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260530_0003"
down_revision: Union[str, None] = "20260530_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "image_assets",
        sa.Column(
            "is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
    )
    op.add_column(
        "image_assets",
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
    )
    op.create_index(
        op.f("ix_image_assets_is_deleted"), "image_assets", ["is_deleted"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_image_assets_is_deleted"), table_name="image_assets")
    op.drop_column("image_assets", "deleted_at")
    op.drop_column("image_assets", "is_deleted")
