from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from decimal import Decimal
from typing import Iterable, Mapping, Any

from .models import FusionInput, MarketContext
from .ranking import SymbolRanker
from .regime import RegimeClassifier


class MarketIntelligenceFusionService:
    def __init__(self) -> None:
        self.regime_classifier = RegimeClassifier()
        self.ranker = SymbolRanker()

    def fuse(self, records: Iterable[FusionInput | Mapping[str, Any]]) -> MarketContext:
        items = tuple(
            record if isinstance(record, FusionInput) else FusionInput.from_mapping(record)
            for record in records
        )
        regime, risk_mode, market_score = self.regime_classifier.classify(items)
        ranked = tuple(
            sorted(
                (self.ranker.rank(item, regime) for item in items),
                key=lambda x: (x.composite_score, x.confidence, x.symbol),
                reverse=True,
            )
        )
        warnings: list[str] = []
        blockers: list[str] = []
        if not items:
            blockers.append("NO_MARKET_DATA")
        if all(x.trade_bias == "BLOCKED" for x in ranked) and ranked:
            blockers.append("ALL_SYMBOLS_BLOCKED")
        if any(x.confidence < Decimal("0.70") for x in ranked):
            warnings.append("LOW_CONFIDENCE_SYMBOLS_PRESENT")
        if risk_mode == "RISK_OFF":
            warnings.append("MARKET_RISK_OFF")

        confidence = (
            sum((x.confidence for x in ranked), start=market_score * 0) / len(ranked)
            if ranked
            else market_score * 0
        )
        return MarketContext(
            market_regime=regime,
            risk_mode=risk_mode,
            market_score=market_score,
            confidence=confidence,
            ranked_symbols=ranked,
            warnings=tuple(sorted(set(warnings))),
            blockers=tuple(sorted(set(blockers))),
            source_count=len(items),
        )

    def run_file(self, input_path: Path, output_path: Path) -> dict:
        payload = json.loads(input_path.read_text(encoding="utf-8"))
        records = payload["symbols"] if isinstance(payload, dict) else payload
        context = self.fuse(records)
        result = {
            "stage": "MARKET_INTELLIGENCE_DATA_FUSION_MEGA_BUNDLE",
            "status": "PASS" if not context.blockers else "BLOCKED",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "market_context": context.as_json(),
            "actual_external_network_used": False,
            "actual_broker_read_performed": False,
            "actual_broker_write_performed": False,
            "actual_order_submission_performed": False,
            "actual_paper_orders_submitted": 0,
            "actual_live_orders_submitted": 0,
            "next_fixed_development": "AI_SYMBOL_SELECTION_AND_DECISION_ORCHESTRATION",
            "next_market_dependent_action": "P3_ACTUAL_PAPER_ORDER_VALIDATION",
        }
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        return result
