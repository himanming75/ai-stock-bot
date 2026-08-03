
import json
import tempfile
import unittest
from pathlib import Path

from paper_runtime.end_of_day_v82_33_36 import (
    evaluate_end_of_day,
    run_end_of_day_manager,
)


class Tests(unittest.TestCase):
    def policy(self):
        return {
            "paper_only": True,
            "read_only": True,
            "broker_write_enabled": False,
            "order_submission_enabled": False,
            "live_trading_enabled": False,
            "allow_inactive_session_certification": True,
        }

    def write(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")

    def base_inputs(self):
        return {
            "session": {
                "state": "PAPER_SESSION_CLOSED",
                "session_active": False,
                "market_closed": True,
                "session_id": "session-test",
                "trading_date": "2026-08-03",
            },
            "scheduler": {
                "state": "PAPER_SCHEDULER_TICK_COMPLETED",
                "active_tick": False,
            },
            "intraday": {
                "state": "INTRADAY_LOOP_COMPLETE",
                "active_loop": False,
            },
            "performance": {
                "state": "SHADOW_ANALYTICS_IN_PROGRESS",
                "cumulative_pnl": 125.5,
                "cumulative_return_pct": 0.1255,
                "trade_count": 2,
                "maximum_drawdown_pct": 0.2,
            },
            "risk": {
                "state": "SHADOW_RISK_CLEAR",
            },
        }

    def test_eod_ready(self):
        items = self.base_inputs()
        result = evaluate_end_of_day(
            session=items["session"],
            scheduler=items["scheduler"],
            intraday=items["intraday"],
            performance=items["performance"],
            risk=items["risk"],
            policy=self.policy(),
        )
        self.assertTrue(result["eod_ready"])

    def test_market_open_blocks(self):
        items = self.base_inputs()
        items["session"]["market_closed"] = False
        result = evaluate_end_of_day(
            session=items["session"],
            scheduler=items["scheduler"],
            intraday=items["intraday"],
            performance=items["performance"],
            risk=items["risk"],
            policy=self.policy(),
        )
        self.assertIn("MARKET_NOT_CLOSED", result["eod_reasons"])

    def test_active_tick_blocks(self):
        items = self.base_inputs()
        items["scheduler"]["active_tick"] = True
        result = evaluate_end_of_day(
            session=items["session"],
            scheduler=items["scheduler"],
            intraday=items["intraday"],
            performance=items["performance"],
            risk=items["risk"],
            policy=self.policy(),
        )
        self.assertIn(
            "ACTIVE_SCHEDULER_TICK_EXISTS",
            result["eod_reasons"],
        )

    def test_active_loop_blocks(self):
        items = self.base_inputs()
        items["intraday"]["active_loop"] = True
        result = evaluate_end_of_day(
            session=items["session"],
            scheduler=items["scheduler"],
            intraday=items["intraday"],
            performance=items["performance"],
            risk=items["risk"],
            policy=self.policy(),
        )
        self.assertIn(
            "ACTIVE_INTRADAY_LOOP_EXISTS",
            result["eod_reasons"],
        )

    def run_case(
        self,
        *,
        certify=False,
        prepare=False,
        market_closed=True,
        certification_exists=False,
    ):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        items = self.base_inputs()
        items["session"]["market_closed"] = market_closed

        for name, payload in items.items():
            self.write(root / f"{name}.json", payload)
        self.write(root / "policy.json", self.policy())
        if certification_exists:
            self.write(root / "cert.json", {
                "certified": True,
                "certification_state": "DAILY_PAPER_CERTIFIED",
            })

        result = run_end_of_day_manager(
            session_result_path=root / "session.json",
            scheduler_result_path=root / "scheduler.json",
            intraday_result_path=root / "intraday.json",
            performance_result_path=root / "performance.json",
            risk_result_path=root / "risk.json",
            policy_path=root / "policy.json",
            daily_report_path=root / "report.json",
            certification_path=root / "cert.json",
            ledger_path=root / "ledger.jsonl",
            next_day_state_path=root / "next.json",
            dashboard_path=root / "dashboard.json",
            result_path=root / "result.json",
            certify_day_requested=certify,
            prepare_next_day_requested=prepare,
        )
        return result, root

    def test_ready_to_certify(self):
        result, _ = self.run_case()
        self.assertEqual(result["state"], "END_OF_DAY_READY_TO_CERTIFY")

    def test_certify_day(self):
        result, root = self.run_case(certify=True)
        self.assertTrue(result["day_certified"])
        self.assertEqual(result["state"], "DAILY_PAPER_CERTIFIED")
        self.assertTrue((root / "cert.json").exists())
        self.assertTrue((root / "ledger.jsonl").exists())

    def test_wait_certification_gates(self):
        result, _ = self.run_case(
            certify=True,
            market_closed=False,
        )
        self.assertEqual(
            result["state"],
            "DAILY_CERTIFICATION_WAIT_GATES",
        )

    def test_prepare_next_day(self):
        result, root = self.run_case(
            prepare=True,
            certification_exists=True,
        )
        self.assertTrue(result["next_day_ready"])
        self.assertTrue((root / "next.json").exists())

    def test_dashboard_written(self):
        result, root = self.run_case()
        self.assertTrue(result["dashboard_state_written"])
        self.assertTrue((root / "dashboard.json").exists())

    def test_read_only_contract(self):
        result, _ = self.run_case()
        self.assertFalse(result["broker_write_enabled"])
        self.assertFalse(result["order_submission_enabled"])
        self.assertEqual(result["network_requests_executed"], 0)
        self.assertEqual(result["write_requests_executed"], 0)
        self.assertEqual(result["actual_paper_orders_submitted"], 0)


if __name__ == "__main__":
    unittest.main()
