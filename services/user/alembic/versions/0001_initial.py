"""initial user schema

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
        "user_profiles",
        sa.Column("user_id", sa.Integer(), primary_key=True, autoincrement=False),
        sa.Column("display_name", sa.String(60), nullable=False),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column("preferred_language", sa.String(30), nullable=False, server_default="English"),
        sa.Column("avatar_color", sa.String(7), nullable=False, server_default="#1f80e0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("user_profiles")
