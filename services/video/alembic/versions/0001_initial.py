"""initial video schema

Revision ID: 0001
Revises:
"""
import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "media_assets",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("content_id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("object_key", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(100), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=True),
        sa.Column("uploaded_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("content_id", "kind", name="uq_media_content_kind"),
        sa.CheckConstraint("kind IN ('video','poster','thumbnail')", name="ck_media_kind"),
    )
    op.create_index("ix_media_assets_content_id", "media_assets", ["content_id"])


def downgrade() -> None:
    op.drop_table("media_assets")
