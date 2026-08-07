from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class PerformanceIntelligencePack:
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
    def _load_jsonl(path: Path, limit: int = 10000) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        out = []
        try:
            for line in path.read_text(encoding="utf-8-sig").splitlines()[-limit:]:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    if isinstance(obj, dict):
                        out.append(obj)
                except Exception:
                    pass
        except Exception:
            pass
        return out

    @staticmethod
    def _write(path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8")

    @staticmethod
    def _append(path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, sort_keys=True) + "\n")

    def _v4(self) -> dict[str, Any]:
        return self._load(
            self.root / "runtime/closed_trade_calibration_v4/latest_calibration_report.json"
        )

    def _v16_20(self) -> dict[str, Any]:
        return self._load(
            self.root / "runtime/market_context_v16_v20/latest_market_context_report.json"
        )

    def _closed_trades(self) -> list[dict[str, Any]]:
        linked = self._v4().get("linked_outcomes", [])
        return linked if isinstance(linked, list) else []

    @staticmethod
    def _summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
        pnls = []
        for row in rows:
            try:
                pnls.append(float(row.get("realized_pl", 0.0) or 0.0))
            except Exception:
                pnls.append(0.0)

        wins = [v for v in pnls if v > 0]
        losses = [v for v in pnls if v < 0]
        count = len(pnls)
        gross_profit = sum(wins)
        gross_loss = abs(sum(losses))

        return {
            "sample_count": count,
            "wins": len(wins),
            "losses": len(losses),
            "flats": sum(1 for v in pnls if v == 0),
            "win_rate": round(len(wins)/count, 6) if count else None,
            "total_realized_pl": round(sum(pnls), 6),
            "average_realized_pl": round(sum(pnls)/count, 6) if count else None,
            "profit_factor": (
                round(gross_profit/gross_loss, 6) if gross_loss > 0 else None
            ),
        }

    def symbol_performance_memory(self) -> dict[str, Any]:
        groups: dict[str, list[dict[str, Any]]] = {}
        for row in self._closed_trades():
            symbol = str(row.get("symbol", "")).upper()
            if symbol:
                groups.setdefault(symbol, []).append(row)

        ranked = []
        for symbol, rows in groups.items():
            stats = self._summary(rows)
            ranked.append({"symbol": symbol, **stats})

        ranked.sort(
            key=lambda x: (
                -(x["average_realized_pl"] or 0.0),
                -x["sample_count"],
                x["symbol"],
            )
        )

        return {
            "status": "PASS" if ranked else "COLLECTING_DATA",
            "ranked_symbols": ranked,
            "best_symbol": ranked[0]["symbol"] if ranked else None,
            "automatic_symbol_exclusion": False,
        }

    def time_of_day_performance(self) -> dict[str, Any]:
        buckets = {
            "PREMARKET": [],
            "OPEN_0930_1030": [],
            "MIDDAY_1030_1400": [],
            "AFTERNOON_1400_1530": [],
            "CLOSE_1530_1600": [],
            "UNKNOWN": [],
        }

        for row in self._closed_trades():
            ts = row.get("entry_time") or row.get("candidate", {}).get("observed_at_utc")
            if not ts:
                buckets["UNKNOWN"].append(row)
                continue
            try:
                dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
                hour = dt.hour
                minute = dt.minute
                hm = hour * 60 + minute
                # This is a generic bucketing layer; exact exchange-local conversion
                # should be supplied later when normalized entry times are available.
                if hm < 9*60+30:
                    key = "PREMARKET"
                elif hm < 10*60+30:
                    key = "OPEN_0930_1030"
                elif hm < 14*60:
                    key = "MIDDAY_1030_1400"
                elif hm < 15*60+30:
                    key = "AFTERNOON_1400_1530"
                elif hm < 16*60:
                    key = "CLOSE_1530_1600"
                else:
                    key = "UNKNOWN"
                buckets[key].append(row)
            except Exception:
                buckets["UNKNOWN"].append(row)

        return {
            "status": "PASS" if any(buckets[k] for k in buckets if k != "UNKNOWN")
                      else "COLLECTING_DATA",
            "buckets": {k: self._summary(v) for k, v in buckets.items()},
            "automatic_time_filtering": False,
            "note": "Exact exchange-local normalization should use normalized closed-trade timestamps when available.",
        }

    def day_of_week_performance(self) -> dict[str, Any]:
        names = ["MONDAY","TUESDAY","WEDNESDAY","THURSDAY","FRIDAY","SATURDAY","SUNDAY"]
        groups = {name: [] for name in names}
        unknown = []

        for row in self._closed_trades():
            ts = row.get("entry_time") or row.get("exit_time")
            if not ts:
                unknown.append(row)
                continue
            try:
                dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
                groups[names[dt.weekday()]].append(row)
            except Exception:
                unknown.append(row)

        data = {k: self._summary(v) for k, v in groups.items()}
        data["UNKNOWN"] = self._summary(unknown)
        useful = sum(v["sample_count"] for k, v in data.items() if k != "UNKNOWN")

        return {
            "status": "PASS" if useful else "COLLECTING_DATA",
            "days": data,
            "automatic_day_filtering": False,
        }

    def regime_conditioned_performance(self) -> dict[str, Any]:
        # Outcome-regime linking is only trusted when each outcome itself carries
        # a regime label. We do not retroactively assign today's regime to old trades.
        groups: dict[str, list[dict[str, Any]]] = {}
        unlinked = 0
        for row in self._closed_trades():
            regime = row.get("market_regime") or row.get("context", {}).get("market_regime")
            if not regime:
                unlinked += 1
                continue
            groups.setdefault(str(regime), []).append(row)

        matrix = {regime: self._summary(rows) for regime, rows in sorted(groups.items())}
        return {
            "status": "PASS" if matrix else "COLLECTING_DATA",
            "regimes": matrix,
            "outcome_regime_linked_count": sum(v["sample_count"] for v in matrix.values()),
            "unlinked_outcome_count": unlinked,
            "automatic_regime_weight_changes": False,
        }

    def counterfactual_shadow_review(self) -> dict[str, Any]:
        allow = []
        block = []
        unknown = []

        for row in self._closed_trades():
            action = row.get("candidate", {}).get("guard_action")
            if action == "SHADOW_ALLOW":
                allow.append(row)
            elif action == "SHADOW_BLOCK":
                block.append(row)
            else:
                unknown.append(row)

        allow_stats = self._summary(allow)
        block_stats = self._summary(block)

        if allow_stats["sample_count"] >= 10 and block_stats["sample_count"] >= 10:
            status = "REVIEW_READY"
        else:
            status = "COLLECTING_DATA"

        interpretation = "INSUFFICIENT_DATA"
        if status == "REVIEW_READY":
            a = allow_stats["average_realized_pl"] or 0.0
            b = block_stats["average_realized_pl"] or 0.0
            if a > b:
                interpretation = "GUARD_ALLOW_OUTPERFORMS_BLOCK"
            elif b > a:
                interpretation = "BLOCKED_SET_OUTPERFORMS_REVIEW_GUARD_STRICTNESS"
            else:
                interpretation = "NO_CLEAR_DIFFERENCE"

        return {
            "status": status,
            "shadow_allow": allow_stats,
            "shadow_block": block_stats,
            "unknown": self._summary(unknown),
            "interpretation": interpretation,
            "guard_enforcement_changed": False,
            "order_effect": "NONE",
        }

    def run(self) -> dict[str, Any]:
        runtime = self.root / "runtime/performance_intelligence_v21_v25"

        result = {
            "stage": "PERFORMANCE_INTELLIGENCE_V21_TO_V25",
            "status": "PASS",
            "mode": "READ_ONLY_SHADOW",
            "paper_only": True,
            "etrade_live_write_enabled": False,
            "broker_write_performed": False,
            "v21_symbol_performance_memory": self.symbol_performance_memory(),
            "v22_time_of_day_performance": self.time_of_day_performance(),
            "v23_day_of_week_performance": self.day_of_week_performance(),
            "v24_regime_conditioned_performance": self.regime_conditioned_performance(),
            "v25_counterfactual_shadow_review": self.counterfactual_shadow_review(),
            "generated_at_utc": self._now(),
        }

        self._write(runtime / "latest_performance_intelligence_report.json", result)
        self._append(runtime / "performance_intelligence_ledger.jsonl", result)

        summary = {
            "generated_at_utc": self._now(),
            "status": "PASS",
            "symbol_memory_status": result["v21_symbol_performance_memory"]["status"],
            "time_of_day_status": result["v22_time_of_day_performance"]["status"],
            "day_of_week_status": result["v23_day_of_week_performance"]["status"],
            "regime_matrix_status": result["v24_regime_conditioned_performance"]["status"],
            "counterfactual_status": result["v25_counterfactual_shadow_review"]["status"],
            "broker_write_performed": False,
            "etrade_live_write_enabled": False,
        }
        self._write(runtime / "daily_performance_intelligence_summary.json", summary)
        return result
