"""add user token_version for JWT session invalidation (SRS §4.4 REQ-4)

Revision ID: d4e8f1a2b3c5
Revises: b7f2a1c9e4d3
Create Date: 2026-06-03 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = "d4e8f1a2b3c5"
down_revision = "b7f2a1c9e4d3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("token_version", sa.Integer(), nullable=False, server_default="0"),
    )
    op.alter_column("users", "token_version", server_default=None)


def downgrade() -> None:
    op.drop_column("users", "token_version")
