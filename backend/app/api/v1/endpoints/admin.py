"""
Admin endpoints — SRS §4.4.

  GET   /admin/reports                   list all reports (REQ-2)
  PATCH /admin/reports/{report_id}       set status (REQ-3)
  POST  /admin/users/{user_id}/block     suspend user + revoke sessions (REQ-4..6)
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from supabase import create_client

from app.config import settings
from app.core.database import get_db
from app.core.dependencies import require_admin
from app.models.admin_audit_log import AdminAuditLog
from app.models.blacklist import Blacklist
from app.models.report import Report, ReportStatus
from app.models.url import Url
from app.models.user import User, UserStatus
from app.schemas.admin import BlockUserRequest
from app.schemas.report import ReportPublic, ReportStatusUpdate
from app.utils.report_public import report_to_public

router = APIRouter()

_RISK_COUNTED_STATUSES = {ReportStatus.ACTIVE, ReportStatus.VERIFIED}


@router.get("/reports", response_model=list[ReportPublic])
def list_reports(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """SRS §4.4 REQ-2 — admins see all reports."""
    rows = (
        db.query(Report, Url)
        .join(Url, Report.url_id == Url.id)
        .order_by(Report.created_at.desc())
        .all()
    )
    return [report_to_public(report, url_row) for report, url_row in rows]


@router.patch("/reports/{report_id}", response_model=ReportPublic)
def update_report_status(
    report_id: str,
    payload: ReportStatusUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """SRS §4.4 REQ-3 — change report status (Active / Hidden / Pending)."""
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    old_status = report.status
    report.status = payload.status

    db.add(AdminAuditLog(
        admin_id=admin.id,
        target_id=str(report.id),
        action_type="UPDATE_REPORT_STATUS",
        reason=f"{old_status.value} -> {payload.status.value}",
    ))
    url_row = db.query(Url).filter(Url.id == report.url_id).first()
    db.commit()
    db.refresh(report)
    return report_to_public(report, url_row)


@router.post("/users/{user_id}/block", status_code=204)
def block_user(
    user_id: str,
    payload: BlockUserRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """
    SRS §4.4 REQ-4..6:
      - mark user SUSPENDED → get_current_user denies further requests
      - add email to BLACKLIST → registration is blocked
      - disable in Supabase Auth → token refresh is revoked
      - write audit log
    """
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if str(target.id) == str(admin.id):
        raise HTTPException(status_code=400, detail="Cannot block yourself")

    target.status = UserStatus.SUSPENDED

    if not db.query(Blacklist).filter(Blacklist.email == target.email).first():
        db.add(Blacklist(email=target.email, reason=payload.reason))

    db.add(AdminAuditLog(
        admin_id=admin.id,
        target_id=str(target.id),
        action_type="BLOCK_USER",
        reason=payload.reason,
    ))
    db.commit()

    # Disable in Supabase Auth so existing refresh tokens become invalid.
    # "876600h" ≈ 100 years — effectively permanent.
    try:
        supabase_admin = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
        supabase_admin.auth.admin.update_user_by_id(
            str(target.supabase_uid),
            {"ban_duration": "876600h"},
        )
    except Exception:
        # Local suspension is the authoritative gate; Supabase ban is best-effort.
        pass
