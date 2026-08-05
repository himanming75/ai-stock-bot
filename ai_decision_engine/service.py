from __future__ import annotations
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from .fusion import fuse_symbol
from .io import append_jsonl, read_json, read_json_optional, write_json
from .ranking import rank_candidates
from .timeframes import timeframe_consensus

class AIDecisionEngineService:
    def evaluate(
        self,
        *,
        strategy_path: Path,
        risk_path: Path,
        timeframe_path: Path,
        policy_path: Path,
        output_dir: Path,
        now: datetime | None = None,
    ) -> dict:
        now = now or datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        strategy = read_json_optional(strategy_path)
        risk = read_json_optional(risk_path)
        timeframe_input = read_json_optional(timeframe_path)
        policy = read_json(policy_path)

        strategy_results = strategy.get("strategy_results", [])
        symbol_inputs = strategy.get("symbol_decisions", [])
        decisions = [
            fuse_symbol(item, strategy_results, policy, risk)
            for item in symbol_inputs
        ]

        required_frames = list(
            policy.get("required_timeframes", ["1m", "5m", "15m", "60m"])
        )
        timeframe_results = [
            timeframe_consensus(
                item.get("symbol"),
                timeframe_input,
                required_frames,
            )
            for item in decisions
        ]
        tf_by_symbol = {
            item["symbol"]: item for item in timeframe_results
        }

        for item in decisions:
            tf = tf_by_symbol.get(item["symbol"], {})
            item["timeframe_consensus"] = tf.get("consensus", "HOLD")
            item["timeframe_complete"] = bool(tf.get("complete", False))
            item["missing_timeframes"] = tf.get(
                "missing_timeframes", required_frames
            )
            if policy.get("require_complete_timeframes", False):
                if not item["timeframe_complete"]:
                    item["decision"] = "HOLD"
                    item["reasons"].append(
                        "MULTI_TIMEFRAME_INPUT_INCOMPLETE"
                    )
            if (
                item["decision"] in {"BUY", "SELL"}
                and item["timeframe_complete"]
                and item["timeframe_consensus"] != item["decision"]
            ):
                item["decision"] = "HOLD"
                item["reasons"].append(
                    "MULTI_TIMEFRAME_CONFLICT"
                )

        candidates = rank_candidates(decisions)
        insufficient_input = not symbol_inputs
        status = (
            "INSUFFICIENT_INPUT"
            if insufficient_input
            else "PASS"
        )

        seed = {
            "strategy_fingerprint": strategy.get("framework_fingerprint"),
            "risk_level": risk.get("risk_level"),
            "decisions": decisions,
            "candidates": candidates,
        }
        decision_fingerprint = hashlib.sha256(
            json.dumps(
                seed,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()

        result = {
            "stage": "V491_TO_V540_AI_DECISION_ENGINE",
            "status": status,
            "generated_at": now.isoformat(),
            "decision_fingerprint": decision_fingerprint,
            "source_strategy_status": strategy.get("status"),
            "source_strategy_fingerprint": strategy.get(
                "framework_fingerprint"
            ),
            "risk_context": {
                "risk_level": risk.get("risk_level"),
                "portfolio_risk_score": risk.get(
                    "portfolio_risk_score"
                ),
                "alert_count": risk.get("alert_count"),
            },
            "symbol_decision_count": len(decisions),
            "candidate_count": len(candidates),
            "decisions": decisions,
            "candidate_queue": candidates,
            "timeframe_results": timeframe_results,
            "actual_ai_network_used": False,
            "actual_external_network_used": False,
            "actual_market_network_used": False,
            "actual_broker_read_performed": False,
            "actual_broker_write_performed": False,
            "actual_order_ticket_created": False,
            "actual_order_submission_performed": False,
            "actual_paper_orders_submitted": 0,
            "actual_live_orders_submitted": 0,
            "controller_files_modified": False,
            "runtime_files_modified": False,
            "next_fixed_development": (
                "V541_TO_V590_PORTFOLIO_AND_RISK_INTELLIGENCE"
            ),
        }

        output_dir.mkdir(parents=True, exist_ok=True)
        write_json(output_dir / "ai_decision_latest.json", result)
        write_json(
            output_dir / "candidate_queue.json",
            {
                "generated_at": now.isoformat(),
                "candidate_count": len(candidates),
                "candidates": candidates,
                "order_ticket_created": False,
                "order_submission_enabled": False,
            },
        )
        write_json(
            output_dir / "ai_decision_dashboard.json",
            {
                "generated_at": now.isoformat(),
                "status": status,
                "decision_fingerprint": decision_fingerprint,
                "symbol_decision_count": len(decisions),
                "candidate_count": len(candidates),
                "risk_level": risk.get("risk_level"),
                "decisions": decisions,
                "paper_orders_submitted": 0,
                "live_orders_submitted": 0,
            },
        )
        write_json(
            output_dir / "timeframe_consensus.json",
            {
                "generated_at": now.isoformat(),
                "required_timeframes": required_frames,
                "results": timeframe_results,
            },
        )
        append_jsonl(
            output_dir / "ai_decision_ledger.jsonl",
            result,
        )
        for decision in decisions:
            append_jsonl(
                output_dir / "symbol_decision_ledger.jsonl",
                {
                    "generated_at": now.isoformat(),
                    **decision,
                    "order_ticket_created": False,
                    "order_submission_enabled": False,
                },
            )
        return result
