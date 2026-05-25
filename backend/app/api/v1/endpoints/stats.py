"""Public platform stats — homepage counters."""
from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.url import RiskLevel, Url
from app.models.user import User, UserStatus
from app.schemas.stats import PlatformStats

router = APIRouter()


@router.get("", response_model=PlatformStats)
def get_platform_stats(db: Session = Depends(get_db)) -> PlatformStats:
    shops_analyzed = (
        db.query(func.count(Url.id))
        .filter(Url.current_risk_score.isnot(None))
        .scalar()
        or 0
    )
    scam_sites_blocked = (
        db.query(func.count(Url.id))
        .filter(Url.current_risk_level.in_([RiskLevel.DANGER, RiskLevel.CRITICAL]))
        .scalar()
        or 0
    )
    users_protected = (
        db.query(func.count(User.id))
        .filter(User.status == UserStatus.ACTIVE)
        .scalar()
        or 0
    )
    return PlatformStats(
        shops_analyzed=shops_analyzed,
        scam_sites_blocked=scam_sites_blocked,
        users_protected=users_protected,
    )
