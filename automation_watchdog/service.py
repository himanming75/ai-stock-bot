from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .models import WatchdogPolicy
from .state import WatchdogStateStore


class AutomationWatchdog:
    def __init__(self, root: Path, clock_provider=None) -> None:
        self.root = root
        self.clock_provider = clock_provider

    def _clock(self) -> dict:
        if self.clock_provider is not None:
            return self.clock_provider()
        from actual_market_polling.service import ReadOnlyAlpaca
        return ReadOnlyAlpaca().clock()

    def _load_policy(self, path: Path) -> WatchdogPolicy:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
        policy = WatchdogPolicy.from_mapping(payload)
        if policy.actual_submission_allowed:
            raise RuntimeError("WATCHDOG_ACTUAL_SUBMISSION_MUST_REMAIN_FALSE")
        return policy

    def _controller_command(self, profile_path: str) -> list[str]:
        return [
            sys.executable,
            str(self.root / "tools/run_paper_automation_controller.py"),
            "--profile",
            profile_path,
        ]

    def _is_process_alive(self, pid: int) -> bool:
        if pid <= 0:
            return False
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False

    def _cleanup_stale_lock(self, lock_path: Path, stale_seconds: int) -> bool:
        if not lock_path.exists():
            return False
        try:
            payload = json.loads(lock_path.read_text(encoding="utf-8-sig"))
        except Exception:
            payload = {}
        pid = int(payload.get("pid", 0) or 0)
        age = time.time() - lock_path.stat().st_mtime
        if self._is_process_alive(pid):
            return False
        if age < stale_seconds:
            return False
        lock_path.unlink()
        return True

    def _heartbeat_is_stale(
        self, checkpoint_path: Path, timeout_seconds: int
    ) -> bool:
        if not checkpoint_path.exists():
            return True
        try:
            payload = json.loads(
                checkpoint_path.read_text(encoding="utf-8-sig")
            )
            saved_at = datetime.fromisoformat(payload["saved_at"])
        except Exception:
            return True
        return (
            datetime.now(timezone.utc) - saved_at
        ).total_seconds() > timeout_seconds

    def _recent_restart_count(
        self, attempts: list[str], window_seconds: int
    ) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(
            seconds=window_seconds
        )
        count = 0
        for value in attempts:
            try:
                if datetime.fromisoformat(value) >= cutoff:
                    count += 1
            except Exception:
                continue
        return count

    def run(
        self,
        *,
        policy_path: Path,
        max_watch_cycles: int = 2,
        controller_runner=None,
    ) -> dict:
        policy = self._load_policy(policy_path)

        actual_dir = (
            self.root
            / "release/automation_watchdog_restart_recovery/actual"
        )
        controller_actual = (
            self.root
            / "release/paper_automation_controller/actual"
        )
        actual_dir.mkdir(parents=True, exist_ok=True)

        state_store = WatchdogStateStore(actual_dir / "watchdog_state.json")
        state = state_store.load()
        restart_attempts = list(state.get("restart_attempts", []))

        lock_path = controller_actual / "controller.lock"
        checkpoint_path = controller_actual / "checkpoint.json"
        ledger_path = actual_dir / "watchdog_ledger.jsonl"

        observations = []
        restart_count = 0
        stop_reason = None

        if controller_runner is None:
            def controller_runner(command):
                return subprocess.run(
                    command,
                    cwd=self.root,
                    capture_output=True,
                    text=True,
                    timeout=3600,
                )

        for watch_cycle in range(1, max(1, max_watch_cycles) + 1):
            clock = self._clock()
            market_open = bool(clock.get("is_open", False))

            if policy.stop_when_market_closed and not market_open:
                stop_reason = "MARKET_CLOSED"
                observation = {
                    "watch_cycle": watch_cycle,
                    "market_is_open": False,
                    "action": "IDLE",
                    "reason": "MARKET_CLOSED",
                }
                observations.append(observation)
                break

            stale_lock_removed = self._cleanup_stale_lock(
                lock_path, policy.stale_lock_seconds
            )
            heartbeat_stale = self._heartbeat_is_stale(
                checkpoint_path, policy.heartbeat_timeout_seconds
            )
            recent_restarts = self._recent_restart_count(
                restart_attempts, policy.crash_window_seconds
            )

            if recent_restarts >= policy.maximum_restart_attempts:
                stop_reason = "CRASH_LOOP_BLOCKED"
                observation = {
                    "watch_cycle": watch_cycle,
                    "market_is_open": market_open,
                    "action": "BLOCK",
                    "reason": "CRASH_LOOP_BLOCKED",
                    "recent_restart_count": recent_restarts,
                    "stale_lock_removed": stale_lock_removed,
                    "heartbeat_stale": heartbeat_stale,
                }
                observations.append(observation)
                break

            command = self._controller_command(policy.controller_profile)
            started_at = datetime.now(timezone.utc).isoformat()
            process = controller_runner(command)
            exit_code = int(process.returncode)
            completed_at = datetime.now(timezone.utc).isoformat()

            action = "CONTROLLER_COMPLETED"
            reason = None
            if exit_code != 0:
                restart_attempts.append(completed_at)
                restart_count += 1
                action = "RESTART_SCHEDULED"
                reason = f"CONTROLLER_EXIT_CODE:{exit_code}"
                if watch_cycle < max_watch_cycles:
                    time.sleep(policy.restart_backoff_seconds)

            observation = {
                "watch_cycle": watch_cycle,
                "started_at": started_at,
                "completed_at": completed_at,
                "market_is_open": market_open,
                "controller_command": command,
                "controller_exit_code": exit_code,
                "controller_stdout_tail": (process.stdout or "")[-4000:],
                "controller_stderr_tail": (process.stderr or "")[-4000:],
                "stale_lock_removed": stale_lock_removed,
                "heartbeat_stale_before_run": heartbeat_stale,
                "action": action,
                "reason": reason,
                "actual_broker_write_performed": False,
                "actual_order_submission_performed": False,
                "actual_paper_orders_submitted": 0,
                "actual_live_orders_submitted": 0,
            }
            observations.append(observation)

            with ledger_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(observation, sort_keys=True) + "\n")

            state_store.save(
                {
                    "state": "HEALTHY" if exit_code == 0 else "RESTARTING",
                    "restart_attempts": restart_attempts,
                    "last_controller_exit_code": exit_code,
                    "last_observation": observation,
                }
            )

            print(
                json.dumps(observation, indent=2, sort_keys=True),
                flush=True,
            )

            if exit_code == 0:
                stop_reason = "CONTROLLER_COMPLETED"
                break

        status = "PASS"
        if stop_reason == "CRASH_LOOP_BLOCKED":
            status = "BLOCKED"
        elif stop_reason == "MARKET_CLOSED":
            status = "IDLE"
        elif observations and observations[-1].get(
            "controller_exit_code", 0
        ) != 0:
            status = "BLOCKED"

        summary = {
            "stage": "AUTOMATION_WATCHDOG_RESTART_RECOVERY",
            "status": status,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "policy": policy.as_json(),
            "completed_watch_cycles": len(observations),
            "restart_count": restart_count,
            "stop_reason": stop_reason,
            "observations": observations,
            "actual_broker_write_performed": False,
            "actual_order_submission_performed": False,
            "actual_paper_orders_submitted": 0,
            "actual_live_orders_submitted": 0,
            "next_fixed_development": "DAILY_SESSION_MANAGER_AND_STARTUP_AUTORUN",
            "next_market_validation": "FULL_SESSION_WATCHDOG_RUN",
        }

        (actual_dir / "watchdog_summary.json").write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return summary
