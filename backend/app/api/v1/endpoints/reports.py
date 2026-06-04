"""
Fraud Reporting endpoints — SRS §4.2.

  POST /reports                      submit a fraud report (REQ-1..5)
  GET  /reports/{report_id}          fetch a report (own or admin)
  GET  /reports/{report_id}/evidence download stored evidence image
"""
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile
from fastapi.responses import Response
from pydantic import ValidationError
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.report import FraudType, Report, ReportStatus
from app.models.report_evidence import ReportEvidence
from app.models.url import Url
from app.models.user import User, UserRole
from app.schemas.report import ReportCreate, ReportPublic
from app.utils.evidence_upload import read_validated_evidence
from app.utils.report_public import report_to_public
from app.utils.url_normalizer import normalize_url

router = APIRouter()


def _inline_content_disposition(filename: str) -> str:
    """HTTP headers must be latin-1; use RFC 5987 for non-ASCII filenames."""
    ascii_name = filename.encode("ascii", "ignore").decode() or "evidence"
    return f"inline; filename=\"{ascii_name}\"; filename*=UTF-8''{quote(filename)}"


def _load_report(db: Session, report_id: str) -> Report | None:
    return (
        db.query(Report)
        .options(joinedload(Report.evidence))
        .filter(Report.id == report_id)
        .first()
    )


def _parse_form_bool(value: str | None) -> bool:
    if value is None:
        return False
    return str(value).strip().lower() in ("true", "1", "yes", "on")


async def _extract_report_payload(
    request: Request,
) -> tuple[str, FraudType, str, bool, UploadFile | None]:
    """Accept JSON (no file) or multipart/form-data (optional evidence file)."""
    content_type = request.headers.get("content-type", "")

    if "multipart/form-data" in content_type or "application/x-www-form-urlencoded" in content_type:
        form = await request.form()
        url = form.get("url")
        fraud_type = form.get("fraud_type")
        description = form.get("description")
        legal_raw = form.get("legal_consent")
        evidence = form.get("evidence")

        missing = [
            name
            for name, val in (
                ("url", url),
                ("fraud_type", fraud_type),
                ("description", description),
                ("legal_consent", legal_raw),
            )
            if val is None or (isinstance(val, str) and not str(val).strip())
        ]
        if missing:
            raise HTTPException(
                status_code=422,
                detail=f"Missing required fields: {', '.join(missing)}",
            )

        try:
            fraud_enum = FraudType(str(fraud_type))
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="Invalid fraud_type") from exc

        upload: UploadFile | None = None
        if evidence is not None and getattr(evidence, "filename", None):
            upload = evidence  # type: ignore[assignment]

        return (
            str(url),
            fraud_enum,
            str(description),
            _parse_form_bool(str(legal_raw)),
            upload,
        )

    if "application/json" in content_type:
        try:
            body = await request.json()
            payload = ReportCreate.model_validate(body)
        except ValidationError as exc:
            raise HTTPException(status_code=422, detail=exc.errors()) from exc
        return (
            str(payload.url),
            payload.fraud_type,
            payload.description,
            payload.legal_consent,
            None,
        )

    raise HTTPException(
        status_code=415,
        detail="Content-Type must be multipart/form-data or application/json",
    )


async def _create_report_record(
    db: Session,
    current_user: User,
    url: str,
    fraud_type: FraudType,
    description: str,
    legal_consent: bool,
    evidence: UploadFile | None,
) -> tuple[Report, Url]:
    if not legal_consent:
        raise HTTPException(status_code=400, detail="Legal consent is required")

    if len(description.strip()) < 20:
        raise HTTPException(
            status_code=422,
            detail="Description must be at least 20 characters",
        )

    normalized = normalize_url(url)
    normalized_hash = Url.compute_hash(normalized)

    url_row = db.query(Url).filter(Url.normalized_url_hash == normalized_hash).first()
    if url_row is None:
        url_row = Url(normalized_url=normalized, normalized_url_hash=normalized_hash)
        db.add(url_row)
        db.flush()

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
        fraud_type=fraud_type,
        description=description,
        legal_consent=legal_consent,
        status=ReportStatus.SUBMITTED,
    )
    db.add(report)
    db.flush()

    if evidence is not None and evidence.filename:
        data, content_type, filename = await read_validated_evidence(evidence)
        db.add(
            ReportEvidence(
                report_id=report.id,
                content_type=content_type,
                filename=filename,
                data=data,
            )
        )

    db.commit()
    report = _load_report(db, report.id)
    return report, url_row


@router.post("", response_model=ReportPublic, status_code=201)
async def create_report(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """SRS §4.2 REQ-1..5 — JSON or multipart (with optional evidence image)."""
    url, fraud_type, description, legal_consent, evidence = await _extract_report_payload(
        request
    )
    report, url_row = await _create_report_record(
        db,
        current_user,
        url,
        fraud_type,
        description,
        legal_consent,
        evidence,
    )
    return report_to_public(report, url_row)


@router.get("/{report_id}/evidence")
def get_report_evidence(
    report_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return stored evidence bytes (reporter or admin only)."""
    report = _load_report(db, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    if report.user_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Forbidden")
    if report.evidence is None:
        raise HTTPException(status_code=404, detail="No evidence for this report")

    ev = report.evidence
    return Response(
        content=bytes(ev.data),
        media_type=ev.content_type,
        headers={
            "Content-Disposition": _inline_content_disposition(ev.filename),
            "Cache-Control": "private, max-age=3600",
        },
    )


@router.get("/{report_id}", response_model=ReportPublic)
def get_report(
    report_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """SRS §4.3 REQ-4: users can only view their own reports."""
    report = _load_report(db, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    if report.user_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Forbidden")
    url_row = db.query(Url).filter(Url.id == report.url_id).first()
    return report_to_public(report, url_row)
