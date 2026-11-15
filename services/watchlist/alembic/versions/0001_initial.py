"""initial watchlist schema

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
        "watchlist_items",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("content_id", sa.Integer(), nullable=False),
        sa.Column("added_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("user_id", "content_id", name="uq_watchlist_user_content"),
    )
    op.create_index("ix_watchlist_user_added", "watchlist_items", ["user_id", "added_at"])


def downgrade() -> None:
    op.drop_table("watchlist_items")
