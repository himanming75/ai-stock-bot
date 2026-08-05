from __future__ import annotations

import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from .models import DailySessionPolicy
from .state import DailySessionStateStore


class DailySessionManager:
    def __init__(
        self,
        root: Path,
        clock_provider=None,
        process_runner=None,
    ) -> None:
        self.root = root
        self.clock_provider = clock_provider
        self.process_runner = process_runner

    def _clock(self) -> dict:
        if self.clock_provider is not None:
            return self.clock_provider()
        from actual_market_polling.service import ReadOnlyAlpaca
        return ReadOnlyAlpaca().clock()

    def _load_policy(
        self, path: Path
    ) -> DailySessionPolicy:
        payload = json.loads(
            path.read_text(encoding="utf-8-sig")
        )
        policy = DailySessionPolicy.from_mapping(payload)
        if policy.actual_submission_allowed:
            raise RuntimeError(
                "DAILY_SESSION_ACTUAL_SUBMISSION_MUST_REMAIN_FALSE"
            )
        return policy

    def _local_session_date(
        self, timezone_name: str
    ) -> str:
        now = datetime.now(ZoneInfo(timezone_name))
        return now.date().isoformat()

    def _weekday_allowed(
        self, timezone_name: str, allow_weekend: bool
    ) -> bool:
        now = datetime.now(ZoneInfo(timezone_name))
        return allow_weekend or now.weekday() < 5

    def _watchdog_command(
        self, script_path: Path
    ) -> list[str]:
        return [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script_path),
            "-MaxWatchCycles",
            "1",
        ]

    def evaluate(
        self,
        *,
        policy_path: Path,
        execute_watchdog: bool = False,
    ) -> dict:
        policy = self._load_policy(policy_path)
        actual_dir = (
            self.root
            / "release/daily_session_manager_startup_autorun/actual"
        )
        actual_dir.mkdir(parents=True, exist_ok=True)

        state_store = DailySessionStateStore(
            actual_dir / "daily_session_state.json"
        )
        state = state_store.load()

        session_date = self._local_session_date(
            policy.session_timezone
        )
        if state.get("session_date") != session_date:
            state = {
                "session_date": session_date,
                "launch_count": 0,
                "state": "NEW_DAY",
                "last_action": None,
            }

        clock = self._clock()
        market_is_open = bool(clock.get("is_open", False))
        weekday_allowed = self._weekday_allowed(
            policy.session_timezone,
            policy.allow_weekend_start,
        )

        action = "IDLE"
        reason = "NO_ACTION_REQUIRED"
        launched = False
        watchdog_exit_code = None
        watchdog_stdout_tail = ""
        watchdog_stderr_tail = ""

        can_launch = (
            weekday_allowed
            and market_is_open
            and policy.launch_watchdog_when_market_open
            and int(state.get("launch_count", 0))
            < policy.maximum_daily_launches
        )

        if can_launch:
            action = (
                "LAUNCH_WATCHDOG"
                if execute_watchdog
                else "WATCHDOG_LAUNCH_READY"
            )
            reason = "MARKET_OPEN_AND_DAILY_LIMIT_AVAILABLE"

            if execute_watchdog:
                if policy.startup_delay_seconds > 0:
                    time.sleep(policy.startup_delay_seconds)

                script_path = self.root / policy.watchdog_script
                if not script_path.exists():
                    raise RuntimeError(
                        f"WATCHDOG_SCRIPT_MISSING:{script_path}"
                    )

                command = self._watchdog_command(script_path)
                runner = self.process_runner or subprocess.run
                process = runner(
                    command,
                    cwd=self.root,
                    capture_output=True,
                    text=True,
                )
                watchdog_exit_code = int(process.returncode)
                watchdog_stdout_tail = (
                    process.stdout or ""
                )[-4000:]
                watchdog_stderr_tail = (
                    process.stderr or ""
                )[-4000:]
                launched = True
                state["launch_count"] = (
                    int(state.get("launch_count", 0)) + 1
                )
                state["state"] = (
                    "WATCHDOG_COMPLETED"
                    if watchdog_exit_code == 0
                    else "WATCHDOG_FAILED"
                )
                state["last_action"] = action
        elif not weekday_allowed:
            reason = "WEEKEND_BLOCKED"
        elif not market_is_open:
            action = (
                "SESSION_CLOSED"
                if policy.stop_after_market_close
                else "IDLE"
            )
            reason = "MARKET_CLOSED"
            state["state"] = "MARKET_CLOSED"
            state["last_action"] = action
        elif int(state.get("launch_count", 0)) >= (
            policy.maximum_daily_launches
        ):
            reason = "DAILY_LAUNCH_LIMIT_REACHED"
            state["state"] = "DAILY_LIMIT_REACHED"
            state["last_action"] = action

        result = {
            "stage": (
                "DAILY_SESSION_MANAGER_AND_STARTUP_AUTORUN"
            ),
            "status": (
                "PASS"
                if watchdog_exit_code in {None, 0}
                else "BLOCKED"
            ),
            "generated_at": (
                datetime.now(timezone.utc).isoformat()
            ),
            "session_date": session_date,
            "market_is_open": market_is_open,
            "weekday_allowed": weekday_allowed,
            "action": action,
            "reason": reason,
            "execute_watchdog": execute_watchdog,
            "watchdog_launched": launched,
            "watchdog_exit_code": watchdog_exit_code,
            "watchdog_stdout_tail": watchdog_stdout_tail,
            "watchdog_stderr_tail": watchdog_stderr_tail,
            "launch_count": int(
                state.get("launch_count", 0)
            ),
            "policy": policy.as_json(),
            "actual_broker_write_performed": False,
            "actual_order_submission_performed": False,
            "actual_paper_orders_submitted": 0,
            "actual_live_orders_submitted": 0,
            "next_fixed_development": (
                "WINDOWS_AUTORUN_REGISTRATION_AND_HEALTH_AUDIT"
            ),
            "next_market_validation": (
                "NEXT_TRADING_DAY_AUTOSTART_VALIDATION"
            ),
        }

        state["session_date"] = session_date
        state["last_result"] = result
        state_store.save(state)

        with (
            actual_dir / "daily_session_ledger.jsonl"
        ).open("a", encoding="utf-8") as handle:
            handle.write(
                json.dumps(result, sort_keys=True) + "\n"
            )

        (
            actual_dir / "daily_session_summary.json"
        ).write_text(
            json.dumps(result, indent=2, sort_keys=True)
            + "\n",
            encoding="utf-8",
        )
        return result
