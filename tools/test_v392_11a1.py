from __future__ import annotations
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class Tests(unittest.TestCase):
    def _run_verify(self, payload: dict) -> subprocess.CompletedProcess[str]:
        target = ROOT / "release/v392_11a/actual/paper_execution_simulator_result.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(payload), encoding="utf-8")

        return subprocess.run(
            [sys.executable, str(ROOT / "tools/verify_v392_11a.py")],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )

    def base_result(self) -> dict:
        return {
            "stage": "V392.11A",
            "status": "PASS",
            "state": "PAPER_EXECUTION_SIMULATOR_READY",
            "partial_fill_supported": True,
            "slippage_supported": True,
            "broker_adapter_enabled": False,
            "broker_network_enabled": False,
            "paper_submission_enabled": False,
            "live_submission_enabled": False,
            "broker_write_enabled": False,
            "actual_paper_orders_submitted": 0,
            "actual_live_orders_submitted": 0,
            "evaluation": {
                "approved": True,
                "replay_detected": False,
                "failed": [],
                "fill_event": {"fill_event_id": "fill-001"},
                "fill_event_hash": "a" * 64,
                "actual_broker_orders_submitted": 0,
            },
        }

    def test_ready_result_passes(self):
        proc = self._run_verify(self.base_result())
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_replay_blocked_result_passes(self):
        payload = self.base_result()
        payload["state"] = "PAPER_EXECUTION_SIMULATOR_BLOCKED"
        payload["evaluation"] = {
            "approved": False,
            "replay_detected": True,
            "failed": ["execution_not_simulated"],
            "fill_event": {},
            "fill_event_hash": "",
            "actual_broker_orders_submitted": 0,
        }
        proc = self._run_verify(payload)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_missing_broker_count_defaults_to_zero(self):
        payload = self.base_result()
        payload["state"] = "PAPER_EXECUTION_SIMULATOR_BLOCKED"
        payload["evaluation"] = {
            "approved": False,
            "replay_detected": True,
            "failed": ["execution_not_simulated"],
            "fill_event": {},
            "fill_event_hash": "",
        }
        proc = self._run_verify(payload)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_unexplained_block_fails(self):
        payload = self.base_result()
        payload["state"] = "PAPER_EXECUTION_SIMULATOR_BLOCKED"
        payload["evaluation"] = {
            "approved": False,
            "replay_detected": False,
            "failed": [],
            "fill_event": {},
            "fill_event_hash": "",
            "actual_broker_orders_submitted": 0,
        }
        proc = self._run_verify(payload)
        self.assertNotEqual(proc.returncode, 0)

    def test_nonzero_broker_count_fails(self):
        payload = self.base_result()
        payload["evaluation"]["actual_broker_orders_submitted"] = 1
        proc = self._run_verify(payload)
        self.assertNotEqual(proc.returncode, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
