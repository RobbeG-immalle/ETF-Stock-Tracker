"""Main Streamlit dashboard for the ETF & Stock AI Tracker.

Run with:
    streamlit run src/dashboard/app.py
"""

from __future__ import annotations

import sys
import os

# Ensure project root is on the path so config and src packages are importable
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import streamlit as st

from config import (
    DASHBOARD_TITLE,
    ETF_WATCHLIST,
    REFRESH_INTERVAL_MINUTES,
    STOCK_SCORING_WEIGHTS,
    ETF_SCORING_WEIGHTS,
    STOCK_WATCHLIST,
    TOP_N_PICKS,
)
from src.analysis.scoring_engine import run_full_analysis
from src.dashboard.charts import (
    candlestick_with_indicators,
    etf_expense_ratio_chart,
    investment_projection_chart,
    macd_chart,
    radar_chart,
    score_bar_chart,
    sector_heatmap,
    sparkline,
)
from src.dashboard.auth import render_login_page, render_logout_button
from src.dashboard.components import (
    metric_card,
    render_fundamentals_table,
    render_news_list,
    render_score_row,
    score_badge,
    ticker_search,
)
from src.data.data_manager import DataManager

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title=DASHBOARD_TITLE,
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Session state helpers
# ---------------------------------------------------------------------------

def _init_session_state() -> None:
    if "last_refresh" not in st.session_state:
        st.session_state["last_refresh"] = None
    if "analysis_results" not in st.session_state:
        st.session_state["analysis_results"] = []
    if "stock_watchlist" not in st.session_state:
        st.session_state["stock_watchlist"] = list(STOCK_WATCHLIST)
    if "etf_watchlist" not in st.session_state:
        st.session_state["etf_watchlist"] = list(ETF_WATCHLIST)
    if "scoring_weights_stock" not in st.session_state:
        st.session_state["scoring_weights_stock"] = dict(STOCK_SCORING_WEIGHTS)
    if "scoring_weights_etf" not in st.session_state:
        st.session_state["scoring_weights_etf"] = dict(ETF_SCORING_WEIGHTS)


def _load_data_and_analyze(force: bool = False) -> list[dict[str, Any]]:
    """Fetch data and run analysis, using session cache."""
    last = st.session_state.get("last_refresh")
    if (
        not force
        and last is not None
        and st.session_state.get("analysis_results")
    ):
        elapsed = (datetime.now(tz=timezone.utc) - last).total_seconds() / 60
        if elapsed < REFRESH_INTERVAL_MINUTES:
            return st.session_state["analysis_results"]  # type: ignore[return-value]

    with st.spinner("🔄 Fetching data and running AI analysis… (this may take a minute)"):
        dm = DataManager(
            stock_watchlist=st.session_state["stock_watchlist"],
            etf_watchlist=st.session_state["etf_watchlist"],
        )
        data = dm.fetch_all_data(verbose=False)
        results = run_full_analysis(data)

    st.session_state["analysis_results"] = results
    st.session_state["last_refresh"] = datetime.now(tz=timezone.utc)
    return results


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

def _render_sidebar(results: list[dict[str, Any]]) -> str:
    with st.sidebar:
        st.title("📈 ETF & Stock AI Tracker")
        st.caption(f"Logged in as **{st.session_state.get('username', '')}**")
        render_logout_button()
        st.divider()

        page = st.radio(
            "Navigate",
            ["🏠 Overview", "📊 Stock Analysis", "📈 ETF Analysis", "💰 Investment Estimator", "⚙️ Settings"],
        )

        st.divider()
        last = st.session_state.get("last_refresh")
        if last:
            st.caption(f"Last updated: {last.strftime('%Y-%m-%d %H:%M UTC')}")
        if st.button("🔄 Refresh Data", use_container_width=True):
            _load_data_and_analyze(force=True)
            st.rerun()

    return page


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------

