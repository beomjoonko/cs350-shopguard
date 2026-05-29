"""
URL Analysis Service — SRS §4.5 (simplified, synchronous).

  POST /analysis/search        check / perform synchronous analysis for a URL
  GET  /analysis/jobs/{id}     get analysis result (REQ-5, REQ-11)
"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.analysis_job import AnalysisJob, JobStatus
from app.models.report import Report, ReportStatus
from app.models.url import Url
from app.models.user import User
from app.schemas.url import (
    AnalysisJobStatus,
    UrlAnalysisResult,
    UrlSearchRequest,
)
from app.utils.url_normalizer import normalize_url

router = APIRouter()


def _compute_dummy_risk_score(report_count: int) -> tuple[int, str]:
    """
    Simple synchronous risk scoring based on report count only.
    Formula: min(report_count × 10, 100)
    """
    score = min(report_count * 10, 100)

    if score <= 30:
        level = "SAFE"
    elif score <= 60:
        level = "WARNING"
    elif score <= 80:
        level = "DANGER"
    else:
        level = "CRITICAL"

    return score, level


@router.post("/search", response_model=UrlAnalysisResult)
def search_url(
    payload: UrlSearchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """SRS §4.5 REQ-1..6 (synchronous)."""
    normalized = normalize_url(str(payload.url))
    normalized_hash = Url.compute_hash(normalized)

    url_row = db.query(Url).filter(Url.normalized_url_hash == normalized_hash).first()

    # Count active/verified reports
    report_count = (
        db.query(Report)
        .filter(
            (Report.url_id == url_row.id) if url_row else False,
            Report.status.in_([ReportStatus.ACTIVE, ReportStatus.VERIFIED]),
        )
        .count()
    )

    score, level = _compute_dummy_risk_score(report_count)

    # Create or update URL row
    if url_row is None:
        url_row = Url(
            normalized_url=normalized,
            normalized_url_hash=normalized_hash,
            current_risk_score=score,
            current_risk_level=level,
            last_analyzed_at=datetime.utcnow(),
        )
        db.add(url_row)
    else:
        url_row.current_risk_score = score
        url_row.current_risk_level = level
        url_row.last_analyzed_at = datetime.utcnow()

    db.commit()
    db.refresh(url_row)

    return UrlAnalysisResult(
        url=normalized,
        risk_score=score,
        risk_level=level,
        report_count=report_count,
        last_analyzed_at=url_row.last_analyzed_at,
        cached=False,
    )


@router.get("/jobs/{job_id}", response_model=AnalysisJobStatus)
def get_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Kept for backward compatibility; analysis is now synchronous."""
    job = db.query(AnalysisJob).filter(AnalysisJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    url_row = db.query(Url).filter(Url.id == job.url_id).first()

    return AnalysisJobStatus(
        job_id=job.id,
        status=JobStatus.COMPLETED,
        final_risk_score=url_row.current_risk_score if url_row else 0,
        risk_level=url_row.current_risk_level if url_row else "SAFE",
    )
