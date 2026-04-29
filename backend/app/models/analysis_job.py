"""
ANALYSIS_JOBS table — SRS Appendix B Figure B.3.

Tracks an asynchronous analysis run for a URL (SRS §4.5 REQ-5, §4.6).
Created when a new URL is submitted; updated by ai-worker as the pipeline
progresses.
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, Float, ForeignKey, Integer
from sqlalchemy.dialects.mysql import CHAR

from app.core.database import Base


class JobStatus(str, enum.Enum):
    PENDING = "PENDING"
    CRAWLING = "CRAWLING"
    ANALYZING = "ANALYZING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class AnalysisJob(Base):
    __tablename__ = "analysis_jobs"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    url_id = Column(CHAR(36), ForeignKey("urls.id"), nullable=False, index=True)
    status = Column(Enum(JobStatus), nullable=False, default=JobStatus.PENDING)

    # Score components — SRS §4.7 REQ-2
    ai_score = Column(Float, nullable=True)       # output of NLP model
    report_count = Column(Integer, nullable=True) # # of user reports for the URL
    final_risk_score = Column(Integer, nullable=True)  # 0–100, §4.7 REQ-3/4

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
