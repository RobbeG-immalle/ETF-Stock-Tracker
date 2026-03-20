"""Reusable Plotly chart components for the finance dashboard."""

from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from config import BB_PERIOD, EMA_LONG, EMA_SHORT, MACD_FAST, MACD_SLOW, RSI_PERIOD, SMA_MID, SMA_SHORT


def candlestick_with_indicators(
    df: pd.DataFrame,
    ticker: str,
    show_volume: bool = True,
    show_bb: bool = True,
    show_sma: bool = True,
    show_ema: bool = False,
) -> go.Figure:
    """Return an interactive candlestick chart with optional overlays."""
    rows = 3 if show_volume else 2
    row_heights = [0.6, 0.2, 0.2] if show_volume else [0.7, 0.3]
    subplot_titles = [ticker, "Volume", f"RSI({RSI_PERIOD})"] if show_volume else [ticker, f"RSI({RSI_PERIOD})"]

    fig = make_subplots(
        rows=rows,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=row_heights,
        subplot_titles=subplot_titles,
    )

    # Candlestick
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            name=ticker,
            increasing_line_color="#00d4aa",
            decreasing_line_color="#ff4b4b",
        ),
        row=1,
        col=1,
    )

    # Bollinger Bands
    if show_bb and "BB_upper" in df.columns:
        for col, dash, name_ in [
            ("BB_upper", "dash", "BB Upper"),
            ("BB_middle", "dot", f"SMA({BB_PERIOD})"),
            ("BB_lower", "dash", "BB Lower"),
        ]:
            if col in df.columns:
                fig.add_trace(
                    go.Scatter(x=df.index, y=df[col], name=name_, line=dict(dash=dash, width=1, color="rgba(100,149,237,0.7)"), showlegend=True),
                    row=1, col=1,
                )

    # SMAs
    if show_sma:
        sma_configs = [(f"SMA_{SMA_SHORT}", "#ffd700"), (f"SMA_{SMA_MID}", "#ff8c00")]
        for col, color in sma_configs:
            if col in df.columns:
                fig.add_trace(
                    go.Scatter(x=df.index, y=df[col], name=col.replace("_", " "), line=dict(width=1.5, color=color)),
                    row=1, col=1,
                )

    # EMAs
    if show_ema:
        ema_configs = [(f"EMA_{EMA_SHORT}", "#00fa9a"), (f"EMA_{EMA_LONG}", "#dc143c")]
        for col, color in ema_configs:
            if col in df.columns:
                fig.add_trace(
                    go.Scatter(x=df.index, y=df[col], name=col.replace("_", " "), line=dict(width=1, color=color, dash="dot")),
                    row=1, col=1,
                )

    # Volume
    if show_volume and "Volume" in df.columns:
        colors = ["#00d4aa" if c >= o else "#ff4b4b" for c, o in zip(df["Close"], df["Open"])]
        fig.add_trace(
            go.Bar(x=df.index, y=df["Volume"], marker_color=colors, name="Volume", showlegend=False),
            row=2, col=1,
        )

    # RSI
    rsi_col = f"RSI_{RSI_PERIOD}"
    rsi_row = 3 if show_volume else 2
    if rsi_col in df.columns:
        fig.add_trace(
            go.Scatter(x=df.index, y=df[rsi_col], name=f"RSI({RSI_PERIOD})", line=dict(color="#9370db", width=1.5)),
            row=rsi_row, col=1,
        )
        fig.add_hline(y=70, line_dash="dash", line_color="red", row=rsi_row, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="green", row=rsi_row, col=1)

    fig.update_layout(
        template="plotly_dark",
        xaxis_rangeslider_visible=False,
        height=600,
        margin=dict(l=40, r=40, t=40, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


def macd_chart(df: pd.DataFrame, ticker: str) -> go.Figure:
    """Return a MACD chart (MACD line, signal, histogram)."""
    if "MACD" not in df.columns:
        return go.Figure()

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df["MACD"], name="MACD", line=dict(color="#00d4aa", width=1.5)))
    fig.add_trace(go.Scatter(x=df.index, y=df["MACD_signal"], name="Signal", line=dict(color="#ff8c00", width=1.5)))

    colors = ["#00d4aa" if v >= 0 else "#ff4b4b" for v in df["MACD_hist"].fillna(0)]
    fig.add_trace(go.Bar(x=df.index, y=df["MACD_hist"], name="Histogram", marker_color=colors))

    fig.update_layout(
        title=f"{ticker} — MACD ({MACD_FAST}/{MACD_SLOW})",
        template="plotly_dark",
        height=300,
        margin=dict(l=40, r=40, t=40, b=40),
    )
    return fig


