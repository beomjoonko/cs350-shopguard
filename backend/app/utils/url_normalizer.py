"""
URL normalization — SRS §4.5 REQ-2.

The goal is that two URLs which point to the same resource hash to the same
key, so we don't analyze duplicates. Tactics:

  - lowercase scheme & host
  - drop default ports (:80, :443)
  - drop trailing slash
  - drop common tracking params (utm_*, fbclid, gclid, ...)
  - sort remaining query parameters

This is a starting point. Site-specific normalization (e.g. extracting
Coupang's product id from various URL forms) belongs in ai-worker/crawler/.
"""
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode


_TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "fbclid", "gclid", "yclid", "msclkid", "mc_cid", "mc_eid",
    "_ga", "ref", "referrer",
}


def normalize_url(raw_url: str) -> str:
    """Return a canonical form of the URL safe to use as a DB key."""
    parts = urlsplit(raw_url.strip())

    scheme = parts.scheme.lower() or "https"
    host = parts.hostname or ""
    host = host.lower()

    port = parts.port
    if (scheme == "http" and port == 80) or (scheme == "https" and port == 443):
        port = None
    netloc = f"{host}:{port}" if port else host

    path = parts.path or "/"
    if len(path) > 1 and path.endswith("/"):
        path = path.rstrip("/")

    query_pairs = [
        (k, v) for k, v in parse_qsl(parts.query, keep_blank_values=False)
        if k.lower() not in _TRACKING_PARAMS
    ]
    query_pairs.sort()
    query = urlencode(query_pairs)

    return urlunsplit((scheme, netloc, path, query, ""))
