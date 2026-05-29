"""Initial schema for PostgreSQL / Supabase.

Replaces the previous MySQL-based migrations. Uses PostgreSQL-native types:
  - UUID(as_uuid=True) for all primary keys and foreign keys
  - DateTime(timezone=True) for all timestamps (timestamptz)
  - Named Enum types registered in the PostgreSQL catalogue

Revision ID: 0001_initial_schema_pg
Revises:
Create Date: 2026-05-27
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, ENUM as PgEnum

# revision identifiers
revision = "0001_initial_schema_pg"
down_revision = None
branch_labels = None
depends_on = None

# ---------------------------------------------------------------------------
# Pre-declare all named PostgreSQL enum types.
# create_type=False tells SQLAlchemy NOT to auto-emit CREATE TYPE DDL;
# we create them explicitly via op.execute() with IF NOT EXISTS safety.
# ---------------------------------------------------------------------------
_risklevel   = PgEnum("SAFE", "WARNING", "DANGER", "CRITICAL",         name="risklevel",    create_type=False)
_userrole    = PgEnum("USER", "ADMIN",                                  name="userrole",     create_type=False)
_userstatus  = PgEnum("ACTIVE", "SUSPENDED",                           name="userstatus",   create_type=False)
_jobstatus   = PgEnum("PENDING", "CRAWLING", "ANALYZING", "COMPLETED", "FAILED",
                      name="jobstatus",   create_type=False)
_fraudtype   = PgEnum("NON_DELIVERY", "FALSE_ADVERTISING", "REFUSAL_OF_REFUND",
                      "DEFECTIVE_PRODUCTS", "PERSONAL_DATA_LEAKAGE", "OTHERS",
                      name="fraudtype",   create_type=False)
_reportstatus = PgEnum("DRAFT", "SUBMITTED", "ACTIVE", "UNDER_REVIEW",
                       "VERIFIED", "BLINDED_DELETED", "PENDING", "HIDDEN",
                       name="reportstatus", create_type=False)


def _sql_create_enum(name: str, *values: str) -> str:
    vals = ", ".join(f"'{v}'" for v in values)
    return f"""
        DO $$ BEGIN
            CREATE TYPE {name} AS ENUM ({vals});
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
    """


def upgrade() -> None:
    bind = op.get_bind()

    # ── Create all named enum types (idempotent via DO block) ────────────────
    bind.execute(sa.text(_sql_create_enum("risklevel",    "SAFE", "WARNING", "DANGER", "CRITICAL")))
    bind.execute(sa.text(_sql_create_enum("userrole",     "USER", "ADMIN")))
    bind.execute(sa.text(_sql_create_enum("userstatus",   "ACTIVE", "SUSPENDED")))
    bind.execute(sa.text(_sql_create_enum("jobstatus",    "PENDING", "CRAWLING", "ANALYZING", "COMPLETED", "FAILED")))
    bind.execute(sa.text(_sql_create_enum("fraudtype",
        "NON_DELIVERY", "FALSE_ADVERTISING", "REFUSAL_OF_REFUND",
        "DEFECTIVE_PRODUCTS", "PERSONAL_DATA_LEAKAGE", "OTHERS")))
    bind.execute(sa.text(_sql_create_enum("reportstatus",
        "DRAFT", "SUBMITTED", "ACTIVE", "UNDER_REVIEW",
        "VERIFIED", "BLINDED_DELETED", "PENDING", "HIDDEN")))

    # ── blacklist ────────────────────────────────────────────────────────────
    op.create_table(
        "blacklist",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("reason", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_blacklist_email", "blacklist", ["email"], unique=True)

    # ── urls ─────────────────────────────────────────────────────────────────
    op.create_table(
        "urls",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("normalized_url", sa.String(2048), nullable=False),
        sa.Column("normalized_url_hash", sa.String(64), unique=True, nullable=False),
        sa.Column("current_risk_score", sa.Integer, nullable=True),
        sa.Column("current_risk_level", _risklevel, nullable=True),
        sa.Column("last_analyzed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_urls_normalized_url_hash", "urls", ["normalized_url_hash"], unique=True)

    # ── users ────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("supabase_uid", UUID(as_uuid=True), unique=True, nullable=False),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("role",   _userrole,   nullable=False, server_default="USER"),
        sa.Column("status", _userstatus, nullable=False, server_default="ACTIVE"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_users_email",        "users", ["email"],        unique=True)
    op.create_index("ix_users_supabase_uid", "users", ["supabase_uid"], unique=True)

    # ── analysis_jobs ────────────────────────────────────────────────────────
    op.create_table(
        "analysis_jobs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("url_id", UUID(as_uuid=True), sa.ForeignKey("urls.id"), nullable=False),
        sa.Column("status", _jobstatus, nullable=False, server_default="PENDING"),
        sa.Column("ai_score",          sa.Float,   nullable=True),
        sa.Column("report_count",      sa.Integer, nullable=True),
        sa.Column("final_risk_score",  sa.Integer, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_analysis_jobs_url_id", "analysis_jobs", ["url_id"])

    # ── reports ──────────────────────────────────────────────────────────────
    op.create_table(
        "reports",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"),  nullable=False),
        sa.Column("url_id",  UUID(as_uuid=True), sa.ForeignKey("urls.id"),   nullable=False),
        sa.Column("fraud_type",  _fraudtype,    nullable=False),
        sa.Column("description", sa.Text,       nullable=False),
        sa.Column("evidence_image_url", sa.String(2048), nullable=True),
        sa.Column("status", _reportstatus, nullable=False, server_default="SUBMITTED"),
        sa.Column("legal_consent", sa.Boolean, nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_reports_user_id", "reports", ["user_id"])
    op.create_index("ix_reports_url_id",  "reports", ["url_id"])

    # ── admin_audit_logs ─────────────────────────────────────────────────────
    op.create_table(
        "admin_audit_logs",
        sa.Column("id",          UUID(as_uuid=True), primary_key=True),
        sa.Column("admin_id",    UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("target_id",   sa.String(255), nullable=False),
        sa.Column("action_type", sa.String(64),  nullable=False),
        sa.Column("reason",      sa.Text,        nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_admin_audit_logs_admin_id", "admin_audit_logs", ["admin_id"])

    # ── crawl_snapshots ──────────────────────────────────────────────────────
    op.create_table(
        "crawl_snapshots",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "analysis_job_id",
            UUID(as_uuid=True),
            sa.ForeignKey("analysis_jobs.id"),
            nullable=False,
        ),
        sa.Column("url_id",   UUID(as_uuid=True), sa.ForeignKey("urls.id"), nullable=False),
        sa.Column("scan_date", sa.DateTime(timezone=True), nullable=False),
        # HTTP
        sa.Column("protocol",     sa.String(16),  nullable=True),
        sa.Column("fetch_status", sa.Integer,     nullable=True),
        sa.Column("fetch_ok",     sa.Boolean,     nullable=False, server_default="false"),
        # Page content
        sa.Column("features_text", sa.Text, nullable=True),
        sa.Column("features_html", sa.JSON, nullable=True),
        sa.Column("features_css",  sa.JSON, nullable=True),
        # Metadata
        sa.Column("language",           sa.String(16), nullable=True),
        sa.Column("assets_downloaded",  sa.Integer,    nullable=True),
        # TLS
        sa.Column("security_state",      sa.String(64),  nullable=True),
        sa.Column("security_protocol",   sa.String(64),  nullable=True),
        sa.Column("security_issuer",     sa.String(512), nullable=True),
        sa.Column("security_valid_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("security_valid_to",   sa.DateTime(timezone=True), nullable=True),
        # WHOIS
        sa.Column("whois_domain_age",         sa.Float,               nullable=True),
        sa.Column("whois_registry_expired_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("whois_registrar",          sa.String(255),         nullable=True),
        # Geo IP
        sa.Column("remote_ip_country", sa.String(8),   nullable=True),
        sa.Column("remote_ip_asn",     sa.String(64),  nullable=True),
        sa.Column("remote_ip_isp",     sa.String(255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_crawl_snapshots_analysis_job_id", "crawl_snapshots", ["analysis_job_id"])
    op.create_index("ix_crawl_snapshots_url_id",          "crawl_snapshots", ["url_id"])


def downgrade() -> None:
    op.drop_table("crawl_snapshots")
    op.drop_table("admin_audit_logs")
    op.drop_table("reports")
    op.drop_table("analysis_jobs")
    op.drop_table("users")
    op.drop_table("urls")
    op.drop_table("blacklist")

    op.execute("DROP TYPE IF EXISTS reportstatus")
    op.execute("DROP TYPE IF EXISTS fraudtype")
    op.execute("DROP TYPE IF EXISTS jobstatus")
    op.execute("DROP TYPE IF EXISTS userstatus")
    op.execute("DROP TYPE IF EXISTS userrole")
    op.execute("DROP TYPE IF EXISTS risklevel")
