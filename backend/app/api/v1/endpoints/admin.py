"""
Admin endpoints — SRS §4.4.

  GET   /admin/reports                   list all reports (REQ-2)
  PATCH /admin/reports/{report_id}       set status (REQ-3)
  POST  /admin/users/{user_id}/block     suspend user + revoke sessions (REQ-4..6)
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_admin
from app.models.admin_audit_log import AdminAuditLog
from app.models.blacklist import Blacklist
from app.models.report import Report
from app.models.user import User, UserStatus
from app.schemas.admin import BlockUserRequest
from app.schemas.report import ReportPublic, ReportStatusUpdate

router = APIRouter()


@router.get("/reports", response_model=list[ReportPublic])
def list_reports(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """SRS §4.4 REQ-2 — admins see all reports."""
    return db.query(Report).order_by(Report.created_at.desc()).all()


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
        target_id=report.id,
        action_type="UPDATE_REPORT_STATUS",
        reason=f"{old_status.value} -> {payload.status.value}",
    ))
    db.commit()
    db.refresh(report)
    return report


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
      - write audit log

    NOTE: real session revocation would also push the JTI to a Redis denylist
          checked by `decode_token`. Marked as TODO for now.
    """
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if target.id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot block yourself")

    target.status = UserStatus.SUSPENDED
    target.locked_until = None

    if not db.query(Blacklist).filter(Blacklist.email == target.email).first():
        db.add(Blacklist(email=target.email, reason=payload.reason))

    db.add(AdminAuditLog(
        admin_id=admin.id,
        target_id=target.id,
        action_type="BLOCK_USER",
        reason=payload.reason,
    ))
    db.commit()
    # TODO: invalidate any active JWTs by adding their jti to a Redis denylist