def _page_overview(results: list[dict[str, Any]]) -> None:
    st.header("🏠 Market Overview")

    stock_results = [r for r in results if not r.get("is_etf")]
    etf_results = [r for r in results if r.get("is_etf")]

    # ---- Top picks summary
    col_s, col_e = st.columns(2)

    with col_s:
        st.subheader(f"🏆 Top {TOP_N_PICKS} Stock Picks")
        for r in stock_results[:TOP_N_PICKS]:
            with st.container():
                c1, c2, c3 = st.columns([3, 3, 2])
                with c1:
                    st.markdown(f"**{r['ticker']}** — {r.get('name', '')[:25]}")
                with c2:
                    st.markdown(score_badge(r["category"], r["buy_score"]), unsafe_allow_html=True)
                with c3:
                    price = r.get("price")
                    st.write(f"${price:.2f}" if price else "N/A")

    with col_e:
        st.subheader(f"🏆 Top {TOP_N_PICKS} ETF Picks")
        for r in etf_results[:TOP_N_PICKS]:
            with st.container():
                c1, c2, c3 = st.columns([3, 3, 2])
                with c1:
                    st.markdown(f"**{r['ticker']}** — {r.get('name', '')[:25]}")
                with c2:
                    st.markdown(score_badge(r["category"], r["buy_score"]), unsafe_allow_html=True)
                with c3:
                    price = r.get("price")
                    st.write(f"${price:.2f}" if price else "N/A")

    st.divider()

    # ---- Score bar charts
    c1, c2 = st.columns(2)
    with c1:
        if stock_results:
            st.plotly_chart(score_bar_chart(stock_results, top_n=15), use_container_width=True)
    with c2:
        if etf_results:
            st.plotly_chart(score_bar_chart(etf_results, top_n=10), use_container_width=True)

    # ---- Sector heatmap
    if results:
        st.subheader("🗺️ Sector Performance Heatmap")
        st.plotly_chart(sector_heatmap(results), use_container_width=True)


def _page_stock_analysis(results: list[dict[str, Any]]) -> None:
    st.header("📊 Stock Analysis")

    stock_results = [r for r in results if not r.get("is_etf")]
    if not stock_results:
        st.info("No stock data yet. Click **Refresh Data** in the sidebar.")
        return

    # Summary table
    st.subheader("All Stocks")
    df_table = pd.DataFrame(
        [
            {
                "Ticker": r["ticker"],
                "Name": (r.get("name") or "")[:30],
                "Price": f"${r['price']:.2f}" if r.get("price") else "N/A",
                "Buy Score": r["buy_score"],
                "Category": r["category"],
                "Technical": r.get("technical_score", 0),
                "Fundamental": r.get("fundamental_score", 0),
                "Sentiment": r.get("sentiment_score", 0),
                "Sector": r.get("sector", "N/A"),
                "P/E": f"{r['pe_ratio']:.1f}" if r.get("pe_ratio") else "N/A",
                "Div Yield": f"{r['dividend_yield']*100:.2f}%" if r.get("dividend_yield") else "N/A",
            }
            for r in stock_results
        ]
    )
    st.dataframe(
        df_table.sort_values("Buy Score", ascending=False),
        use_container_width=True,
        hide_index=True,
    )

    st.divider()

    # ---- Detailed view
    st.subheader("🔍 Detailed Analysis")
    selected = ticker_search([r["ticker"] for r in stock_results], key="stock_search")
    if selected:
        r = next((x for x in stock_results if x["ticker"] == selected), None)
        if r:
            _render_detailed_analysis(r)


def _page_etf_analysis(results: list[dict[str, Any]]) -> None:
    st.header("📈 ETF Analysis")

    etf_results = [r for r in results if r.get("is_etf")]
    if not etf_results:
        st.info("No ETF data yet. Click **Refresh Data** in the sidebar.")
        return

    # Summary table
    st.subheader("All ETFs")
    df_table = pd.DataFrame(
        [
            {
                "Ticker": r["ticker"],
                "Name": (r.get("name") or "")[:35],
                "Price": f"${r['price']:.2f}" if r.get("price") else "N/A",
                "Buy Score": r["buy_score"],
                "Category": r["category"],
                "Technical": r.get("technical_score", 0),
                "Expense Ratio": f"{r['expense_ratio']*100:.2f}%" if r.get("expense_ratio") else "N/A",
                "Category/Sector": r.get("sector", "N/A"),
            }
            for r in etf_results
        ]
    )
    st.dataframe(
        df_table.sort_values("Buy Score", ascending=False),
        use_container_width=True,
        hide_index=True,
    )

    st.divider()

    # Expense ratio comparison
    st.subheader("💰 Expense Ratio Comparison")
    st.plotly_chart(etf_expense_ratio_chart(etf_results), use_container_width=True)

    st.divider()

    # Detailed view
    st.subheader("🔍 Detailed ETF Analysis")
    selected = ticker_search([r["ticker"] for r in etf_results], key="etf_search")
    if selected:
        r = next((x for x in etf_results if x["ticker"] == selected), None)
        if r:
            _render_detailed_analysis(r)


