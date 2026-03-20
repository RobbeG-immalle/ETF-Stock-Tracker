"""Sentiment analysis of financial news headlines using VADER.

Downloads VADER lexicon on first use (requires internet).  Aggregates
per-ticker sentiment from a list of article dicts.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_vader_analyzer = None  # lazy singleton


def _get_analyzer():
    """Return (and cache) the VADER SentimentIntensityAnalyzer."""
    global _vader_analyzer  # noqa: PLW0603
    if _vader_analyzer is not None:
        return _vader_analyzer
    try:
        import nltk
        from nltk.sentiment.vader import SentimentIntensityAnalyzer

        # Ensure VADER lexicon is available
        try:
            nltk.data.find("sentiment/vader_lexicon.zip")
        except LookupError:
            nltk.download("vader_lexicon", quiet=True)

        _vader_analyzer = SentimentIntensityAnalyzer()
    except ImportError:
        logger.warning("nltk not installed; sentiment analysis disabled.")
        _vader_analyzer = None
    return _vader_analyzer


def score_text(text: str) -> dict[str, float]:
    """Return VADER scores for *text*.

    Keys: neg, neu, pos, compound (all in [-1, 1] or [0, 1]).
    """
    analyzer = _get_analyzer()
    if analyzer is None or not text:
        return {"neg": 0.0, "neu": 1.0, "pos": 0.0, "compound": 0.0}
    try:
        return analyzer.polarity_scores(text)
    except Exception as exc:  # noqa: BLE001
        logger.debug("VADER scoring error: %s", exc)
        return {"neg": 0.0, "neu": 1.0, "pos": 0.0, "compound": 0.0}


def analyze_news_sentiment(articles: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate sentiment over a list of article dicts.

    Each article should have at least a ``title`` key.

    Returns:
        avg_compound: float in [-1, 1]
        positive_pct: fraction of articles with compound > 0.05
        negative_pct: fraction of articles with compound < -0.05
        neutral_pct: fraction of articles in between
        article_count: int
        trend: "improving" | "declining" | "stable" | "unknown"
        sentiment_label: "Bullish" | "Slightly Bullish" | "Neutral" |
                         "Slightly Bearish" | "Bearish"
        score: float in [0, 100]  (mapped from avg_compound)
    """
    if not articles:
        return _neutral_result()

    compounds: list[float] = []
    for art in articles:
        text = f"{art.get('title', '')} {art.get('summary', '')}".strip()
        sc = score_text(text)
        compounds.append(sc["compound"])

    avg = sum(compounds) / len(compounds)
    pos = sum(1 for c in compounds if c > 0.05)
    neg = sum(1 for c in compounds if c < -0.05)
    neu = len(compounds) - pos - neg
    n = len(compounds)

    # Trend: compare first half vs second half
    half = n // 2
    trend = "unknown"
    if half >= 2:
        first_half_avg = sum(compounds[:half]) / half
        second_half_avg = sum(compounds[half:]) / (n - half)
        if second_half_avg - first_half_avg > 0.05:
            trend = "improving"
        elif first_half_avg - second_half_avg > 0.05:
            trend = "declining"
        else:
            trend = "stable"

    # Map compound [-1, 1] → score [0, 100]
    score = (avg + 1) / 2 * 100

    label = _compound_to_label(avg)

    return {
        "avg_compound": round(avg, 4),
        "positive_pct": round(pos / n, 3) if n else 0,
        "negative_pct": round(neg / n, 3) if n else 0,
        "neutral_pct": round(neu / n, 3) if n else 0,
        "article_count": n,
        "trend": trend,
        "sentiment_label": label,
        "score": round(score, 1),
    }


def _neutral_result() -> dict[str, Any]:
    return {
        "avg_compound": 0.0,
        "positive_pct": 0.0,
        "negative_pct": 0.0,
        "neutral_pct": 1.0,
        "article_count": 0,
        "trend": "unknown",
        "sentiment_label": "Neutral",
        "score": 50.0,
    }


def _compound_to_label(compound: float) -> str:
    if compound >= 0.35:
        return "Bullish"
    if compound >= 0.05:
        return "Slightly Bullish"
    if compound <= -0.35:
        return "Bearish"
    if compound <= -0.05:
        return "Slightly Bearish"
    return "Neutral"
