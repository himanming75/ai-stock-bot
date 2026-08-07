from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


STATE_RELATIVE = Path(
    "runtime/market_open_auto_validation/latest_status.json"
)
LOCK_RELATIVE = Path(
    "runtime/market_open_auto_validation/runner.lock"
)
LEDGER_RELATIVE = Path(
    "runtime/market_open_auto_validation/validation_ledger.jsonl"
)

PREFLIGHT_PATTERNS = [
    "RUN_V14001_TO_V15000_PREFLIGHT.ps1",
    "RUN_*PREFLIGHT*.ps1",
]
ARM_PATTERNS = [
    "ARM_PAPER_ONLY_V14001_TO_V15000.ps1",
    "ARM_*PAPER_ONLY*.ps1",
]
VALIDATION_PATTERNS = [
    "RUN_ONE_PAPER_VALIDATION_ORDER_V14001_TO_V15000.ps1",
    "RUN_ONE_*PAPER*VALIDATION*ORDER*.ps1",
]

LIVE_BLOCK_ENV_NAMES = {
    "ETRADE_LIVE_WRITE_ENABLED",
    "ETRADE_LIVE_SUBMISSION_ENABLED",
    "LIVE_TRADING_ENABLED",
    "BROKER_WRITE_ENABLED",
}


