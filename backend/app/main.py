"""
ShopGuard API — entry point.

Stitches together: routers, middleware (CORS + rate limit per SRS §4.8),
exception handlers, and lifespan events for DB/Redis connections.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.api.v1.router import api_router
from app.middleware.rate_limit import limiter


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: warm DB connections, ping Redis, etc.
    # TODO: ping_redis(), check_db_connection()
    yield
    # Shutdown: close pools


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

# Rate limit — SRS §4.8 REQ-1 (60 req/min per IP)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Routes
app.include_router(api_router, prefix="/api/v1")


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok", "version": settings.APP_VERSION}
