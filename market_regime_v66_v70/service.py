from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class MarketRegimeEnvironmentPack:
    def __init__(self, project_root: Path) -> None:
        self.root = project_root.resolve()
        self.runtime = self.root / "runtime/market_regime_v66_v70"
        self.runtime.mkdir(parents=True, exist_ok=True)

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

    def _context(self) -> dict[str, Any]:
        return {
            "market": self._load(
                self.root
                / "runtime/market_context_v16_v20/"
                  "latest_market_context_report.json"
            ),
            "brain": self._load(
                self.root
                / "runtime/ai_brain_v4/"
                  "latest_ai_brain_report.json"
            ),
            "execution": self._load(
                self.root
                / "runtime/execution_quality_v26_v30/"
                  "latest_execution_quality_report.json"
            ),
            "guard": self._load(
                self.root
                / "runtime/paper_autonomous_daily_session/"
                  "latest_shadow_guard_decision.json"
            ),
        }

    def _trades(self) -> list[dict[str, Any]]:
        rows = self._load_jsonl(
            self.root
            / "runtime/closed_trade_outcome_v41_v45/"
              "closed_trade_outcomes.jsonl"
        )
        return rows

    def v66_market_regime_classifier(self) -> dict[str, Any]:
        ctx = self._context()
        market = ctx["market"]
        brain = ctx["brain"]

        summary = market.get("market_context_summary", {})
        regime_predictor = market.get("v16_market_regime_predictor", {})
        mtf = brain.get("multi_timeframe_ai", {})

        entry_context = summary.get("market_entry_context")
        mtf_direction = mtf.get("direction")
        alignment = self._float(mtf.get("alignment_score"), 0.5)
        volatility = self._float(
            regime_predictor.get("volatility_risk"), 0.5
        )

        if entry_context == "UNFAVORABLE" and volatility >= 0.7:
            regime = "RISK_OFF_HIGH_VOL"
        elif mtf_direction == "BULLISH" and alignment >= 0.75:
            regime = "TRENDING_BULLISH"
        elif mtf_direction == "BEARISH" and alignment >= 0.75:
            regime = "TRENDING_BEARISH"
        elif volatility >= 0.7:
            regime = "HIGH_VOLATILITY"
        elif alignment <= 0.55:
            regime = "SIDEWAYS_OR_UNCERTAIN"
        else:
            regime = "MIXED"

        confidence = min(
            max(abs(alignment - 0.5) * 2.0, 0.0),
            1.0,
        )

        return {
            "status": "PASS",
            "regime": regime,
            "regime_confidence": round(confidence, 6),
            "market_entry_context": entry_context,
            "multi_timeframe_direction": mtf_direction,
            "multi_timeframe_alignment": round(alignment, 6),
            "volatility_risk": round(volatility, 6),
            "enforced": False,
            "order_effect": "NONE",
        }

    def v67_environment_snapshot(self) -> dict[str, Any]:
        ctx = self._context()
        market = ctx["market"]
        brain = ctx["brain"]
        execution = ctx["execution"]

        regime_predictor = market.get("v16_market_regime_predictor", {})
        mtf = brain.get("multi_timeframe_ai", {})
        slippage = execution.get(
            "v27_slippage_liquidity_risk", {}
        )

        snapshot = {
            "captured_at_utc": self._now(),
            "trend_direction": mtf.get("direction"),
            "trend_alignment": mtf.get("alignment_score"),
            "trend_dispersion": mtf.get("dispersion"),
            "volatility_risk": regime_predictor.get("volatility_risk"),
            "liquidity_score": slippage.get("liquidity_score"),
            "estimated_slippage_bps": slippage.get(
                "estimated_slippage_bps"
            ),
            "market_entry_context": market.get(
                "market_context_summary", {}
            ).get("market_entry_context"),
            "market_regime": self.v66_market_regime_classifier()["regime"],
            "read_only": True,
            "broker_write_performed": False,
        }

        useful = any(
            snapshot.get(k) not in (None, "")
            for k in [
                "trend_direction",
                "trend_alignment",
                "volatility_risk",
                "liquidity_score",
            ]
        )

        return {
            "status": "PASS" if useful else "COLLECTING_DATA",
            "snapshot": snapshot,
            "broker_write_performed": False,
        }

    def v68_trade_context_linker(self) -> dict[str, Any]:
        trades = self._trades()
        snapshot = self.v67_environment_snapshot()["snapshot"]
        linked = []

        for trade in trades:
            linked.append({
                **trade,
                "market_context_snapshot": snapshot,
                "market_regime": (
                    trade.get("market_regime")
                    or snapshot.get("market_regime")
                ),
                "environment_linked": True,
            })

        return {
            "status": "PASS" if linked else "COLLECTING_DATA",
            "trade_count": len(linked),
            "linked_trades": linked,
            "existing_trade_ledger_overwritten": False,
            "broker_write_performed": False,
        }

    def v69_regime_performance_dataset(self) -> dict[str, Any]:
        linked = self.v68_trade_context_linker()["linked_trades"]
        groups = defaultdict(list)

        for trade in linked:
            regime = str(
                trade.get("market_regime") or "UNKNOWN"
            )
            groups[regime].append(
                self._float(trade.get("realized_pl"))
            )

        dataset = []
        for regime, pnls in groups.items():
            count = len(pnls)
            wins = sum(1 for x in pnls if x > 0)
            losses = sum(1 for x in pnls if x < 0)

            dataset.append({
                "regime": regime,
                "trade_count": count,
                "wins": wins,
                "losses": losses,
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

        dataset.sort(
            key=lambda x: (
                -(x["average_realized_pl"] or 0.0),
                -x["trade_count"],
                x["regime"],
            )
        )

        return {
            "status": "PASS" if dataset else "COLLECTING_DATA",
            "regime_count": len(dataset),
            "regime_performance": dataset,
            "automatic_regime_weighting": False,
            "automatic_strategy_changes": False,
            "order_effect": "NONE",
        }

    def v70_environment_health_summary(self) -> dict[str, Any]:
        classifier = self.v66_market_regime_classifier()
        snapshot = self.v67_environment_snapshot()
        linker = self.v68_trade_context_linker()
        perf = self.v69_regime_performance_dataset()

        checks = {
            "regime_classifier_available": classifier["status"] == "PASS",
            "environment_snapshot_available": snapshot["status"] in {
                "PASS", "COLLECTING_DATA"
            },
            "trade_linker_not_blocked": linker["status"] in {
                "PASS", "COLLECTING_DATA"
            },
            "regime_dataset_not_blocked": perf["status"] in {
                "PASS", "COLLECTING_DATA"
            },
            "broker_write_off": True,
            "etrade_live_write_off": True,
        }

        passed = sum(1 for value in checks.values() if value)
        score = round(passed / len(checks) * 100.0, 2)

        status = (
            "HEALTHY"
            if score == 100
            else "REVIEW_RECOMMENDED"
        )

        return {
            "status": status,
            "health_score": score,
            "passed_checks": passed,
            "total_checks": len(checks),
            "checks": checks,
            "current_regime": classifier["regime"],
            "regime_trade_count": linker["trade_count"],
            "automatic_strategy_changes": False,
            "broker_write_performed": False,
        }

    def run(self) -> dict[str, Any]:
        result = {
            "stage": "MARKET_REGIME_ENVIRONMENT_V66_TO_V70",
            "status": "PASS",
            "mode": "READ_ONLY_MARKET_CONTEXT",
            "paper_only": True,
            "etrade_live_write_enabled": False,
            "broker_write_performed": False,
            "v66_market_regime_classifier": (
                self.v66_market_regime_classifier()
            ),
            "v67_environment_snapshot": (
                self.v67_environment_snapshot()
            ),
            "v68_trade_context_linker": (
                self.v68_trade_context_linker()
            ),
            "v69_regime_performance_dataset": (
                self.v69_regime_performance_dataset()
            ),
            "v70_environment_health_summary": (
                self.v70_environment_health_summary()
            ),
            "generated_at_utc": self._now(),
        }

        self._write(
            self.runtime / "latest_market_regime_report.json",
            result,
        )
        self._append(
            self.runtime / "market_regime_ledger.jsonl",
            result,
        )
        self._write(
            self.runtime / "latest_environment_snapshot.json",
            result["v67_environment_snapshot"]["snapshot"],
        )
        self._write(
            self.runtime / "regime_performance_dataset.json",
            {
                "generated_at_utc": self._now(),
                "regime_performance": result[
                    "v69_regime_performance_dataset"
                ]["regime_performance"],
                "read_only": True,
                "broker_write_performed": False,
            },
        )

        return result
