from __future__ import annotations
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from .ensemble import combine
from .io import append_jsonl, read_json_optional, write_csv, write_json
from .strategies import STRATEGIES

class MultiStrategyEnsembleService:
    def evaluate(self, feature_path: Path, regime_path: Path, output_dir: Path, now=None) -> dict:
        now = now or datetime.now(timezone.utc)
        feature_payload = read_json_optional(feature_path)
        regime_payload = read_json_optional(regime_path)
        records = list(feature_payload.get("records", []))
        regime = regime_payload.get("regime", "UNKNOWN")
        blockers = []
        if not feature_payload:
            blockers.append("FEATURE_VECTOR_INPUT_MISSING")
        if not records:
            blockers.append("FEATURE_RECORDS_EMPTY")
        if not regime_payload:
            blockers.append("MARKET_REGIME_INPUT_MISSING")

        outputs = []
        for record in records:
            strategy_results = [fn(record) for fn in STRATEGIES]
            ensemble = combine(strategy_results, regime)
            outputs.append({
                "symbol": record.get("symbol"),
                "timestamp": record.get("timestamp"),
                "rank_from_feature_store": record.get("rank"),
                "market_regime": regime,
                "strategy_results": strategy_results,
                **ensemble,
                "eligible_for_decision_pipeline": (
                    ensemble["confidence"] >= 55
                    and ensemble["ensemble_signal"] != "NEUTRAL"
                ),
            })

        outputs.sort(
            key=lambda x: (x["eligible_for_decision_pipeline"], x["confidence"], abs(x["ensemble_score"])),
            reverse=True,
        )
        for rank, item in enumerate(outputs, 1):
            item["ensemble_rank"] = rank

        seed = {"records": outputs, "regime": regime, "blockers": blockers}
        fingerprint = hashlib.sha256(
            json.dumps(seed, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        status = "PASS" if outputs and not blockers else "BLOCKED"

        result = {
            "stage": "V1201_TO_V1400_MULTI_STRATEGY_ENSEMBLE_ENGINE",
            "status": status,
            "generated_at": now.isoformat(),
            "ensemble_bundle_fingerprint": fingerprint,
            "market_regime": regime,
            "input_feature_count": len(records),
            "ensemble_record_count": len(outputs),
            "eligible_symbol_count": sum(1 for x in outputs if x["eligible_for_decision_pipeline"]),
            "global_blockers": blockers,
            "ranked_ensemble_results": outputs,
            "actual_external_network_used": False,
            "actual_broker_read_performed": False,
            "actual_broker_write_performed": False,
            "actual_order_submission_performed": False,
            "actual_paper_orders_submitted": 0,
            "actual_live_orders_submitted": 0,
            "controller_files_modified": False,
            "runtime_files_modified": False,
            "next_fixed_development": "V1401_TO_V1600_NEWS_EARNINGS_MACRO_INTELLIGENCE",
        }

        output_dir.mkdir(parents=True, exist_ok=True)
        write_json(output_dir / "multi_strategy_ensemble_latest.json", result)
        write_json(output_dir / "ensemble_ranking.json", {"records": outputs})
        write_json(output_dir / "decision_candidate_queue.json", {
            "generated_at": now.isoformat(),
            "items": [x for x in outputs if x["eligible_for_decision_pipeline"]],
            "automatic_execution_enabled": False,
        })
        flat = []
        for item in outputs:
            flat.append({
                "symbol": item["symbol"],
                "ensemble_rank": item["ensemble_rank"],
                "ensemble_score": item["ensemble_score"],
                "ensemble_signal": item["ensemble_signal"],
                "confidence": item["confidence"],
                "disagreement": item["disagreement"],
                "eligible_for_decision_pipeline": item["eligible_for_decision_pipeline"],
            })
        write_csv(output_dir / "ensemble_dataset_latest.csv", flat)
        for item in outputs:
            append_jsonl(output_dir / "strategy_signal_store.jsonl", item)
        append_jsonl(output_dir / "multi_strategy_ensemble_ledger.jsonl", result)
        return result
