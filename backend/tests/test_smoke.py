"""Smoke tests — replace with real ones as features land."""


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_url_normalizer():
    """Trivial unit test for SRS §4.5 REQ-2."""
    from app.utils.url_normalizer import normalize_url

    a = normalize_url("HTTPS://Example.com:443/path/?utm_source=x&z=1")
    b = normalize_url("https://example.com/path?z=1")
    assert a == b
