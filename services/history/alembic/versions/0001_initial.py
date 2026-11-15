"""initial watch history schema

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
        "watch_history",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("content_id", sa.Integer(), nullable=False),
        sa.Column("position_seconds", sa.Float(), nullable=False, server_default="0"),
        sa.Column("duration_seconds", sa.Float(), nullable=False, server_default="0"),
        sa.Column("completed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("first_watched_at", sa.DateTime(), nullable=False),
        sa.Column("last_watched_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("user_id", "content_id", name="uq_history_user_content"),
    )
    op.create_index("ix_history_user_last", "watch_history", ["user_id", "last_watched_at"])


def downgrade() -> None:
    op.drop_table("watch_history")
