"""
User Page endpoints — SRS §4.3.

  GET  /users/me            account info
  GET  /users/me/reports    list of reports submitted by current user (REQ-1)

Password change is handled directly by the frontend via
supabase.auth.updateUser({ password: newPassword }) — no backend endpoint needed.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.report import Report
from app.models.url import Url
from app.models.user import User
from app.schemas.report import ReportPublic
from app.schemas.user import UserPublic
from app.utils.report_public import report_to_public

router = APIRouter()


@router.get("/me", response_model=UserPublic)
def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("/me/reports", response_model=list[ReportPublic])
def my_reports(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """SRS §4.3 REQ-1, REQ-4 (access control: own reports only)."""
    rows = (
        db.query(Report, Url)
        .join(Url, Report.url_id == Url.id)
        .filter(Report.user_id == current_user.id)
        .order_by(Report.created_at.desc())
        .all()
    )
    return [report_to_public(report, url_row) for report, url_row in rows]
