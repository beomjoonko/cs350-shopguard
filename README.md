# ShopGuard

> SaaS-based fraud prevention system for e-commerce. Crowdsourced fraud reporting + AI-driven Risk Score analysis.

This repository is a **monorepo skeleton** generated from the ShopGuard SRS v1.0 (KAIST CS350, Team 2). It contains scaffolding for all components defined in the SRS — wired together with Docker Compose for local development.

## Architecture

```
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│   Frontend   │◄────►│   Backend    │◄────►│   AI Worker  │
│  (Next.js)   │ HTTP │  (FastAPI)   │ Queue│   (Python)   │
└──────────────┘      └──────┬───────┘      └──────┬───────┘
                             │                     │
                      ┌──────▼─────────────────────▼───────┐
                      │        MySQL  +  Redis             │
                      │  (persistent storage + cache/queue)│
                      └────────────────────────────────────┘
```

## Repository Layout

```
shopguard/
├── backend/         # FastAPI REST API server  (SRS §2.1.1.2, §3.4)
├── ai-worker/       # Async NLP analysis worker (SRS §4.6)
├── frontend/        # Next.js web client       (SRS §3.1)
├── infra/           # Nginx, MySQL init scripts
├── docs/            # SRS, API spec, setup guides
├── docker-compose.yml
├── .env.example
└── Makefile
```

## SRS → Code Mapping

| SRS Section | Feature | Implementation Location |
|---|---|---|
| §4.1 | User Account Management | `backend/app/api/v1/endpoints/auth.py` |
| §4.2 | Fraud Reporting System | `backend/app/api/v1/endpoints/reports.py` |
| §4.3 | User Page | `backend/app/api/v1/endpoints/users.py` + `frontend/src/app/my-page` |
| §4.4 | Admin Features | `backend/app/api/v1/endpoints/admin.py` + `frontend/src/app/admin` |
| §4.5 | URL Analysis Service | `backend/app/api/v1/endpoints/analysis.py` |
| §4.6 | AI Analysis Pipeline | `ai-worker/worker/pipeline/` |
| §4.7 | Risk Score Model | `ai-worker/worker/scoring/risk_scorer.py` |
| §4.8 | System Guardrails | `backend/app/middleware/rate_limit.py` |
| §5.3 | Security (JWT + Argon2) | `backend/app/core/security.py` |

## ERD → ORM Mapping (SRS Appendix B Figure B.3)

| Table | SQLAlchemy Model |
|---|---|
| `users` | `backend/app/models/user.py` |
| `reports` | `backend/app/models/report.py` |
| `urls` | `backend/app/models/url.py` |
| `analysis_jobs` | `backend/app/models/analysis_job.py` |
| `admin_audit_logs` | `backend/app/models/admin_audit_log.py` |
| `blacklist` | `backend/app/models/blacklist.py` |

## Quick Start

### Prerequisites
- Docker & Docker Compose
- (Optional) Python 3.11+, Node.js 20+ for local non-Docker dev

### Run everything

```bash
cp .env.example .env # copy .env.example .env
make up            # docker compose up --build
```

Then open:
- Frontend → http://localhost:3000
- Backend API docs → http://localhost:8000/docs
- MySQL → localhost:3306
- Redis → localhost:6379

### Run database migrations

```bash
make migrate
```

## Testing

Each layer has **one consolidated test suite**, backed by a human-readable case
catalogue in `docs/`. File names follow a unified `test_be` / `test_wk` /
`test_fe` scheme.

| Layer | Test file | Case catalogue | Cases |
|---|---|---|---|
| Backend (FastAPI) | `backend/tests/test_be.py` | `docs/backend_test_cases.csv` | TC-01–TC-65 |
| AI Worker (pipeline + scoring) | `ai-worker/tests/test_wk.py` | `docs/worker_test_cases.csv` | WT-01–WT-26 |
| Frontend (Next.js) | `frontend/src/__tests__/test_fe_lib.test.tsx` + `test_fe_pages.test.tsx` | `docs/frontend_test_cases.csv` | FT-01–FT-27 |

Two backend suites are kept separate by design:
- `backend/tests/test_smoke.py` — health/liveness smoke check
- `backend/tests/test_mutation_lockout.py` — mutation testing of the lockout logic (own runner)

### What each suite covers

