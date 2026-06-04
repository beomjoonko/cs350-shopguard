"""add report_evidence table

Revision ID: f6b3c8d2e1a4
Revises: e5a9c2d7f1b6
Create Date: 2026-06-03 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision = "f6b3c8d2e1a4"
down_revision = "e5a9c2d7f1b6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "report_evidence",
        sa.Column("id", mysql.CHAR(length=36), nullable=False),
        sa.Column("report_id", mysql.CHAR(length=36), nullable=False),
        sa.Column("content_type", sa.String(length=128), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("data", sa.LargeBinary(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["report_id"], ["reports.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_report_evidence_report_id"),
        "report_evidence",
        ["report_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_report_evidence_report_id"), table_name="report_evidence")
    op.drop_table("report_evidence")
