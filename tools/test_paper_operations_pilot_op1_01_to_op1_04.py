import json, tempfile, unittest
from pathlib import Path

from autonomous_paper_runtime.paper_operations_pilot import PaperOperationsPilot, LIVE_BASE_URL


class Tests(unittest.TestCase):
    def write(self, path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value), encoding="utf-8")

    def data(self):
        release = {
            "status": "PASS",
            "state": "V143_FINAL_PRODUCTION_PACKAGE_READY",
            "final_production_package_ready": True,
            "release_id": "release-001",
            "safe_mode_engaged": False,
        }
        policy = {
            "pilot_id": "pilot-001",
            "read_only": True,
            "order_submission_enabled": False,
            "live_trading_enabled": False,
            "max_daily_orders": 0,
            "expected_base_url": "https://paper-api.alpaca.markets",
        }
        snapshot = {
            "account": {
                "status": "ACTIVE",
                "account_blocked": False,
                "trading_blocked": False,
                "cash": "100000",
                "equity": "100000",
                "buying_power": "200000",
            },
            "clock": {"is_open": True},
            "open_orders": [],
            "positions": [],
        }
        return release, policy, snapshot

    def run_case(self, values, base_url="https://paper-api.alpaca.markets"):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        root = Path(td.name)
        release, policy, snapshot = values
        self.write(root/"release.json", release)
        if policy is not None:
            self.write(root/"policy.json", policy)
        if snapshot is not None:
            self.write(root/"snapshot.json", snapshot)
        result = PaperOperationsPilot().run(
            final_release_result_path=root/"release.json",
            pilot_policy_path=root/"policy.json",
            local_snapshot_path=root/"snapshot.json",
            account_snapshot_path=root/"account.json",
            preflight_report_path=root/"preflight.json",
            pilot_token_path=root/"token.json",
            result_path=root/"result.json",
            base_url=base_url,
            enable_network=False,
        )
        return result, root

    def test_wait_before_final_release(self):
        release, policy, snapshot = self.data()
        release = {"status":"PASS","state":"WAIT_SCHEDULED_RUNTIME","final_production_package_ready":False,"safe_mode_engaged":False}
        result, _ = self.run_case((release, policy, snapshot))
        self.assertEqual(result["state"], "WAIT_FINAL_PRODUCTION_PACKAGE")

    def test_local_read_only_pilot_ready(self):
        result, root = self.run_case(self.data())
        self.assertEqual(result["state"], "PAPER_OPERATIONS_READ_ONLY_READY")
        self.assertTrue(result["paper_operations_pilot_ready"])
        self.assertTrue((root/"token.json").exists())

    def test_live_endpoint_blocks(self):
        result, _ = self.run_case(self.data(), base_url=LIVE_BASE_URL)
        self.assertEqual(result["status"], "BLOCKED")

    def test_order_submission_policy_blocks(self):
        release, policy, snapshot = self.data()
        policy = dict(policy)
        policy["order_submission_enabled"] = True
        result, _ = self.run_case((release, policy, snapshot))
        self.assertEqual(result["status"], "BLOCKED")

    def test_blocked_account_blocks(self):
        release, policy, snapshot = self.data()
        snapshot = dict(snapshot)
        snapshot["account"] = dict(snapshot["account"])
        snapshot["account"]["account_blocked"] = True
        result, _ = self.run_case((release, policy, snapshot))
        self.assertEqual(result["status"], "BLOCKED")

    def test_missing_snapshot_blocks(self):
        release, policy, _ = self.data()
        result, _ = self.run_case((release, policy, None))
        self.assertEqual(result["status"], "BLOCKED")


if __name__ == "__main__":
    unittest.main()