def _render_detailed_analysis(r: dict[str, Any]) -> None:
    """Render the detailed analysis view for a single ticker."""
    ticker = r["ticker"]
    st.markdown(
        f"### {ticker} — {r.get('name', ticker)}\n"
        + score_badge(r["category"], r["buy_score"]),
        unsafe_allow_html=True,
    )
    st.write(r.get("explanation", ""))
    st.divider()

    # Metrics row
    price = r.get("price")
    cols = st.columns(4)
    cols[0].metric("Price", f"${price:.2f}" if price else "N/A")
    cols[1].metric("Buy Score", f"{r['buy_score']:.0f}/100")
    cols[2].metric("Technical", f"{r.get('technical_score', 0):.0f}/100")
    cols[3].metric("Fundamental", f"{r.get('fundamental_score', 0):.0f}/100")

    tab_chart, tab_fund, tab_sent, tab_radar = st.tabs(
        ["📉 Chart", "📋 Fundamentals", "📰 News & Sentiment", "🕸️ Score Radar"]
    )

    with tab_chart:
        prices_df = r.get("prices_df")
        if prices_df is not None and not prices_df.empty:
            st.plotly_chart(candlestick_with_indicators(prices_df, ticker), use_container_width=True)
            st.plotly_chart(macd_chart(prices_df, ticker), use_container_width=True)
        else:
            st.info("No price data available.")

    with tab_fund:
        fund_details = r.get("fund_details", {})
        if fund_details:
            render_fundamentals_table(fund_details)
        # Raw meta metrics
        meta_cols = st.columns(3)
        meta_cols[0].metric("P/E Ratio", f"{r['pe_ratio']:.1f}" if r.get("pe_ratio") else "N/A")
        if not r.get("is_etf"):
            meta_cols[1].metric(
                "Div Yield",
                f"{r['dividend_yield']*100:.2f}%" if r.get("dividend_yield") else "N/A",
            )
            meta_cols[2].metric("Sector", r.get("sector", "N/A"))
        else:
            meta_cols[1].metric(
                "Expense Ratio",
                f"{r['expense_ratio']*100:.2f}%" if r.get("expense_ratio") else "N/A",
            )
            meta_cols[2].metric("Category", r.get("sector", "N/A"))

    with tab_sent:
        sent = r.get("sentiment_details", {})
        if sent:
            s_cols = st.columns(3)
            s_cols[0].metric("Avg Compound", f"{sent.get('avg_compound', 0):.3f}")
            s_cols[1].metric("Sentiment", sent.get("sentiment_label", "N/A"))
            s_cols[2].metric("Articles", sent.get("article_count", 0))
        news = r.get("news", [])
        if news:
            render_news_list(news)
        else:
            st.info("No recent news available.")

    with tab_radar:
        fund_details = r.get("fund_details", {})
        radar_scores = {k.replace("_", " ").title(): v for k, v in fund_details.items() if k != "composite"}
        radar_scores["Technical"] = r.get("technical_score", 50)
        radar_scores["Sentiment"] = r.get("sentiment_score", 50)
        if radar_scores:
            st.plotly_chart(radar_chart(radar_scores, ticker), use_container_width=True)


def _compute_projection(
    prices_df: pd.DataFrame,
    budget: float,
    months: int,
) -> dict[str, Any]:
    """Compute projected investment growth based on historical returns.

    Uses log-returns from the historical price series to derive annualised
    return and volatility, then projects three scenarios (average ± 1 std‑dev).
    """
    if prices_df is None or prices_df.empty or "Close" not in prices_df.columns:
        return {}

    close = prices_df["Close"].dropna()
    if len(close) < 2:
        return {}

    # Daily log-returns
    log_returns = np.log(close / close.shift(1)).dropna()
    if log_returns.empty:
        return {}

    trading_days_per_year = 252
    daily_mean = float(log_returns.mean())
    daily_std = float(log_returns.std())

    annual_return = daily_mean * trading_days_per_year
    annual_volatility = daily_std * np.sqrt(trading_days_per_year)

    # Monthly rates (linear approximation, suitable for estimation purposes)
    monthly_return = annual_return / 12
    monthly_std = annual_volatility / np.sqrt(12)

    month_range = list(range(months + 1))
    conservative_vals: list[float] = []
    average_vals: list[float] = []
    optimistic_vals: list[float] = []

    for m in month_range:
        avg = budget * np.exp(monthly_return * m)
        con = budget * np.exp((monthly_return - monthly_std) * m)
        opt = budget * np.exp((monthly_return + monthly_std) * m)
        average_vals.append(float(avg))
        conservative_vals.append(float(con))
        optimistic_vals.append(float(opt))

    return {
        "months": month_range,
        "conservative": conservative_vals,
        "average": average_vals,
        "optimistic": optimistic_vals,
        "annual_return": annual_return,
        "annual_volatility": annual_volatility,
    }


