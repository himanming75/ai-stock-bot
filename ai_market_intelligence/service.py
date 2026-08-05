from __future__ import annotations
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from .indicators import feature_record
from .io import append_jsonl, read_json_optional, write_csv, write_json
from .quality import validate_record
from .scoring import market_regime, score_record


class AIMarketIntelligenceService:
    def evaluate(
        self,
        *,
        snapshot_path: Path,
        output_dir: Path,
        minimum_bars: int = 35,
        now=None,
    ) -> dict:
        now = now or datetime.now(timezone.utc)
        snapshot = read_json_optional(snapshot_path)
        bars_by_symbol = snapshot.get("bars_by_symbol", {})
        blockers = []
        if not snapshot:
            blockers.append("SNAPSHOT_INPUT_MISSING")
        if not bars_by_symbol:
            blockers.append("BARS_BY_SYMBOL_MISSING")

        records = []
        quality = []
        for symbol, bars in sorted(bars_by_symbol.items()):
            if not bars:
                quality.append({
                    "symbol": symbol,
                    "passed": False,
                    "blockers": ["EMPTY_BARS"],
                    "warnings": [],
                    "feature_count": 0,
                })
                continue
            record = score_record(feature_record(symbol, bars))
            check = validate_record(record, minimum_bars=minimum_bars)
            quality.append(check)
            if check["passed"]:
                records.append(record)

        records.sort(key=lambda x: x["technical_score"], reverse=True)
        for rank, record in enumerate(records, 1):
            record["rank"] = rank

        regime = market_regime(records)
        failed_quality = [x for x in quality if not x["passed"]]
        status = "PASS" if not blockers and records else "BLOCKED"

        seed = {
            "snapshot_sha256": hashlib.sha256(snapshot_path.read_bytes()).hexdigest()
            if snapshot_path.exists() else None,
            "records": records,
            "quality": quality,
            "regime": regime,
        }
        fingerprint = hashlib.sha256(
            json.dumps(seed, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()

        result = {
            "stage": "V1001_TO_V1200_AI_MARKET_INTELLIGENCE_FEATURE_STORE",
            "status": status,
            "generated_at": now.isoformat(),
            "feature_bundle_fingerprint": fingerprint,
            "source_snapshot_path": str(snapshot_path),
            "global_blockers": blockers,
            "symbol_input_count": len(bars_by_symbol),
            "feature_record_count": len(records),
            "quality_failure_count": len(failed_quality),
            "market_regime": regime,
            "ranked_symbols": records,
            "quality_checks": quality,
            "actual_external_network_used": False,
            "actual_broker_read_performed": False,
            "actual_broker_write_performed": False,
            "actual_order_submission_performed": False,
            "actual_paper_orders_submitted": 0,
            "actual_live_orders_submitted": 0,
            "controller_files_modified": False,
            "runtime_files_modified": False,
            "next_fixed_development": "V1201_TO_V1400_MULTI_STRATEGY_ENSEMBLE",
        }

        output_dir.mkdir(parents=True, exist_ok=True)
        write_json(output_dir / "ai_market_intelligence_latest.json", result)
        write_json(output_dir / "feature_vector_latest.json", {
            "generated_at": now.isoformat(),
            "fingerprint": fingerprint,
            "records": records,
        })
        write_json(output_dir / "market_regime_latest.json", regime)
        write_json(output_dir / "feature_quality_report.json", {
            "status": "PASS" if not failed_quality else "PARTIAL",
            "checks": quality,
        })
        write_json(output_dir / "symbol_ranking.json", {
            "generated_at": now.isoformat(),
            "ranking": [
                {
                    "rank": x["rank"],
                    "symbol": x["symbol"],
                    "technical_score": x["technical_score"],
                    "confidence": x["confidence"],
                    "signal": x["signal"],
                }
                for x in records
            ],
        })
        write_csv(output_dir / "feature_dataset_latest.csv", records)
        for record in records:
            append_jsonl(output_dir / "feature_store.jsonl", record)
        append_jsonl(output_dir / "ai_market_intelligence_ledger.jsonl", result)
        return result
