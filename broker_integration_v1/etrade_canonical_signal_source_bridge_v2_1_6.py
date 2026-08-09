from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Iterable

from alpaca_market_data.historical_signal_engine_v79_71_75 import (
    SignalConfig,
    build_signals,
    validate_signal_rows,
)
from .etrade_ai_signal_bridge_v2_1_5 import ETradeAISignalDecisionBridge


def _latest_per_symbol(rows: Iterable[dict]) -> list[dict]:
    latest={}
    for row in rows:
        symbol=str(row["symbol"]).upper().strip()
        ts=str(row["timestamp"])
        key=(symbol,str(row.get("timeframe","")))
        if key not in latest or ts > str(latest[key]["timestamp"]):
            latest[key]=row
    return sorted(latest.values(),key=lambda x:(x["symbol"],x.get("timeframe","")))


def canonical_signal_to_recommendation(row: dict, quantity: Decimal=Decimal("1")) -> dict:
    action=str(row["signal"]).upper()
    if action not in {"BUY","SELL","HOLD"}:
        raise ValueError("canonical signal action must be BUY/SELL/HOLD")
    confidence=Decimal(str(row["confidence"]))
    if confidence < 0 or confidence > 1:
        raise ValueError("canonical signal confidence must be between 0 and 1")
    return {
        "symbol":str(row["symbol"]).upper(),
        "action":action,
        "confidence":str(confidence),
        "quantity":str(quantity if action!="HOLD" else Decimal("0")),
        "strategy_id":"V79_71_75_CANONICAL_HISTORICAL_SIGNAL",
        "reason":";".join(str(x) for x in row.get("reasons",[])),
        "source_timestamp":str(row.get("timestamp","")),
        "source_timeframe":str(row.get("timeframe","")),
        "source_score":row.get("score"),
    }


class CanonicalSignalSourceBridgeV216:
    """
    Reuses the existing V79.71-V79.75 canonical signal engine.
    This class performs no network requests and submits no broker orders.
    """

    def __init__(self, signal_config: SignalConfig|None=None, decision_bridge=None):
        self.signal_config=signal_config or SignalConfig()
        self.decision_bridge=decision_bridge or ETradeAISignalDecisionBridge()

    def from_indicator_rows(self, indicator_rows: list[dict], quantity=Decimal("1"), max_signals=3):
        signal_rows=build_signals(indicator_rows,self.signal_config)
        validate_signal_rows(signal_rows)
        latest=_latest_per_symbol(signal_rows)
        recommendations=[canonical_signal_to_recommendation(x,quantity) for x in latest]
        queue=self.decision_bridge.build_signal_queue(recommendations,max_signals=max_signals)
        return {
            "source":"V79_71_75_CANONICAL_HISTORICAL_SIGNAL_ENGINE",
            "source_mode":"OFFLINE_INDICATOR_ROWS",
            "signal_rows":signal_rows,
            "latest_signal_rows":latest,
            "recommendations":recommendations,
            "decision_queue":queue,
            "network_requests_executed":0,
            "broker_orders_submitted":0,
            "profitability_validated":False,
        }

    def from_indicator_jsonl(self, path: str|Path, quantity=Decimal("1"), max_signals=3):
        path=Path(path)
        rows=[]
        for n,line in enumerate(path.read_text(encoding="utf-8").splitlines(),1):
            if not line.strip(): continue
            try:
                rows.append(json.loads(line))
            except Exception as exc:
                raise ValueError(f"invalid indicator JSONL line {n}") from exc
        if not rows:
            raise ValueError("indicator source is empty")
        return self.from_indicator_rows(rows,quantity=quantity,max_signals=max_signals)
