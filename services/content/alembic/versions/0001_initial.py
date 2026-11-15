"""initial content schema

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
        "contents",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("genre", sa.String(50), nullable=False),
        sa.Column("language", sa.String(50), nullable=False),
        sa.Column("release_year", sa.SmallInteger(), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("category", sa.String(20), nullable=False),
        sa.Column("maturity_rating", sa.String(10), nullable=False, server_default="U/A 13+"),
        sa.Column("is_featured", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("category IN ('movie','tv_show','web_series','other')", name="ck_contents_category"),
        sa.CheckConstraint("duration_minutes > 0", name="ck_contents_duration"),
    )
    op.create_index("ix_contents_title", "contents", ["title"])
    op.create_index("ix_contents_genre", "contents", ["genre"])
    op.create_index("ix_contents_language", "contents", ["language"])
    op.create_index("ix_contents_release_year", "contents", ["release_year"])
    op.create_index("ix_contents_category_genre", "contents", ["category", "genre"])
    op.create_index("ix_contents_featured_created", "contents", ["is_featured", "created_at"])


def downgrade() -> None:
    op.drop_table("contents")
