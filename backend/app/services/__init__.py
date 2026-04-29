"""
Service layer (currently empty).

When endpoint files grow past trivial CRUD, extract reusable logic here:

  - auth_service.py     — multi-step flows (registration + welcome email)
  - report_service.py   — moderation pipeline, evidence-image uploads
  - analysis_service.py — orchestrates the cache-vs-enqueue decision
  - risk_score_service.py — re-computation after report-status changes

Currently endpoints are thin enough that we keep logic inline.
"""
