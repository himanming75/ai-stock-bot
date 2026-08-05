from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from .io import append_jsonl, read_json, write_json
from .models import D
from .registry import build_registry
from .voting import vote


class StrategyFrameworkService:
    def evaluate(
        self,
        *,
        strategy_config_path: Path,
        market_fixture_path: Path,
        output_dir: Path,
        now: datetime | None = None,
    ) -> dict:
        now = now or datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        config = read_json(strategy_config_path)
        market = read_json(market_fixture_path)
        strategies, registry_blockers = build_registry(config)
        symbols = market.get("symbols", {})

        strategy_results = []
        symbol_decisions = []
        weights = {
            item["name"]: item["weight"]
            for item in strategies
        }
        minimum_score = D(
            config.get("voting", {}).get(
                "minimum_combined_score", "5"
            )
        )

        for symbol, symbol_data in symbols.items():
            bars = list(symbol_data.get("bars", []))
            per_symbol = []
            for item in strategies:
                result = item["instance"].evaluate(
                    symbol,
                    bars,
                    item["config"],
                )
                per_symbol.append(result)
                strategy_results.append(result)
            combined = vote(
                per_symbol,
                weights,
                minimum_score,
            )
            symbol_decisions.append(
                {
                    "symbol": symbol,
                    "status": (
                        "PASS"
                        if combined["contributor_count"] > 0
                        else "INSUFFICIENT_DATA"
                    ),
                    **combined,
                    "order_ticket_created": False,
                    "order_submission_enabled": False,
                }
            )

        strategy_health = []
        for item in strategies:
            rows = [
                result for result in strategy_results
                if result["strategy"] == item["name"]
            ]
            pass_count = sum(
                1 for result in rows
                if result["status"] == "PASS"
            )
            strategy_health.append(
                {
                    "strategy": item["name"],
                    "evaluation_count": len(rows),
                    "pass_count": pass_count,
                    "insufficient_data_count": len(rows) - pass_count,
                    "health_status": (
                        "PASS" if pass_count else "NO_USABLE_DATA"
                    ),
                }
            )

        seed = {
            "config": config,
            "symbols": sorted(symbols),
            "decisions": symbol_decisions,
        }
        framework_fingerprint = hashlib.sha256(
            json.dumps(
                seed,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()

        result = {
            "stage": "V461_TO_V490_STRATEGY_FRAMEWORK",
            "status": (
                "PASS"
                if not registry_blockers
                else "PASS_WITH_REGISTRY_BLOCKERS"
            ),
            "generated_at": now.isoformat(),
            "framework_fingerprint": framework_fingerprint,
            "registry_blockers": registry_blockers,
            "enabled_strategy_count": len(strategies),
            "symbol_count": len(symbols),
            "strategy_results": strategy_results,
            "symbol_decisions": symbol_decisions,
            "strategy_health": strategy_health,
            "candidate_signal_count": sum(
                1 for item in symbol_decisions
                if item["signal"] in {"BUY", "SELL"}
            ),
            "actual_market_network_used": False,
            "actual_external_network_used": False,
            "actual_broker_read_performed": False,
            "actual_broker_write_performed": False,
            "actual_order_ticket_created": False,
            "actual_order_submission_performed": False,
            "actual_paper_orders_submitted": 0,
            "actual_live_orders_submitted": 0,
            "controller_files_modified": False,
            "runtime_files_modified": False,
            "next_fixed_development": (
                "V491_TO_V520_AI_DECISION_ENGINE"
            ),
        }

        output_dir.mkdir(parents=True, exist_ok=True)
        write_json(
            output_dir / "strategy_framework_latest.json",
            result,
        )
        write_json(
            output_dir / "strategy_dashboard.json",
            {
                "generated_at": now.isoformat(),
                "status": result["status"],
                "enabled_strategy_count": len(strategies),
                "symbol_count": len(symbols),
                "candidate_signal_count": result[
                    "candidate_signal_count"
                ],
                "symbol_decisions": symbol_decisions,
                "strategy_health": strategy_health,
                "broker_write": False,
                "order_ticket_created": False,
                "paper_orders_submitted": 0,
                "live_orders_submitted": 0,
            },
        )
        write_json(
            output_dir / "strategy_registry_snapshot.json",
            {
                "strategies": [
                    {
                        "name": item["name"],
                        "weight": item["weight"],
                        "config": item["config"],
                    }
                    for item in strategies
                ],
                "blockers": registry_blockers,
            },
        )
        append_jsonl(
            output_dir / "strategy_decision_ledger.jsonl",
            result,
        )
        for item in strategy_results:
            append_jsonl(
                output_dir / "strategy_signal_ledger.jsonl",
                {
                    "generated_at": now.isoformat(),
                    **item,
                    "order_ticket_created": False,
                    "order_submission_enabled": False,
                },
            )
        return result
