from __future__ import annotations
import json, tempfile, unittest
from pathlib import Path
from autonomous_paper_runtime.alpaca_paper_integration_bundle import (
    AlpacaPaperIntegrationBundle,
    LIVE_BASE_URL,
)

class Tests(unittest.TestCase):
    def write(self, path, payload):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")

    def data(self):
        engine = {
            "status": "PASS",
            "state": "AUTONOMOUS_ENGINE_READY",
            "autonomous_engine_ready": True,
            "engine_id": "engine-001",
            "runtime_cycle_id": "runtime-001",
            "safe_mode_engaged": False,
        }
        token = {
            "engine_id": "engine-001",
            "runtime_cycle_id": "runtime-001",
            "autonomous_engine_ready": True,
        }
        candidate = {
            "engine_id": "engine-001",
            "symbol": "SPY",
            "side": "BUY",
            "quantity": 1,
            "order_type": "MARKET",
            "time_in_force": "DAY",
        }
        broker = {
            "account": {"status": "ACTIVE", "trading_blocked": False},
            "clock": {"is_open": True},
            "open_orders": [],
            "positions": [],
        }
        reconciliation = {
            "client_order_id": "engine-001",
            "expected_open_order_count": 0,
            "expected_position_count": 0,
        }
        return engine, token, candidate, broker, reconciliation

    def run_case(self, values, base_url="https://paper-api.alpaca.markets"):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        root = Path(td.name)
        names = ["engine", "token", "candidate", "broker", "reconciliation"]
        paths = {name: root/f"{name}.json" for name in names}
        for name, value in zip(names, values):
            if value is not None:
                self.write(paths[name], value)
        return AlpacaPaperIntegrationBundle().run(
            engine_result_path=paths["engine"],
            engine_token_path=paths["token"],
            order_candidate_path=paths["candidate"],
            local_broker_snapshot_path=paths["broker"],
            reconciliation_snapshot_path=paths["reconciliation"],
            read_result_path=root/"read.json",
            submission_result_path=root/"submission.json",
            reconciliation_result_path=root/"recon.json",
            final_result_path=root/"result.json",
            base_url=base_url,
            enable_network=False,
            enable_submission=False,
            approval_phrase="",
        )

    def test_wait_before_engine_ready(self):
        values = list(self.data())
        values[0] = {
            "status": "PASS",
            "state": "WAIT_RUNTIME_CONTROL",
            "autonomous_engine_ready": False,
            "safe_mode_engaged": False,
        }
        result = self.run_case(values)
        self.assertEqual(result["state"], "WAIT_AUTONOMOUS_ENGINE")

    def test_local_paper_read_and_reconciliation_ready(self):
        result = self.run_case(self.data())
        self.assertEqual(
            result["state"],
            "PAPER_INTEGRATION_READY_SUBMISSION_DISABLED",
        )
        self.assertTrue(result["broker_read_verified"])
        self.assertTrue(result["reconciliation_verified"])

    def test_live_endpoint_blocks(self):
        result = self.run_case(self.data(), base_url=LIVE_BASE_URL)
        self.assertEqual(result["status"], "BLOCKED")

    def test_market_closed_blocks(self):
        values = list(self.data())
        values[3] = dict(values[3])
        values[3]["clock"] = {"is_open": False}
        result = self.run_case(values)
        self.assertEqual(result["status"], "BLOCKED")

    def test_open_order_reconciliation(self):
        values = list(self.data())
        values[3] = dict(values[3])
        values[3]["open_orders"] = [{"id": "open-1"}]
        values[4] = dict(values[4])
        values[4]["expected_open_order_count"] = 1
        result = self.run_case(values)
        self.assertEqual(
            result["state"],
            "PAPER_INTEGRATION_READY_SUBMISSION_DISABLED",
        )

    def test_reconciliation_mismatch_blocks(self):
        values = list(self.data())
        values[4] = dict(values[4])
        values[4]["expected_position_count"] = 1
        result = self.run_case(values)
        self.assertEqual(result["status"], "BLOCKED")

if __name__ == "__main__":
    unittest.main()
