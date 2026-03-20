"""Composite scoring engine — the AI brain of the tracker.

Combines technical, fundamental, and sentiment scores into a single
weighted "Buy Score" (0-100) and a recommendation category.
"""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd

from config import ETF_SCORING_WEIGHTS, SCORE_THRESHOLDS, STOCK_SCORING_WEIGHTS
from src.analysis.fundamental_analysis import score_etf_fundamentals, score_fundamentals
from src.analysis.sentiment_analysis import analyze_news_sentiment
from src.analysis.technical_indicators import calculate_technical_score, compute_indicators, get_latest_signals

logger = logging.getLogger(__name__)

# Recommendation categories ordered from best to worst
_CATEGORIES = ["Strong Buy", "Buy", "Hold", "Sell", "Strong Sell"]


def _score_to_category(score: float) -> str:
    for cat, threshold in sorted(SCORE_THRESHOLDS.items(), key=lambda x: -x[1]):
        if score >= threshold:
            return cat
    return "Strong Sell"


def _generate_explanation(
    ticker: str,
    composite: float,
    technical_score: float,
    fundamental_score: float,
    sentiment_score: float,
    signals: dict[str, Any],
    category: str,
    is_etf: bool,
) -> str:
    """Generate a human-readable explanation of the recommendation."""
    parts: list[str] = [f"**{ticker}** ({category} — Score: {composite:.0f}/100). "]

    # Technical summary
    rsi = signals.get("rsi")
    if rsi is not None:
        rsi_desc = signals.get("rsi_signal", "neutral")
        parts.append(f"RSI {rsi:.1f} ({rsi_desc}). ")
    macd_cross = signals.get("macd_crossover", "unknown")
    if macd_cross != "unknown":
        parts.append(f"MACD is {macd_cross}. ")
    if signals.get("golden_cross") is True:
        parts.append("SMA50 > SMA200 (golden cross). ")
    elif signals.get("golden_cross") is False:
        parts.append("SMA50 < SMA200 (death cross). ")

    # Fundamental summary (stocks only)
    if not is_etf:
        if fundamental_score >= 70:
            parts.append("Strong fundamentals. ")
        elif fundamental_score >= 50:
            parts.append("Adequate fundamentals. ")
        else:
            parts.append("Weak fundamentals. ")
    else:
        parts.append(f"ETF technical score: {technical_score:.0f}/100. ")

    # Sentiment summary
    if sentiment_score >= 65:
        parts.append("Positive news sentiment. ")
    elif sentiment_score <= 35:
        parts.append("Negative news sentiment. ")
    else:
        parts.append("Neutral news sentiment. ")

    return "".join(parts).strip()


def score_ticker(
    ticker: str,
    prices: pd.DataFrame,
    meta: dict[str, Any],
    news: list[dict[str, Any]],
    is_etf: bool = False,
) -> dict[str, Any]:
    """Compute the composite Buy Score for a single ticker.

    Returns a rich dict with all sub-scores, signals, recommendation,
    and explanation text.
    """
    weights = ETF_SCORING_WEIGHTS if is_etf else STOCK_SCORING_WEIGHTS

    # --- Technical ---
    if not prices.empty:
        prices_with_indicators = compute_indicators(prices.copy())
        signals = get_latest_signals(prices_with_indicators)
    else:
        prices_with_indicators = prices
        signals = {}
    technical_score = calculate_technical_score(signals)

    # --- Fundamental ---
    if is_etf:
        fund_scores = score_etf_fundamentals(meta)
    else:
        fund_scores = score_fundamentals(meta)
    fundamental_score = fund_scores.get("composite", 50.0)

    # --- Sentiment ---
    sentiment_result = analyze_news_sentiment(news)
    sentiment_score = sentiment_result.get("score", 50.0)

    # --- Composite ---
    composite = (
        technical_score * weights["technical"]
        + fundamental_score * weights["fundamental"]
        + sentiment_score * weights["sentiment"]
    )
    composite = round(max(0.0, min(100.0, composite)), 1)

    category = _score_to_category(composite)

    explanation = _generate_explanation(
        ticker, composite, technical_score, fundamental_score,
        sentiment_score, signals, category, is_etf,
    )

    # Build latest-price info for convenience
    name = meta.get("name", ticker)
    price = signals.get("close")
    if price is None and not prices.empty:
        price = float(prices["Close"].iloc[-1])

    return {
        "ticker": ticker,
        "name": name,
        "is_etf": is_etf,
        "price": price,
        "buy_score": composite,
        "category": category,
        "explanation": explanation,
        # Sub-scores
        "technical_score": round(technical_score, 1),
        "fundamental_score": round(fundamental_score, 1),
        "sentiment_score": round(sentiment_score, 1),
        # Details
        "signals": signals,
        "fund_details": fund_scores,
        "sentiment_details": sentiment_result,
        # For charts
        "prices_df": prices_with_indicators,
        # Meta pass-through
        "sector": meta.get("sector", "N/A"),
        "industry": meta.get("industry", "N/A"),
        "market_cap": meta.get("market_cap"),
        "pe_ratio": meta.get("pe_ratio"),
        "dividend_yield": meta.get("dividend_yield"),
        "expense_ratio": meta.get("expense_ratio"),
        "news": news,
    }


def run_full_analysis(
    data: dict[str, dict[str, Any]],
    custom_weights: dict[str, dict[str, float]] | None = None,
) -> list[dict[str, Any]]:
    """Score all tickers in *data* and return a sorted list.

    *data* is the output of ``DataManager.fetch_all_data()``.
    *custom_weights* can override per-profile scoring weights.
    """
    results: list[dict[str, Any]] = []
    total = len(data)
    for i, (ticker, ticker_data) in enumerate(data.items(), 1):
        logger.info("[%d/%d] Scoring %s…", i, total, ticker)
        try:
            result = score_ticker(
                ticker=ticker,
                prices=ticker_data.get("prices", pd.DataFrame()),
                meta=ticker_data.get("meta", {}),
                news=ticker_data.get("news", []),
                is_etf=ticker_data.get("is_etf", False),
            )
            results.append(result)
        except Exception as exc:  # noqa: BLE001
            logger.error("Scoring failed for %s: %s", ticker, exc)

    # Sort by buy_score descending
    results.sort(key=lambda x: x.get("buy_score", 0), reverse=True)
    return results
