"""create image assets table

Revision ID: 20260530_0001
Revises:
Create Date: 2026-05-30 00:00:00

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260530_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "image_assets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("public_id", sa.String(length=255), nullable=False),
        sa.Column("secure_url", sa.String(length=1000), nullable=False),
        sa.Column("resource_type", sa.String(length=50), nullable=False),
        sa.Column("format", sa.String(length=50), nullable=True),
        sa.Column("bytes", sa.Integer(), nullable=True),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_image_assets_id"), "image_assets", ["id"], unique=False)
    op.create_index(
        op.f("ix_image_assets_public_id"),
        "image_assets",
        ["public_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_image_assets_public_id"), table_name="image_assets")
    op.drop_index(op.f("ix_image_assets_id"), table_name="image_assets")
    op.drop_table("image_assets")
