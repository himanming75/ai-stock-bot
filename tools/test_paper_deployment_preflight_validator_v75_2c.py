import json
import tempfile
import unittest
from pathlib import Path

from tools.paper_deployment_preflight_validator_v75_2c import (
    PaperDeploymentPreflightError,
    SCHEMA_VERSION,
    VERSION,
    build_preflight,
    deterministic_preflight_id,
    main,
    safe_repo_path,
    sha256_of,
)


def bundle():
    runtime = {
        "bundle_id": "PDB-0123456789ABCDEF",
        "session_id": "PAPER-0123456789ABCDEF",
        "deployment_mode": "OFFLINE_PAPER",
        "python_command": "python",
        "environment": {
            "AI_STOCK_BOT_MODE": "OFFLINE_PAPER",
            "AI_STOCK_BOT_NETWORK_ENABLED": "0",
            "AI_STOCK_BOT_LIVE_ORDERS_ENABLED": "0",
            "AI_STOCK_BOT_BROKER_CREDENTIALS_REQUIRED": "0",
        },
        "network_enabled": False,
        "live_orders_enabled": False,
        "broker_credentials_required": False,
        "runtime_state": "DEFINED_NOT_STARTED",
    }
    runtime["runtime_manifest_sha256"] = sha256_of(runtime)
    data = {
        "status": "PASS",
        "decision": "paper_deployment_bundle_created",
        "deployment_state": "READY_FOR_PAPER_DEPLOYMENT_PREFLIGHT",
        "bundle_id": "PDB-0123456789ABCDEF",
        "session_id": "PAPER-0123456789ABCDEF",
        "session_mode": "OFFLINE_PAPER",
        "promotion_scope": "PROVISIONAL_PAPER_ONLY",
        "champion_candidate_id": "CAND-A",
        "runner_up_candidate_id": "CAND-B",
        "file_inventory": [
            {"inventory_index": 1, "path": "a.json", "required": True, "verification_state": "PENDING_PREFLIGHT"},
            {"inventory_index": 2, "path": "nested/b.json", "required": True, "verification_state": "PENDING_PREFLIGHT"},
        ],
        "runtime_manifest": runtime,
        "launch_plan": [
            {"step": 1, "action": "VERIFY_DEPLOYMENT_BUNDLE_INTEGRITY", "state": "PENDING_PREFLIGHT"},
            {"step": 2, "action": "VERIFY_REQUIRED_FILES", "state": "PENDING_PREFLIGHT"},
            {"step": 3, "action": "VERIFY_OFFLINE_RUNTIME_LOCKS", "state": "PENDING_PREFLIGHT"},
            {"step": 4, "action": "REQUEST_OPERATOR_REVIEW", "state": "PENDING_PREFLIGHT"},
            {"step": 5, "action": "HOLD_PAPER_SESSION_ACTIVATION", "state": "BLOCKED_UNTIL_REVIEW"},
        ],
        "deployment_ledger": [
            {"ledger_index": 1, "event": "A"},
            {"ledger_index": 2, "event": "B"},
        ],
        "safety_lock": {
            "network_enabled": False,
            "live_orders_enabled": False,
            "broker_credentials_required": False,
            "external_side_effects_allowed": False,
            "lock_state": "ENFORCED",
        },
        "activation_gate": {
            "activation_allowed": False,
            "operator_review_required": True,
            "preflight_required": True,
            "next_version": "75.2C",
        },
        "approved_for_live": False,
        "network_used": False,
        "schema_version": "v75.2b.paper_deployment_bundle.1",
        "version": "75.2B",
    }
    data["paper_deployment_bundle_sha256"] = sha256_of(data)
    return data


def config():
    return {
        "repository_root_required": True,
        "verify_required_files": True,
        "operator_review_required": True,
        "activation_allowed": False,
        "network_enabled": False,
        "forbidden_environment_variables": ["BROKER_API_KEY", "BROKER_API_SECRET", "LIVE_TRADING_ENABLED"],
    }


