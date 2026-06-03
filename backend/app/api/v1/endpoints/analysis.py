"""
URL Analysis Service — SRS §4.5.

  POST /analysis/search        check / kick off analysis for a URL
  GET  /analysis/jobs/{id}     poll an analysis job (REQ-5, REQ-11)

The actual heavy work happens in ai-worker; this module only owns the
contract: normalize → cache check → enqueue if missing → return job id.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.redis import enqueue_analysis_job
from app.models.analysis_job import AnalysisJob, JobStatus
from app.models.report import Report, ReportStatus
from app.models.url import Url
from app.models.user import User
from app.schemas.url import (
    AnalysisJobStatus,
    UrlAnalysisResult,
    UrlSearchRequest,
)
from app.utils.url_normalizer import is_hostname_encodable, normalize_url

router = APIRouter()


@router.post("/search", response_model=UrlAnalysisResult)
def search_url(
    payload: UrlSearchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """SRS §4.5 REQ-1..6."""
    normalized = normalize_url(str(payload.url))

    # Reject hostnames the crawler's HTTP client can't IDNA-encode (e.g. a DNS
    # label > 63 chars or invalid non-ASCII). These would otherwise crash the
    # worker mid-pipeline and surface as a confusing "Analysis failed".
    if not is_hostname_encodable(normalized):
        raise HTTPException(
            status_code=422,
            detail="URL hostname is invalid or too long to analyze",
        )

    normalized_hash = Url.compute_hash(normalized)

    url_row = db.query(Url).filter(Url.normalized_url_hash == normalized_hash).first()

    # REQ-3 + REQ-4: cached path
    if url_row and url_row.current_risk_score is not None:
        report_count = (
            db.query(Report)
            .filter(
                Report.url_id == url_row.id,
                Report.status.in_([ReportStatus.ACTIVE, ReportStatus.VERIFIED]),
            )
            .count()
        )
        return UrlAnalysisResult(
            url=normalized,
            risk_score=url_row.current_risk_score,
            risk_level=url_row.current_risk_level,
            report_count=report_count,
            last_analyzed_at=url_row.last_analyzed_at,
            cached=True,
        )

    # New URL — create row + enqueue async job (REQ-5, REQ-6)
    if url_row is None:
        url_row = Url(normalized_url=normalized, normalized_url_hash=normalized_hash)
        db.add(url_row)
        db.flush()

    job = AnalysisJob(url_id=url_row.id, status=JobStatus.PENDING)
    db.add(job)
    db.commit()
    db.refresh(job)

    enqueue_analysis_job(job_id=job.id, url=normalized)

    return UrlAnalysisResult(
        url=normalized,
        job_id=job.id,
        cached=False,
    )


@router.get("/jobs/{job_id}", response_model=AnalysisJobStatus)
def get_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    job = db.query(AnalysisJob).filter(AnalysisJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    risk_level = None
    if job.status == JobStatus.COMPLETED:
        url_row = db.query(Url).filter(Url.id == job.url_id).first()
        if url_row:
            risk_level = url_row.current_risk_level

    return AnalysisJobStatus(
        job_id=job.id,
        status=job.status,
        final_risk_score=job.final_risk_score,
        risk_level=risk_level,
    )
