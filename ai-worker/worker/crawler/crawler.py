"""
Page crawler — produces a CrawlSnapshot in the phishpedia training schema.

Single-file implementation. Site-specific subclasses can be introduced later
if a real divergence in strategy emerges (e.g., one site requires Playwright);
until then, requests + BS4 is enough to populate the fields the classifier
preprocessor was fitted on.

TBD-2 is still open — this crawler has no anti-bot evasion. Blocked fetches
return a CrawlSnapshot with `fetch_ok=False`; the classifier treats the
empty/missing fields uniformly via the "__missing__" sentinel its preprocessor
was fitted with.

WHOIS and IP-geo fields are intentionally left None for now. They require
python-whois and geoip2+MaxMind which are not yet on the requirements list.
"""
from __future__ import annotations

import logging
import re
import socket
import ssl
from datetime import datetime
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from worker.config import settings
from worker.crawler.snapshot import CrawlSnapshot


log = logging.getLogger(__name__)

_FETCH_TIMEOUT_S = 15.0
_TLS_TIMEOUT_S = 5.0
_MAX_BYTES = 2_000_000  # ~2 MB cap; phishing pages are usually small

# Matches "property: value;" inside CSS rule bodies. Good enough for
# aggregation into {prop: [vals]} without pulling in cssutils.
_CSS_DECL_RE = re.compile(r"([a-zA-Z\-]+)\s*:\s*([^;{}]+);")

# X.509 cert dates look like 'Jun  1 12:00:00 2024 GMT'.
_CERT_DATE_FMT = "%b %d %H:%M:%S %Y %Z"


def crawl(url: str) -> CrawlSnapshot:
    """Fetch the URL and produce a CrawlSnapshot."""
    scan_date = datetime.utcnow()
    parsed = urlparse(url)
    snap = CrawlSnapshot(url=url, scan_date=scan_date, protocol=parsed.scheme or None)

    html_text = _fetch_html(url, snap)
    if html_text:
        _populate_from_html(html_text, snap)

    if (parsed.scheme or "").lower() == "https" and parsed.hostname:
        _populate_tls(parsed.hostname, parsed.port or 443, snap)

    return snap


def _fetch_html(url: str, snap: CrawlSnapshot) -> str:
    headers = {"User-Agent": settings.CRAWLER_USER_AGENT}
    try:
        with httpx.Client(
            timeout=_FETCH_TIMEOUT_S,
            follow_redirects=True,
            headers=headers,
        ) as client:
            resp = client.get(url)
        snap.fetch_status = resp.status_code
        snap.fetch_ok = resp.is_success

        # Update protocol to reflect the final URL after redirects.
        final_scheme = urlparse(str(resp.url)).scheme
        if final_scheme:
            snap.protocol = final_scheme

        if not resp.is_success:
            return ""
        content = resp.content[:_MAX_BYTES]
        encoding = resp.encoding or "utf-8"
        try:
            return content.decode(encoding, errors="replace")
        except LookupError:
            return content.decode("utf-8", errors="replace")
    except httpx.HTTPError as exc:
        log.warning("crawl fetch failed url=%s err=%s", url, exc)
        return ""


def _populate_from_html(html_text: str, snap: CrawlSnapshot) -> None:
    soup = BeautifulSoup(html_text, "lxml")

    # Tag-name list — phishpedia features.html shape.
    snap.features_html = [el.name for el in soup.find_all(True) if el.name]

    # Visible text — drop script/style first.
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    snap.features_text = " ".join(soup.get_text(separator=" ").split())

    # CSS dict — aggregate property -> [values] from inline <style> blocks
    # and `style="..."` attributes. External stylesheets are not followed
    # (would multiply fetches; phishpedia training included inline CSS only
    # for many rows, so this matches the lower-bound case).
    css: dict[str, list[str]] = {}
    for style_block in soup.find_all("style"):
        _harvest_css(style_block.get_text() or "", css)
    for el in soup.find_all(style=True):
        _harvest_css(el["style"], css)
    snap.features_css = css

    # <html lang="...">
    html_el = soup.find("html")
    if html_el and html_el.get("lang"):
        snap.language = str(html_el["lang"]).strip().lower() or None

    # Count external-asset references on the page.
    assets = 0
    assets += sum(1 for _ in soup.find_all("img", src=True))
    assets += sum(1 for _ in soup.find_all("script", src=True))
    assets += sum(1 for _ in soup.find_all("link", href=True))
    snap.assets_downloaded = assets


def _harvest_css(block: str, into: dict[str, list[str]]) -> None:
    for prop, val in _CSS_DECL_RE.findall(block):
        key = prop.strip().lower()
        v = val.strip()
        if key and v:
            into.setdefault(key, []).append(v)


def _populate_tls(host: str, port: int, snap: CrawlSnapshot) -> None:
    ctx = ssl.create_default_context()
    try:
        with socket.create_connection((host, port), timeout=_TLS_TIMEOUT_S) as raw:
            with ctx.wrap_socket(raw, server_hostname=host) as tls:
                cert = tls.getpeercert()
                snap.security_protocol = tls.version()
    except (ssl.SSLError, socket.timeout, OSError) as exc:
        log.info("tls handshake failed host=%s err=%s", host, exc)
        snap.security_state = "insecure"
        return

    if not cert:
        snap.security_state = "secure"
        return

    snap.security_state = "secure"
    issuer = cert.get("issuer") or ()
    # issuer is a tuple of RDNs; pick the organizationName if present.
    for rdn in issuer:
        for k, v in rdn:
            if k == "organizationName":
                snap.security_issuer = v
                break
        if snap.security_issuer:
            break

    snap.security_valid_from = _parse_cert_date(cert.get("notBefore"))
    snap.security_valid_to = _parse_cert_date(cert.get("notAfter"))


def _parse_cert_date(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.strptime(raw, _CERT_DATE_FMT)
    except ValueError:
        return None