@dataclass
class ScriptSet:
    preflight: Path
    arm: Path
    validation: Path


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def append_jsonl(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(
            json.dumps(data, ensure_ascii=False, sort_keys=True) + "\n"
        )


def env_truthy(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {
        "1", "true", "yes", "on", "enabled"
    }


def resolve_unique(root: Path, patterns: list[str]) -> Path:
    """
    Resolve patterns in priority order.

    The first pattern that produces exactly one file wins.
    Broader fallback patterns are only checked when an earlier,
    more specific pattern finds no file.
    """
    for pattern in patterns:
        unique = sorted({
            path.resolve()
            for path in root.glob(pattern)
            if path.is_file()
        })

        if len(unique) == 1:
            return unique[0]

        if len(unique) > 1:
            raise RuntimeError(
                f"EXPECTED_ONE_SCRIPT:{pattern}:FOUND_{len(unique)}:"
                + ",".join(path.name for path in unique[:10])
            )

    raise RuntimeError(
        f"EXPECTED_ONE_SCRIPT:{patterns[0]}:FOUND_0"
    )


class AutoValidationRunner:
    def __init__(
        self,
        root: Path,
        poll_seconds: int = 30,
        timeout_minutes: int = 480,
        dry_run: bool = False,
    ) -> None:
        self.root = root.resolve()
        self.poll_seconds = max(10, int(poll_seconds))
        self.timeout_minutes = max(1, int(timeout_minutes))
        self.dry_run = bool(dry_run)
        self.state_path = self.root / STATE_RELATIVE
        self.lock_path = self.root / LOCK_RELATIVE
        self.ledger_path = self.root / LEDGER_RELATIVE

    def _state(self, stage: str, **extra: Any) -> dict[str, Any]:
        data = {
            "stage": stage,
            "updated_at_utc": utc_now(),
            "paper_broker": "ALPACA",
            "live_broker": "ETRADE",
            "paper_only": True,
            "etrade_live_write_enabled": False,
            "live_orders_submitted": 0,
            "maximum_validation_orders": 1,
            "dry_run": self.dry_run,
        }
        data.update(extra)
        write_json(self.state_path, data)
        append_jsonl(self.ledger_path, data)
        return data

    def _acquire_lock(self) -> None:
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        if self.lock_path.exists():
            raise RuntimeError("RUNNER_ALREADY_LOCKED")
        self.lock_path.write_text(
            json.dumps({
                "pid": os.getpid(),
                "created_at_utc": utc_now(),
            }),
            encoding="utf-8",
        )

    def _release_lock(self) -> None:
        self.lock_path.unlink(missing_ok=True)

    def _validate_environment(self) -> None:
        missing = [
            name for name in (
                "APCA_API_KEY_ID",
                "APCA_API_SECRET_KEY",
            )
            if not os.getenv(name)
        ]
        if missing:
            raise RuntimeError(
                "PAPER_CREDENTIALS_MISSING:" + ",".join(missing)
            )
        enabled_live = [
            name for name in LIVE_BLOCK_ENV_NAMES
            if env_truthy(name)
        ]
        if enabled_live:
            raise RuntimeError(
                "LIVE_WRITE_ENV_MUST_BE_OFF:" + ",".join(enabled_live)
            )

    def _resolve_scripts(self) -> ScriptSet:
        return ScriptSet(
            preflight=resolve_unique(self.root, PREFLIGHT_PATTERNS),
            arm=resolve_unique(self.root, ARM_PATTERNS),
            validation=resolve_unique(self.root, VALIDATION_PATTERNS),
        )

    def _trading_client(self):
        try:
            from alpaca.trading.client import TradingClient
        except ImportError as exc:
            raise RuntimeError("ALPACA_PY_NOT_INSTALLED") from exc
        return TradingClient(
            os.environ["APCA_API_KEY_ID"],
            os.environ["APCA_API_SECRET_KEY"],
            paper=True,
        )

    def _paper_account_check(self, client) -> dict[str, Any]:
        account = client.get_account()
        status = str(getattr(account, "status", ""))
        blocked = any(bool(getattr(account, name, False)) for name in (
            "account_blocked",
            "trading_blocked",
            "transfers_blocked",
        ))
        if blocked:
            raise RuntimeError("ALPACA_PAPER_ACCOUNT_BLOCKED")
        return {
            "account_status": status,
            "account_number_suffix": str(
                getattr(account, "account_number", "")
            )[-4:],
            "equity": str(getattr(account, "equity", "")),
            "buying_power": str(getattr(account, "buying_power", "")),
        }

    def _wait_market_open(self, client) -> dict[str, Any]:
        started = time.monotonic()
        timeout_seconds = self.timeout_minutes * 60
        while True:
            clock = client.get_clock()
            is_open = bool(getattr(clock, "is_open", False))
            clock_data = {
                "market_open": is_open,
                "clock_timestamp": str(
                    getattr(clock, "timestamp", "")
                ),
                "next_open": str(getattr(clock, "next_open", "")),
                "next_close": str(getattr(clock, "next_close", "")),
            }
            if is_open:
                self._state("MARKET_OPEN_DETECTED", **clock_data)
                return clock_data
            if time.monotonic() - started >= timeout_seconds:
                raise RuntimeError("MARKET_OPEN_WAIT_TIMEOUT")
            self._state("WAITING_MARKET_OPEN", **clock_data)
            time.sleep(self.poll_seconds)

    def _run_script(self, path: Path, label: str) -> dict[str, Any]:
        if self.dry_run:
            return {
                "label": label,
                "path": str(path),
                "exit_code": 0,
                "stdout": "DRY_RUN",
                "stderr": "",
            }
        process = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(path),
            ],
            cwd=self.root,
            capture_output=True,
            text=True,
            errors="replace",
        )
        result = {
            "label": label,
            "path": str(path),
            "exit_code": process.returncode,
            "stdout": process.stdout[-12000:],
            "stderr": process.stderr[-12000:],
        }
        if process.returncode != 0:
            raise RuntimeError(
                f"{label}_FAILED_EXIT_{process.returncode}"
            )
        return result

    def run(self) -> dict[str, Any]:
        self._acquire_lock()
        try:
            self._state("STARTING")
            self._validate_environment()
            scripts = self._resolve_scripts()
            self._state(
                "SCRIPTS_RESOLVED",
                scripts={
                    "preflight": str(scripts.preflight),
                    "arm": str(scripts.arm),
                    "validation": str(scripts.validation),
                },
            )

            client = self._trading_client()
            account = self._paper_account_check(client)
            self._state("PAPER_ACCOUNT_VALIDATED", account=account)
            clock = self._wait_market_open(client)

            self._state("RUNNING_PREFLIGHT", account=account, clock=clock)
            preflight = self._run_script(scripts.preflight, "PREFLIGHT")

            self._state("ARMING_ONE_VALIDATION_ORDER")
            arm = self._run_script(scripts.arm, "ARM")

            self._state("SUBMITTING_ONE_PAPER_VALIDATION_ORDER")
            validation = self._run_script(
                scripts.validation,
                "ONE_PAPER_VALIDATION_ORDER",
            )

            result = self._state(
                "VALIDATION_COMMAND_COMPLETED",
                status="PASS",
                actual_live_orders_submitted=0,
                maximum_validation_orders=1,
                account=account,
                clock=clock,
                execution={
                    "preflight": preflight,
                    "arm": arm,
                    "validation": validation,
                },
                next_action=(
                    "REVIEW_ORDER_FILL_POSITION_ACCOUNT_CERTIFICATION"
                ),
            )
            return result
        except Exception as exc:
            result = self._state(
                "BLOCKED",
                status="BLOCKED",
                reason=str(exc),
                actual_live_orders_submitted=0,
            )
            return result
        finally:
            self._release_lock()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    parser.add_argument("--poll-seconds", type=int, default=30)
    parser.add_argument("--timeout-minutes", type=int, default=480)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    runner = AutoValidationRunner(
        Path(args.repository_root),
        poll_seconds=args.poll_seconds,
        timeout_minutes=args.timeout_minutes,
        dry_run=args.dry_run,
    )
    result = runner.run()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