- **Backend** — REST endpoints (register, login + 5-attempt lockout, password
  change, URL analysis, fraud reports, my-page, admin), an auth-enforcement
  sweep over every protected route (TC-57), and security-config gates
  (JWT secret strength, CORS — TC-60–65). Runs on in-memory SQLite, no external
  services. The frontend split (`_lib` vs `_pages`) exists because the page
  tests `jest.mock("@/lib/api")`, which would otherwise shadow the real client.
- **AI Worker** — risk-score formula & level thresholds, NLP score blend /
  fetch-failure fallback, URL feature extraction + ONNX classifier sanity, and
  regression guards documenting known feature-extraction anomalies. Loads local
  model artifacts only.
- **Frontend** — pure lib logic (token/JWT decode, recent searches, label maps,
  HTTP client 401/204/error handling) plus page-component bug documentation.
  Runs in jsdom with `fetch` mocked.

### How to run

Each `make` target runs only that layer's consolidated case suite:

```bash
make test-backend     # docker compose exec backend pytest tests/test_be.py -v
make test-frontend    # docker compose exec frontend npm test -- test_fe
make test-worker      # docker compose exec ai-worker python -m pytest tests/test_wk.py -v
```

Narrower / ad-hoc runs:

```bash
docker compose exec backend pytest tests/test_be.py -k tc09   # one TC group
cd frontend && npm install && npm test -- test_fe_lib         # local, one file
```

Tests **not** covered by the `make` targets (run explicitly):

```bash
docker compose exec backend pytest tests/test_smoke.py -v             # smoke
docker compose exec backend pytest tests/test_mutation_lockout.py -v  # mutation
docker compose exec backend pytest -v                                 # every backend test
make up && docker compose exec backend pytest tests/test_be.py -k "tc36 or tc37"  # Redis rate limit
```

### Expected results

| Suite | Command | Expected |
|---|---|---|
| Backend | `pytest tests/test_be.py` | **84 passed, 3 skipped, 1 xfail/xpass** |
| Worker | `pytest tests/test_wk.py` | **44 passed, 1 xfailed** |
| Frontend | `npm test` | **32 passed** (2 suites) |

Counts above are for a configured local run (`.env` present). In CI there is no
`.env`, so the deployment-gate tests (TC-60/61/64) skip and the backend shows
**81 passed, 6 skipped**.

Intentional non-passes (these are **not** failures):

- **Skipped — backend (3):** TC-19 (DANGER/CRITICAL modal is frontend-only) and
  TC-36/37 (need a live Redis rate limiter). Run the rate-limit pair against a
  running stack: `make up && docker compose exec backend pytest tests/test_be.py -k "tc36 or tc37"`.
- **Skipped under default config — backend:** TC-60/61/64 are security-config
  deployment gates; they enforce only when a real `.env` overrides the JWT secret
  (so they pass locally and skip in CI rather than failing on placeholder config).
- **xfail — backend TC-09a:** the lockout race condition is non-deterministic on
  the in-memory SQLite harness (single shared connection); faithful concurrency
  needs the MySQL backend.
- **xfail — worker WT-21:** the URL classifier ranks a `.xyz` phishing URL below
  `paypal.com` — a known domain-mismatch model-quality gap, tracked until retrain.
- **Frontend FT-24/25** use Jest `it.failing` to document BUG-2 (admin status
  filter missing `SUBMITTED`) while keeping the suite green; flip to `it` once fixed.

The `Pass/Fail` column in each `docs/*_test_cases.csv` is intentionally blank for
manual QA sign-off; only the xfail rows are pre-marked.

## Open Questions (from SRS Appendix C)

The skeleton does **not** resolve the TBDs in the SRS. Each is left as a placeholder with `# TBD` comments:

- TBD-1: Risk Score formula → `ai-worker/worker/scoring/risk_scorer.py`
- TBD-2: Anti-bot bypass strategy → `ai-worker/worker/crawler/`
- TBD-3: NLP model selection → `ai-worker/worker/pipeline/nlp_analyzer.py`
- TBD-4: Default UI language → `frontend/src/lib/i18n.ts` (not yet created)
- TBD-5: PII masking on evidence images → `backend/app/services/report_service.py`
- TBD-6: Cloud provider choice → `infra/`
- TBD-7: Legal disclaimer wording → `frontend/src/components/report/`

## License

For academic use (KAIST CS350, Spring 2026).
