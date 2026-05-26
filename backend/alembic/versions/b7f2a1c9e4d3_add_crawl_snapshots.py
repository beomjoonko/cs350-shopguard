"""add crawl_snapshots

Revision ID: b7f2a1c9e4d3
Revises: c9ccbed9973a
Create Date: 2026-05-25 18:10:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = 'b7f2a1c9e4d3'
down_revision = 'c9ccbed9973a'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'crawl_snapshots',
        sa.Column('id', mysql.CHAR(length=36), nullable=False),
        sa.Column('analysis_job_id', mysql.CHAR(length=36), nullable=False),
        sa.Column('url_id', mysql.CHAR(length=36), nullable=False),
        sa.Column('scan_date', sa.DateTime(), nullable=False),
        sa.Column('protocol', sa.String(length=16), nullable=True),
        sa.Column('fetch_status', sa.Integer(), nullable=True),
        sa.Column('fetch_ok', sa.Boolean(), nullable=False),
        sa.Column('features_text', mysql.LONGTEXT(), nullable=True),
        sa.Column('features_html', sa.JSON(), nullable=True),
        sa.Column('features_css', sa.JSON(), nullable=True),
        sa.Column('language', sa.String(length=16), nullable=True),
        sa.Column('assets_downloaded', sa.Integer(), nullable=True),
        sa.Column('security_state', sa.String(length=64), nullable=True),
        sa.Column('security_protocol', sa.String(length=64), nullable=True),
        sa.Column('security_issuer', sa.String(length=512), nullable=True),
        sa.Column('security_valid_from', sa.DateTime(), nullable=True),
        sa.Column('security_valid_to', sa.DateTime(), nullable=True),
        sa.Column('whois_domain_age', sa.Float(), nullable=True),
        sa.Column('whois_registry_expired_at', sa.DateTime(), nullable=True),
        sa.Column('whois_registrar', sa.String(length=255), nullable=True),
        sa.Column('remote_ip_country', sa.String(length=8), nullable=True),
        sa.Column('remote_ip_asn', sa.String(length=64), nullable=True),
        sa.Column('remote_ip_isp', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['analysis_job_id'], ['analysis_jobs.id'], ),
        sa.ForeignKeyConstraint(['url_id'], ['urls.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_crawl_snapshots_analysis_job_id'), 'crawl_snapshots', ['analysis_job_id'], unique=False)
    op.create_index(op.f('ix_crawl_snapshots_url_id'), 'crawl_snapshots', ['url_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_crawl_snapshots_url_id'), table_name='crawl_snapshots')
    op.drop_index(op.f('ix_crawl_snapshots_analysis_job_id'), table_name='crawl_snapshots')
    op.drop_table('crawl_snapshots')
