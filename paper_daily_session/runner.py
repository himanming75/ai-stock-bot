from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from paper_daily_session.shadow_integration import DailySessionShadowGuard
from paper_autonomous_execution.lifecycle import PaperPositionLifecycle


PAPER_URL = "https://paper-api.alpaca.markets"
STATE_REL = Path("runtime/paper_autonomous_daily_session/latest_status.json")
LEDGER_REL = Path("runtime/paper_autonomous_daily_session/session_ledger.jsonl")
LOCK_REL = Path("runtime/paper_autonomous_daily_session/session.lock")
STOP_REL = Path("runtime/paper_autonomous_daily_session/STOP")
LOG_REL = Path("runtime/paper_autonomous_daily_session/session.log")
CLOSED_TRADES_REL = Path("runtime/paper_full_auto_lifecycle/closed_round_trips.jsonl")
VALIDATION_BASELINE_REL = Path("runtime/paper_validation_2week_300/baseline.json")
ORDER_SCRIPT = "RUN_ONE_PAPER_VALIDATION_ORDER_V14001_TO_V15000.ps1"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(
            json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n"
        )


def env_truthy(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {
        "1", "true", "yes", "on", "enabled"
    }


class PaperDailySessionRunner:
    def __init__(
        self,
        root: Path,
        poll_seconds: int = 60,
        maximum_daily_orders: int = 1,
        maximum_order_notional: float = 100.0,
        market_close_buffer_minutes: int = 15,
        dry_run: bool = False,
    ) -> None:
        self.root = root.resolve()
        self.poll_seconds = max(15, int(poll_seconds))
        self.maximum_daily_orders = int(maximum_daily_orders)
        self.maximum_order_notional = float(maximum_order_notional)
        self.market_close_buffer_minutes = int(market_close_buffer_minutes)
        self.dry_run = bool(dry_run)
        self.state_path = self.root / STATE_REL
        self.ledger_path = self.root / LEDGER_REL
        self.lock_path = self.root / LOCK_REL
        self.stop_path = self.root / STOP_REL
        self.log_path = self.root / LOG_REL
        self.lifecycle = PaperPositionLifecycle(self.root)

    def _status(self, stage: str, **extra: Any) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "stage": stage,
            "updated_at_utc": utc_now(),
            "paper_broker": "ALPACA",
            "paper_base_url": PAPER_URL,
            "paper_only": True,
            "live_broker": "ETRADE",
            "etrade_live_write_enabled": False,
            "live_orders_submitted": 0,
            "maximum_daily_orders": self.maximum_daily_orders,
            "maximum_order_notional": self.maximum_order_notional,
            "market_close_buffer_minutes": self.market_close_buffer_minutes,
            "poll_seconds": self.poll_seconds,
            "dry_run": self.dry_run,
        }
        payload.update(extra)
        write_json(self.state_path, payload)
        append_jsonl(self.ledger_path, payload)
        return payload

    def _acquire_lock(self) -> None:
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        if self.lock_path.exists():
            raise RuntimeError("DAILY_SESSION_ALREADY_RUNNING")
        self.lock_path.write_text(
            json.dumps({"pid": os.getpid(), "created_at_utc": utc_now()}),
            encoding="utf-8",
        )

    def _release_lock(self) -> None:
        self.lock_path.unlink(missing_ok=True)

    def _validate_environment(self) -> None:
        missing = [
            name for name in ("APCA_API_KEY_ID", "APCA_API_SECRET_KEY")
            if not os.getenv(name, "").strip()
        ]
        if missing:
            raise RuntimeError(
                "PAPER_CREDENTIALS_MISSING:" + ",".join(missing)
            )

        live_names = (
            "LIVE_TRADING_ENABLED",
            "ETRADE_LIVE_WRITE_ENABLED",
            "ETRADE_LIVE_SUBMISSION_ENABLED",
        )
        enabled = [name for name in live_names if env_truthy(name)]
        if enabled:
            raise RuntimeError(
                "LIVE_WRITE_MUST_REMAIN_OFF:" + ",".join(enabled)
            )

        script = self.root / ORDER_SCRIPT
        if not script.exists():
            raise RuntimeError(f"ORDER_SCRIPT_MISSING:{script}")


        if not 1 <= self.maximum_daily_orders <= 50:
            raise RuntimeError("MAXIMUM_DAILY_ORDERS_INVALID")
        if not 0 < self.maximum_order_notional <= 100:
            raise RuntimeError("MAXIMUM_ORDER_NOTIONAL_INVALID")

    def _validation_target_closed_trades(self) -> int:
        try:
            return max(0, int(os.getenv("PAPER_VALIDATION_TARGET_CLOSED_TRADES", "0")))
        except (TypeError, ValueError):
            return 0

    def _closed_trade_line_count(self) -> int:
        path = self.root / CLOSED_TRADES_REL
        if not path.exists():
            return 0
        with path.open("r", encoding="utf-8-sig", errors="replace") as handle:
            return sum(1 for line in handle if line.strip())

    def _validation_baseline_closed_count(self) -> int:
        raw = os.getenv("PAPER_VALIDATION_BASELINE_PATH", "").strip()
        path = Path(raw) if raw else (self.root / VALIDATION_BASELINE_REL)
        if not path.is_absolute():
            path = self.root / path
        if not path.exists():
            raise RuntimeError("PAPER_VALIDATION_BASELINE_MISSING")
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
        return max(0, int(payload.get("baseline_closed_trade_count", 0)))

    def _validation_closed_trade_count(self) -> int:
        if self._validation_target_closed_trades() <= 0:
            return 0
        return max(0, self._closed_trade_line_count() - self._validation_baseline_closed_count())

    def _client(self):
        try:
            from alpaca.trading.client import TradingClient
        except ImportError as exc:
            raise RuntimeError("ALPACA_PY_NOT_INSTALLED") from exc
        return TradingClient(
            os.environ["APCA_API_KEY_ID"],
            os.environ["APCA_API_SECRET_KEY"],
            paper=True,
        )

    def _today_orders(self, client) -> list[Any]:
        from alpaca.trading.enums import QueryOrderStatus
        from alpaca.trading.requests import GetOrdersRequest

        orders = client.get_orders(
            filter=GetOrdersRequest(
                status=QueryOrderStatus.ALL,
                limit=500,
            )
        )
        now_et = datetime.now(timezone.utc).astimezone()
        today = now_et.date()
        result = []
        for order in orders:
            created = getattr(order, "created_at", None)
            if created is None:
                continue
            try:
                if created.astimezone().date() == today:
                    result.append(order)
            except Exception:
                continue
        return result

    def _today_buy_orders(self, client) -> list[Any]:
        return [
            order for order in self._today_orders(client)
            if "buy" in str(getattr(order, "side", "")).lower()
        ]

    def _clock_data(self, client) -> dict[str, Any]:
        clock = client.get_clock()
        now = getattr(clock, "timestamp", None)
        next_close = getattr(clock, "next_close", None)
        minutes_to_close = 999999
        if now is not None and next_close is not None:
            minutes_to_close = int(
                max(0, (next_close - now).total_seconds() // 60)
            )
        return {
            "market_open": bool(getattr(clock, "is_open", False)),
            "clock_timestamp": str(now or ""),
            "next_open": str(getattr(clock, "next_open", "")),
            "next_close": str(next_close or ""),
            "minutes_to_close": minutes_to_close,
        }

    def _run_order_cycle(self) -> dict[str, Any]:
        script = self.root / ORDER_SCRIPT
        if self.dry_run:
            return {
                "exit_code": 0,
                "stdout": "DRY_RUN_NO_ORDER",
                "stderr": "",
            }
        process = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(script),
            ],
            cwd=self.root,
            capture_output=True,
            text=True,
            errors="replace",
        )
        return {
            "exit_code": process.returncode,
            "stdout": (process.stdout or "")[-12000:],
            "stderr": (process.stderr or "")[-12000:],
        }


    def _run_regime_shadow_cycle(self) -> dict[str, Any]:
        script = self.root / "tools" / "run_regime_aware_shadow_v2_7.py"
        audit_dir = self.root / "runtime" / "regime_aware_buy_shadow_v2_8_1"
        audit_dir.mkdir(parents=True, exist_ok=True)
        ledger = audit_dir / "hook_ledger.jsonl"

        result: dict[str, Any] = {
            "stage": "V2.8.1_REGIME_SHADOW_HOOK",
            "timestamp_utc": utc_now(),
            "mode": "READ_ONLY_SHADOW",
            "script": str(script),
            "attempted": False,
            "exit_code": None,
            "status": None,
            "stdout_tail": "",
            "stderr_tail": "",
            "broker_write_performed": False,
            "paper_order_submission_performed": False,
            "live_order_submission_performed": False,
            "primary_paper_flow_blocked": False,
        }

        try:
            if not script.exists():
                result["status"] = "SHADOW_SCRIPT_MISSING"
            else:
                result["attempted"] = True
                process = subprocess.run(
                    [
                        sys.executable,
                        str(script),
                        "--root",
                        str(self.root),
                    ],
                    cwd=self.root,
                    capture_output=True,
                    text=True,
                    errors="replace",
                    timeout=45,
                    check=False,
                )
                result["exit_code"] = process.returncode
                result["stdout_tail"] = (process.stdout or "")[-4000:]
                result["stderr_tail"] = (process.stderr or "")[-4000:]
                result["status"] = (
                    "PASS"
                    if process.returncode == 0
                    else "SHADOW_NONZERO_ISOLATED"
                )
        except subprocess.TimeoutExpired as exc:
            result["status"] = "SHADOW_TIMEOUT_ISOLATED"
            result["stderr_tail"] = str(exc)
        except Exception as exc:
            result["status"] = "SHADOW_EXCEPTION_ISOLATED"
            result["stderr_tail"] = str(exc)

        append_jsonl(ledger, result)
        return result

    def run(self) -> dict[str, Any]:
        self._acquire_lock()
        try:
            self._validate_environment()
            self.stop_path.unlink(missing_ok=True)
            client = self._client()
            account = client.get_account()

            self._status(
                "SESSION_STARTING",
                account_status=str(getattr(account, "status", "")),
                trading_blocked=bool(
                    getattr(account, "trading_blocked", False)
                ),
            )

            while True:
                if self.stop_path.exists():
                    return self._status(
                        "SESSION_STOPPED_BY_OPERATOR",
                        status="PASS",
                    )


                # V2.8.2: read-only regime-aware shadow hook.
                # Failure is intentionally isolated from primary Paper flow.
                regime_shadow_v2_8_1 = self._run_regime_shadow_cycle()

                clock = self._clock_data(client)
                today_orders = self._today_orders(client)
                today_buy_orders = self._today_buy_orders(client)
                order_count = len(today_orders)
                entry_order_count = len(today_buy_orders)

                if not clock["market_open"]:
                    return self._status(
                        "SESSION_MARKET_CLOSED",
                        status="PASS",
                        clock=clock,
                        today_order_count=order_count,
                    )

                if self.dry_run:
                    lifecycle = {
                        "status": "DRY_RUN_NO_POSITION_LIFECYCLE",
                        "paper_only": True,
                        "live_order_submitted": False,
                        "actions": [],
                        "action_count": 0,
                    }
                else:
                    lifecycle = self.lifecycle.evaluate_and_exit(
                        client,
                        minutes_to_close=clock["minutes_to_close"],
                    )

                validation_target = self._validation_target_closed_trades()
                validation_closed = self._validation_closed_trade_count()
                if validation_target > 0:
                    current_positions = list(client.get_all_positions())
                    if validation_closed + len(current_positions) >= validation_target:
                        if current_positions:
                            self._status(
                                "VALIDATION_TARGET_NEAR_MONITORING_POSITIONS",
                                status="PASS",
                                clock=clock,
                                validation_closed_trades=validation_closed,
                                validation_target_closed_trades=validation_target,
                                open_position_count=len(current_positions),
                                lifecycle=lifecycle,
                            )
                            time.sleep(self.poll_seconds)
                            continue
                        return self._status(
                            "VALIDATION_TARGET_REACHED",
                            status="PASS",
                            clock=clock,
                            validation_closed_trades=validation_closed,
                            validation_target_closed_trades=validation_target,
                            lifecycle=lifecycle,
                        )

                if (
                    clock["minutes_to_close"]
                    <= self.market_close_buffer_minutes
                ):
                    return self._status(
                        "SESSION_CLOSE_BUFFER_REACHED",
                        status="PASS",
                        clock=clock,
                        today_order_count=order_count,
                        today_entry_order_count=entry_order_count,
                        lifecycle=lifecycle,
                    )

                try:
                    shadow_guard = DailySessionShadowGuard(
                        self.root
                    ).evaluate(
                        client=client,
                        account=account,
                        clock=clock,
                        today_order_count=order_count,
                    )
                except Exception as shadow_error:
                    shadow_guard = {
                        "mode": "SHADOW",
                        "enforced": False,
                        "action": "SHADOW_UNAVAILABLE",
                        "would_allow_order": None,
                        "quality_score": None,
                        "issue_codes": [
                            "SHADOW_EVALUATION_ERROR"
                        ],
                        "error": str(shadow_error),
                    }

                # PAPER-ONLY SMART SAFETY ENFORCEMENT V3.
                # DAILY_ORDER_LIMIT is intentionally handled by the
                # session's dynamic 5 -> 10 -> 15 ramp. All other
                # Smart Guard blockers are hard blockers for Alpaca Paper.
                if not self.dry_run and isinstance(shadow_guard, dict):
                    guard_issue_codes = set(
                        shadow_guard.get("issue_codes") or []
                    )
                    hard_guard_issue_codes = sorted(
                        code
                        for code in guard_issue_codes
                        if code != "DAILY_ORDER_LIMIT"
                    )

                    if hard_guard_issue_codes:
                        enforced_shadow_guard = dict(shadow_guard)
                        enforced_shadow_guard[
                            "paper_enforced_issue_codes"
                        ] = hard_guard_issue_codes
                        enforced_shadow_guard[
                            "daily_order_limit_delegated_to_ramp"
                        ] = True

                        self._status(
                            "SMART_SAFE_GUARD_BLOCKED_MONITORING",
                            status="PASS",
                            clock=clock,
                            today_order_count=order_count,
                            shadow_guard=enforced_shadow_guard,
                        )
                        time.sleep(self.poll_seconds)
                        continue

                if entry_order_count >= self.maximum_daily_orders:
                    limit_status = self._status(
                        "DAILY_ORDER_LIMIT_REACHED_MONITORING",
                        status="PASS",
                        clock=clock,
                        today_order_count=order_count,
                        shadow_guard=shadow_guard,
                    )

                    if self.dry_run:
                        return limit_status

                    time.sleep(self.poll_seconds)
                    continue

                self._status(
                    "RUNNING_ONE_CONTROLLED_CYCLE",
                    clock=clock,
                    today_order_count=order_count,
                    shadow_guard=shadow_guard,
                )

                # Shadow only: existing Paper order path remains unchanged.
                cycle = self._run_order_cycle()
                if cycle["exit_code"] != 0:
                    return self._status(
                        "SESSION_BLOCKED",
                        status="BLOCKED",
                        reason=(
                            "ORDER_CYCLE_FAILED_EXIT_"
                            + str(cycle["exit_code"])
                        ),
                        cycle=cycle,
                        clock=clock,
                        today_order_count=order_count,
                    )

                if self.dry_run:
                    return self._status(
                        "DRY_RUN_COMPLETED",
                        status="PASS",
                        cycle=cycle,
                        clock=clock,
                        today_order_count=order_count,
                    )

                time.sleep(5)
                after_orders = self._today_orders(client)
                after_buy_orders = self._today_buy_orders(client)
                self._status(
                    "CONTROLLED_CYCLE_COMPLETED",
                    status="PASS",
                    cycle=cycle,
                    clock=clock,
                    today_order_count_before=order_count,
                    today_order_count_after=len(after_orders),
                    today_entry_order_count_after=len(after_buy_orders),
                    lifecycle=lifecycle,
                    next_action=(
                        "MONITOR_AND_MANAGE_POSITIONS"
                        if len(after_buy_orders) >= self.maximum_daily_orders
                        else "CONTINUE_AUTONOMOUS_CYCLES"
                    ),
                )
                time.sleep(self.poll_seconds)
                continue

        except Exception as exc:
            return self._status(
                "SESSION_BLOCKED",
                status="BLOCKED",
                reason=str(exc),
            )
        finally:
            self._release_lock()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    parser.add_argument("--poll-seconds", type=int, default=60)
    parser.add_argument("--maximum-daily-orders", type=int, default=1)
    parser.add_argument("--maximum-order-notional", type=float, default=100)
    parser.add_argument(
        "--market-close-buffer-minutes", type=int, default=15
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    runner = PaperDailySessionRunner(
        Path(args.repository_root),
        poll_seconds=args.poll_seconds,
        maximum_daily_orders=args.maximum_daily_orders,
        maximum_order_notional=args.maximum_order_notional,
        market_close_buffer_minutes=args.market_close_buffer_minutes,
        dry_run=args.dry_run,
    )
    result = runner.run()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