class TestV752C(unittest.TestCase):
    def setup_root(self, root: Path):
        (root / "nested").mkdir()
        (root / "a.json").write_text("{}", encoding="utf-8")
        (root / "nested" / "b.json").write_text("{}", encoding="utf-8")

    def build(self):
        td = tempfile.TemporaryDirectory()
        root = Path(td.name)
        self.setup_root(root)
        result = build_preflight(bundle(), config(), root, "2026-07-30T00:00:00+00:00")
        td.cleanup()
        return result

    def test_version_schema(self):
        self.assertEqual(VERSION, "75.2C")
        self.assertEqual(SCHEMA_VERSION, "v75.2c.paper_deployment_preflight.1")

    def test_pass(self):
        self.assertEqual(self.build()["status"], "PASS")

    def test_state(self):
        self.assertEqual(self.build()["preflight_state"], "READY_FOR_OPERATOR_REVIEW")

    def test_activation_blocked(self):
        self.assertFalse(self.build()["activation_gate"]["activation_allowed"])

    def test_live_false(self):
        self.assertFalse(self.build()["approved_for_live"])

    def test_network_false(self):
        self.assertFalse(self.build()["network_used"])

    def test_operator_review_pending(self):
        self.assertEqual(self.build()["operator_review"]["state"], "PENDING")

    def test_verified_files(self):
        result = self.build()
        self.assertEqual(len(result["verified_files"]), 2)
        self.assertTrue(all(x["exists"] for x in result["verified_files"]))

    def test_hash(self):
        result = self.build()
        observed = result["paper_deployment_preflight_sha256"]
        copied = dict(result)
        copied.pop("paper_deployment_preflight_sha256")
        self.assertEqual(observed, sha256_of(copied))

    def test_deterministic_id(self):
        a = deterministic_preflight_id("PDB-A", "b" * 64, "2026")
        b = deterministic_preflight_id("PDB-A", "b" * 64, "2026")
        self.assertEqual(a, b)
        self.assertTrue(a.startswith("PDP-"))

    def test_safe_paths(self):
        self.assertTrue(safe_repo_path("release/a.json"))
        self.assertFalse(safe_repo_path("../a.json"))
        self.assertFalse(safe_repo_path("C:/a.json"))
        self.assertFalse(safe_repo_path("/a.json"))

    def test_bad_bundle_integrity(self):
        bad = bundle(); bad["paper_deployment_bundle_sha256"] = "0" * 64
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(PaperDeploymentPreflightError):
                build_preflight(bad, config(), Path(td))

    def test_bad_runtime_lock(self):
        bad = bundle(); bad["runtime_manifest"]["network_enabled"] = True
        bad["paper_deployment_bundle_sha256"] = sha256_of({k:v for k,v in bad.items() if k != "paper_deployment_bundle_sha256"})
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(PaperDeploymentPreflightError):
                build_preflight(bad, config(), Path(td))

    def test_bad_launch_order(self):
        bad = bundle(); bad["launch_plan"].reverse()
        bad["paper_deployment_bundle_sha256"] = sha256_of({k:v for k,v in bad.items() if k != "paper_deployment_bundle_sha256"})
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(PaperDeploymentPreflightError):
                build_preflight(bad, config(), Path(td))

    def test_unsafe_inventory_path(self):
        bad = bundle(); bad["file_inventory"][0]["path"] = "../secret"
        bad["paper_deployment_bundle_sha256"] = sha256_of({k:v for k,v in bad.items() if k != "paper_deployment_bundle_sha256"})
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(PaperDeploymentPreflightError):
                build_preflight(bad, config(), Path(td))

    def test_missing_required_file(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "nested").mkdir()
            (root / "a.json").write_text("{}", encoding="utf-8")
            with self.assertRaises(PaperDeploymentPreflightError):
                build_preflight(bundle(), config(), root)

    def test_bad_config(self):
        bad = config(); bad["activation_allowed"] = True
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); self.setup_root(root)
            with self.assertRaises(PaperDeploymentPreflightError):
                build_preflight(bundle(), bad, root)

    def test_main_success_failure(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.setup_root(root)
            inp = root / "bundle.json"
            cfg = root / "config.json"
            out = root / "out"
            inp.write_text(json.dumps(bundle()), encoding="utf-8")
            cfg.write_text(json.dumps(config()), encoding="utf-8")
            self.assertEqual(main(["--input", str(inp), "--config", str(cfg), "--repository-root", str(root), "--output-dir", str(out)]), 0)
            for name in [
                "paper_deployment_preflight_v75_2c.json",
                "paper_deployment_preflight_v75_2c.sha256",
                "paper_deployment_preflight_checklist_v75_2c.json",
                "paper_deployment_preflight_ledger_v75_2c.json",
            ]:
                self.assertTrue((out / name).exists())
            self.assertEqual(main(["--input", str(root / "missing.json"), "--config", str(cfg), "--repository-root", str(root), "--output-dir", str(root / "bad")]), 1)


if __name__ == "__main__":
    unittest.main()
