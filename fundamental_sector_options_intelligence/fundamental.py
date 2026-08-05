from __future__ import annotations
from .utils import clamp, f, signal


def inverse_valuation(value: float, good: float, bad: float) -> float:
    if value <= 0:
        return -0.25
    if value <= good:
        return 1.0
    if value >= bad:
        return -1.0
    return 1.0 - 2.0 * (value - good) / (bad - good)


def score_fundamental(item: dict) -> dict:
    pe = f(item.get("pe"))
    forward_pe = f(item.get("forward_pe"))
    peg = f(item.get("peg"))
    price_sales = f(item.get("price_sales"))
    price_book = f(item.get("price_book"))
    ev_ebitda = f(item.get("ev_ebitda"))
    roe = f(item.get("roe"))
    roa = f(item.get("roa"))
    gross_margin = f(item.get("gross_margin"))
    operating_margin = f(item.get("operating_margin"))
    net_margin = f(item.get("net_margin"))
    debt_equity = f(item.get("debt_equity"))
    current_ratio = f(item.get("current_ratio"))
    quick_ratio = f(item.get("quick_ratio"))
    revenue_growth = f(item.get("revenue_growth"))
    eps_growth = f(item.get("eps_growth"))
    fcf_margin = f(item.get("fcf_margin"))
    dividend_yield = f(item.get("dividend_yield"))
    buyback_yield = f(item.get("buyback_yield"))

    valuation = (
        inverse_valuation(pe, 15, 40) * 0.20
        + inverse_valuation(forward_pe, 14, 35) * 0.20
        + inverse_valuation(peg, 1, 3) * 0.20
        + inverse_valuation(price_sales, 2, 10) * 0.12
        + inverse_valuation(price_book, 2, 8) * 0.10
        + inverse_valuation(ev_ebitda, 10, 25) * 0.18
    )

    quality = clamp(
        roe * 1.8
        + roa * 1.2
        + gross_margin * 0.35
        + operating_margin * 0.85
        + net_margin * 0.75
        + fcf_margin * 0.65
    )

    growth = clamp(
        revenue_growth * 2.2
        + eps_growth * 2.8
    )

    balance_sheet = clamp(
        (current_ratio - 1.0) * 0.35
        + (quick_ratio - 1.0) * 0.25
        - max(debt_equity - 0.5, 0.0) * 0.45
    )

    shareholder = clamp(
        dividend_yield * 7.0
        + buyback_yield * 8.0
    )

    score = clamp(
        valuation * 0.25
        + quality * 0.30
        + growth * 0.25
        + balance_sheet * 0.12
        + shareholder * 0.08
    )

    return {
        "fundamental_score": round(score, 8),
        "fundamental_signal": signal(score),
        "valuation_score": round(valuation, 8),
        "quality_score": round(quality, 8),
        "growth_score": round(growth, 8),
        "balance_sheet_score": round(balance_sheet, 8),
        "shareholder_return_score": round(shareholder, 8),
    }
