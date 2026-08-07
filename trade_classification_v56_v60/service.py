from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class TradeClassificationAttribution:
    def __init__(self, project_root: Path) -> None:
        self.root = project_root.resolve()
        self.runtime = self.root / "runtime/trade_classification_v56_v60"
        self.runtime.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _load(path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception:
            return {}

    @staticmethod
    def _load_jsonl(path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        rows = []
        try:
            for line in path.read_text(encoding="utf-8-sig").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    if isinstance(obj, dict):
                        rows.append(obj)
                except Exception:
                    pass
        except Exception:
            pass
        return rows

    @staticmethod
    def _write(path: Path, payload: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n",
            encoding="utf-8",
        )

    @staticmethod
    def _append(path: Path, payload: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, sort_keys=True, default=str) + "\n")

    @staticmethod
    def _float(value: Any, default: float = 0.0) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _dt(value: Any):
        if not value:
            return None
        try:
            return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except Exception:
            return None

    def _trades(self) -> list[dict[str, Any]]:
        rows = self._load_jsonl(
            self.root
            / "runtime/closed_trade_outcome_v41_v45/"
              "closed_trade_outcomes.jsonl"
        )
        if rows:
            return rows

        bridge = self._load(
            self.root
            / "runtime/closed_trade_outcome_v41_v45/"
              "v4_v36_outcome_bridge.json"
        )
        linked = bridge.get("linked_outcomes", [])
        return linked if isinstance(linked, list) else []

    def _context_sources(self) -> dict[str, Any]:
        return {
            "brain": self._load(
                self.root
                / "runtime/ai_brain_v4/"
                  "latest_ai_brain_report.json"
            ),
            "market": self._load(
                self.root
                / "runtime/market_context_v16_v20/"
                  "latest_market_context_report.json"
            ),
            "guard": self._load(
                self.root
                / "runtime/paper_autonomous_daily_session/"
                  "latest_shadow_guard_decision.json"
            ),
            "execution": self._load(
                self.root
                / "runtime/execution_quality_v26_v30/"
                  "latest_execution_quality_report.json"
            ),
        }

    def v56_closed_trade_classifier(self) -> dict[str, Any]:
        trades = self._trades()
        classified = []

        for trade in trades:
            pnl = self._float(trade.get("realized_pl"))
            ret = self._float(trade.get("realized_return"))
            side = str(trade.get("side", "")).upper()

            if pnl > 0:
                outcome = "WIN"
            elif pnl < 0:
                outcome = "LOSS"
            else:
                outcome = "FLAT"

            magnitude = (
                "LARGE"
                if abs(ret) >= 0.03
                else "MEDIUM"
                if abs(ret) >= 0.01
                else "SMALL"
            )

            classified.append({
                **trade,
                "outcome_class": outcome,
                "return_magnitude": magnitude,
                "position_direction": side or "UNKNOWN",
            })

        return {
            "status": "PASS" if classified else "COLLECTING_DATA",
            "trade_count": len(classified),
            "classified_trades": classified,
            "automatic_strategy_changes": False,
            "broker_write_performed": False,
        }

    def v57_holding_period_analyzer(self) -> dict[str, Any]:
        rows = self.v56_closed_trade_classifier()["classified_trades"]
        analyzed = []

        for trade in rows:
            entry = self._dt(trade.get("entry_time"))
            exit_ = self._dt(trade.get("exit_time"))
            hold_minutes = None

            if entry and exit_:
                hold_minutes = max(
                    0.0,
                    (exit_ - entry).total_seconds() / 60.0,
                )

            if hold_minutes is None:
                bucket = "UNKNOWN"
            elif hold_minutes < 15:
                bucket = "ULTRA_SHORT_LT_15M"
            elif hold_minutes < 60:
                bucket = "INTRADAY_15M_TO_1H"
            elif hold_minutes < 240:
                bucket = "INTRADAY_1H_TO_4H"
            elif hold_minutes < 1440:
                bucket = "SAME_DAY_4H_PLUS"
            else:
                bucket = "MULTI_DAY"

            analyzed.append({
                "trade_id": trade.get("trade_id"),
                "symbol": trade.get("symbol"),
                "hold_minutes": (
                    round(hold_minutes, 3)
                    if hold_minutes is not None else None
                ),
                "holding_bucket": bucket,
                "realized_pl": trade.get("realized_pl"),
                "outcome_class": trade.get("outcome_class"),
            })

        return {
            "status": "PASS" if analyzed else "COLLECTING_DATA",
            "trade_count": len(analyzed),
            "holding_period_records": analyzed,
            "broker_write_performed": False,
        }

    def v58_strategy_signal_attribution(self) -> dict[str, Any]:
        trades = self.v56_closed_trade_classifier()["classified_trades"]
        context = self._context_sources()

        brain = context["brain"]
        decision = brain.get("explainable_final_decision", {})
        top = brain.get("multi_factor_ranking", {}).get("top_candidate") or {}

        attributed = []
        for trade in trades:
            candidate = trade.get("candidate", {}) if isinstance(
                trade.get("candidate"), dict
            ) else {}

            attributed.append({
                "trade_id": trade.get("trade_id"),
                "symbol": trade.get("symbol"),
                "realized_pl": trade.get("realized_pl"),
                "outcome_class": trade.get("outcome_class"),
                "signal_confidence": (
                    candidate.get("confidence")
                    if candidate
                    else top.get("confidence")
                ),
                "signal_consensus": (
                    candidate.get("consensus_score")
                    if candidate
                    else top.get("consensus_score")
                ),
                "reward_risk": (
                    candidate.get("reward_risk")
                    if candidate
                    else top.get("reward_risk")
                ),
                "brain_decision": decision.get("decision"),
                "brain_score": decision.get("brain_score"),
                "strategy_source": (
                    trade.get("strategy")
                    or trade.get("signal_source")
                    or "UNSPECIFIED"
                ),
            })

        return {
            "status": "PASS" if attributed else "COLLECTING_DATA",
            "trade_count": len(attributed),
            "attributed_trades": attributed,
            "automatic_strategy_selection": False,
            "broker_write_performed": False,
        }

    def v59_trade_tagging_context(self) -> dict[str, Any]:
        trades = self.v56_closed_trade_classifier()["classified_trades"]
        holding = {
            row["trade_id"]: row
            for row in self.v57_holding_period_analyzer()[
                "holding_period_records"
            ]
        }
        context = self._context_sources()

        market = context["market"].get("market_context_summary", {})
        guard = context["guard"]
        execution = context["execution"]

        guard_issues = [
            item.get("code")
            for item in guard.get("issues", [])
            if isinstance(item, dict) and item.get("code")
        ]

        tagged = []
        for trade in trades:
            trade_id = trade.get("trade_id")
            tags = [
                f"OUTCOME_{trade.get('outcome_class')}",
                f"MAGNITUDE_{trade.get('return_magnitude')}",
                f"HOLD_{holding.get(trade_id, {}).get('holding_bucket', 'UNKNOWN')}",
            ]

            if market.get("market_entry_context"):
                tags.append(
                    f"MARKET_{market.get('market_entry_context')}"
                )

            timing_state = execution.get(
                "v26_entry_timing_quality", {}
            ).get("timing_state")
            if timing_state:
                tags.append(f"TIMING_{timing_state}")

            for code in guard_issues[:5]:
                tags.append(f"GUARD_{code}")

            tagged.append({
                "trade_id": trade_id,
                "symbol": trade.get("symbol"),
                "tags": tags,
                "market_regime": trade.get("market_regime"),
                "market_entry_context": market.get(
                    "market_entry_context"
                ),
            })

        return {
            "status": "PASS" if tagged else "COLLECTING_DATA",
            "trade_count": len(tagged),
            "tagged_trades": tagged,
            "automatic_filtering": False,
            "broker_write_performed": False,
        }

    def v60_performance_attribution_dataset(self) -> dict[str, Any]:
        classified = self.v56_closed_trade_classifier()
        holding = self.v57_holding_period_analyzer()
        attribution = self.v58_strategy_signal_attribution()
        tagging = self.v59_trade_tagging_context()

        by_symbol = defaultdict(list)
        by_hold = defaultdict(list)
        by_strategy = defaultdict(list)

        for row in classified["classified_trades"]:
            by_symbol[str(row.get("symbol", "UNKNOWN"))].append(
                self._float(row.get("realized_pl"))
            )

        for row in holding["holding_period_records"]:
            by_hold[str(row.get("holding_bucket", "UNKNOWN"))].append(
                self._float(row.get("realized_pl"))
            )

        for row in attribution["attributed_trades"]:
            by_strategy[str(row.get("strategy_source", "UNSPECIFIED"))].append(
                self._float(row.get("realized_pl"))
            )

        def summarize(groups):
            out = []
            for name, pnls in groups.items():
                count = len(pnls)
                wins = sum(1 for x in pnls if x > 0)
                out.append({
                    "name": name,
                    "trade_count": count,
                    "win_rate": (
                        round(wins / count, 6)
                        if count else None
                    ),
                    "total_realized_pl": round(sum(pnls), 8),
                    "average_realized_pl": (
                        round(sum(pnls) / count, 8)
                        if count else None
                    ),
                })
            out.sort(
                key=lambda x: (
                    -(x["average_realized_pl"] or 0.0),
                    -x["trade_count"],
                    x["name"],
                )
            )
            return out

        dataset = {
            "generated_at_utc": self._now(),
            "trade_count": classified["trade_count"],
            "classified_trades": classified["classified_trades"],
            "holding_period_records": holding["holding_period_records"],
            "strategy_attribution_records": attribution["attributed_trades"],
            "tagged_trades": tagging["tagged_trades"],
            "symbol_performance": summarize(by_symbol),
            "holding_period_performance": summarize(by_hold),
            "strategy_performance": summarize(by_strategy),
            "read_only": True,
            "broker_write_performed": False,
        }

        return {
            "status": (
                "PASS"
                if classified["trade_count"] > 0
                else "COLLECTING_DATA"
            ),
            "dataset": dataset,
            "automatic_parameter_changes": False,
            "automatic_strategy_changes": False,
            "order_effect": "NONE",
        }

    def run(self) -> dict[str, Any]:
        result = {
            "stage": "TRADE_CLASSIFICATION_ATTRIBUTION_V56_TO_V60",
            "status": "PASS",
            "mode": "READ_ONLY_ANALYTICS",
            "paper_only": True,
            "etrade_live_write_enabled": False,
            "broker_write_performed": False,
            "v56_closed_trade_classifier": (
                self.v56_closed_trade_classifier()
            ),
            "v57_holding_period_analyzer": (
                self.v57_holding_period_analyzer()
            ),
            "v58_strategy_signal_attribution": (
                self.v58_strategy_signal_attribution()
            ),
            "v59_trade_tagging_context": (
                self.v59_trade_tagging_context()
            ),
            "v60_performance_attribution_dataset": (
                self.v60_performance_attribution_dataset()
            ),
            "generated_at_utc": self._now(),
        }

        self._write(
            self.runtime / "latest_trade_classification_report.json",
            result,
        )
        self._append(
            self.runtime / "trade_classification_ledger.jsonl",
            result,
        )
        self._write(
            self.runtime / "performance_attribution_dataset.json",
            result["v60_performance_attribution_dataset"]["dataset"],
        )

        summary = {
            "generated_at_utc": self._now(),
            "status": "PASS",
            "trade_count": result[
                "v56_closed_trade_classifier"
            ]["trade_count"],
            "classification_status": result[
                "v56_closed_trade_classifier"
            ]["status"],
            "holding_status": result[
                "v57_holding_period_analyzer"
            ]["status"],
            "attribution_status": result[
                "v58_strategy_signal_attribution"
            ]["status"],
            "tagging_status": result[
                "v59_trade_tagging_context"
            ]["status"],
            "dataset_status": result[
                "v60_performance_attribution_dataset"
            ]["status"],
            "broker_write_performed": False,
            "etrade_live_write_enabled": False,
        }

        self._write(
            self.runtime / "daily_trade_classification_summary.json",
            summary,
        )

        return result
