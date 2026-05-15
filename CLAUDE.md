# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ShopGuard is a SaaS fraud prevention system for e-commerce (KAIST CS350, Team 2). Users submit URLs or fraud reports; an async AI pipeline scores the URL's risk level using crawled data + crowdsourced reports.

## Common Commands

All commands assume Docker is running. Use `make` targets as the primary interface:

```bash
# Start all services (MySQL, Redis, backend, ai-worker, frontend)
make up

# Stop all services
make down

# View logs (all services)
make logs

# Run DB migrations
make migrate

# Generate a new migration
make revision m="describe your change"

# Run backend tests
make test-backend

# Run frontend tests
make test-frontend

# Lint everything
make lint
```

### Running a single backend test

```bash
docker compose exec backend pytest tests/test_smoke.py::test_health -v
```

### Running backend lint only

```bash
docker compose exec backend ruff check app/
```

### Local (non-Docker) backend development

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Local frontend development

```bash
cd frontend
npm install
npm run dev     # http://localhost:3000
npm run build   # production build check
npm run lint
```

## Architecture

### System Overview

```
Frontend (Next.js 14)
    ↕ HTTP/JSON
Backend (FastAPI :8000) ──BLPOP→ Redis queue ──→ AI Worker (Python)
    ↕                                                    ↕
   MySQL 8.0  ←──────────────────────────────────────────
```

### URL Analysis Data Flow

1. Frontend `POST /analysis/search` → backend normalizes URL, checks Redis cache
2. Cache miss → backend creates `AnalysisJob` (PENDING) and enqueues `{job_id, url}` to Redis key `shopguard:queue:analysis`
3. Frontend polls `GET /analysis/jobs/{id}` every 2 seconds
4. AI worker dequeues via BLPOP → runs pipeline: **crawl → preprocess → feature extract → NLP score → risk score**
5. Worker updates `urls` table and caches result in Redis for 24 hours (key prefix `shopguard:url:`)
6. Frontend displays result; DANGER/CRITICAL triggers warning modal

### Risk Score Formula

```
report_score  = min(report_count × 10, 100)
ai_score      = weighted_sum(features)  # see nlp_analyzer.py
final_score   = round(0.7 × ai_score + 0.3 × report_score)   # TBD-1
level         = SAFE(0–30) | WARNING(31–60) | DANGER(61–80) | CRITICAL(81–100)
```

AI score weights: `review_repetition_rate(×40) + rating_skew(×30) + price_anomaly(×20) + image_similarity(×10)`. `price_anomaly` and `image_similarity` are currently always 0.0 (placeholders).

### Backend (`backend/app/`)

- **`core/`** — DB session (`database.py`), Redis client + queue helpers (`redis.py`), JWT + Argon2id security (`security.py`), FastAPI dependency injection (`dependencies.py`)
- **`api/v1/endpoints/`** — `auth.py` (register/login/password-reset), `users.py` (me, my reports, change password), `reports.py` (submit/view fraud report), `analysis.py` (search URL, poll job), `admin.py` (list reports, update status, block user)
- **`models/`** — SQLAlchemy ORM: `User`, `Report`, `Url`, `AnalysisJob`, `AdminAuditLog`, `Blacklist`
- **`schemas/`** — Pydantic v2 request/response models
- **`utils/url_normalizer.py`** — Canonical URL normalization (strips tracking params, sorts query string, drops default ports); used in both `/reports` and `/analysis/search`
- **`middleware/rate_limit.py`** — slowapi (Redis-backed), 60 req/min per IP; returns 429

Authentication flow: JWT Bearer token (HS256). `get_current_user()` dependency validates token and rejects SUSPENDED users. `require_admin()` adds ADMIN role check on top.

Account lockout: 5 failed logins → `locked_until = now + 30 min`. Checked on every login attempt.

### AI Worker (`ai-worker/worker/`)

- **`main.py`** — Blocking event loop: BLPOP → `process_job()` → pipeline → DB/Redis update. Sleeps `CRAWLER_REQUEST_DELAY_MS` between jobs.
- **`crawler/`** — `dispatch_crawler(url)` routes by hostname. `coupang.py`, `aliexpress.py`, `temu.py` are **stubs** returning empty `CrawlResult`. Anti-bot strategy is TBD-2.
- **`pipeline/preprocessor.py`** — Deduplicates and lowercases review text
- **`pipeline/feature_extractor.py`** — Returns 6 features from `CrawlResult` (review_repetition_rate, rating_skew, price_anomaly, image_similarity, review_count, has_product)
- **`pipeline/nlp_analyzer.py`** — Linear weighted sum → AI score 0–100. Replace with trained model when TBD-3 is resolved.
- **`scoring/risk_scorer.py`** — `compute_final_risk_score(ai_score, report_count)` and `score_to_level(score)`

### Frontend (`frontend/src/`)

- **`lib/api.ts`** — Single HTTP client; all backend calls go here. Reads `NEXT_PUBLIC_API_BASE_URL`. Handles 401 by clearing token.
- **`lib/auth.ts`** — `getToken()` / `setToken()` / `clearToken()` using `localStorage` key `shopguard.token`. SSR-safe.
- **`app/search/page.tsx`** — Polls job status every 2s, shows risk badge, triggers DANGER/CRITICAL modal
- **`app/report/page.tsx`** — Fraud report form; requires `legal_consent=true` and description ≥ 20 chars
- **`app/admin/page.tsx`** — Admin dashboard; report status management and user blocking

### Database Schema (key relationships)

```
users ──< reports >── urls ──< analysis_jobs
users ──< admin_audit_logs
blacklist (email)
```

All PKs are UUID (CHAR 36). `reports.status` has 8 states; `analysis_jobs.status` tracks pipeline progress (PENDING → CRAWLING → ANALYZING → COMPLETED/FAILED).

## Key Unresolved Items (SRS Appendix C TBDs)

| ID | Where | Status |
|---|---|---|
| TBD-1 | `scoring/risk_scorer.py` | Formula uses placeholder weights |
| TBD-2 | `crawler/*.py` | All crawlers are stubs; anti-bot strategy undecided |
| TBD-3 | `pipeline/nlp_analyzer.py` | NLP model not selected; linear placeholder in use |
| TBD-4 | `frontend/src/lib/i18n.ts` | File not yet created |
| TBD-5 | `backend/app/services/report_service.py` | PII masking not implemented |

Additional in-code TODOs: password reset email (SMTP), JWT denylist for immediate session revocation after user block, price anomaly detection, image similarity scoring.

## Environment Variables

Copy `.env.example` to `.env` before running. Critical variables:

- `DATABASE_URL` — MySQL connection string
- `JWT_SECRET_KEY` — Must be set; used for all token signing
- `REDIS_HOST` / `REDIS_PORT`
- `NEXT_PUBLIC_API_BASE_URL` — Backend URL seen by browser (default `http://localhost:8000/api/v1`)
- `S3_*` — Object storage for evidence images (not required for local dev without image upload)