def _page_investment_estimator(results: list[dict[str, Any]]) -> None:
    st.header("💰 Investment Estimator")
    st.markdown(
        "Estimate how your investment could grow over time based on "
        "historical performance. Select a ticker, enter your budget, "
        "and choose a time horizon."
    )

    if not results:
        st.info("No data yet. Click **Refresh Data** in the sidebar.")
        return

    all_tickers = sorted([r["ticker"] for r in results])

    # ---- User inputs
    col_ticker, col_budget, col_period = st.columns([2, 2, 2])

    with col_ticker:
        selected_ticker = st.selectbox(
            "📌 Ticker",
            options=all_tickers,
            key="estimator_ticker",
        )

    with col_budget:
        budget = st.number_input(
            "💶 Budget (€)",
            min_value=1.0,
            max_value=10_000_000.0,
            value=500.0,
            step=50.0,
            key="estimator_budget",
        )

    period_options = {
        "6 Months": 6,
        "1 Year": 12,
        "2 Years": 24,
        "3 Years": 36,
        "5 Years": 60,
        "10 Years": 120,
    }
    with col_period:
        period_label = st.selectbox(
            "📅 Time Horizon",
            options=list(period_options.keys()),
            index=1,
            key="estimator_period",
        )
    months = period_options[period_label]

    r = next((x for x in results if x["ticker"] == selected_ticker), None)
    if r is None:
        st.warning("Ticker not found in current analysis results.")
        return

    prices_df = r.get("prices_df")
    projection = _compute_projection(prices_df, budget, months)

    if not projection:
        st.warning(
            f"Not enough historical price data for **{selected_ticker}** to compute a projection."
        )
        return

    st.divider()

    # ---- Projection chart
    fig = investment_projection_chart(
        months=projection["months"],
        conservative=projection["conservative"],
        average=projection["average"],
        optimistic=projection["optimistic"],
        ticker=selected_ticker,
        budget=budget,
    )
    st.plotly_chart(fig, use_container_width=True)

    # ---- Summary metrics
    st.subheader("📊 Projected Outcomes")
    final_avg = projection["average"][-1]
    final_con = projection["conservative"][-1]
    final_opt = projection["optimistic"][-1]

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(
            "🔻 Conservative",
            f"€{final_con:,.2f}",
            delta=f"{(final_con / budget - 1) * 100:+.1f}%",
        )
    with col2:
        st.metric(
            "📈 Average",
            f"€{final_avg:,.2f}",
            delta=f"{(final_avg / budget - 1) * 100:+.1f}%",
        )
    with col3:
        st.metric(
            "🔺 Optimistic",
            f"€{final_opt:,.2f}",
            delta=f"{(final_opt / budget - 1) * 100:+.1f}%",
        )

    st.divider()

    # ---- Historical statistics
    st.subheader("📉 Historical Statistics")
    annual_ret = projection["annual_return"]
    annual_vol = projection["annual_volatility"]
    stat_c1, stat_c2, stat_c3 = st.columns(3)
    stat_c1.metric("Annualised Return", f"{annual_ret * 100:.1f}%")
    stat_c2.metric("Annualised Volatility", f"{annual_vol * 100:.1f}%")
    stat_c3.metric("Buy Score", f"{r.get('buy_score', 0):.0f}/100")

    st.caption(
        "⚠️ **Disclaimer:** Projections are based on historical performance and "
        "do not guarantee future results. The conservative and optimistic scenarios "
        "represent ±1 standard deviation from the historical average. "
        "Always do your own research before investing."
    )


