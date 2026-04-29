# API Reference (v1)

The canonical API spec is the auto-generated OpenAPI document at
`http://localhost:8000/openapi.json` (and the Swagger UI at `/docs`).

This file is a hand-written cheat sheet for the most-used endpoints.
All paths are prefixed with `/api/v1`.

## Auth — `/auth`

| Method | Path | Auth | Body |
|---|---|---|---|
| POST | `/auth/register` | — | `{ email, password }` |
| POST | `/auth/login` | — | `{ email, password }` → `{ access_token }` |
| POST | `/auth/password-reset/request` | — | `{ email }` |

Login enforces SRS §4.1 REQ-3 (5 failed attempts → 30-minute lockout).

## Users — `/users`  (auth required)

| Method | Path | Returns |
|---|---|---|
| GET  | `/users/me` | current user |
| GET  | `/users/me/reports` | own reports (SRS §4.3 REQ-1, REQ-4) |
| POST | `/users/me/password` | 204 (SRS §4.3 REQ-5, REQ-6) |

## Reports — `/reports`  (auth required)

| Method | Path | Body / Notes |
|---|---|---|
| POST | `/reports` | `{ url, fraud_type, description, evidence_image_url?, legal_consent }` — REQ-3 enforced |
| GET  | `/reports/{id}` | own only, unless admin |

## Analysis — `/analysis`  (auth required)

| Method | Path | Notes |
|---|---|---|
| POST | `/analysis/search` | normalize → cache → enqueue if missing |
| GET  | `/analysis/jobs/{job_id}` | poll until `status == COMPLETED` |

## Admin — `/admin`  (admin only)

| Method | Path | Notes |
|---|---|---|
| GET   | `/admin/reports` | all reports |
| PATCH | `/admin/reports/{id}` | `{ status: "ACTIVE" \| "HIDDEN" \| "PENDING" }` |
| POST  | `/admin/users/{user_id}/block` | `{ reason }` — adds to blacklist + audit log |

## Rate limit

All endpoints share a 60 req / minute / IP limit (SRS §4.8 REQ-1).
Exceeding it returns `429 Too Many Requests`.
