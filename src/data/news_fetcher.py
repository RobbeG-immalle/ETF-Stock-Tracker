"""Financial news fetcher using RSS feeds via feedparser.

Fetches recent headlines for a given ticker and returns them as a list
of dicts with keys: title, link, published.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import feedparser

logger = logging.getLogger(__name__)

# Per-ticker RSS URL templates (Yahoo Finance)
_TICKER_FEED_TEMPLATES: list[str] = [
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US",
]

# Generic market news (fallback / supplement)
_GENERIC_FEEDS: list[str] = [
    "https://feeds.finance.yahoo.com/rss/2.0/headline?region=US&lang=en-US",
    "https://www.reutersagency.com/feed/?best-topics=business-finance&post_type=best",
]

_MAX_ARTICLES_PER_TICKER: int = 20


def _parse_feed(url: str) -> list[dict[str, Any]]:
    """Parse a single RSS feed URL and return a list of article dicts."""
    articles: list[dict[str, Any]] = []
    try:
        feed = feedparser.parse(url)
        for entry in feed.entries:
            published: str | None = None
            if hasattr(entry, "published"):
                published = entry.published
            elif hasattr(entry, "updated"):
                published = entry.updated

            articles.append(
                {
                    "title": getattr(entry, "title", ""),
                    "link": getattr(entry, "link", ""),
                    "published": published,
                    "summary": getattr(entry, "summary", ""),
                }
            )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to parse feed %s: %s", url, exc)
    return articles


def fetch_news_for_ticker(
    ticker: str,
    max_articles: int = _MAX_ARTICLES_PER_TICKER,
) -> list[dict[str, Any]]:
    """Fetch recent news headlines for *ticker*.

    Returns a list of dicts with keys: ticker, title, link, published, summary.
    """
    articles: list[dict[str, Any]] = []

    for template in _TICKER_FEED_TEMPLATES:
        url = template.format(ticker=ticker)
        articles.extend(_parse_feed(url))
        if len(articles) >= max_articles:
            break

    # Deduplicate by title
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for art in articles:
        key = art["title"].strip().lower()
        if key and key not in seen:
            seen.add(key)
            unique.append({**art, "ticker": ticker})

    return unique[:max_articles]


def fetch_market_news(max_articles: int = 30) -> list[dict[str, Any]]:
    """Fetch general market / finance news headlines.

    Useful for market-wide sentiment.
    """
    articles: list[dict[str, Any]] = []
    for url in _GENERIC_FEEDS:
        articles.extend(_parse_feed(url))

    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for art in articles:
        key = art["title"].strip().lower()
        if key and key not in seen:
            seen.add(key)
            unique.append(art)

    return unique[:max_articles]
