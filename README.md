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

### Run tests

```bash
make test-backend
make test-frontend
```

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
