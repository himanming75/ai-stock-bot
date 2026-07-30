import copy
import json
import tempfile
import unittest
from pathlib import Path

from tools.offline_paper_runtime_readiness_certificate_v75_2h import (
    RuntimeReadinessError,
    build_certificate,
    certificate_id,
    main,
    sha256_of,
)


def source_fixture():
    checks = [
        {"check_index": 1, "check": "A", "state": "PASS"},
        {"check_index": 2, "check": "B", "state": "CONSUMED"},
    ]
    ledger = [
        {"ledger_index": 1, "event": "A", "state": "PASS", "activation_id": "OPA-A"},
        {"ledger_index": 2, "event": "B", "state": "OFFLINE_PAPER_SESSION_ACTIVE", "activation_id": "OPA-A"},
    ]
    runtime = {
        "mode": "OFFLINE_PAPER",
        "state": "ACTIVE",
        "session_id": "PAPER-A",
        "champion_candidate_id": "CAND-A",
        "initialized_at": "2026-07-30T20:30:00+00:00",
        "network_enabled": False,
        "live_orders_enabled": False,
        "broker_connected": False,
        "external_side_effects_allowed": False,
        "order_queue": [],
        "positions_mutated": False,
        "orders_submitted": 0,
    }
    source = {
        "status": "PASS",
        "decision": "offline_paper_activation_executed",
        "activation_id": "OPA-A",
        "authorization_id": "PAA-A",
        "decision_id": "POD-A",
        "review_id": "POR-A",
        "preflight_id": "PDP-A",
        "bundle_id": "PDB-A",
        "session_id": "PAPER-A",
        "champion_candidate_id": "CAND-A",
        "activation_state": "OFFLINE_PAPER_SESSION_ACTIVE",
        "authorization_state": "CONSUMED",
        "consumed_activation_token": {
            "token_sha256": "1" * 64,
            "single_use": True,
            "consumed": True,
            "consumed_at": "2026-07-30T20:30:00+00:00",
            "authorization_id": "PAA-A",
            "activation_id": "OPA-A",
        },
        "runtime_state": runtime,
        "runtime_state_sha256": sha256_of(runtime),
        "activation_checks": checks,
        "activation_checks_sha256": sha256_of(checks),
        "activation_ledger": ledger,
        "activation_ledger_sha256": sha256_of(ledger),
        "activation_gate": {
            "paper_activation_authorized": True,
            "activation_allowed": True,
            "activation_executed": True,
            "token_consumed": True,
            "live_activation_allowed": False,
            "next_version": "75.2H",
        },
        "safety_lock": {
            "network_enabled": False,
            "live_orders_enabled": False,
            "broker_credentials_required": False,
            "broker_connected": False,
            "external_side_effects_allowed": False,
            "live_activation_allowed": False,
            "lock_state": "ENFORCED",
        },
        "approved_for_live": False,
        "network_used": False,
        "orders_submitted": 0,
        "executed_at": "2026-07-30T20:30:00+00:00",
        "schema_version": "v75.2g.offline_paper_activation.1",
        "version": "75.2G",
    }
    source["offline_paper_activation_sha256"] = sha256_of(source)
    return source


def config_fixture():
    return {
        "require_active_offline_runtime": True,
        "require_consumed_single_use_token": True,
        "require_empty_order_queue": True,
        "require_zero_submitted_orders": True,
        "require_unmutated_positions": True,
        "issue_readiness_certificate": True,
        "network_enabled": False,
        "live_orders_enabled": False,
        "broker_credentials_required": False,
        "broker_connected": False,
        "external_side_effects_allowed": False,
        "live_trading_approval_allowed": False,
    }


CERTIFIED_AT = "2026-07-30T20:40:00+00:00"


