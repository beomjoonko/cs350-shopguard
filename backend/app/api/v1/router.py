"""Aggregate router for /api/v1/*."""
from fastapi import APIRouter

from app.api.v1.endpoints import auth, reports, users, admin, analysis, stats

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
api_router.include_router(analysis.router, prefix="/analysis", tags=["analysis"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(stats.router, prefix="/stats", tags=["stats"])
