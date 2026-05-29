"""
Auth endpoints — post-Supabase migration.

  POST /auth/register   blacklist check → create Supabase Auth user via Admin
                        API → auto-provision local users row

Login, password-change, and password-reset are now handled entirely by the
Supabase JS SDK on the frontend. FastAPI only manages the one-time registration
gate (blacklist check) that requires server-side enforcement.
"""
import uuid as _uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from supabase import create_client

from app.config import settings
from app.core.database import get_db
from app.models.blacklist import Blacklist
from app.models.user import User, UserRole, UserStatus
from app.schemas.user import UserPublic, UserRegister

router = APIRouter()


def _supabase_admin():
    """Return a Supabase client authenticated with the service-role key."""
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)


@router.post("/register", response_model=UserPublic, status_code=201)
def register(payload: UserRegister, db: Session = Depends(get_db)):
    """
    Register a new account.

    Flow:
      1. Enforce blacklist (SRS §4.4 REQ-5)
      2. Check for local duplicate
      3. Create Supabase Auth user via Admin API (bypasses email confirmation)
      4. Create local users row with the Supabase Auth UUID as supabase_uid
    """
    # 1. Blacklist gate
    if db.query(Blacklist).filter(Blacklist.email == payload.email).first():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This email is not allowed to register",
        )

    # 2. Local duplicate guard
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    # 3. Create user in Supabase Auth
    try:
        auth_response = _supabase_admin().auth.admin.create_user({
            "email": payload.email,
            "password": payload.password,
            "email_confirm": True,  # skip email confirmation in dev
        })
    except Exception as exc:
        # Supabase returns an error if the email already exists in auth.users
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Registration failed: {exc}",
        )

    supabase_uid = _uuid.UUID(str(auth_response.user.id))

    # 4. Provision local users row
    user = User(
        supabase_uid=supabase_uid,
        email=payload.email,
        role=UserRole.USER,
        status=UserStatus.ACTIVE,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