def radar_chart(scores: dict[str, float], ticker: str) -> go.Figure:
    """Return a radar/spider chart of score dimensions."""
    categories = list(scores.keys())
    values = list(scores.values())

    fig = go.Figure(
        go.Scatterpolar(
            r=values + [values[0]],
            theta=categories + [categories[0]],
            fill="toself",
            fillcolor="rgba(0,212,170,0.2)",
            line=dict(color="#00d4aa", width=2),
            name=ticker,
        )
    )
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        template="plotly_dark",
        title=f"{ticker} — Score Breakdown",
        height=350,
        margin=dict(l=60, r=60, t=60, b=60),
    )
    return fig


def score_bar_chart(results: list[dict[str, Any]], top_n: int = 20) -> go.Figure:
    """Return a horizontal bar chart of buy scores for top *top_n* tickers."""
    subset = results[:top_n]
    tickers = [r["ticker"] for r in reversed(subset)]
    scores = [r["buy_score"] for r in reversed(subset)]
    categories = [r["category"] for r in reversed(subset)]

    color_map = {
        "Strong Buy": "#00d4aa",
        "Buy": "#7ec8a0",
        "Hold": "#ffd700",
        "Sell": "#ff8c00",
        "Strong Sell": "#ff4b4b",
    }
    colors = [color_map.get(c, "#aaa") for c in categories]

    fig = go.Figure(
        go.Bar(
            x=scores,
            y=tickers,
            orientation="h",
            marker_color=colors,
            text=[f"{s:.0f}" for s in scores],
            textposition="outside",
        )
    )
    fig.update_layout(
        template="plotly_dark",
        title="Buy Scores",
        xaxis=dict(range=[0, 105]),
        height=max(300, top_n * 28),
        margin=dict(l=80, r=80, t=40, b=40),
    )
    return fig


def sparkline(prices: pd.DataFrame, color: str = "#00d4aa") -> go.Figure:
    """Return a minimal sparkline figure for a price series."""
    fig = go.Figure(
        go.Scatter(
            x=prices.index,
            y=prices["Close"],
            line=dict(color=color, width=2),
            fill="tozeroy",
            fillcolor=f"rgba(0,212,170,0.1)" if color == "#00d4aa" else "rgba(255,75,75,0.1)",
        )
    )
    fig.update_layout(
        template="plotly_dark",
        height=80,
        margin=dict(l=0, r=0, t=0, b=0),
        showlegend=False,
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def sector_heatmap(results: list[dict[str, Any]]) -> go.Figure:
    """Return a heatmap of average buy scores by sector."""
    from collections import defaultdict

    sector_scores: dict[str, list[float]] = defaultdict(list)
    for r in results:
        sector = r.get("sector", "N/A") or "N/A"
        sector_scores[sector].append(r.get("buy_score", 50))

    sectors = sorted(sector_scores.keys())
    avgs = [sum(v) / len(v) for s in sectors for v in [sector_scores[s]]]

    fig = go.Figure(
        go.Bar(
            x=sectors,
            y=avgs,
            marker_color=avgs,
            marker_colorscale="RdYlGn",
            marker_cmin=0,
            marker_cmax=100,
            text=[f"{a:.0f}" for a in avgs],
            textposition="outside",
        )
    )
    fig.update_layout(
        template="plotly_dark",
        title="Average Buy Score by Sector",
        yaxis=dict(range=[0, 105]),
        height=350,
        margin=dict(l=40, r=40, t=40, b=80),
    )
    return fig


def etf_expense_ratio_chart(etf_results: list[dict[str, Any]]) -> go.Figure:
    """Return a bar chart comparing ETF expense ratios."""
    tickers = [r["ticker"] for r in etf_results if r.get("expense_ratio") is not None]
    ratios = [r["expense_ratio"] * 100 for r in etf_results if r.get("expense_ratio") is not None]

    fig = go.Figure(
        go.Bar(
            x=tickers,
            y=ratios,
            marker_color="#00d4aa",
            text=[f"{v:.2f}%" for v in ratios],
            textposition="outside",
        )
    )
    fig.update_layout(
        template="plotly_dark",
        title="ETF Expense Ratios (%)",
        yaxis_title="Expense Ratio (%)",
        height=350,
        margin=dict(l=40, r=40, t=40, b=80),
    )
    return fig
