from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class ClosedTradeOutcomeCalibration:
    def __init__(self, project_root: Path) -> None:
        self.root = project_root.resolve()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _float(value: Any, default: float = 0.0) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _load(path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception:
            return {}

    @staticmethod
    def _load_jsonl(path: Path, limit: int = 5000) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        rows: list[dict[str, Any]] = []
        try:
            for line in path.read_text(encoding="utf-8-sig").splitlines()[-limit:]:
                line = line.strip()
                if not line:
                    continue
                try:
                    payload = json.loads(line)
                    if isinstance(payload, dict):
                        rows.append(payload)
                except Exception:
                    continue
        except Exception:
            return []
        return rows

    @staticmethod
    def _write(path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    @staticmethod
    def _append(path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, sort_keys=True) + "\n")

    def _candidate_history(self) -> list[dict[str, Any]]:
        return self._load_jsonl(
            self.root
            / "runtime/paper_observability_intelligence/trade_journal.jsonl"
        )

    def _guard_history(self) -> list[dict[str, Any]]:
        return self._load_jsonl(
            self.root
            / "runtime/paper_autonomous_daily_session/shadow_guard_ledger.jsonl"
        )

    def _outcomes(self) -> list[dict[str, Any]]:
        candidates = [
            self.root
            / "runtime/closed_trade_outcomes/closed_trade_outcomes.jsonl",
            self.root
            / "runtime/paper_trade_outcomes/closed_trade_outcomes.jsonl",
            self.root
            / "release/v14001_15000_paper_autonomous_execution/actual/"
              "closed_trade_outcomes.jsonl",
        ]
        rows: list[dict[str, Any]] = []
        for path in candidates:
            rows.extend(self._load_jsonl(path))
        return rows

    @staticmethod
    def _bucket(confidence: float) -> str:
        if confidence < 0.70:
            return "0.50-0.69"
        if confidence < 0.80:
            return "0.70-0.79"
        if confidence < 0.90:
            return "0.80-0.89"
        return "0.90-1.00"

    def _normalize_outcome(self, row: dict[str, Any]) -> dict[str, Any]:
        pnl = self._float(
            row.get("realized_pl", row.get("pnl", row.get("profit_loss", 0.0)))
        )
        return {
            "trade_id": str(
                row.get("trade_id", row.get("order_id", row.get("id", "")))
            ),
            "symbol": str(row.get("symbol", "")).upper(),
            "side": str(row.get("side", "")).upper(),
            "entry_time": row.get("entry_time"),
            "exit_time": row.get("exit_time"),
            "entry_price": self._float(row.get("entry_price")),
            "exit_price": self._float(row.get("exit_price")),
            "quantity": self._float(row.get("quantity", row.get("qty"))),
            "realized_pl": pnl,
            "realized_return": self._float(
                row.get("realized_return", row.get("return_pct"))
            ),
            "win": pnl > 0,
            "loss": pnl < 0,
            "flat": pnl == 0,
            "source": str(row.get("source", "CLOSED_TRADE_OUTCOME_LEDGER")),
        }

    def _candidate_index(self) -> dict[str, list[dict[str, Any]]]:
        index: dict[str, list[dict[str, Any]]] = {}
        for row in self._candidate_history():
            candidate = row.get("selected_candidate", {})
            if not isinstance(candidate, dict):
                continue
            symbol = str(candidate.get("symbol", "")).upper()
            if not symbol:
                continue
            index.setdefault(symbol, []).append({
                "observed_at_utc": row.get("observed_at_utc"),
                "confidence": self._float(candidate.get("confidence")),
                "consensus_score": self._float(candidate.get("consensus_score")),
                "reward_risk": self._float(candidate.get("reward_risk")),
                "guard_action": row.get("shadow_guard", {}).get("action"),
                "guard_would_allow": row.get("shadow_guard", {}).get(
                    "would_allow_order"
                ),
            })
        return index

    def linked_outcomes(self) -> list[dict[str, Any]]:
        index = self._candidate_index()
        linked: list[dict[str, Any]] = []

        for raw in self._outcomes():
            outcome = self._normalize_outcome(raw)
            history = index.get(outcome["symbol"], [])

            match = history[-1] if history else None
            linked.append({
                **outcome,
                "candidate_linked": match is not None,
                "candidate": match or {
                    "confidence": None,
                    "consensus_score": None,
                    "reward_risk": None,
                    "guard_action": None,
                    "guard_would_allow": None,
                },
            })
        return linked

    def calibration(self) -> dict[str, Any]:
        linked = self.linked_outcomes()
        buckets = {
            "0.50-0.69": [],
            "0.70-0.79": [],
            "0.80-0.89": [],
            "0.90-1.00": [],
        }

        for row in linked:
            confidence = row.get("candidate", {}).get("confidence")
            if confidence is None:
                continue
            confidence = self._float(confidence, -1)
            if confidence < 0:
                continue
            buckets[self._bucket(confidence)].append(row)

        result: dict[str, Any] = {}
        for key, rows in buckets.items():
            pnl_values = [self._float(row.get("realized_pl")) for row in rows]
            wins = sum(1 for value in pnl_values if value > 0)
            losses = sum(1 for value in pnl_values if value < 0)
            flats = sum(1 for value in pnl_values if value == 0)
            count = len(rows)

            avg_win = (
                sum(value for value in pnl_values if value > 0) / wins
                if wins else None
            )
            avg_loss = (
                sum(value for value in pnl_values if value < 0) / losses
                if losses else None
            )
            win_rate = wins / count if count else None
            expectancy = (
                sum(pnl_values) / count if count else None
            )

            result[key] = {
                "sample_count": count,
                "wins": wins,
                "losses": losses,
                "flats": flats,
                "realized_win_rate": (
                    round(win_rate, 6) if win_rate is not None else None
                ),
                "average_win": (
                    round(avg_win, 6) if avg_win is not None else None
                ),
                "average_loss": (
                    round(avg_loss, 6) if avg_loss is not None else None
                ),
                "expectancy": (
                    round(expectancy, 6)
                    if expectancy is not None else None
                ),
            }

        total_linked = sum(item["sample_count"] for item in result.values())
        return {
            "buckets": result,
            "linked_outcome_count": total_linked,
            "status": (
                "CALIBRATION_READY"
                if total_linked >= 20
                else "COLLECTING_CLOSED_TRADE_DATA"
            ),
            "automatic_confidence_adjustment": False,
        }

    def performance_summary(self) -> dict[str, Any]:
        linked = self.linked_outcomes()
        pnl_values = [self._float(row.get("realized_pl")) for row in linked]
        wins = [value for value in pnl_values if value > 0]
        losses = [value for value in pnl_values if value < 0]

        gross_profit = sum(wins)
        gross_loss = abs(sum(losses))
        profit_factor = (
            gross_profit / gross_loss if gross_loss > 0 else None
        )

        return {
            "closed_trade_count": len(linked),
            "win_count": len(wins),
            "loss_count": len(losses),
            "flat_count": sum(1 for value in pnl_values if value == 0),
            "total_realized_pl": round(sum(pnl_values), 6),
            "average_realized_pl": (
                round(sum(pnl_values) / len(pnl_values), 6)
                if pnl_values else None
            ),
            "win_rate": (
                round(len(wins) / len(pnl_values), 6)
                if pnl_values else None
            ),
            "average_win": (
                round(sum(wins) / len(wins), 6) if wins else None
            ),
            "average_loss": (
                round(sum(losses) / len(losses), 6) if losses else None
            ),
            "profit_factor": (
                round(profit_factor, 6)
                if profit_factor is not None else None
            ),
        }

    def guard_comparison(self) -> dict[str, Any]:
        linked = self.linked_outcomes()
        allow_rows = []
        block_rows = []

        for row in linked:
            action = row.get("candidate", {}).get("guard_action")
            if action == "SHADOW_ALLOW":
                allow_rows.append(row)
            elif action == "SHADOW_BLOCK":
                block_rows.append(row)

        def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
            values = [self._float(row.get("realized_pl")) for row in rows]
            return {
                "sample_count": len(rows),
                "average_realized_pl": (
                    round(sum(values) / len(values), 6)
                    if values else None
                ),
                "win_rate": (
                    round(
                        sum(1 for value in values if value > 0) / len(values),
                        6,
                    )
                    if values else None
                ),
            }

        return {
            "shadow_allow_outcomes": summarize(allow_rows),
            "shadow_block_outcomes": summarize(block_rows),
            "comparison_status": (
                "READY"
                if len(allow_rows) >= 10 and len(block_rows) >= 10
                else "INSUFFICIENT_DATA"
            ),
            "guard_enforcement_recommendation": "DO_NOT_ENFORCE_YET",
        }

    def calibration_recommendation(self) -> dict[str, Any]:
        calibration = self.calibration()
        recommendations: list[dict[str, Any]] = []

        for bucket, stats in calibration["buckets"].items():
            count = stats["sample_count"]
            win_rate = stats["realized_win_rate"]

            if count < 10 or win_rate is None:
                action = "COLLECT_MORE_DATA"
            elif bucket == "0.90-1.00" and win_rate < 0.70:
                action = "REVIEW_OVERCONFIDENCE"
            elif bucket == "0.80-0.89" and win_rate < 0.60:
                action = "REVIEW_CONFIDENCE_THRESHOLD"
            elif win_rate >= 0.70:
                action = "CONFIDENCE_BUCKET_HEALTHY"
            else:
                action = "MONITOR"

            recommendations.append({
                "bucket": bucket,
                "sample_count": count,
                "realized_win_rate": win_rate,
                "recommended_action": action,
            })

        return {
            "recommendations": recommendations,
            "automatic_changes": False,
            "human_review_required": True,
        }

    def run(self) -> dict[str, Any]:
        runtime = self.root / "runtime/closed_trade_calibration_v4"

        result = {
            "stage": "CLOSED_TRADE_OUTCOME_CALIBRATION_V4_0",
            "status": "PASS",
            "mode": "READ_ONLY_OUTCOME_ANALYTICS",
            "paper_only": True,
            "etrade_live_write_enabled": False,
            "broker_write_performed": False,
            "linked_outcomes": self.linked_outcomes(),
            "performance_summary": self.performance_summary(),
            "confidence_calibration": self.calibration(),
            "guard_comparison": self.guard_comparison(),
            "calibration_recommendation": (
                self.calibration_recommendation()
            ),
            "generated_at_utc": self._now(),
        }

        self._write(runtime / "latest_calibration_report.json", result)
        self._append(runtime / "calibration_ledger.jsonl", result)

        summary = {
            "generated_at_utc": self._now(),
            "status": "PASS",
            "closed_trade_count": result["performance_summary"][
                "closed_trade_count"
            ],
            "win_rate": result["performance_summary"]["win_rate"],
            "profit_factor": result["performance_summary"]["profit_factor"],
            "calibration_status": result["confidence_calibration"]["status"],
            "guard_comparison_status": result["guard_comparison"][
                "comparison_status"
            ],
            "broker_write_performed": False,
            "etrade_live_write_enabled": False,
        }
        self._write(runtime / "daily_calibration_summary.json", summary)

        return result
