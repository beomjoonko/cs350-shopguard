"""Build ReportPublic responses with joined URL risk data."""
from app.models.report import Report
from app.models.url import Url
from app.schemas.report import ReportPublic


def report_to_public(report: Report, url_row: Url | None = None) -> ReportPublic:
    return ReportPublic(
        id=report.id,
        user_id=report.user_id,
        url_id=report.url_id,
        fraud_type=report.fraud_type,
        description=report.description,
        evidence_image_url=report.evidence_image_url,
        status=report.status,
        created_at=report.created_at,
        url=url_row.normalized_url if url_row else None,
        risk_score=url_row.current_risk_score if url_row else None,
        risk_level=url_row.current_risk_level if url_row else None,
    )
