"""
Re-export all models so Alembic's `--autogenerate` can see them.
Order matters less here, but we list them roughly by FK dependency.
"""
from app.models.user import User, UserRole, UserStatus  # noqa: F401
from app.models.url import Url, RiskLevel  # noqa: F401
from app.models.report import Report, FraudType, ReportStatus  # noqa: F401
from app.models.report_evidence import ReportEvidence  # noqa: F401
from app.models.analysis_job import AnalysisJob, JobStatus  # noqa: F401
from app.models.crawl_snapshot import CrawlSnapshot  # noqa: F401
from app.models.admin_audit_log import AdminAuditLog  # noqa: F401
from app.models.blacklist import Blacklist  # noqa: F401
from app.models.password_reset_token import PasswordResetToken  # noqa: F401
