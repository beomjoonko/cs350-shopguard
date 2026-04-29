"""
User Page endpoints — SRS §4.3.

  GET  /users/me            account info
  GET  /users/me/reports    list of reports submitted by current user (REQ-1)
  POST /users/me/password   change password (REQ-5, REQ-6)
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.security import hash_password, verify_password
from app.models.report import Report
from app.models.user import User
from app.schemas.report import ReportPublic
from app.schemas.user import PasswordChange, UserPublic

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
    return (
        db.query(Report)
        .filter(Report.user_id == current_user.id)
        .order_by(Report.created_at.desc())
        .all()
    )


@router.post("/me/password", status_code=204)
def change_password(
    payload: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """SRS §4.3 REQ-5: new password must differ from the current one."""
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(status_code=401, detail="Current password is incorrect")
    if payload.current_password == payload.new_password:
        raise HTTPException(
            status_code=400,
            detail="New password must differ from the current one",
        )
    current_user.password_hash = hash_password(payload.new_password)
    db.commit()
