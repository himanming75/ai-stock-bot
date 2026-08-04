from __future__ import annotations
from typing import Any
from ai_signal_intelligence.engine import analyze
from .allocation import assign_weights, cash_weight, diversification_score
from .models import PortfolioCandidate, PortfolioResult
from .scoring import portfolio_score, selection_score
from .selector import select
from .validation import validate


def _candidate_dict(item: dict[str, Any]) -> dict[str, Any]:
    signal = analyze({
        "symbol": item["symbol"],
        "bars": item["bars"],
        "market_trend": item.get("market_trend", 0.0),
        "news_score": item.get("news_score", 0.0),
    }).to_dict()
    liquidity = float(item.get("liquidity_score", 50.0))
    signal["sector"] = str(item.get("sector", "UNKNOWN")).upper()
    signal["liquidity_score"] = max(0.0, min(100.0, liquidity))
    signal["selection_score"] = selection_score(signal, signal["liquidity_score"])
    signal["weight"] = 0.0
    signal["selected"] = False
    signal["exclusion_reasons"] = []
    return signal


def _model(item: dict[str, Any]) -> PortfolioCandidate:
    return PortfolioCandidate(
        symbol=item["symbol"],
        sector=item["sector"],
        action=item["action"],
        confidence=float(item["confidence"]),
        signal_rank=item["signal_rank"],
        signal_score=float(item["signal_score"]),
        risk_score=int(item["risk_score"]),
        risk_level=item["risk_level"],
        expected_holding_days=item["expected_holding_days"],
        liquidity_score=float(item["liquidity_score"]),
        selected=bool(item["selected"]),
        weight=float(item.get("weight", 0.0)),
        selection_score=float(item["selection_score"]),
        reasons=tuple(item.get("reasons", [])),
        exclusion_reasons=tuple(item.get("exclusion_reasons", [])),
    )


def build_portfolio(payload: dict[str, Any]) -> PortfolioResult:
    errors = validate(payload)
    if errors:
        raise ValueError(",".join(errors))

    candidates = [_candidate_dict(item) for item in payload["candidates"]]
    selected, excluded = select(
        candidates,
        maximum_positions=int(payload.get("maximum_positions", 5)),
        maximum_positions_per_sector=int(payload.get("maximum_positions_per_sector", 2)),
        minimum_confidence=float(payload.get("minimum_confidence", 55.0)),
        maximum_risk_score=int(payload.get("maximum_risk_score", 65)),
    )
    cash = cash_weight(selected)
    selected = assign_weights(
        selected,
        cash=cash,
        maximum_single_weight=float(payload.get("maximum_single_weight", 0.35)),
    )

    for item in excluded:
        item["weight"] = 0.0

    return PortfolioResult(
        selected=tuple(_model(item) for item in selected),
        excluded=tuple(_model(item) for item in excluded),
        cash_weight=cash,
        portfolio_score=portfolio_score(selected),
        diversification_score=diversification_score(selected),
        total_selected_weight=round(sum(float(item["weight"]) for item in selected), 6),
    )
