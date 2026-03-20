"""Reusable UI components for the Streamlit dashboard."""

from __future__ import annotations

from typing import Any

import streamlit as st


_CATEGORY_COLORS: dict[str, str] = {
    "Strong Buy": "#00d4aa",
    "Buy": "#7ec8a0",
    "Hold": "#ffd700",
    "Sell": "#ff8c00",
    "Strong Sell": "#ff4b4b",
}

_SENTIMENT_COLORS: dict[str, str] = {
    "Bullish": "#00d4aa",
    "Slightly Bullish": "#7ec8a0",
    "Neutral": "#aaaaaa",
    "Slightly Bearish": "#ff8c00",
    "Bearish": "#ff4b4b",
}


def score_badge(category: str, score: float) -> str:
    """Return an HTML badge string for the given category and score."""
    color = _CATEGORY_COLORS.get(category, "#aaa")
    return (
        f'<span style="background:{color};color:#000;padding:3px 10px;'
        f'border-radius:12px;font-weight:bold;font-size:0.85em">'
        f"{category} ({score:.0f})</span>"
    )


def sentiment_badge(label: str) -> str:
    """Return an HTML badge for sentiment label."""
    color = _SENTIMENT_COLORS.get(label, "#aaa")
    return (
        f'<span style="background:{color};color:#000;padding:2px 8px;'
        f'border-radius:10px;font-size:0.8em;font-weight:bold">{label}</span>'
    )


def metric_card(label: str, value: Any, delta: Any = None, fmt: str = "{}") -> None:
    """Render a styled metric card using Streamlit columns."""
    formatted = fmt.format(value) if value is not None else "N/A"
    st.metric(label=label, value=formatted, delta=delta)


def render_score_row(result: dict[str, Any]) -> None:
    """Render a compact one-line score row for a ticker."""
    col1, col2, col3, col4, col5 = st.columns([2, 2, 1.5, 1.5, 1.5])
    with col1:
        st.write(f"**{result['ticker']}**")
        st.caption(result.get("name", "")[:30])
    with col2:
        st.markdown(score_badge(result["category"], result["buy_score"]), unsafe_allow_html=True)
    with col3:
        price = result.get("price")
        st.write(f"${price:.2f}" if price else "N/A")
    with col4:
        st.write(f"T: {result.get('technical_score', 0):.0f}")
    with col5:
        st.write(f"F: {result.get('fundamental_score', 0):.0f}")


def render_news_list(news: list[dict[str, Any]], max_items: int = 5) -> None:
    """Render recent news headlines with sentiment badges."""
    from src.analysis.sentiment_analysis import score_text

    for art in news[:max_items]:
        title = art.get("title", "")
        link = art.get("link", "#")
        published = art.get("published", "")
        compound = score_text(title).get("compound", 0)

        if compound >= 0.05:
            label = "Slightly Bullish" if compound < 0.35 else "Bullish"
        elif compound <= -0.05:
            label = "Slightly Bearish" if compound > -0.35 else "Bearish"
        else:
            label = "Neutral"

        badge = sentiment_badge(label)
        st.markdown(
            f'{badge} <a href="{link}" target="_blank">{title}</a>'
            + (f'<br><small style="color:#888">{published}</small>' if published else ""),
            unsafe_allow_html=True,
        )
        st.divider()


def render_fundamentals_table(fund_details: dict[str, float]) -> None:
    """Render a small table of fundamental sub-scores."""
    import pandas as pd

    df = pd.DataFrame(
        [(k.replace("_", " ").title(), f"{v:.1f}") for k, v in fund_details.items() if k != "composite"],
        columns=["Metric", "Score (0-100)"],
    )
    st.dataframe(df, hide_index=True, use_container_width=True)


def ticker_search(all_tickers: list[str], key: str = "search") -> str | None:
    """Render a searchable selectbox for ticker symbols."""
    return st.selectbox("🔍 Search Ticker", options=[""] + sorted(all_tickers), key=key) or None