def _page_settings() -> None:
    st.header("⚙️ Settings")

    # ---- Watchlist editor
    st.subheader("📋 Watchlist")
    col1, col2 = st.columns(2)

    with col1:
        st.write("**Stocks**")
        stocks_text = st.text_area(
            "One ticker per line",
            value="\n".join(st.session_state["stock_watchlist"]),
            height=200,
            key="stocks_input",
        )
        if st.button("Update Stock Watchlist"):
            new_stocks = [s.strip().upper() for s in stocks_text.splitlines() if s.strip()]
            st.session_state["stock_watchlist"] = new_stocks
            st.success(f"Updated: {len(new_stocks)} stocks")

    with col2:
        st.write("**ETFs**")
        etfs_text = st.text_area(
            "One ticker per line",
            value="\n".join(st.session_state["etf_watchlist"]),
            height=200,
            key="etfs_input",
        )
        if st.button("Update ETF Watchlist"):
            new_etfs = [s.strip().upper() for s in etfs_text.splitlines() if s.strip()]
            st.session_state["etf_watchlist"] = new_etfs
            st.success(f"Updated: {len(new_etfs)} ETFs")

    st.divider()

    # ---- Scoring weights
    st.subheader("⚖️ Scoring Weights")
    col_sw, col_ew = st.columns(2)

    with col_sw:
        st.write("**Stock Weights** (must sum to 1.0)")
        w = st.session_state["scoring_weights_stock"]
        tech_w = st.slider("Technical", 0.0, 1.0, w["technical"], 0.05, key="s_tech")
        fund_w = st.slider("Fundamental", 0.0, 1.0, w["fundamental"], 0.05, key="s_fund")
        sent_w = st.slider("Sentiment", 0.0, 1.0, w["sentiment"], 0.05, key="s_sent")
        total = tech_w + fund_w + sent_w
        st.write(f"Sum: {total:.2f}" + (" ✅" if abs(total - 1.0) < 0.01 else " ⚠️ must equal 1.0"))
        if st.button("Save Stock Weights") and abs(total - 1.0) < 0.01:
            st.session_state["scoring_weights_stock"] = {"technical": tech_w, "fundamental": fund_w, "sentiment": sent_w}
            st.success("Stock weights saved!")

    with col_ew:
        st.write("**ETF Weights** (must sum to 1.0)")
        w = st.session_state["scoring_weights_etf"]
        tech_w_e = st.slider("Technical", 0.0, 1.0, w["technical"], 0.05, key="e_tech")
        fund_w_e = st.slider("Fundamental", 0.0, 1.0, w["fundamental"], 0.05, key="e_fund")
        sent_w_e = st.slider("Sentiment", 0.0, 1.0, w["sentiment"], 0.05, key="e_sent")
        total_e = tech_w_e + fund_w_e + sent_w_e
        st.write(f"Sum: {total_e:.2f}" + (" ✅" if abs(total_e - 1.0) < 0.01 else " ⚠️ must equal 1.0"))
        if st.button("Save ETF Weights") and abs(total_e - 1.0) < 0.01:
            st.session_state["scoring_weights_etf"] = {"technical": tech_w_e, "fundamental": fund_w_e, "sentiment": sent_w_e}
            st.success("ETF weights saved!")

    st.divider()

    # ---- Cache management
    st.subheader("🗑️ Cache Management")
    cache_ticker = st.text_input("Ticker to invalidate (leave blank for all)")
    if st.button("Clear Cache"):
        dm = DataManager(
            stock_watchlist=st.session_state["stock_watchlist"],
            etf_watchlist=st.session_state["etf_watchlist"],
        )
        dm.invalidate_cache(cache_ticker.strip().upper() or None)
        st.session_state["analysis_results"] = []
        st.session_state["last_refresh"] = None
        st.success("Cache cleared!")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    # Gate the entire dashboard behind authentication
    if not render_login_page():
        return

    _init_session_state()
    results = _load_data_and_analyze()

    page = _render_sidebar(results)

    if page == "🏠 Overview":
        _page_overview(results)
    elif page == "📊 Stock Analysis":
        _page_stock_analysis(results)
    elif page == "📈 ETF Analysis":
        _page_etf_analysis(results)
    elif page == "💰 Investment Estimator":
        _page_investment_estimator(results)
    elif page == "⚙️ Settings":
        _page_settings()


if __name__ == "__main__":
    main()
