"""TC-01 – TC-65: Full backend test-case suite (consolidated).

Single source of truth for the backend test cases catalogued in
docs/backend_test_cases.csv. Absorbs what were previously many per-area files
(registration / login / password / analysis / report / mypage / admin /
ratelimit) plus the former test_qa_auth.py (TC-57–59) and test_qa_security.py
(TC-60–65).

All tests share the fixtures in conftest.py (client, db, regular_user,
admin_user, auth_headers, admin_headers). Sections are separated by banner
comments; helper functions are namespaced per area to avoid collisions.

Notes:
  * enqueue_analysis_job is mocked wherever a Redis enqueue would otherwise fire.
  * TC-19 (DANGER/CRITICAL modal) is frontend-only and skipped here.
  * TC-09a (lockout race) is xfail on the SQLite harness — needs MySQL.
  * TC-36 / TC-37 (rate limiting) need a live Redis-backed middleware and are
    skipped in the unit suite — run them in Docker:
        docker compose exec backend pytest tests/test_be.py -k "tc36 or tc37"

Run: docker compose exec backend pytest tests/test_be.py -v
"""
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from tests.helpers import make_user, get_token
from app.config import settings
from app.models.admin_audit_log import AdminAuditLog
from app.models.analysis_job import AnalysisJob, JobStatus
from app.models.blacklist import Blacklist
from app.models.report import Report, ReportStatus, FraudType
from app.models.url import Url, RiskLevel
from app.models.password_reset_token import PasswordResetToken
from app.models.user import User, UserStatus, UserRole
from app.utils.reset_token import hash_reset_token
from app.utils.url_normalizer import normalize_url

# ── Endpoint paths ──────────────────────────────────────────────────────────
REGISTER = "/api/v1/auth/register"
LOGIN = "/api/v1/auth/login"
RESET_REQUEST = "/api/v1/auth/password-reset/request"
RESET_CONFIRM = "/api/v1/auth/password-reset/confirm"
PASSWORD = "/api/v1/users/me/password"
SEARCH = "/api/v1/analysis/search"
JOBS = "/api/v1/analysis/jobs"
REPORTS = "/api/v1/reports"
ME = "/api/v1/users/me"
MY_REPORTS = "/api/v1/users/me/reports"
ADMIN_REPORTS = "/api/v1/admin/reports"
ADMIN_BLOCK = "/api/v1/admin/users/{user_id}/block"

# Patch targets for enqueue_analysis_job (imported into each endpoint module).
_MOCK_ANALYSIS_ENQUEUE = "app.api.v1.endpoints.analysis.enqueue_analysis_job"
_MOCK_ADMIN_ENQUEUE = "app.api.v1.endpoints.admin.enqueue_analysis_job"


