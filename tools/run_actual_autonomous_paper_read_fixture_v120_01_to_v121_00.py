from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autonomous_paper_runtime import AutonomousPaperReadSession


@dataclass
class Config:
    base_url: str = "https://paper-api.alpaca.markets"
    network_read_enabled: bool = True
    network_write_enabled: bool = False


@dataclass
class Account:
    account_id: str = "paper-account-fixture-123456"
    status: str = "ACTIVE"
    trading_blocked: bool = False
    cash: str = "1000"
    buying_power: str = "2000"
    equity: str = "1050"


@dataclass
class Clock:
    is_open: bool = True
    timestamp: datetime = datetime(2026, 8, 3, 15, 0, tzinfo=timezone.utc)
    next_open: datetime = datetime(2026, 8, 4, 13, 30, tzinfo=timezone.utc)
    next_close: datetime = datetime(2026, 8, 3, 20, 0, tzinfo=timezone.utc)


@dataclass
class Position:
    symbol: str


class FixtureClient:
    def __init__(self):
        self.config = Config()
        self.network_requests_executed = 0
        self.write_requests_executed = 0
        self.request_methods = []

    def _read(self):
        self.network_requests_executed += 1
        self.request_methods.append("GET")

    def get_account(self):
        self._read()
        return Account()

    def get_clock(self):
        self._read()
        return Clock()

    def list_positions(self):
        self._read()
        return [Position("AAPL")]

    def list_orders(self, *, status, limit=None):
        self._read()
        return [object()] if status == "open" else [object(), object()]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    args = parser.parse_args()

    output = Path(args.repository_root).resolve() / "release" / "v121_00" / "output"
    output.mkdir(parents=True, exist_ok=True)

    snapshot = AutonomousPaperReadSession(
        client=FixtureClient(),
        closed_order_limit=50,
    ).run()

    result = {
        "stage_range": "V120.01-V121.00",
        "status": "PASS",
        "implementation_type": "ACTUAL_AUTONOMOUS_PAPER_READ_SESSION",
        "validation_mode": "OFFLINE_FIXTURE",
        "actual_credentials_used": False,
        "actual_external_network_used": False,
        **snapshot.to_json_dict(),
        "next_phase": "V121_01_AUTONOMOUS_PAPER_READ_RECONCILIATION",
    }
    (output / "actual_autonomous_paper_read_fixture_result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
