import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from tools.paper_deployment_bundle_v75_2b import (
    PaperDeploymentBundleError,
    SCHEMA_VERSION,
    VERSION,
    build_bundle,
    canonical_json,
    deterministic_bundle_id,
    main,
    sha256_of,
)


def source():
    data = {
        "status": "PASS",
        "decision": "paper_session_bootstrap_created",
        "bootstrap_state": "READY_FOR_PAPER_DEPLOYMENT_BUNDLE",
        "session_id": "PAPER-0123456789ABCDEF",
        "session_mode": "OFFLINE_PAPER",
        "promotion_scope": "PROVISIONAL_PAPER_ONLY",
        "champion_candidate_id": "CAND-A",
        "runner_up_candidate_id": "CAND-B",
        "strategy_binding": {
            "candidate_id": "CAND-A",
            "binding_state": "ATTACHED_NOT_ACTIVATED",
        },
        "account_state": {"account_state": "INITIALIZED"},
        "health_check": {"health_state": "READY"},
        "session_ledger": [],
        "safety_lock": {
            "network_enabled": False,
            "live_orders_enabled": False,
            "broker_credentials_required": False,
            "external_side_effects_allowed": False,
            "lock_state": "ENFORCED",
        },
        "activation_gate": {
            "activation_allowed": False,
            "requires_deployment_bundle": True,
            "requires_operator_review": True,
            "next_version": "75.2B",
        },
        "created_at": "2026-07-30T00:00:00+00:00",
        "approved_for_live": False,
        "network_used": False,
        "source_rollback_manifest_sha256": "a" * 64,
        "schema_version": "v75.2a.paper_session_bootstrap.1",
        "version": "75.2A",
        "session_ledger_sha256": "b" * 64,
    }
    data["paper_session_bootstrap_sha256"] = sha256_of(data)
    return data


def config():
    return {
        "deployment_mode": "OFFLINE_PAPER",
        "python_command": "python",
        "network_enabled": False,
        "live_orders_enabled": False,
        "broker_credentials_required": False,
        "operator_review_required": True,
        "required_files": [
            "release/v75_2a/session/paper_session_bootstrap_v75_2a.json",
            "release/v75_2a/session/paper_account_state_v75_2a.json",
            "release/v75_2a/session/paper_session_health_v75_2a.json",
            "release/v75_1c/rollback/rollback_manifest_v75_1c.json",
        ],
    }


class TestV752B(unittest.TestCase):
    def build(self):
        return build_bundle(
            source(), config(), created_at="2026-07-30T00:00:00+00:00"
        )

    def test_version_and_schema(self):
        self.assertEqual(VERSION, "75.2B")
        self.assertEqual(SCHEMA_VERSION, "v75.2b.paper_deployment_bundle.1")

    def test_pass_and_decision(self):
        result = self.build()
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["decision"], "paper_deployment_bundle_created")

    def test_deployment_state(self):
        self.assertEqual(
            self.build()["deployment_state"],
            "READY_FOR_PAPER_DEPLOYMENT_PREFLIGHT",
        )

    def test_bundle_id_is_deterministic(self):
        a = deterministic_bundle_id("PAPER-A", "b" * 64, "2026-01-01")
        b = deterministic_bundle_id("PAPER-A", "b" * 64, "2026-01-01")
        self.assertEqual(a, b)
        self.assertTrue(a.startswith("PDB-"))

    def test_file_inventory(self):
        result = self.build()
        self.assertEqual(len(result["file_inventory"]), 4)
        self.assertTrue(all(x["required"] for x in result["file_inventory"]))

    def test_runtime_is_offline(self):
        runtime = self.build()["runtime_manifest"]
        self.assertEqual(runtime["deployment_mode"], "OFFLINE_PAPER")
        self.assertFalse(runtime["network_enabled"])
        self.assertFalse(runtime["live_orders_enabled"])

    def test_activation_is_blocked(self):
        result = self.build()
        self.assertFalse(result["activation_gate"]["activation_allowed"])
        self.assertEqual(result["activation_gate"]["next_version"], "75.2C")

    def test_safety_lock(self):
        self.assertEqual(self.build()["safety_lock"]["lock_state"], "ENFORCED")

    def test_ledger(self):
        self.assertEqual(len(self.build()["deployment_ledger"]), 5)

    def test_hash(self):
        result = self.build()
        copied = dict(result)
        observed = copied.pop("paper_deployment_bundle_sha256")
        expected = hashlib.sha256(
            canonical_json(copied).encode("utf-8")
        ).hexdigest()
        self.assertEqual(observed, expected)

    def test_bad_source_integrity(self):
        bad = source()
        bad["paper_session_bootstrap_sha256"] = "0" * 64
        with self.assertRaises(PaperDeploymentBundleError):
            build_bundle(bad, config())

    def test_bad_source_state(self):
        bad = source()
        bad["bootstrap_state"] = "BAD"
        with self.assertRaises(PaperDeploymentBundleError):
            build_bundle(bad, config())

    def test_bad_network_config(self):
        bad = config()
        bad["network_enabled"] = True
        with self.assertRaises(PaperDeploymentBundleError):
            build_bundle(source(), bad)

    def test_unsafe_required_path(self):
        bad = config()
        bad["required_files"] = ["../secret.txt"]
        with self.assertRaises(PaperDeploymentBundleError):
            build_bundle(source(), bad)

    def test_main_success_and_failure(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            inp = root / "input.json"
            cfg = root / "config.json"
            out = root / "out"
            inp.write_text(json.dumps(source()), encoding="utf-8")
            cfg.write_text(json.dumps(config()), encoding="utf-8")
            self.assertEqual(main([
                "--input", str(inp),
                "--config", str(cfg),
                "--output-dir", str(out),
            ]), 0)
            expected = [
                "paper_deployment_bundle_v75_2b.json",
                "paper_deployment_bundle_v75_2b.sha256",
                "paper_deployment_file_inventory_v75_2b.json",
                "paper_runtime_manifest_v75_2b.json",
                "paper_deployment_launch_plan_v75_2b.json",
                "paper_deployment_ledger_v75_2b.json",
            ]
            for filename in expected:
                self.assertTrue((out / filename).exists())

            self.assertEqual(main([
                "--input", str(root / "missing.json"),
                "--config", str(root / "missing-config.json"),
                "--output-dir", str(root / "bad-out"),
            ]), 1)


if __name__ == "__main__":
    unittest.main()
