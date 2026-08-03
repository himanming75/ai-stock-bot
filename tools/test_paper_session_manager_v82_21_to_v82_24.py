
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from paper_runtime.session_manager_v82_21_24 import (
    evaluate_market_day,
    run_paper_session_manager,
)


class Tests(unittest.TestCase):
    def policy(self):
        return {
            "paper_only": True,
            "read_only": True,
            "broker_write_enabled": False,
            "order_submission_enabled": False,
            "live_trading_enabled": False,
            "market_timezone": "America/New_York",
            "regular_market_open": "09:30",
            "regular_market_close": "16:00",
            "market_holidays": ["2026-08-04"],
            "starting_equity": 100000,
        }

    def write(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")

    def run_case(
        self,
        *,
        observed,
        start=False,
        end=False,
        recover=False,
        active=False,
        lock_active=False,
    ):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)

        self.write(root / "authorization.json", {
            "state": "SHADOW_TRADE_NO_ACTION"
        })
        self.write(root / "policy.json", self.policy())
        if active:
            self.write(root / "state.json", {
                "session_id": "session-existing",
                "session_active": True,
                "trading_date": "2026-08-03",
                "started_at": "2026-08-03T13:30:00+00:00",
                "start_equity": 100000,
                "trade_count": 0,
            })
        if lock_active:
            self.write(root / "lock.json", {
                "active": True,
                "session_id": "session-recover",
                "trading_date": "2026-08-03",
                "started_at": "2026-08-03T13:30:00+00:00",
            })

        result = run_paper_session_manager(
            authorization_result_path=root / "authorization.json",
            policy_path=root / "policy.json",
            session_state_path=root / "state.json",
            session_lock_path=root / "lock.json",
            daily_ledger_path=root / "ledger.jsonl",
            daily_snapshot_path=root / "snapshot.json",
            dashboard_path=root / "dashboard.json",
            result_path=root / "result.json",
            start_session_requested=start,
            end_session_requested=end,
            recover_session_requested=recover,
            observed_at=observed,
        )
        return result, root

    def test_market_open(self):
        result = evaluate_market_day(
            observed_at=datetime(
                2026, 8, 3, 14, 0, tzinfo=timezone.utc
            ),
            policy=self.policy(),
        )
        self.assertTrue(result["market_open"])

    def test_weekend_skip(self):
        result, _ = self.run_case(
            observed=datetime(
                2026, 8, 2, 14, 0, tzinfo=timezone.utc
            )
        )
        self.assertEqual(
            result["state"],
            "PAPER_SESSION_MARKET_HOLIDAY_OR_WEEKEND",
        )

    def test_policy_holiday_skip(self):
        result, _ = self.run_case(
            observed=datetime(
                2026, 8, 4, 14, 0, tzinfo=timezone.utc
            )
        )
        self.assertTrue(result["holiday"])

    def test_ready_to_start(self):
        result, _ = self.run_case(
            observed=datetime(
                2026, 8, 3, 14, 0, tzinfo=timezone.utc
            )
        )
        self.assertEqual(result["state"], "PAPER_SESSION_READY_TO_START")

    def test_session_start(self):
        result, root = self.run_case(
            observed=datetime(
                2026, 8, 3, 14, 0, tzinfo=timezone.utc
            ),
            start=True,
        )
        self.assertTrue(result["session_started"])
        self.assertEqual(result["state"], "PAPER_SESSION_RUNNING")
        self.assertTrue((root / "ledger.jsonl").exists())

    def test_duplicate_start_blocked(self):
        result, _ = self.run_case(
            observed=datetime(
                2026, 8, 3, 14, 0, tzinfo=timezone.utc
            ),
            start=True,
            active=True,
        )
        self.assertEqual(result["status"], "BLOCKED")

    def test_session_end(self):
        result, root = self.run_case(
            observed=datetime(
                2026, 8, 3, 20, 5, tzinfo=timezone.utc
            ),
            end=True,
            active=True,
        )
        self.assertTrue(result["session_ended"])
        self.assertEqual(result["state"], "PAPER_SESSION_CLOSED")
        self.assertTrue((root / "snapshot.json").exists())

    def test_recovery(self):
        result, _ = self.run_case(
            observed=datetime(
                2026, 8, 3, 15, 0, tzinfo=timezone.utc
            ),
            recover=True,
            lock_active=True,
        )
        self.assertTrue(result["session_recovered"])
        self.assertEqual(result["state"], "PAPER_SESSION_RECOVERED")

    def test_dashboard_written(self):
        result, root = self.run_case(
            observed=datetime(
                2026, 8, 3, 14, 0, tzinfo=timezone.utc
            )
        )
        self.assertTrue(result["dashboard_state_written"])
        self.assertTrue((root / "dashboard.json").exists())

    def test_read_only_contract(self):
        result, _ = self.run_case(
            observed=datetime(
                2026, 8, 3, 14, 0, tzinfo=timezone.utc
            )
        )
        self.assertFalse(result["broker_write_enabled"])
        self.assertFalse(result["order_submission_enabled"])
        self.assertEqual(result["network_requests_executed"], 0)
        self.assertEqual(result["write_requests_executed"], 0)
        self.assertEqual(result["actual_paper_orders_submitted"], 0)


if __name__ == "__main__":
    unittest.main()