class TestV752H(unittest.TestCase):
    def build(self):
        return build_certificate(source_fixture(), config_fixture(), CERTIFIED_AT)

    def rehash(self, source):
        source.pop("offline_paper_activation_sha256", None)
        source["offline_paper_activation_sha256"] = sha256_of(source)
        return source

    def test_pass(self): self.assertEqual(self.build()["status"], "PASS")
    def test_version_schema(self):
        x = self.build()
        self.assertEqual(x["version"], "75.2H")
        self.assertEqual(x["schema_version"], "v75.2h.offline_paper_runtime_readiness_certificate.1")
    def test_state(self): self.assertEqual(self.build()["certificate_state"], "READY_FOR_OFFLINE_PAPER_CYCLE")
    def test_runtime_ready(self): self.assertTrue(self.build()["readiness_gate"]["offline_paper_runtime_ready"])
    def test_cycle_allowed(self): self.assertTrue(self.build()["readiness_gate"]["offline_paper_cycle_allowed"])
    def test_paper_orders_blocked(self): self.assertFalse(self.build()["readiness_gate"]["paper_orders_allowed"])
    def test_live_orders_blocked(self): self.assertFalse(self.build()["readiness_gate"]["live_orders_allowed"])
    def test_network_blocked(self): self.assertFalse(self.build()["readiness_gate"]["network_allowed"])
    def test_live_false(self): self.assertFalse(self.build()["approved_for_live"])
    def test_network_false(self): self.assertFalse(self.build()["network_used"])
    def test_orders_zero(self): self.assertEqual(self.build()["orders_submitted"], 0)
    def test_snapshot(self):
        x = self.build()["runtime_snapshot"]
        self.assertEqual(x["order_queue_size"], 0)
        self.assertFalse(x["broker_connected"])
    def test_checks(self): self.assertEqual(len(self.build()["readiness_checks"]), 9)
    def test_ledger(self): self.assertEqual(len(self.build()["readiness_ledger"]), 5)
    def test_hash(self):
        x = self.build()
        h = x.pop("offline_paper_runtime_readiness_certificate_sha256")
        self.assertEqual(h, sha256_of(x))
    def test_deterministic_id(self):
        self.assertEqual(certificate_id("A", "B", "C"), certificate_id("A", "B", "C"))
    def test_bad_source_integrity(self):
        s = source_fixture()
        s["activation_id"] = "BAD"
        self.assertRaises(RuntimeReadinessError, build_certificate, s, config_fixture(), CERTIFIED_AT)
    def test_nonempty_queue(self):
        s = source_fixture()
        s["runtime_state"]["order_queue"] = [{"symbol": "TEST"}]
        s["runtime_state_sha256"] = sha256_of(s["runtime_state"])
        self.rehash(s)
        self.assertRaises(RuntimeReadinessError, build_certificate, s, config_fixture(), CERTIFIED_AT)
    def test_order_submitted(self):
        s = source_fixture()
        s["runtime_state"]["orders_submitted"] = 1
        s["runtime_state_sha256"] = sha256_of(s["runtime_state"])
        self.rehash(s)
        self.assertRaises(RuntimeReadinessError, build_certificate, s, config_fixture(), CERTIFIED_AT)
    def test_broker_connected(self):
        s = source_fixture()
        s["runtime_state"]["broker_connected"] = True
        s["runtime_state_sha256"] = sha256_of(s["runtime_state"])
        self.rehash(s)
        self.assertRaises(RuntimeReadinessError, build_certificate, s, config_fixture(), CERTIFIED_AT)
    def test_token_not_consumed(self):
        s = source_fixture()
        s["consumed_activation_token"]["consumed"] = False
        self.rehash(s)
        self.assertRaises(RuntimeReadinessError, build_certificate, s, config_fixture(), CERTIFIED_AT)
    def test_unsafe_config(self):
        c = config_fixture()
        c["network_enabled"] = True
        self.assertRaises(RuntimeReadinessError, build_certificate, source_fixture(), c, CERTIFIED_AT)
    def test_main_success_failure(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            (p/"s.json").write_text(json.dumps(source_fixture()), encoding="utf-8")
            (p/"c.json").write_text(json.dumps(config_fixture()), encoding="utf-8")
            self.assertEqual(main([
                "--input", str(p/"s.json"), "--config", str(p/"c.json"),
                "--output-dir", str(p/"out"),
            ]), 0)
            self.assertTrue((p/"out"/"offline_paper_runtime_readiness_certificate_v75_2h.json").is_file())
            self.assertEqual(main([
                "--input", str(p/"missing.json"), "--config", str(p/"c.json"),
                "--output-dir", str(p/"bad"),
            ]), 1)


if __name__ == "__main__":
    unittest.main()
