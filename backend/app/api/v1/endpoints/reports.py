"""
Fraud Reporting endpoints — SRS §4.2.

  POST /reports                   submit a fraud report (REQ-1..5)
  GET  /reports/{report_id}       fetch a report (own or admin)
  POST /reports/upload-evidence   upload evidence image to Supabase Storage
"""
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.report import Report, ReportStatus
from app.models.url import Url
from app.models.user import User, UserRole
from app.schemas.report import ReportCreate, ReportPublic
from app.services.storage import upload_evidence_image
from app.utils.report_public import report_to_public
from app.utils.url_normalizer import normalize_url

router = APIRouter()

_ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
_MAX_EVIDENCE_SIZE = 5 * 1024 * 1024  # 5 MB


@router.post("/upload-evidence", status_code=201)
async def upload_evidence(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """
    Upload an evidence image to Supabase Storage (SRS §3.3).

    Returns the public URL of the uploaded file. The caller should store this
    URL in the `evidence_image_url` field when submitting the fraud report.
    """
    contents = await file.read()

    if len(contents) > _MAX_EVIDENCE_SIZE:
        raise HTTPException(status_code=413, detail="File exceeds 5 MB limit")

    if file.content_type not in _ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported media type. Allowed: {', '.join(_ALLOWED_IMAGE_TYPES)}",
        )

    url = upload_evidence_image(contents, file.filename or "evidence.jpg")
    return {"url": url}


@router.post("", response_model=ReportPublic, status_code=201)
def create_report(
    payload: ReportCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """SRS §4.2 REQ-1..5."""
    if not payload.legal_consent:
        # SRS §4.2 REQ-3: prohibit submission without consent.
        raise HTTPException(status_code=400, detail="Legal consent is required")

    normalized = normalize_url(str(payload.url))
    normalized_hash = Url.compute_hash(normalized)

    url_row = db.query(Url).filter(Url.normalized_url_hash == normalized_hash).first()
    if url_row is None:
        url_row = Url(normalized_url=normalized, normalized_url_hash=normalized_hash)
        db.add(url_row)
        db.flush()

    # SRS §4.2 REQ-4 — duplicate-report prevention (same user + same url).
    existing = (
        db.query(Report)
        .filter(Report.user_id == current_user.id, Report.url_id == url_row.id)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail="You have already reported this URL",
        )

    report = Report(
        user_id=current_user.id,
        url_id=url_row.id,
        fraud_type=payload.fraud_type,
        description=payload.description,
        evidence_image_url=payload.evidence_image_url,
        legal_consent=payload.legal_consent,
        status=ReportStatus.SUBMITTED,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report_to_public(report, url_row)


@router.get("/{report_id}", response_model=ReportPublic)
def get_report(
    report_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """SRS §4.3 REQ-4: users can only view their own reports."""
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    if report.user_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Forbidden")
    url_row = db.query(Url).filter(Url.id == report.url_id).first()
    return report_to_public(report, url_row)
