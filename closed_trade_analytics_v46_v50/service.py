from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from datetime import datetime, timezone


class ClosedTradeAnalyticsReadiness:
    def __init__(self, project_root: Path) -> None:
        self.root = project_root.resolve()
        self.runtime = self.root / "runtime/closed_trade_analytics_v46_v50"
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

    def _outcomes(self) -> list[dict[str, Any]]:
        primary = self._load_jsonl(
            self.root
            / "runtime/closed_trade_outcome_v41_v45/"
              "closed_trade_outcomes.jsonl"
        )
        if primary:
            return primary

        bridge = self._load(
            self.root
            / "runtime/closed_trade_outcome_v41_v45/"
              "v4_v36_outcome_bridge.json"
        )
        rows = bridge.get("linked_outcomes", [])
        return rows if isinstance(rows, list) else []

    def v46_closed_trade_watch(self) -> dict[str, Any]:
        rows = self._outcomes()
        latest = rows[-1] if rows else None

        return {
            "status": "PASS" if rows else "COLLECTING_DATA",
            "closed_trade_count": len(rows),
            "latest_closed_trade": latest,
            "source": "V41_V45_READ_ONLY_OUTCOME_DATA",
            "broker_write_performed": False,
            "order_effect": "NONE",
        }

    def v47_core_performance_metrics(self) -> dict[str, Any]:
        rows = self._outcomes()
        pnls = [self._float(r.get("realized_pl")) for r in rows]
        wins = [x for x in pnls if x > 0]
        losses = [x for x in pnls if x < 0]
        flats = [x for x in pnls if x == 0]

        gross_profit = sum(wins)
        gross_loss = abs(sum(losses))
        count = len(pnls)

        average_win = sum(wins) / len(wins) if wins else None
        average_loss = sum(losses) / len(losses) if losses else None
        win_rate = len(wins) / count if count else None
        expectancy = sum(pnls) / count if count else None
        profit_factor = (
            gross_profit / gross_loss if gross_loss > 0 else None
        )

        return {
            "status": "PASS" if count else "COLLECTING_DATA",
            "trade_count": count,
            "wins": len(wins),
            "losses": len(losses),
            "flats": len(flats),
            "win_rate": round(win_rate, 6) if win_rate is not None else None,
            "average_win": round(average_win, 8) if average_win is not None else None,
            "average_loss": round(average_loss, 8) if average_loss is not None else None,
            "expectancy": round(expectancy, 8) if expectancy is not None else None,
            "profit_factor": round(profit_factor, 6) if profit_factor is not None else None,
            "total_realized_pl": round(sum(pnls), 8),
            "broker_write_performed": False,
        }

    def v48_drawdown_loss_streak(self) -> dict[str, Any]:
        rows = self._outcomes()
        equity = 0.0
        peak = 0.0
        max_drawdown = 0.0
        current_loss_streak = 0
        max_loss_streak = 0
        curve = []

        for idx, row in enumerate(rows, start=1):
            pnl = self._float(row.get("realized_pl"))
            equity += pnl
            peak = max(peak, equity)
            drawdown = equity - peak
            max_drawdown = min(max_drawdown, drawdown)

            if pnl < 0:
                current_loss_streak += 1
                max_loss_streak = max(
                    max_loss_streak,
                    current_loss_streak,
                )
            else:
                current_loss_streak = 0

            curve.append({
                "trade_index": idx,
                "trade_id": row.get("trade_id"),
                "equity_delta": round(equity, 8),
                "drawdown": round(drawdown, 8),
            })

        return {
            "status": "PASS" if rows else "COLLECTING_DATA",
            "trade_count": len(rows),
            "max_drawdown": round(max_drawdown, 8),
            "max_consecutive_losses": max_loss_streak,
            "ending_equity_delta": round(equity, 8),
            "equity_curve": curve,
            "broker_write_performed": False,
        }

    def v49_symbol_regime_breakdown(self) -> dict[str, Any]:
        rows = self._outcomes()
        by_symbol: dict[str, list[float]] = {}
        by_regime: dict[str, list[float]] = {}

        for row in rows:
            pnl = self._float(row.get("realized_pl"))
            symbol = str(row.get("symbol", "")).upper()
            if symbol:
                by_symbol.setdefault(symbol, []).append(pnl)

            regime = (
                row.get("market_regime")
                or row.get("context", {}).get("market_regime")
            )
            if regime:
                by_regime.setdefault(str(regime), []).append(pnl)

        def summarize(groups):
            result = []
            for name, pnls in groups.items():
                count = len(pnls)
                wins = sum(1 for x in pnls if x > 0)
                result.append({
                    "name": name,
                    "trade_count": count,
                    "win_rate": round(wins / count, 6) if count else None,
                    "total_realized_pl": round(sum(pnls), 8),
                    "average_realized_pl": round(sum(pnls) / count, 8) if count else None,
                })
            result.sort(
                key=lambda x: (
                    -(x["average_realized_pl"] or 0.0),
                    -x["trade_count"],
                    x["name"],
                )
            )
            return result

        symbols = summarize(by_symbol)
        regimes = summarize(by_regime)

        return {
            "status": "PASS" if rows else "COLLECTING_DATA",
            "symbol_breakdown": symbols,
            "regime_breakdown": regimes,
            "regime_linked_trade_count": sum(
                item["trade_count"] for item in regimes
            ),
            "automatic_symbol_filtering": False,
            "automatic_regime_weighting": False,
            "order_effect": "NONE",
        }

    def v50_readiness_gate(self) -> dict[str, Any]:
        perf = self.v47_core_performance_metrics()
        dd = self.v48_drawdown_loss_streak()
        split = self.v49_symbol_regime_breakdown()

        trade_count = perf["trade_count"]
        win_rate = perf["win_rate"]
        profit_factor = perf["profit_factor"]
        expectancy = perf["expectancy"]

        checks = {
            "closed_trades_at_least_20": trade_count >= 20,
            "closed_trades_at_least_50_for_strong_review": trade_count >= 50,
            "win_rate_at_least_0_50": (
                win_rate is not None and win_rate >= 0.50
            ),
            "profit_factor_at_least_1_20": (
                profit_factor is not None and profit_factor >= 1.20
            ),
            "expectancy_positive": (
                expectancy is not None and expectancy > 0
            ),
            "max_loss_streak_at_most_3": (
                dd["max_consecutive_losses"] <= 3
                if trade_count else False
            ),
            "symbol_breakdown_available": (
                len(split["symbol_breakdown"]) > 0
            ),
            "broker_write_off": True,
            "etrade_live_write_off": True,
        }

        passed = sum(1 for value in checks.values() if value)
        blockers = [name for name, value in checks.items() if not value]

        if trade_count < 20:
            status = "INSUFFICIENT_SAMPLE"
        elif passed == len(checks):
            status = "READY_FOR_HUMAN_LIVE_REVIEW"
        else:
            status = "PERFORMANCE_REVIEW_REQUIRED"

        return {
            "status": status,
            "passed_checks": passed,
            "total_checks": len(checks),
            "checks": checks,
            "blockers": blockers,
            "live_submission_enabled": False,
            "deployment_effect": "ADVISORY_ONLY",
            "broker_write_performed": False,
        }

    def run(self) -> dict[str, Any]:
        result = {
            "stage": "CLOSED_TRADE_ANALYTICS_READINESS_V46_TO_V50",
            "status": "PASS",
            "mode": "READ_ONLY_ANALYTICS",
            "paper_only": True,
            "etrade_live_write_enabled": False,
            "broker_write_performed": False,
            "v46_closed_trade_watch": self.v46_closed_trade_watch(),
            "v47_core_performance_metrics": (
                self.v47_core_performance_metrics()
            ),
            "v48_drawdown_loss_streak": (
                self.v48_drawdown_loss_streak()
            ),
            "v49_symbol_regime_breakdown": (
                self.v49_symbol_regime_breakdown()
            ),
            "v50_readiness_gate": self.v50_readiness_gate(),
            "generated_at_utc": self._now(),
        }

        self._write(
            self.runtime / "latest_closed_trade_analytics_report.json",
            result,
        )
        self._append(
            self.runtime / "closed_trade_analytics_ledger.jsonl",
            result,
        )

        summary = {
            "generated_at_utc": self._now(),
            "status": "PASS",
            "closed_trade_count": result[
                "v47_core_performance_metrics"
            ]["trade_count"],
            "win_rate": result[
                "v47_core_performance_metrics"
            ]["win_rate"],
            "profit_factor": result[
                "v47_core_performance_metrics"
            ]["profit_factor"],
            "expectancy": result[
                "v47_core_performance_metrics"
            ]["expectancy"],
            "max_drawdown": result[
                "v48_drawdown_loss_streak"
            ]["max_drawdown"],
            "readiness_status": result[
                "v50_readiness_gate"
            ]["status"],
            "broker_write_performed": False,
            "etrade_live_write_enabled": False,
        }

        self._write(
            self.runtime / "daily_closed_trade_analytics_summary.json",
            summary,
        )

        return result
