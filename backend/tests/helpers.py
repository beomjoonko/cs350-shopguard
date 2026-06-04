"""Shared helper functions for test data setup."""
from app.core.security import hash_password, create_access_token
from app.models.user import User, UserRole, UserStatus


def make_user(db, email, password, role=UserRole.USER, status=UserStatus.ACTIVE):
    user = User(
        email=email,
        password_hash=hash_password(password),
        role=role,
        status=status,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_token(user):
    return create_access_token(
        subject=user.id,
        role=user.role.value,
        token_version=user.token_version,
    )
