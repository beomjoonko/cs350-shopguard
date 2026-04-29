"""
Coupang crawler — STUB.

Production version should:
  - use rotating proxies (TBD-2)
  - parse product detail JSON returned by Coupang's internal endpoints
  - paginate through reviews

For now we return an empty CrawlResult so the rest of the pipeline can run
end-to-end during local development.
"""
from worker.crawler.base import CrawlResult


def crawl(url: str) -> CrawlResult:
    # TODO: implement real Coupang scraping (SRS §4.6 REQ-2)
    return CrawlResult(url=url, html="")
