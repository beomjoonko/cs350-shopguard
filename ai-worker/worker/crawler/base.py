"""Shared crawler types."""
from dataclasses import dataclass, field


@dataclass
class Review:
    rating: float | None = None
    text: str = ""
    author: str | None = None
    date: str | None = None


@dataclass
class Product:
    title: str = ""
    price: float | None = None
    image_urls: list[str] = field(default_factory=list)


@dataclass
class Seller:
    name: str = ""
    rating: float | None = None
    history_days: int | None = None


@dataclass
class CrawlResult:
    url: str
    html: str
    reviews: list[Review] = field(default_factory=list)
    product: Product | None = None
    seller: Seller | None = None
