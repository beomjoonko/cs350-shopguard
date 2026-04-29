"""Pydantic schemas for URL search and analysis — SRS §4.5."""
from datetime import datetime
from pydantic import BaseModel, HttpUrl

from app.models.url import RiskLevel
from app.models.analysis_job import JobStatus


class UrlSearchRequest(BaseModel):
    url: HttpUrl


class UrlAnalysisResult(BaseModel):
    """Returned to user after URL search — SRS §4.5."""
    url: str
    risk_score: int | None = None       # 0–100, may be None while analyzing
    risk_level: RiskLevel | None = None
    report_count: int = 0
    last_analyzed_at: datetime | None = None
    job_id: str | None = None           # set when a new analysis was kicked off
    cached: bool = False


class AnalysisJobStatus(BaseModel):
    job_id: str
    status: JobStatus
    final_risk_score: int | None = None
    risk_level: RiskLevel | None = None

    class Config:
        from_attributes = True
