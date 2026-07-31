import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.release_candidate_system_acceptance_v76_5 import (
    AcceptanceError,
    command_gate,
    digest,
    validate_config,
    write_outputs,
)


VALID_CONFIG = {
    "acceptance_scope": "RELEASE_CANDIDATE_SYSTEM_ACCEPTANCE",
    "offline_only": True,
    "preserve_repository": True,
    "require_prior_verification_pass": True,
    "require_deterministic_model_output": True,
    "require_zero_trading_side_effects": True,
    "require_tracked_file_immutability": True,
    "require_all_gates_pass": True,
    "network_allowed": False,
    "broker_connection_allowed": False,
    "order_submission_allowed": False,
    "live_trading_allowed": False,
    "live_approval_allowed": False,
    "command_timeout_seconds": 600,
}


class TestReleaseCandidateSystemAcceptanceV765(unittest.TestCase):
    def test_valid_config(self):
        validate_config(dict(VALID_CONFIG))

    def test_live_approval_is_rejected(self):
        config = dict(VALID_CONFIG)
        config["live_approval_allowed"] = True
        with self.assertRaises(AcceptanceError):
            validate_config(config)

    def test_network_is_rejected(self):
        config = dict(VALID_CONFIG)
        config["network_allowed"] = True
        with self.assertRaises(AcceptanceError):
            validate_config(config)

    def test_command_gate_pass(self):
        execution = {
            "status": "PASS",
            "return_code": 0,
            "timed_out": False,
            "duration_seconds": 0.1,
            "stdout": "OK",
            "stderr": "",
            "command": ["python", "test.py"],
        }
        gate = command_gate("TEST", execution, {"safe": True})
        self.assertEqual(gate["status"], "PASS")

    def test_command_gate_fail(self):
        execution = {
            "status": "FAIL",
            "return_code": 1,
            "timed_out": False,
            "duration_seconds": 0.1,
            "stdout": "",
            "stderr": "failed",
            "command": ["python", "test.py"],
        }
        gate = command_gate("TEST", execution)
        self.assertEqual(gate["status"], "FAIL")

    def test_digest_is_deterministic(self):
        value = {"b": 2, "a": 1}
        self.assertEqual(digest(value), digest({"a": 1, "b": 2}))

    def test_write_outputs(self):
        result = {
            "status": "PASS",
            "decision": "release_candidate_system_acceptance_completed",
            "gate_count": 1,
            "passed_gate_count": 1,
            "failed_gate_count": 0,
            "failed_gate_ids": [],
            "tracked_file_immutability_verified": True,
            "changed_tracked_files": [],
            "orders_submitted": 0,
            "network_allowed": False,
            "approved_for_live": False,
            "release_candidate_accepted": True,
            "next_phase": "V76_6_RELEASE_CANDIDATE_EVIDENCE_SEAL",
            "acceptance_sha256": "abc",
            "gates": [{
                "gate_id": "TEST",
                "status": "PASS",
                "conditions": {"ok": True},
            }],
        }
        with tempfile.TemporaryDirectory() as directory:
            outputs = write_outputs(result, Path(directory))
            self.assertEqual(len(outputs), 2)
            summary = json.loads(outputs[1].read_text(encoding="utf-8"))
            self.assertTrue(summary["release_candidate_accepted"])
            self.assertFalse(summary["approved_for_live"])


if __name__ == "__main__":
    unittest.main()
