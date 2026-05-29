"""
ShopGuard API — entry point.

Stitches together: routers, middleware (CORS + rate limit per SRS §4.8),
and lifespan events for DB connections.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api.v1.router import api_router
from app.middleware.rate_limit import check_rate_limit


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# CORS — SRS §3.4 (HTTPS + REST + JSON between client and server)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Rate limit — SRS §4.8 REQ-1 (60 req/min per IP)."""
    await check_rate_limit(request)
    return await call_next(request)


# Routes
app.include_router(api_router, prefix="/api/v1")


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok", "version": settings.APP_VERSION}
