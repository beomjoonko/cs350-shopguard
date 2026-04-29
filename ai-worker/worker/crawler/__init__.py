"""
Crawler dispatcher — picks the right site-specific scraper based on the URL.

TBD-2 (SRS Appendix C): final anti-bot strategy. Likely combination of:
  - rotating residential proxies
  - playwright/headless browser for JS-rendered pages
  - respect for robots.txt where feasible (SRS §3.4)
"""
from urllib.parse import urlparse

from worker.crawler.base import CrawlResult
from worker.crawler import coupang, aliexpress, temu


_HANDLERS = {
    "coupang.com": coupang.crawl,
    "aliexpress.com": aliexpress.crawl,
    "temu.com": temu.crawl,
}


def dispatch_crawler(url: str) -> CrawlResult:
    host = (urlparse(url).hostname or "").lower()
    for domain, handler in _HANDLERS.items():
        if host.endswith(domain):
            return handler(url)
    # Fallback — generic crawler (TBD)
    return CrawlResult(url=url, html="", reviews=[], product=None, seller=None)
