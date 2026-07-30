import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from tools.paper_session_bootstrap_v75_2a import (
    PaperSessionBootstrapError,
    SCHEMA_VERSION,
    VERSION,
    build_bootstrap,
    canonical_json,
    deterministic_session_id,
    main,
    sha256_of,
)


def source():
    data = {
        "status": "PASS",
        "decision": "rollback_manifest_created",
        "rollback_state": "READY_FOR_PAPER_SESSION_BOOTSTRAP",
        "promotion_scope": "PROVISIONAL_PAPER_ONLY",
        "champion_candidate_id": "CAND-A",
        "runner_up_candidate_id": "CAND-B",
        "rollback_policy": {"mode": "MANUAL_OPERATOR_TRIGGERED"},
        "trigger_conditions": ["OPERATOR_REQUEST"],
        "rollback_sequence": [],
        "rollback_ledger": [],
        "recovery_verification": {
            "verification_state": "PENDING_EXECUTION"
        },
        "paper_session_reference": {
            "bootstrap_version": "75.2A",
            "bootstrap_allowed": True,
            "activation_allowed": False,
        },
        "requires_operator_review": True,
        "requires_paper_session_bootstrap": True,
        "created_at": "2026-07-30T00:00:00+00:00",
        "approved_for_live": False,
        "network_used": False,
        "source_promotion_manifest_sha256": "a" * 64,
        "schema_version": "v75.1c.rollback_manifest.1",
        "version": "75.1C",
        "rollback_sequence_sha256": "b" * 64,
        "rollback_ledger_sha256": "c" * 64,
    }
    data["rollback_manifest_sha256"] = sha256_of(data)
    return data


def config():
    return {
        "starting_cash": 100000,
        "currency": "USD",
        "max_positions": 10,
        "session_mode": "OFFLINE_PAPER",
        "network_enabled": False,
        "live_orders_enabled": False,
    }


class TestV752A(unittest.TestCase):
    def build(self):
        return build_bootstrap(
            source(),
            config(),
            created_at="2026-07-30T00:00:00+00:00",
        )

    def test_version(self):
        self.assertEqual(VERSION, "75.2A")

    def test_schema(self):
        self.assertEqual(
            SCHEMA_VERSION,
            "v75.2a.paper_session_bootstrap.1",
        )

    def test_pass(self):
        self.assertEqual(self.build()["status"], "PASS")

    def test_decision(self):
        self.assertEqual(
            self.build()["decision"],
            "paper_session_bootstrap_created",
        )

    def test_state(self):
        self.assertEqual(
            self.build()["bootstrap_state"],
            "READY_FOR_PAPER_DEPLOYMENT_BUNDLE",
        )

    def test_session_id(self):
        sid = self.build()["session_id"]
        self.assertTrue(sid.startswith("PAPER-"))

    def test_deterministic_session_id(self):
        a = deterministic_session_id("A", "b" * 64, "2026-01-01")
        b = deterministic_session_id("A", "b" * 64, "2026-01-01")
        self.assertEqual(a, b)

    def test_champion(self):
        self.assertEqual(
            self.build()["champion_candidate_id"], "CAND-A"
        )

    def test_runner(self):
        self.assertEqual(
            self.build()["runner_up_candidate_id"], "CAND-B"
        )

    def test_starting_cash(self):
        self.assertEqual(
            self.build()["account_state"]["starting_cash"], 100000.0
        )

    def test_empty_positions(self):
        self.assertEqual(
            self.build()["account_state"]["positions"], []
        )

    def test_empty_orders(self):
        result = self.build()["account_state"]
        self.assertEqual(result["open_orders"], [])
        self.assertEqual(result["closed_orders"], [])

    def test_health_ready(self):
        self.assertEqual(
            self.build()["health_check"]["health_state"], "READY"
        )

    def test_not_activated(self):
        self.assertEqual(
            self.build()["health_check"]["paper_activation_state"],
            "NOT_ACTIVATED",
        )

    def test_safety_lock(self):
        self.assertEqual(
            self.build()["safety_lock"]["lock_state"], "ENFORCED"
        )

    def test_live_false(self):
        self.assertFalse(self.build()["approved_for_live"])

    def test_network_false(self):
        self.assertFalse(self.build()["network_used"])

    def test_activation_false(self):
        self.assertFalse(
            self.build()["activation_gate"]["activation_allowed"]
        )

    def test_ledger(self):
        self.assertEqual(len(self.build()["session_ledger"]), 5)

    def test_hash(self):
        result = self.build()
        copied = dict(result)
        observed = copied.pop("paper_session_bootstrap_sha256")
        expected = hashlib.sha256(
            canonical_json(copied).encode("utf-8")
        ).hexdigest()
        self.assertEqual(observed, expected)

    def test_deterministic(self):
        self.assertEqual(self.build(), self.build())

    def test_bad_status(self):
        bad = source()
        bad["status"] = "FAIL"
        with self.assertRaises(PaperSessionBootstrapError):
            build_bootstrap(bad, config())

    def test_bad_schema(self):
        bad = source()
        bad["schema_version"] = "bad"
        with self.assertRaises(PaperSessionBootstrapError):
            build_bootstrap(bad, config())

    def test_bad_state(self):
        bad = source()
        bad["rollback_state"] = "BAD"
        with self.assertRaises(PaperSessionBootstrapError):
            build_bootstrap(bad, config())

    def test_bad_integrity(self):
        bad = source()
        bad["rollback_manifest_sha256"] = "0" * 64
        with self.assertRaises(PaperSessionBootstrapError):
            build_bootstrap(bad, config())

    def test_bad_cash(self):
        bad = config()
        bad["starting_cash"] = 0
        with self.assertRaises(PaperSessionBootstrapError):
            build_bootstrap(source(), bad)

    def test_bad_mode(self):
        bad = config()
        bad["session_mode"] = "LIVE"
        with self.assertRaises(PaperSessionBootstrapError):
            build_bootstrap(source(), bad)

    def test_bad_network(self):
        bad = config()
        bad["network_enabled"] = True
        with self.assertRaises(PaperSessionBootstrapError):
            build_bootstrap(source(), bad)

    def test_main_success(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            inp = root / "input.json"
            cfg = root / "config.json"
            out = root / "out"
            inp.write_text(json.dumps(source()), encoding="utf-8")
            cfg.write_text(json.dumps(config()), encoding="utf-8")
            code = main([
                "--input", str(inp),
                "--config", str(cfg),
                "--output-dir", str(out),
            ])
            self.assertEqual(code, 0)
            self.assertTrue(
                (out / "paper_session_bootstrap_v75_2a.json").exists()
            )
            self.assertTrue(
                (out / "paper_account_state_v75_2a.json").exists()
            )
            self.assertTrue(
                (out / "paper_session_health_v75_2a.json").exists()
            )
            self.assertTrue(
                (out / "paper_session_ledger_v75_2a.json").exists()
            )
            self.assertTrue(
                (out / "paper_session_bootstrap_v75_2a.sha256").exists()
            )

    def test_main_failure(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            code = main([
                "--input", str(root / "missing.json"),
                "--config", str(root / "missing-config.json"),
                "--output-dir", str(root / "out"),
            ])
            self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
