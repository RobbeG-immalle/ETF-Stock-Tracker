"""Fundamental analysis scoring.

Scores stocks on valuation, growth, profitability, dividend quality, and
financial health dimensions.  Each sub-score is 0-100; the overall
fundamental score is a weighted average.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def _score_pe(pe: float | None) -> float:
    """Score P/E ratio: lower is better (value investing)."""
    if pe is None or pe <= 0:
        return 50.0
    if pe < 10:
        return 90.0
    if pe < 15:
        return 80.0
    if pe < 20:
        return 70.0
    if pe < 25:
        return 60.0
    if pe < 35:
        return 50.0
    if pe < 50:
        return 35.0
    return 20.0


def _score_pb(pb: float | None) -> float:
    """Score P/B ratio: lower is generally better."""
    if pb is None or pb <= 0:
        return 50.0
    if pb < 1:
        return 90.0
    if pb < 2:
        return 75.0
    if pb < 3:
        return 65.0
    if pb < 5:
        return 50.0
    if pb < 10:
        return 35.0
    return 20.0


def _score_peg(peg: float | None) -> float:
    """Score PEG ratio: <1 is ideal."""
    if peg is None:
        return 50.0
    if peg < 0:
        return 50.0  # negative PEG is hard to interpret
    if peg < 0.5:
        return 95.0
    if peg < 1.0:
        return 85.0
    if peg < 1.5:
        return 65.0
    if peg < 2.0:
        return 50.0
    return 30.0


def _score_growth(growth: float | None) -> float:
    """Score a growth rate (expressed as decimal, e.g. 0.15 = 15%)."""
    if growth is None:
        return 50.0
    pct = growth * 100
    if pct > 30:
        return 95.0
    if pct > 20:
        return 85.0
    if pct > 10:
        return 70.0
    if pct > 0:
        return 55.0
    if pct > -10:
        return 35.0
    return 15.0


def _score_profit_margin(margin: float | None) -> float:
    if margin is None:
        return 50.0
    pct = margin * 100
    if pct > 25:
        return 90.0
    if pct > 15:
        return 75.0
    if pct > 8:
        return 60.0
    if pct > 0:
        return 45.0
    return 20.0


def _score_roe(roe: float | None) -> float:
    if roe is None:
        return 50.0
    pct = roe * 100
    if pct > 30:
        return 90.0
    if pct > 20:
        return 80.0
    if pct > 15:
        return 70.0
    if pct > 10:
        return 60.0
    if pct > 0:
        return 45.0
    return 20.0


def _score_dividend(yield_: float | None, payout: float | None) -> float:
    """Score dividend quality based on yield and payout ratio."""
    if yield_ is None:
        return 50.0   # no dividend is neutral (not penalised)

    y_pct = yield_ * 100
    if y_pct < 0.1:
        return 50.0  # no dividend

    score = 0.0
    # Yield component
    if y_pct > 6:
        score += 40  # high yield but check sustainability
    elif y_pct > 4:
        score += 50
    elif y_pct > 2:
        score += 60
    else:
        score += 40

    # Payout ratio sustainability
    if payout is not None and 0 < payout < 1:
        p_pct = payout * 100
        if p_pct < 30:
            score += 40
        elif p_pct < 50:
            score += 35
        elif p_pct < 70:
            score += 25
        elif p_pct < 90:
            score += 10
        else:
            score += 0  # unsustainable
    else:
        score += 20  # unknown payout — neutral

    return min(100.0, score)


def _score_debt_to_equity(de: float | None) -> float:
    """Lower D/E is better."""
    if de is None:
        return 50.0
    if de < 0:
        return 30.0  # negative equity — risky
    if de < 0.5:
        return 90.0
    if de < 1.0:
        return 75.0
    if de < 2.0:
        return 55.0
    if de < 4.0:
        return 35.0
    return 15.0


def _score_current_ratio(cr: float | None) -> float:
    """Current ratio > 2 is healthy."""
    if cr is None:
        return 50.0
    if cr > 3:
        return 80.0
    if cr > 2:
        return 90.0
    if cr > 1.5:
        return 75.0
    if cr > 1.0:
        return 55.0
    return 25.0


def score_fundamentals(meta: dict[str, Any]) -> dict[str, float]:
    """Compute fundamental sub-scores and composite for *meta*.

    Returns dict with keys: valuation, growth, profitability, dividend,
    financial_health, composite.
    """
    pe = meta.get("pe_ratio")
    pb = meta.get("pb_ratio")
    peg = meta.get("peg_ratio")
    rev_growth = meta.get("revenue_growth")
    earn_growth = meta.get("earnings_growth")
    profit_margin = meta.get("profit_margin")
    roe = meta.get("roe")
    div_yield = meta.get("dividend_yield")
    payout = meta.get("payout_ratio")
    de = meta.get("debt_to_equity")
    cr = meta.get("current_ratio")

    valuation = (
        _score_pe(pe) * 0.45
        + _score_pb(pb) * 0.25
        + _score_peg(peg) * 0.30
    )

    growth = (
        _score_growth(rev_growth) * 0.50
        + _score_growth(earn_growth) * 0.50
    )

    profitability = (
        _score_profit_margin(profit_margin) * 0.50
        + _score_roe(roe) * 0.50
    )

    dividend = _score_dividend(div_yield, payout)

    financial_health = (
        _score_debt_to_equity(de) * 0.60
        + _score_current_ratio(cr) * 0.40
    )

    # Composite: value, growth, profitability are most important
    composite = (
        valuation * 0.30
        + growth * 0.25
        + profitability * 0.25
        + dividend * 0.10
        + financial_health * 0.10
    )

    return {
        "valuation": round(valuation, 1),
        "growth": round(growth, 1),
        "profitability": round(profitability, 1),
        "dividend": round(dividend, 1),
        "financial_health": round(financial_health, 1),
        "composite": round(composite, 1),
    }


def score_etf_fundamentals(meta: dict[str, Any]) -> dict[str, float]:
    """Simplified fundamental scoring for ETFs.

    ETFs have limited fundamental data; we focus on expense ratio and
    historical returns.
    """
    expense_ratio = meta.get("expense_ratio")
    ytd_return = meta.get("ytd_return")
    three_y = meta.get("3y_return")
    five_y = meta.get("5y_return")

    # Expense ratio: lower is better
    if expense_ratio is None:
        cost_score = 50.0
    elif expense_ratio < 0.001:
        cost_score = 95.0
    elif expense_ratio < 0.003:
        cost_score = 85.0
    elif expense_ratio < 0.005:
        cost_score = 70.0
    elif expense_ratio < 0.01:
        cost_score = 55.0
    else:
        cost_score = 35.0

    # Return scores
    ytd_score = _score_growth(ytd_return) if ytd_return is not None else 50.0
    three_y_score = _score_growth(three_y) if three_y is not None else 50.0
    five_y_score = _score_growth(five_y) if five_y is not None else 50.0

    composite = cost_score * 0.30 + ytd_score * 0.20 + three_y_score * 0.25 + five_y_score * 0.25

    return {
        "cost_efficiency": round(cost_score, 1),
        "ytd_performance": round(ytd_score, 1),
        "three_year_performance": round(three_y_score, 1),
        "five_year_performance": round(five_y_score, 1),
        "composite": round(composite, 1),
    }
