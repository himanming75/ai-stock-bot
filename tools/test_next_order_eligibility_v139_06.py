from __future__ import annotations
import json, tempfile, unittest
from pathlib import Path
from autonomous_paper_runtime.next_order_eligibility import NextOrderEligibility


class Tests(unittest.TestCase):
    def cycle(self):
        return {
            "status": "PASS",
            "state": "CYCLE_RESUMED",
            "cycle_id": "cycle-001",
            "next_order_eligibility_ready": True,
            "safe_mode_engaged": False,
        }

    def snapshot(self):
        return {
            "account_active": True,
            "trading_blocked": False,
            "market_is_open": True,
            "open_order_count": 0,
            "position_count": 0,
            "risk_approved": True,
            "safe_mode_engaged": False,
        }

    def run_case(self, cycle, snapshot=None, existing=None):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        c = root / "cycle.json"
        s = root / "snapshot.json"
        token = root / "token.json"
        result = root / "result.json"
        c.write_text(json.dumps(cycle), encoding="utf-8")
        if snapshot is not None:
            s.write_text(json.dumps(snapshot), encoding="utf-8")
        if existing is not None:
            token.write_text(json.dumps(existing), encoding="utf-8")
        report = NextOrderEligibility().run(
            cycle_result_path=c,
            eligibility_snapshot_path=s,
            eligibility_token_path=token,
            result_path=result,
        )
        return report, token

    def test_waits_before_cycle_resume(self):
        report, token = self.run_case({
            "status": "PASS",
            "state": "WAIT_RECOVERY_VALIDATION",
            "cycle_id": "",
            "next_order_eligibility_ready": False,
            "safe_mode_engaged": False,
        })
        self.assertEqual(report.state, "WAIT_CYCLE_RESUME")
        self.assertFalse(token.exists())

    def test_all_conditions_create_eligibility_token(self):
        report, token = self.run_case(self.cycle(), self.snapshot())
        self.assertEqual(report.state, "NEXT_ORDER_ELIGIBLE")
        self.assertTrue(report.eligible)
        self.assertTrue(token.exists())

    def test_market_closed_blocks(self):
        snap = self.snapshot()
        snap["market_is_open"] = False
        report, _ = self.run_case(self.cycle(), snap)
        self.assertEqual(report.status, "BLOCKED")
        self.assertTrue(report.safe_mode_engaged)

    def test_open_order_blocks(self):
        snap = self.snapshot()
        snap["open_order_count"] = 1
        report, _ = self.run_case(self.cycle(), snap)
        self.assertEqual(report.status, "BLOCKED")

    def test_risk_not_approved_blocks(self):
        snap = self.snapshot()
        snap["risk_approved"] = False
        report, _ = self.run_case(self.cycle(), snap)
        self.assertEqual(report.status, "BLOCKED")

    def test_missing_snapshot_blocks_after_resume(self):
        report, _ = self.run_case(self.cycle())
        self.assertEqual(report.status, "BLOCKED")

    def test_conflicting_token_blocks(self):
        report, _ = self.run_case(
            self.cycle(),
            self.snapshot(),
            {"eligibility_id": "other", "cycle_id": "cycle-other"},
        )
        self.assertEqual(report.status, "BLOCKED")


if __name__ == "__main__":
    unittest.main()