# ── Shared helpers ──────────────────────────────────────────────────────────
def _seed_report(db, user, url_str, fraud_type=FraudType.NON_DELIVERY, description="A" * 25):
    """Insert a Url + Report owned by `user`; returns the Report."""
    normalized = normalize_url(url_str)
    url_row = Url(
        normalized_url=normalized,
        normalized_url_hash=Url.compute_hash(normalized),
    )
    db.add(url_row)
    db.flush()
    report = Report(
        user_id=user.id,
        url_id=url_row.id,
        fraud_type=fraud_type,
        description=description,
        legal_consent=True,
        status=ReportStatus.SUBMITTED,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


# ════════════════════════════════════════════════════════════════════════════
# TC-01 – TC-05: User Registration (POST /auth/register)
# ════════════════════════════════════════════════════════════════════════════
def _register_payload(email="new@example.com", password="Secure1!pass"):
    return {"email": email, "password": password}


# TC-01 — successful registration
def test_tc01_successful_registration(client):
    res = client.post(REGISTER, json=_register_payload())
    assert res.status_code == 201
    body = res.json()
    assert body["email"] == "new@example.com"
    assert body["role"] == "USER"
    assert body["status"] == "ACTIVE"
    assert "id" in body


# TC-02 — duplicate email
def test_tc02_duplicate_email(client):
    client.post(REGISTER, json=_register_payload())
    res = client.post(REGISTER, json=_register_payload())
    assert res.status_code == 409
    assert "already registered" in res.json()["detail"].lower()


# TC-03 — password too short (< 8 chars → Pydantic 422)
def test_tc03_password_too_short(client):
    res = client.post(REGISTER, json=_register_payload(password="short"))
    assert res.status_code == 422


# TC-03b — password missing number or special character (SRS §4.3 REQ-6)
def test_tc03b_password_missing_complexity(client):
    res = client.post(REGISTER, json=_register_payload(password="12345678"))
    assert res.status_code == 422
    res2 = client.post(REGISTER, json=_register_payload(email="no-special@example.com", password="Abcdefg1"))
    assert res2.status_code == 422


# TC-04 — invalid email format (Pydantic 422)
def test_tc04_invalid_email_format(client):
    res = client.post(REGISTER, json={"email": "not-an-email", "password": "Secure1!pass"})
    assert res.status_code == 422


# ── Password reset (SRS §4.1 REQ-2) ─────────────────────────────────────────

def _token_from_reset_url(url: str) -> str:
    from urllib.parse import parse_qs, urlparse
    return parse_qs(urlparse(url).query)["token"][0]


@patch("app.services.password_reset.send_password_reset_email")
def test_password_reset_request_unknown_email(mock_send, client):
    res = client.post(RESET_REQUEST, json={"email": "nobody@example.com"})
    assert res.status_code == 202
    mock_send.assert_not_called()


@patch("app.services.password_reset.send_password_reset_email")
def test_password_reset_flow(mock_send, client, regular_user):
    res = client.post(RESET_REQUEST, json={"email": "user@example.com"})
    assert res.status_code == 202
    mock_send.assert_called_once()
    raw_token = _token_from_reset_url(mock_send.call_args[0][1])

    old_token = get_token(regular_user)
    confirm = client.post(
        RESET_CONFIRM,
        json={"token": raw_token, "new_password": "Reset1!pass"},
    )
    assert confirm.status_code == 204

    login = client.post(LOGIN, json={"email": "user@example.com", "password": "Reset1!pass"})
    assert login.status_code == 200

    me_old = client.get(ME, headers={"Authorization": f"Bearer {old_token}"})
    assert me_old.status_code == 401

    reuse = client.post(
        RESET_CONFIRM,
        json={"token": raw_token, "new_password": "Another1!x"},
    )
    assert reuse.status_code == 400


def test_password_reset_confirm_invalid_token(client):
    res = client.post(
        RESET_CONFIRM,
        json={"token": "not-a-valid-stored-token-xyz", "new_password": "Reset1!pass"},
    )
    assert res.status_code == 400


@patch("app.services.password_reset.send_password_reset_email")
def test_password_reset_expired_token(mock_send, client, db, regular_user):
    client.post(RESET_REQUEST, json={"email": "user@example.com"})
    raw_token = _token_from_reset_url(mock_send.call_args[0][1])
    row = db.query(PasswordResetToken).filter(
        PasswordResetToken.token_hash == hash_reset_token(raw_token)
    ).first()
    row.expires_at = datetime.utcnow() - timedelta(minutes=1)
    db.commit()

    res = client.post(
        RESET_CONFIRM,
        json={"token": raw_token, "new_password": "Reset1!pass"},
    )
    assert res.status_code == 400


# TC-05 — blacklisted email
def test_tc05_blacklisted_email(client, db):
    db.add(Blacklist(email="blocked@example.com", reason="test"))
    db.commit()

    res = client.post(REGISTER, json=_register_payload(email="blocked@example.com"))
    assert res.status_code == 403
    assert "not allowed" in res.json()["detail"].lower()


# ════════════════════════════════════════════════════════════════════════════
# TC-06 – TC-12: Login (POST /auth/login)
# ════════════════════════════════════════════════════════════════════════════
def _creds(email="user@example.com", password="Passw0rd!"):
    return {"email": email, "password": password}


# TC-06 — successful login returns access_token
def test_tc06_successful_login(client, regular_user):
    res = client.post(LOGIN, json=_creds())
    assert res.status_code == 200
    body = res.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


# TC-07 — unknown email
def test_tc07_unknown_email(client):
    res = client.post(LOGIN, json=_creds(email="nobody@example.com"))
    assert res.status_code == 401
    assert "invalid credentials" in res.json()["detail"].lower()


# TC-08 — correct email, wrong password
def test_tc08_wrong_password(client, regular_user):
    res = client.post(LOGIN, json=_creds(password="wrongpass"))
    assert res.status_code == 401
    assert "invalid credentials" in res.json()["detail"].lower()


# TC-09 — 5 consecutive failed logins → account locked (HTTP 423)
def test_tc09_five_failed_logins_locks_account(client, db, regular_user):
    for _ in range(5):
        client.post(LOGIN, json=_creds(password="wrong"))

    # 6th attempt — even with correct password — returns 423
    res = client.post(LOGIN, json=_creds())
    assert res.status_code == 423
    assert "locked" in res.json()["detail"].lower()

    # DB 검증: 잠금 발생 시 failed_login_attempts는 0으로 리셋됨 (auth.py:90)
    db.expire_all()
    user = db.query(User).filter(User.email == "user@example.com").first()
    assert user.failed_login_attempts == 0
    assert user.locked_until is not None


# TC-09a — 잠금 카운터 race condition: 동시 실패 요청에도 카운터가 원자적으로 처리됨
# NON-DETERMINISTIC on the in-memory SQLite harness: StaticPool shares a single
# connection, so concurrent atomic UPDATEs are serialized/lost differently than
# on production MySQL — the assertion intermittently sees counter=4 (no lock).
# Faithful concurrency verification requires the MySQL backend; xfail here so the
# unit suite stays deterministic (passes as xpass when the increments don't race).
@pytest.mark.xfail(
    reason="Concurrency race test is non-deterministic on in-memory SQLite "
    "(StaticPool single connection). Run against MySQL/Docker for a faithful result.",
    strict=False,
)
def test_tc09a_lockout_counter_race_condition(client, db, regular_user):
    import threading

    # 한 번 잠갔다가 즉시 만료시켜 깨끗한 상태에서 동시성만 검증
    for _ in range(5):
        client.post(LOGIN, json=_creds(password="wrong"))
    db.expire_all()
    user = db.query(User).filter(User.email == "user@example.com").first()
    user.locked_until = datetime.utcnow() - timedelta(seconds=1)  # 즉시 만료
    user.failed_login_attempts = 0
    db.commit()

    # 잘못된 비밀번호 요청 5개를 동시에 발사 → 원자적 UPDATE면 정확히 5 누적 → 잠금
    def fire():
        client.post(LOGIN, json=_creds(password="wrong"))

    threads = [threading.Thread(target=fire) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    db.expire_all()
    user = db.query(User).filter(User.email == "user@example.com").first()

    # race condition 없으면: 5번 실패 → 잠금 → failed_login_attempts=0
    # race condition 있으면: 카운터가 원자적으로 증가하지 않아 0이 아닌 값이 남음
    assert user.failed_login_attempts == 0, (
        f"Race condition 의심: failed_login_attempts={user.failed_login_attempts} (expected 0)"
    )
    # locked_until이 설정됐는지 (잠금이 한 번 이상 제대로 트리거됐는지)
    assert user.locked_until is not None, (
        "Race condition 의심: locked_until이 None — 잠금이 설정되지 않음"
    )


# TC-09b DB error injection — 5번째 실패 commit 중 OperationalError 발생 시 일관성 검증
def test_tc09b_db_error_during_lockout_commit(client, db):
    from sqlalchemy.exc import OperationalError as SAError
    from sqlalchemy.orm import Session as SASession

    EMAIL, PW = "dberror@example.com", "Passw0rd!"
    make_user(db, EMAIL, PW)

    # 4번 실패 → failed_login_attempts = 4 (정상 커밋)
    for _ in range(4):
        client.post(LOGIN, json={"email": EMAIL, "password": "wrong"})

    # 5번째 실패 처리 중 첫 번째 db.commit() → OperationalError 주입
    original_commit = SASession.commit
    call_count = [0]

    def fail_first_commit(self):
        call_count[0] += 1
        if call_count[0] == 1:
            raise SAError("injected DB error", {}, Exception("disk full simulation"))
        return original_commit(self)

    with patch.object(SASession, "commit", fail_first_commit):
        res = client.post(LOGIN, json={"email": EMAIL, "password": "wrong"})

    # 1. 클라이언트에게 에러 응답 (500)
    assert res.status_code == 500, (
        f"DB 에러 시 {res.status_code} 반환 (500 기대)"
    )

    # 2. 트랜잭션 롤백 확인: failed_login_attempts는 4 그대로
    db.expire_all()
    user = db.query(User).filter(User.email == EMAIL).first()
    assert user.failed_login_attempts == 4, (
        f"롤백 실패: failed_login_attempts={user.failed_login_attempts} (expected 4 — "
        "카운터가 1 늘어난 채 커밋되면 다음 정상 시도의 잠금 기준이 어긋남)"
    )

    # 3. locked_until은 NULL (잠금 미적용)
    assert user.locked_until is None, (
        "롤백 실패: locked_until이 NULL이어야 함 (잠금이 반쯤 적용된 채 남으면 안 됨)"
    )

    # 참고: auth.py에는 로그인 실패에 대한 audit log가 없으므로 partial entry 검증 생략
    # (audit log는 admin 작업에만 기록됨 — admin.py 참조)

    # 4. 이후 정상적인 5번째 실패 → 잠금 정확히 트리거 (카운터 누적 window 없음)
    client.post(LOGIN, json={"email": EMAIL, "password": "wrong"})  # 실제 5번째 실패
    res_locked = client.post(LOGIN, json={"email": EMAIL, "password": PW})
    assert res_locked.status_code == 423, (
        "DB 에러 후 5번째 실패 시 잠금이 트리거되지 않음"
    )


# TC-09c email normalization — 대소문자/공백 변형이 잠금 카운터를 우회하는지 검증
def test_tc09c_email_variants_lockout_bypass(client, db):
    """
    Pydantic EmailStr 정규화 동작:
      - 도메인: 항상 소문자 → user@Example.com → user@example.com (동일 계정, 카운터 적용)
      - 앞뒤 공백 제거  → ' user@example.com ' → user@example.com   (동일 계정, 카운터 적용)
      - 로컬파트 대소문자 보존 → User@example.com ≠ user@example.com (다른 계정으로 인식 → 우회!)
      - +태그 보존        → user+tag@example.com  (명백히 다른 주소 → 우회!)

    우회 가능 변형(BYPASS)은 잠금 카운터에 포함되지 않아 브루트포스 방어가 무력화될 수 있음.
    """
    EMAIL, PW = "user@example.com", "Passw0rd!"
    make_user(db, EMAIL, PW)

    # 4번 정상 실패 → counter = 4
    for _ in range(4):
        client.post(LOGIN, json={"email": EMAIL, "password": "wrong"})

    variants = [
        # (입력값,                       같은 계정으로 인식되는가)
        ("User@example.com",             False),  # 로컬파트 대소문자 — BYPASS
        ("USER@EXAMPLE.COM",             False),  # 로컬파트 대소문자 — BYPASS
        (" user@example.com ",           True),   # 공백 제거 후 동일
        ("user@Example.com",             True),   # 도메인 소문자화 후 동일
        ("user+tag@example.com",         False),  # +태그 — BYPASS
    ]

    bypass_variants = []
    for email_input, same_account in variants:
        res = client.post(LOGIN, json={"email": email_input, "password": "wrong"})
        if not same_account:
            # 다른 계정으로 인식 → "Invalid credentials" (user not found)
            # 카운터가 증가하지 않으므로 우회 성공
            assert res.status_code == 401
            bypass_variants.append(email_input)

    # 카운터에 포함된 변형이 임계값(5)을 채웠는지 확인
    db.expire_all()
    user = db.query(User).filter(User.email == EMAIL).first()

    if user.locked_until is not None:
        # 정상 계정이 잠겼는지 확인
        res_locked = client.post(LOGIN, json={"email": EMAIL, "password": PW})
        assert res_locked.status_code == 423
    else:
        # 잠금 미도달 — bypass 변형들이 counter를 채우지 못했음을 기록
        pass

    # 핵심 보안 검증: bypass 변형으로 계속 틀려도 원본 계정은 잠기지 않아야 한다고 가정하면
    # 아래는 취약점 문서화용 — bypass_variants 목록이 비어있으면 완전한 보호
    assert bypass_variants, (
        "예상 밖 결과: bypass 변형이 없음 — 이메일 정규화가 개선된 것일 수 있음"
    )

    # 우회 가능 변형으로만 5번 추가 시도 → 원본 계정 잠금 카운터 영향 없는지 검증
    # 카운터 초기화 후 bypass 변형 단독으로 테스트
    user.failed_login_attempts = 0
    user.locked_until = None
    db.commit()

    for _ in range(5):
        client.post(LOGIN, json={"email": bypass_variants[0], "password": "wrong"})

    db.expire_all()
    user = db.query(User).filter(User.email == EMAIL).first()
    assert user.failed_login_attempts == 0, (
        f"보안 이슈: '{bypass_variants[0]}' 변형 5회 실패가 원본 계정 카운터({user.failed_login_attempts})에 영향 — "
        "공격자가 이 변형으로 브루트포스 시 잠금을 우회할 수 있음"
    )
    assert user.locked_until is None, (
        f"예상 밖 결과: bypass 변형으로 원본 계정이 잠겼음"
    )


# TC-09d parametrize — MAX_LOGIN_ATTEMPTS × LOGIN_LOCKOUT_MINUTES 조합 검증
@pytest.mark.parametrize("max_attempts,lockout_minutes", [
    (3,  1), (3,  30), (3,  60),
    (5,  1), (5,  30), (5,  60),
    (10, 1), (10, 30), (10, 60),
])
def test_tc09d_lockout_parametrized(client, db, monkeypatch, max_attempts, lockout_minutes):
    from app.config import settings

    monkeypatch.setattr(settings, "MAX_LOGIN_ATTEMPTS", max_attempts)
    monkeypatch.setattr(settings, "LOGIN_LOCKOUT_MINUTES", lockout_minutes)

    make_user(db, "param@example.com", "Passw0rd!")

    # max_attempts - 1번 실패 → 아직 잠금 아님, 올바른 비밀번호로 로그인 가능
    for _ in range(max_attempts - 1):
        client.post(LOGIN, json={"email": "param@example.com", "password": "wrong"})
    res_ok = client.post(LOGIN, json={"email": "param@example.com", "password": "Passw0rd!"})
    assert res_ok.status_code == 200, (
        f"[attempts={max_attempts}] {max_attempts-1}번 실패 후 정상 로그인이 막힘"
    )

    # 성공 로그인으로 카운터 리셋 → 다시 max_attempts번 실패 → 잠금
    for _ in range(max_attempts):
        client.post(LOGIN, json={"email": "param@example.com", "password": "wrong"})
    res_locked = client.post(LOGIN, json={"email": "param@example.com", "password": "Passw0rd!"})
    assert res_locked.status_code == 423, (
        f"[attempts={max_attempts}] {max_attempts}번 실패 후 423이 아님"
    )
    assert "locked" in res_locked.json()["detail"].lower()

    # locked_until이 now + lockout_minutes 기준 ±5초 범위인지
    db.expire_all()
    u = db.query(User).filter(User.email == "param@example.com").first()
    assert u.locked_until is not None
    expected = datetime.utcnow() + timedelta(minutes=lockout_minutes)
    diff = abs((u.locked_until - expected).total_seconds())
    assert diff <= 5, (
        f"[lockout={lockout_minutes}m] locked_until 오차 {diff:.1f}s (±5s 허용)"
    )


# TC-10 — locked account rejects correct password until lockout expires
def test_tc10_correct_password_during_lockout(client, db, regular_user):
    # Trigger lockout
    for _ in range(5):
        client.post(LOGIN, json=_creds(password="wrong"))

    # Correct password while locked must still return 423
    res = client.post(LOGIN, json=_creds())
    assert res.status_code == 423


# TC-11 — login succeeds after lockout expires
def test_tc11_login_after_lockout_expires(client, db, regular_user):
    # Trigger lockout by brute force
    for _ in range(5):
        client.post(LOGIN, json=_creds(password="wrong"))

    # Directly expire the lockout in the database
    user = db.query(User).filter(User.email == "user@example.com").first()
    user.locked_until = datetime.utcnow() - timedelta(seconds=1)
    db.commit()

    # Should succeed now
    res = client.post(LOGIN, json=_creds())
    assert res.status_code == 200
    assert "access_token" in res.json()


# TC-12 — suspended account login
def test_tc12_suspended_account(client, db):
    make_user(db, "suspended@example.com", "Passw0rd!", status=UserStatus.SUSPENDED)
    res = client.post(LOGIN, json=_creds(email="suspended@example.com"))
    assert res.status_code == 403
    assert "suspended" in res.json()["detail"].lower()


# ════════════════════════════════════════════════════════════════════════════
# TC-13 – TC-15: Password Change (POST /users/me/password)
# ════════════════════════════════════════════════════════════════════════════
def _change_password(current, new):
    return {"current_password": current, "new_password": new}


# TC-13 — successful password change; new password works on next login
def test_tc13_successful_password_change(client, regular_user, auth_headers):
    res = client.post(PASSWORD, json=_change_password("Passw0rd!", "Newpass1!"), headers=auth_headers)
    assert res.status_code == 204

    # Verify the new password works
    login_res = client.post(LOGIN, json={"email": "user@example.com", "password": "Newpass1!"})
    assert login_res.status_code == 200
    assert "access_token" in login_res.json()


# TC-14 — wrong current password
def test_tc14_wrong_current_password(client, auth_headers):
    res = client.post(PASSWORD, json=_change_password("wrongcurrent", "Newpass1!"), headers=auth_headers)
    assert res.status_code == 401
    assert "current password is incorrect" in res.json()["detail"].lower()


# TC-15 — new password same as current (SRS §4.3 REQ-5)
def test_tc15_new_password_same_as_current(client, auth_headers):
    res = client.post(PASSWORD, json=_change_password("Passw0rd!", "Passw0rd!"), headers=auth_headers)
    assert res.status_code == 400
    assert "differ" in res.json()["detail"].lower()


# ════════════════════════════════════════════════════════════════════════════
# TC-16 – TC-22: URL Analysis (POST /analysis/search, GET /analysis/jobs/{id})
# ════════════════════════════════════════════════════════════════════════════
# TC-16 — no JWT → 401
def test_tc16_search_without_login(client):
    res = client.post(SEARCH, json={"url": "https://example.com"})
    assert res.status_code == 401


# TC-17 — new URL creates a job (PENDING); full pipeline needs Docker/worker
def test_tc17_new_url_creates_pending_job(client, auth_headers):
    with patch(_MOCK_ANALYSIS_ENQUEUE) as mock_enqueue:
        res = client.post(SEARCH, json={"url": "https://en.wikipedia.org/wiki/Phishing"}, headers=auth_headers)

    assert res.status_code == 200
    body = res.json()
    assert body["cached"] is False
    assert "job_id" in body
    mock_enqueue.assert_called_once()

    # Poll the job — should be PENDING (worker not running in unit tests)
    job_res = client.get(f"{JOBS}/{body['job_id']}", headers=auth_headers)
    assert job_res.status_code == 200
    assert job_res.json()["status"] == "PENDING"


# TC-18 — re-analysis of a cached URL returns immediately without a new job
def test_tc18_cached_url_returns_immediately(client, db, auth_headers):
    url_str = "https://example.com"
    normalized = normalize_url(url_str)
    url_row = Url(
        normalized_url=normalized,
        normalized_url_hash=Url.compute_hash(normalized),
        current_risk_score=10,
        current_risk_level=RiskLevel.SAFE,
    )
    db.add(url_row)
    db.commit()

    with patch(_MOCK_ANALYSIS_ENQUEUE) as mock_enqueue:
        res = client.post(SEARCH, json={"url": url_str}, headers=auth_headers)

    assert res.status_code == 200
    body = res.json()
    assert body["cached"] is True
    assert body["risk_score"] == 10
    assert body["risk_level"] == "SAFE"
    mock_enqueue.assert_not_called()


# TC-19 — warning modal is frontend-only; no backend assertion possible
@pytest.mark.skip(reason="TC-19: DANGER/CRITICAL modal is rendered by Next.js frontend — not testable here")
def test_tc19_warning_modal_for_high_risk_url():
    pass


# TC-20 — poll a job whose status was manually set to each pipeline stage
@pytest.mark.parametrize("status", [
    JobStatus.PENDING,
    JobStatus.CRAWLING,
    JobStatus.ANALYZING,
    JobStatus.COMPLETED,
])
def test_tc20_job_status_polling(client, db, auth_headers, status):
    url_row = Url(
        normalized_url="https://poll-test.example.com",
        normalized_url_hash=Url.compute_hash("https://poll-test.example.com"),
    )
    db.add(url_row)
    db.flush()
    job = AnalysisJob(url_id=url_row.id, status=status)
    db.add(job)
    db.commit()

    res = client.get(f"{JOBS}/{job.id}", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["status"] == status.value


# TC-21 — invalid URL format → 422
def test_tc21_invalid_url_format(client, auth_headers):
    res = client.post(SEARCH, json={"url": "not-a-url"}, headers=auth_headers)
    assert res.status_code == 422


# TC-22 — poll non-existent job ID → 404
def test_tc22_poll_nonexistent_job(client, auth_headers):
    res = client.get(f"{JOBS}/00000000-0000-0000-0000-000000000000", headers=auth_headers)
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


# ════════════════════════════════════════════════════════════════════════════
# TC-23 – TC-27: Fraud Report (POST /reports, GET /reports/{id})
# ════════════════════════════════════════════════════════════════════════════
_REPORT_URL = "https://scam-shop.example.com"
_REPORT_FRAUD_TYPE = "NON_DELIVERY"
_REPORT_DESCRIPTION = "This shop took my money and never delivered the product."


def _report_form(url=_REPORT_URL, description=_REPORT_DESCRIPTION, legal_consent=True):
    return {
        "url": url,
        "fraud_type": _REPORT_FRAUD_TYPE,
        "description": description,
        "legal_consent": "true" if legal_consent else "false",
    }


# Minimal 1×1 PNG for evidence upload tests
_PNG_1X1 = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
    b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


# TC-23 — successful report submission
def test_tc23_successful_report(client, auth_headers):
    res = client.post(REPORTS, data=_report_form(), headers=auth_headers)
    assert res.status_code == 201
    body = res.json()
    assert body["fraud_type"] == _REPORT_FRAUD_TYPE
    assert body["status"] == "SUBMITTED"
    assert "id" in body


# TC-24 — legal_consent=false → 400
def test_tc24_report_without_legal_consent(client, auth_headers):
    res = client.post(REPORTS, data=_report_form(legal_consent=False), headers=auth_headers)
    assert res.status_code == 400
    assert "legal consent" in res.json()["detail"].lower()


# TC-25 — description too short (< 20 chars) → 422
def test_tc25_description_too_short(client, auth_headers):
    res = client.post(REPORTS, data=_report_form(description="Too short"), headers=auth_headers)
    assert res.status_code == 422


# TC-26 — duplicate report from the same user for the same URL → 409
def test_tc26_duplicate_report(client, auth_headers):
    client.post(REPORTS, data=_report_form(), headers=auth_headers)
    res = client.post(REPORTS, data=_report_form(), headers=auth_headers)
    assert res.status_code == 409
    assert "already reported" in res.json()["detail"].lower()


# TC-27 — report without login → 401
def test_tc27_report_without_login(client):
    res = client.post(REPORTS, data=_report_form())
    assert res.status_code == 401


def test_report_with_evidence_image(client, auth_headers):
    files = {"evidence": ("proof.png", _PNG_1X1, "image/png")}
    res = client.post(REPORTS, data=_report_form(), files=files, headers=auth_headers)
    assert res.status_code == 201
    body = res.json()
    assert body["has_evidence"] is True
    ev = client.get(f"{REPORTS}/{body['id']}/evidence", headers=auth_headers)
    assert ev.status_code == 200
    assert ev.headers["content-type"] == "image/png"
    assert ev.content == _PNG_1X1


def test_report_evidence_non_ascii_filename(client, auth_headers):
    """Korean filenames must not crash Content-Disposition (latin-1 headers)."""
    files = {"evidence": ("스크린샷.png", _PNG_1X1, "image/png")}
    res = client.post(
        REPORTS,
        data=_report_form(url="https://evidence-filename.example.com"),
        files=files,
        headers=auth_headers,
    )
    assert res.status_code == 201
    ev = client.get(f"{REPORTS}/{res.json()['id']}/evidence", headers=auth_headers)
    assert ev.status_code == 200
    assert ev.content == _PNG_1X1


# ════════════════════════════════════════════════════════════════════════════
# TC-28 – TC-30: My Page (GET /users/me, /users/me/reports, /reports/{id})
# ════════════════════════════════════════════════════════════════════════════
# TC-28 — GET /users/me returns own profile
def test_tc28_get_own_profile(client, regular_user, auth_headers):
    res = client.get(ME, headers=auth_headers)
    assert res.status_code == 200
    body = res.json()
    assert body["email"] == "user@example.com"
    assert body["role"] == "USER"
    assert body["status"] == "ACTIVE"


# TC-29 — GET /users/me/reports returns only the current user's reports
def test_tc29_get_own_reports_only(client, db, regular_user, auth_headers):
    # Seed one report for regular_user
    _seed_report(db, regular_user, "https://tc28.example.com")

    # Create a second user with their own report
    other = make_user(db, "other@example.com", "otherpass1")
    _seed_report(db, other, "https://other.example.com")

    res = client.get(MY_REPORTS, headers=auth_headers)
    assert res.status_code == 200
    reports = res.json()
    # Only the current user's report is returned
    assert len(reports) == 1
    assert reports[0]["user_id"] == regular_user.id


# TC-30 — GET /reports/{id} for another user's report → 403
def test_tc30_access_other_user_report(client, db, regular_user, auth_headers):
    other = make_user(db, "other2@example.com", "otherpass2")
    report = _seed_report(db, other, "https://tc30.example.com")

    res = client.get(f"{REPORTS}/{report.id}", headers=auth_headers)
    assert res.status_code == 403
    assert "forbidden" in res.json()["detail"].lower()


# ════════════════════════════════════════════════════════════════════════════
# TC-31 – TC-35: Admin endpoints
# enqueue_analysis_job is mocked for TC-33 (status change may trigger re-analysis).
# ════════════════════════════════════════════════════════════════════════════
# TC-31 — regular user cannot access admin API → 403
def test_tc31_regular_user_denied(client, auth_headers):
    res = client.get(ADMIN_REPORTS, headers=auth_headers)
    assert res.status_code == 403


# TC-32 — admin can list all reports
def test_tc32_admin_lists_all_reports(client, db, admin_user, admin_headers, regular_user):
    _seed_report(db, regular_user, "https://admin-test.example.com", fraud_type=FraudType.FALSE_ADVERTISING)
    _seed_report(db, regular_user, "https://second.example.com", fraud_type=FraudType.FALSE_ADVERTISING)

    res = client.get(ADMIN_REPORTS, headers=admin_headers)
    assert res.status_code == 200
    assert len(res.json()) == 2


# TC-33 — admin updates report status; audit log is created
def test_tc33_update_report_status(client, db, admin_user, admin_headers, regular_user):
    report = _seed_report(db, regular_user, "https://admin-test.example.com", fraud_type=FraudType.FALSE_ADVERTISING)

    with patch(_MOCK_ADMIN_ENQUEUE):
        res = client.patch(
            f"{ADMIN_REPORTS}/{report.id}",
            json={"status": "ACTIVE"},
            headers=admin_headers,
        )

    assert res.status_code == 200
    assert res.json()["status"] == "ACTIVE"

    # Audit log must exist
    log = db.query(AdminAuditLog).filter(AdminAuditLog.target_id == report.id).first()
    assert log is not None
    assert log.action_type == "UPDATE_REPORT_STATUS"


# TC-34 — admin blocks a user: status → SUSPENDED, email added to blacklist
def test_tc34_block_user(client, db, admin_user, admin_headers, regular_user):
    res = client.post(
        ADMIN_BLOCK.format(user_id=regular_user.id),
        json={"reason": "spam"},
        headers=admin_headers,
    )
    assert res.status_code == 204

    db.expire_all()
    target = db.query(User).filter(User.id == regular_user.id).first()
    assert target.status == UserStatus.SUSPENDED
    assert target.token_version == 1

    bl = db.query(Blacklist).filter(Blacklist.email == regular_user.email).first()
    assert bl is not None


# TC-34b — block invalidates pre-block JWT via token_version (SRS §4.4 REQ-4)
def test_tc34b_block_invalidates_existing_jwt(client, admin_headers, regular_user):
    token = get_token(regular_user)
    res = client.post(
        ADMIN_BLOCK.format(user_id=regular_user.id),
        json={"reason": "abuse"},
        headers=admin_headers,
    )
    assert res.status_code == 204

    me = client.get(ME, headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 401


# TC-35 — admin cannot block themselves → 400
def test_tc35_admin_cannot_block_self(client, admin_user, admin_headers):
    res = client.post(
        ADMIN_BLOCK.format(user_id=admin_user.id),
        json={"reason": "self-block attempt"},
        headers=admin_headers,
    )
    assert res.status_code == 400
    assert "cannot block yourself" in res.json()["detail"].lower()


# ════════════════════════════════════════════════════════════════════════════
# TC-36 – TC-37: Rate Limiting
#
# These require a live Redis connection and the rate-limit middleware active
# (i.e., `make up` via Docker Compose). They are skipped in the unit suite.
# Run against Docker:
#     docker compose exec backend pytest tests/test_be.py -k "tc36 or tc37"
# ════════════════════════════════════════════════════════════════════════════
_RATELIMIT_SKIP = pytest.mark.skip(
    reason="TC-36/TC-37 require Docker (Redis-backed rate limiter). "
    "Run with: make up && docker compose exec backend pytest tests/test_be.py -k 'tc36 or tc37'"
)
_BURST = 61  # one over the 60 req/min limit (SRS §3.5)


# TC-36 — 61st request from the same IP within 1 minute → HTTP 429
@_RATELIMIT_SKIP
def test_tc36_exceed_rate_limit(client):
    # In Docker, 60 requests succeed and the 61st returns 429.
    # The client fixture connects to localhost:8000 when running inside Docker.
    responses = [client.get("/api/v1/health") for _ in range(_BURST)]
    status_codes = [r.status_code for r in responses]
    assert 429 in status_codes, f"Expected at least one 429, got: {set(status_codes)}"


# TC-37 — after the 1-minute window resets, requests succeed again
@_RATELIMIT_SKIP
def test_tc37_recovery_after_rate_limit(client):
    import time
    # Saturate the limit
    for _ in range(_BURST):
        client.get("/api/v1/health")
    # Wait for the slowapi window to reset (60 s)
    time.sleep(61)
    res = client.get("/api/v1/health")
    assert res.status_code == 200


# ════════════════════════════════════════════════════════════════════════════
# TC-38 – TC-56: Additional coverage
# (boundaries, JWT/session, URL normalization, positive reads, 404 / 422 paths)
# ════════════════════════════════════════════════════════════════════════════
# TC-38 — password of exactly 8 chars (boundary) → 201
def test_tc38_password_exactly_min_length(client):
    res = client.post(REGISTER, json={"email": "boundary8@example.com", "password": "Abcd1!xy"})
    assert res.status_code == 201


# TC-39 — a successful login resets the failed-attempt counter to 0
def test_tc39_successful_login_resets_counter(client, db, regular_user):
    for _ in range(4):
        client.post(LOGIN, json=_creds(password="wrong"))
    db.expire_all()
    user = db.query(User).filter(User.email == "user@example.com").first()
    assert user.failed_login_attempts == 4

    res = client.post(LOGIN, json=_creds())
    assert res.status_code == 200

    db.expire_all()
    user = db.query(User).filter(User.email == "user@example.com").first()
    assert user.failed_login_attempts == 0
    assert user.locked_until is None


# TC-40 — a valid JWT grants access to a protected endpoint
def test_tc40_valid_jwt_grants_access(client, regular_user):
    token = client.post(LOGIN, json=_creds()).json()["access_token"]
    res = client.get(ME, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()["email"] == "user@example.com"


# TC-41 — a malformed/undecodable JWT is rejected
def test_tc41_malformed_jwt_rejected(client, regular_user):
    res = client.get(ME, headers={"Authorization": "Bearer not.a.valid.token"})
    assert res.status_code == 401


# TC-42 — a token minted before suspension is rejected after the user is suspended
def test_tc42_suspended_user_token_revoked(client, db, regular_user):
    token = get_token(regular_user)
    # Suspend the user after the token was issued
    regular_user.status = UserStatus.SUSPENDED
    db.commit()

    res = client.get(ME, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 403
    assert "suspended" in res.json()["detail"].lower()


# TC-43 — password change without authentication → 401
def test_tc43_password_change_without_auth(client):
    res = client.post(PASSWORD, json=_change_password("Passw0rd!", "Newpass1!"))
    assert res.status_code == 401


# TC-44 — new password shorter than 8 chars → 422
def test_tc44_new_password_too_short(client, auth_headers):
    res = client.post(PASSWORD, json=_change_password("Passw0rd!", "short"), headers=auth_headers)
    assert res.status_code == 422


# TC-45 — a cached URL is matched even when re-searched with tracking params
def test_tc45_tracking_params_hit_same_cache(client, db, auth_headers):
    base = "https://shop.example.com/item"
    normalized = normalize_url(base)
    url_row = Url(
        normalized_url=normalized,
        normalized_url_hash=Url.compute_hash(normalized),
        current_risk_score=20,
        current_risk_level=RiskLevel.SAFE,
    )
    db.add(url_row)
    db.commit()

    noisy = f"{base}?utm_source=newsletter&fbclid=abc123"
    with patch(_MOCK_ANALYSIS_ENQUEUE) as mock_enqueue:
        res = client.post(SEARCH, json={"url": noisy}, headers=auth_headers)

    assert res.status_code == 200
    body = res.json()
    assert body["cached"] is True
    assert body["risk_score"] == 20
    mock_enqueue.assert_not_called()


# TC-46 — polling a COMPLETED job exposes the URL's risk level
def test_tc46_completed_job_exposes_risk_level(client, db, auth_headers):
    url_row = Url(
        normalized_url="https://done.example.com",
        normalized_url_hash=Url.compute_hash("https://done.example.com"),
        current_risk_score=75,
        current_risk_level=RiskLevel.DANGER,
    )
    db.add(url_row)
    db.flush()
    job = AnalysisJob(url_id=url_row.id, status=JobStatus.COMPLETED, final_risk_score=75)
    db.add(job)
    db.commit()

    res = client.get(f"{JOBS}/{job.id}", headers=auth_headers)
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "COMPLETED"
    assert body["risk_level"] == "DANGER"


# TC-47 — description of exactly 20 chars (boundary) → 201
def test_tc47_description_exactly_min_length(client, auth_headers):
    res = client.post(REPORTS, data=_report_form(description="A" * 20), headers=auth_headers)
    assert res.status_code == 201


# TC-48 — invalid fraud_type enum → 422
def test_tc48_invalid_fraud_type(client, auth_headers):
    form = _report_form()
    form["fraud_type"] = "NOT_A_REAL_TYPE"
    res = client.post(REPORTS, data=form, headers=auth_headers)
    assert res.status_code == 422


# TC-49 — get own report by id → 200
def test_tc49_get_own_report(client, db, regular_user, auth_headers):
    report = _seed_report(db, regular_user, "https://tc49.example.com")
    res = client.get(f"{REPORTS}/{report.id}", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["id"] == report.id


# TC-50 — get non-existent report id → 404
def test_tc50_get_nonexistent_report(client, auth_headers):
    res = client.get(f"{REPORTS}/00000000-0000-0000-0000-000000000000", headers=auth_headers)
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


# TC-51 — admin can view another user's report (role bypass)
def test_tc51_admin_views_other_user_report(client, db, admin_user, admin_headers, regular_user):
    report = _seed_report(db, regular_user, "https://tc51.example.com")
    res = client.get(f"{REPORTS}/{report.id}", headers=admin_headers)
    assert res.status_code == 200
    assert res.json()["id"] == report.id


# TC-52 — GET /users/me without a token → 401
def test_tc52_profile_without_auth(client):
    res = client.get(ME)
    assert res.status_code == 401


# TC-53 — a user with no reports gets an empty list
def test_tc53_empty_report_list(client, regular_user, auth_headers):
    res = client.get(MY_REPORTS, headers=auth_headers)
    assert res.status_code == 200
    assert res.json() == []


# TC-54 — update status of a non-existent report → 404
def test_tc54_update_nonexistent_report(client, admin_user, admin_headers):
    res = client.patch(
        f"{ADMIN_REPORTS}/00000000-0000-0000-0000-000000000000",
        json={"status": "ACTIVE"},
        headers=admin_headers,
    )
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


# TC-55 — block a non-existent user → 404
def test_tc55_block_nonexistent_user(client, admin_user, admin_headers):
    res = client.post(
        ADMIN_BLOCK.format(user_id="00000000-0000-0000-0000-000000000000"),
        json={"reason": "ghost"},
        headers=admin_headers,
    )
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


# TC-56 — invalid report status value → 422
def test_tc56_invalid_report_status(client, admin_user, admin_headers):
    res = client.patch(
        f"{ADMIN_REPORTS}/00000000-0000-0000-0000-000000000000",
        json={"status": "NONSENSE"},
        headers=admin_headers,
    )
    assert res.status_code == 422


# ════════════════════════════════════════════════════════════════════════════
# TC-57 – TC-65: Auth-enforcement sweep & security config
# (absorbed from former test_qa_auth.py / test_qa_security.py — BUG-1, SEC-1/2)
# NOTE: a malformed-token → 401 check already lives in TC-41.
# ════════════════════════════════════════════════════════════════════════════
# TC-57 — every protected endpoint rejects an unauthenticated request (BUG-1)
_PROTECTED_ENDPOINTS = [
    ("POST", "/api/v1/analysis/search", {"url": "https://example.com"}),
    ("GET", "/api/v1/analysis/jobs/fake-id", None),
    ("GET", "/api/v1/users/me", None),
    ("POST", "/api/v1/users/me/password", {"current_password": "x", "new_password": "y"}),
    ("POST", "/api/v1/reports", {}),
    ("GET", "/api/v1/admin/reports", None),
    ("PATCH", "/api/v1/admin/reports/fake-id", {"status": "ACTIVE"}),
    ("POST", "/api/v1/admin/users/fake-id/block", {"reason": "test"}),
]


@pytest.mark.parametrize("method,path,body", _PROTECTED_ENDPOINTS)
def test_tc57_protected_endpoints_require_auth(client, method, path, body):
    kwargs = {"json": body} if body is not None else {}
    resp = getattr(client, method.lower())(path, **kwargs)
    assert resp.status_code == 401, (
        f"{method} {path} → {resp.status_code} (expected 401); "
        "endpoint may be missing the get_current_user dependency"
    )


# TC-58 — /health is public (liveness probe, no auth)
def test_tc58_health_is_public(client):
    assert client.get("/health").status_code == 200


# TC-59 — /stats is public (homepage counters need no login)
def test_tc59_stats_is_public(client):
    # DB-backed; the contract is simply "never 401".
    assert client.get("/api/v1/stats").status_code != 401


# TC-60/61/64 are deployment-config gates: they only mean something when a real
# .env is supplied (local / staging / prod). Under the default CI config (no .env)
# the secret & CORS are placeholders, so these are skipped there rather than
# failing the build — they enforce wherever the JWT secret has been overridden.
_requires_configured_env = pytest.mark.skipif(
    settings.JWT_SECRET_KEY == "change-me-in-production",
    reason="deployment gate — needs a configured .env (JWT secret overridden); "
    "skipped under the default CI config",
)


# TC-60 — JWT secret is not the default placeholder (SEC-1)
@_requires_configured_env
def test_tc60_jwt_secret_not_default():
    assert settings.JWT_SECRET_KEY != "change-me-in-production"


# TC-61 — JWT secret is at least 32 chars (SEC-1)
@_requires_configured_env
def test_tc61_jwt_secret_min_length():
    assert len(settings.JWT_SECRET_KEY) >= 32


# TC-62 — every configured CORS origin receives an ACAO header (SEC-2)
def test_tc62_cors_allows_configured_origins(client):
    for origin in settings.cors_origins_list:
        resp = client.get("/health", headers={"Origin": origin})
        assert "access-control-allow-origin" in resp.headers, (
            f"Configured origin '{origin}' got no Access-Control-Allow-Origin header"
        )


# TC-63 — an unknown origin does not receive a permissive ACAO header (SEC-2)
def test_tc63_cors_blocks_unknown_origin(client):
    resp = client.get("/health", headers={"Origin": "https://attacker.example.com"})
    acao = resp.headers.get("access-control-allow-origin", "")
    assert acao != "*" and "attacker.example.com" not in acao


# TC-64 — at least one HTTPS origin is configured for production (SEC-2)
@_requires_configured_env
def test_tc64_cors_has_https_origin():
    origins = settings.cors_origins_list
    assert any(o.startswith("https://") for o in origins), (
        f"No HTTPS origin in CORS_ALLOWED_ORIGINS: {origins}"
    )


# TC-65 — CORS preflight (OPTIONS) succeeds for a known origin (SEC-2)
def test_tc65_cors_preflight(client):
    if not settings.cors_origins_list:
        pytest.skip("No CORS origins configured")
    origin = settings.cors_origins_list[0]
    resp = client.options(
        "/api/v1/analysis/search",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Authorization,Content-Type",
        },
    )
    assert resp.status_code in (200, 204)


# TC-66 — a hostname the crawler can't IDNA-encode is rejected up front (422)
# (a DNS label > 63 chars would otherwise crash the worker → "Analysis failed")
def test_tc66_unencodable_hostname_rejected(client, auth_headers):
    long_label = "a" * 70  # exceeds the 63-byte DNS label limit
    with patch(_MOCK_ANALYSIS_ENQUEUE) as mock_enqueue:
        res = client.post(
            SEARCH, json={"url": f"https://{long_label}.com"}, headers=auth_headers
        )
    assert res.status_code == 422
    mock_enqueue.assert_not_called()  # rejected before any job is enqueued


def _fuzz_url_inputs(n=120, seed=20260603):
    """A deterministic corpus of random + hand-picked nasty URL inputs."""
    import random
    import string

    rng = random.Random(seed)
    charset = (
        string.ascii_letters + string.digits
        + "-._~:/?#[]@!$&'()*+,;= %"        # URL/reserved chars + space
        + "한글가나다🎉<>\"\\|^`{}"          # unicode + unsafe chars
    )
    schemes = ["", "http://", "https://", "https://", "ftp://", "://", "HtTpS://"]
    cases = [rng.choice(schemes) + "".join(rng.choice(charset) for _ in range(rng.randint(0, 60)))
             for _ in range(n)]
    cases += [
        "https://" + "a" * 100 + ".com",          # DNS label > 63
        "https://" + "한" * 40 + ".com",           # long IDN
        "http://192.168.0.1:99999/x",             # out-of-range port
        "http://host:notaport/x",                 # non-numeric port
        "https://exa mple.com",                   # space in host
        "https://.com", "https://..", "http://",  # empty labels / missing host
        "https://[::1]/x", "https://user:pass@h.com/p",
        "https://" + "x" * 1000 + ".com/path",    # long but under the column limit
        "javascript:alert(1)", "data:text/html,x",
    ]
    return cases


# TC-67 — fuzz the analysis search endpoint: random/malformed URLs never 500
# Every input must be either accepted (200) or rejected with a validation error
# (422) — the endpoint must never raise an unhandled exception.
def test_tc67_search_url_fuzz(client, auth_headers):
    unexpected = []
    with patch(_MOCK_ANALYSIS_ENQUEUE):
        for raw in _fuzz_url_inputs():
            res = client.post(SEARCH, json={"url": raw}, headers=auth_headers)
            if res.status_code not in (200, 422):
                unexpected.append((raw[:60], res.status_code))
    assert not unexpected, (
        f"{len(unexpected)} input(s) returned an unexpected status "
        f"(expected 200 or 422, never 500): {unexpected[:10]}"
    )
