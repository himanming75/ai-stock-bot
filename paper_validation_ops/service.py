from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    try:
        for raw in path.read_text(encoding="utf-8-sig").splitlines():
            raw = raw.strip()
            if not raw:
                continue
            try:
                value = json.loads(raw)
                if isinstance(value, dict):
                    rows.append(value)
            except json.JSONDecodeError:
                continue
    except Exception:
        return []
    return rows


def _safe_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_dt(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


@dataclass(frozen=True)
class ValidationTargets:
    minimum_closed_trades: int = 200
    target_closed_trades: int = 300
    minimum_trading_days: int = 10
    minimum_profit_factor: float = 1.20
    require_positive_expectancy: bool = True
    maximum_major_operational_errors: int = 0


class ValidationOperationsService:
    """Read-only operational/validation aggregation."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.runtime = self.root / "runtime"
        self.out = self.runtime / "paper_validation_ops"
        self.out.mkdir(parents=True, exist_ok=True)
        self.targets = ValidationTargets()

    def _closed_rows(self) -> tuple[list[dict[str, Any]], str]:
        candidates = [
            self.runtime / "paper_full_auto_lifecycle/closed_round_trips.jsonl",
            self.runtime / "closed_trade_outcome_v41_v45/closed_trade_outcomes.jsonl",
        ]
        for path in candidates:
            rows = _read_jsonl(path)
            if rows:
                return rows, str(path)
        # preserve preferred source even when empty
        return [], str(candidates[0])

    def _trade_day(self, row: dict[str, Any]) -> str | None:
        for key in ("exit_time", "exit_time_utc", "closed_at_utc", "generated_at_utc"):
            dt = _parse_dt(row.get(key))
            if dt:
                return dt.date().isoformat()
        return None

    def _metrics(self, rows: list[dict[str, Any]]) -> dict[str, Any]:
        pnls: list[float] = []
        for row in rows:
            for key in ("realized_pl", "realized_pnl", "pnl"):
                value = _safe_float(row.get(key))
                if value is not None:
                    pnls.append(value)
                    break

        wins = [x for x in pnls if x > 0]
        losses = [x for x in pnls if x < 0]
        flats = [x for x in pnls if x == 0]

        gross_profit = sum(wins)
        gross_loss = abs(sum(losses))
        profit_factor = (
            gross_profit / gross_loss
            if gross_loss > 0
            else (float("inf") if gross_profit > 0 else None)
        )
        expectancy = sum(pnls) / len(pnls) if pnls else None
        win_rate = len(wins) / len(pnls) if pnls else None

        running = 0.0
        peak = 0.0
        max_drawdown = 0.0
        current_loss_streak = 0
        max_loss_streak = 0
        equity_curve = []
        for pnl in pnls:
            running += pnl
            peak = max(peak, running)
            max_drawdown = max(max_drawdown, peak - running)
            equity_curve.append(round(running, 8))
            if pnl < 0:
                current_loss_streak += 1
                max_loss_streak = max(max_loss_streak, current_loss_streak)
            else:
                current_loss_streak = 0

        return {
            "trade_count_with_pnl": len(pnls),
            "wins": len(wins),
            "losses": len(losses),
            "flats": len(flats),
            "win_rate": round(win_rate, 6) if win_rate is not None else None,
            "total_realized_pl": round(sum(pnls), 8),
            "average_win": round(sum(wins) / len(wins), 8) if wins else None,
            "average_loss": round(sum(losses) / len(losses), 8) if losses else None,
            "expectancy": round(expectancy, 8) if expectancy is not None else None,
            "profit_factor": (
                round(profit_factor, 6)
                if profit_factor is not None and profit_factor != float("inf")
                else ("INF" if profit_factor == float("inf") else None)
            ),
            "max_drawdown_dollars": round(max_drawdown, 8),
            "max_consecutive_losses": max_loss_streak,
            "equity_curve": equity_curve[-100:],
        }

    def _symbol_breakdown(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        buckets: dict[str, list[float]] = {}
        for row in rows:
            symbol = str(row.get("symbol", "")).upper()
            if not symbol:
                continue
            pnl = None
            for key in ("realized_pl", "realized_pnl", "pnl"):
                pnl = _safe_float(row.get(key))
                if pnl is not None:
                    break
            if pnl is None:
                continue
            buckets.setdefault(symbol, []).append(pnl)
        result = []
        for symbol, vals in buckets.items():
            result.append({
                "symbol": symbol,
                "trades": len(vals),
                "realized_pl": round(sum(vals), 8),
                "win_rate": round(sum(1 for x in vals if x > 0) / len(vals), 6),
            })
        return sorted(result, key=lambda x: (-x["trades"], x["symbol"]))

    def _daily_breakdown(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        buckets: dict[str, list[float]] = {}
        counts: dict[str, int] = {}
        for row in rows:
            day = self._trade_day(row)
            if not day:
                continue
            counts[day] = counts.get(day, 0) + 1
            pnl = None
            for key in ("realized_pl", "realized_pnl", "pnl"):
                pnl = _safe_float(row.get(key))
                if pnl is not None:
                    break
            if pnl is not None:
                buckets.setdefault(day, []).append(pnl)
        out = []
        for day in sorted(counts):
            vals = buckets.get(day, [])
            out.append({
                "date": day,
                "closed_trades": counts[day],
                "realized_pl": round(sum(vals), 8) if vals else None,
            })
        return out

    def _task_info(self, task_name: str) -> dict[str, Any]:
        # Read-only PowerShell query only.
        ps = (
            f"$t=Get-ScheduledTask -TaskName '{task_name}' -ErrorAction SilentlyContinue;"
            f"$i=Get-ScheduledTaskInfo -TaskName '{task_name}' -ErrorAction SilentlyContinue;"
            "if($t){[pscustomobject]@{TaskName=$t.TaskName;State=[string]$t.State;"
            "LastRunTime=[string]$i.LastRunTime;LastTaskResult=$i.LastTaskResult;"
            "NextRunTime=[string]$i.NextRunTime}|ConvertTo-Json -Compress}"
        )
        try:
            cp = subprocess.run(
                ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", ps],
                capture_output=True, text=True, timeout=8, errors="replace"
            )
            if cp.returncode == 0 and cp.stdout.strip():
                return json.loads(cp.stdout.strip())
        except Exception:
            pass
        return {"TaskName": task_name, "State": "UNKNOWN"}

    def _operational(self) -> dict[str, Any]:
        latest = _read_json(
            self.runtime / "paper_autonomous_daily_session/latest_status.json"
        )
        lifecycle = _read_json(
            self.runtime / "paper_full_auto_lifecycle/latest_lifecycle_status.json"
        )
        health = _read_json(
            self.runtime / "operational_reliability_v71_v75/latest_operational_reliability_report.json"
        )
        return {
            "daily_session": latest,
            "lifecycle": lifecycle,
            "operational_health": health.get("v75_operational_health_report", health),
            "paper_task": self._task_info("AIStockBot-PaperAutonomousDailySession"),
            "validation_gate_task": self._task_info("AIStockBot-PaperRoundtripValidationGate"),
        }

    def build(self) -> dict[str, Any]:
        rows, source = self._closed_rows()
        days = sorted({d for r in rows if (d := self._trade_day(r))})
        metrics = self._metrics(rows)
        count = len(rows)

        minimum_progress = min(1.0, count / self.targets.minimum_closed_trades)
        target_progress = min(1.0, count / self.targets.target_closed_trades)
        day_progress = min(1.0, len(days) / self.targets.minimum_trading_days)

        pf = metrics["profit_factor"]
        pf_numeric = float("inf") if pf == "INF" else _safe_float(pf)
        expectancy = metrics["expectancy"]

        checks = {
            "minimum_200_closed_trades": count >= self.targets.minimum_closed_trades,
            "target_300_closed_trades": count >= self.targets.target_closed_trades,
            "minimum_10_trading_days": len(days) >= self.targets.minimum_trading_days,
            "profit_factor_at_least_1_20": (
                pf_numeric is not None
                and pf_numeric >= self.targets.minimum_profit_factor
            ),
            "expectancy_positive": (
                expectancy is not None and expectancy > 0
            ),
        }

        minimum_gate = (
            checks["minimum_200_closed_trades"]
            and checks["minimum_10_trading_days"]
            and checks["profit_factor_at_least_1_20"]
            and checks["expectancy_positive"]
        )

        if minimum_gate:
            gate_status = "PAPER_VALIDATION_MINIMUM_GATE_PASSED"
        elif count >= self.targets.minimum_closed_trades and len(days) >= self.targets.minimum_trading_days:
            gate_status = "REVIEW_REQUIRED"
        else:
            gate_status = "COLLECTING_DATA"

        report = {
            "stage": "PAPER_VALIDATION_OPERATIONS_DASHBOARD_V1",
            "status": "PASS",
            "mode": "READ_ONLY",
            "broker_write_performed": False,
            "trading_configuration_changed": False,
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "targets": {
                "minimum_closed_trades": self.targets.minimum_closed_trades,
                "target_closed_trades": self.targets.target_closed_trades,
                "minimum_trading_days": self.targets.minimum_trading_days,
                "minimum_profit_factor": self.targets.minimum_profit_factor,
            },
            "progress": {
                "closed_trades": count,
                "trading_days": len(days),
                "closed_trade_minimum_progress_pct": round(minimum_progress * 100, 2),
                "closed_trade_target_progress_pct": round(target_progress * 100, 2),
                "trading_day_progress_pct": round(day_progress * 100, 2),
                "gate_status": gate_status,
            },
            "checks": checks,
            "metrics": metrics,
            "daily_breakdown": self._daily_breakdown(rows),
            "symbol_breakdown": self._symbol_breakdown(rows),
            "closed_trade_source": source,
            "operational": self._operational(),
        }

        (self.out / "latest_validation_operations_report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True, default=str),
            encoding="utf-8",
        )
        return report
