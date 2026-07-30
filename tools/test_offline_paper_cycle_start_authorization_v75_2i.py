import copy
import json
import tempfile
import unittest
from pathlib import Path

from tools.offline_paper_cycle_start_authorization_v75_2i import (
    CycleAuthorizationError,
    authorization_id,
    build_authorization,
    main,
    sha256_of,
)


def source_fixture():
    checks = [{"check_index": 1, "check": "A", "state": "PASS"}]
    ledger = [{"ledger_index": 1, "event": "A", "state": "READY_FOR_OFFLINE_PAPER_CYCLE", "certificate_id": "PRC-A"}]
    snapshot = {
        "activation_id": "OPA-A", "broker_connected": False,
        "champion_candidate_id": "CAND-A", "live_orders_enabled": False,
        "mode": "OFFLINE_PAPER", "network_enabled": False,
        "order_queue_size": 0, "orders_submitted": 0,
        "positions_mutated": False, "session_id": "PAPER-A", "state": "ACTIVE",
    }
    source = {
        "status": "PASS",
        "decision": "offline_paper_runtime_readiness_certified",
        "certificate_id": "PRC-A",
        "certificate_state": "READY_FOR_OFFLINE_PAPER_CYCLE",
        "activation_id": "OPA-A",
        "authorization_id": "PAA-A",
        "session_id": "PAPER-A",
        "champion_candidate_id": "CAND-A",
        "runtime_snapshot": snapshot,
        "runtime_snapshot_sha256": sha256_of(snapshot),
        "readiness_checks": checks,
        "readiness_checks_sha256": sha256_of(checks),
        "readiness_ledger": ledger,
        "readiness_ledger_sha256": sha256_of(ledger),
        "readiness_gate": {
            "offline_paper_runtime_ready": True,
            "offline_paper_cycle_allowed": True,
            "paper_orders_allowed": False,
            "live_orders_allowed": False,
            "network_allowed": False,
            "operator_cycle_start_required": True,
            "next_version": "75.2I",
        },
        "safety_lock": {
            "broker_connected": False,
            "broker_credentials_required": False,
            "external_side_effects_allowed": False,
            "live_orders_enabled": False,
            "live_trading_approval_allowed": False,
            "network_enabled": False,
            "lock_state": "ENFORCED",
        },
        "approved_for_live": False,
        "network_used": False,
        "orders_submitted": 0,
        "schema_version": "v75.2h.offline_paper_runtime_readiness_certificate.1",
        "version": "75.2H",
    }
    source["offline_paper_runtime_readiness_certificate_sha256"] = sha256_of(source)
    return source


def config_fixture():
    return {
        "authorization_token_ttl_seconds": 3600,
        "require_operator_cycle_start": True,
        "require_single_use_token": True,
        "require_zero_orders_before_start": True,
        "require_empty_order_queue": True,
        "require_unmutated_positions": True,
        "paper_orders_allowed": False,
        "live_orders_allowed": False,
        "network_allowed": False,
        "broker_connection_allowed": False,
        "external_side_effects_allowed": False,
    }


ISSUED_AT = "2026-07-30T20:50:00+00:00"


class TestV752I(unittest.TestCase):
    def build(self):
        return build_authorization(source_fixture(), config_fixture(), ISSUED_AT, "token-value")

    def rehash(self, source):
        source.pop("offline_paper_runtime_readiness_certificate_sha256", None)
        source["offline_paper_runtime_readiness_certificate_sha256"] = sha256_of(source)

    def test_pass(self): self.assertEqual(self.build()["status"], "PASS")
    def test_version_schema(self):
        x = self.build()
        self.assertEqual(x["version"], "75.2I")
        self.assertEqual(x["schema_version"], "v75.2i.offline_paper_cycle_start_authorization.1")
    def test_state(self): self.assertEqual(self.build()["authorization_state"], "AUTHORIZED_NOT_STARTED")
    def test_scope(self): self.assertEqual(self.build()["authorization_scope"], "OFFLINE_PAPER_CYCLE_START_ONLY")
    def test_cycle_authorized(self): self.assertTrue(self.build()["cycle_start_authorized"])
    def test_cycle_not_started(self): self.assertFalse(self.build()["cycle_started"])
    def test_cycle_start_not_yet_allowed(self): self.assertFalse(self.build()["authorization_gate"]["cycle_start_allowed"])
    def test_token_single_use(self): self.assertTrue(self.build()["cycle_start_token"]["single_use"])
    def test_token_not_consumed(self): self.assertFalse(self.build()["cycle_start_token"]["consumed"])
    def test_token_ttl(self): self.assertEqual(self.build()["cycle_start_token"]["ttl_seconds"], 3600)
    def test_paper_orders_blocked(self): self.assertFalse(self.build()["paper_orders_allowed"])
    def test_live_orders_blocked(self): self.assertFalse(self.build()["live_orders_allowed"])
    def test_network_blocked(self): self.assertFalse(self.build()["network_allowed"])
    def test_live_false(self): self.assertFalse(self.build()["approved_for_live"])
    def test_network_false(self): self.assertFalse(self.build()["network_used"])
    def test_orders_zero(self): self.assertEqual(self.build()["orders_submitted"], 0)
    def test_checks(self): self.assertEqual(len(self.build()["authorization_checks"]), 9)
    def test_ledger(self): self.assertEqual(len(self.build()["authorization_ledger"]), 5)
    def test_hash(self):
        x = self.build()
        h = x.pop("offline_paper_cycle_start_authorization_sha256")
        self.assertEqual(h, sha256_of(x))
    def test_deterministic_id(self):
        self.assertEqual(authorization_id("A", "B"), authorization_id("A", "B"))
    def test_bad_source_integrity(self):
        s = source_fixture(); s["certificate_id"] = "BAD"
        self.assertRaises(CycleAuthorizationError, build_authorization, s, config_fixture(), ISSUED_AT, "token")
    def test_nonempty_queue(self):
        s = source_fixture(); s["runtime_snapshot"]["order_queue_size"] = 1
        s["runtime_snapshot_sha256"] = sha256_of(s["runtime_snapshot"]); self.rehash(s)
        self.assertRaises(CycleAuthorizationError, build_authorization, s, config_fixture(), ISSUED_AT, "token")
    def test_broker_connected(self):
        s = source_fixture(); s["runtime_snapshot"]["broker_connected"] = True
        s["runtime_snapshot_sha256"] = sha256_of(s["runtime_snapshot"]); self.rehash(s)
        self.assertRaises(CycleAuthorizationError, build_authorization, s, config_fixture(), ISSUED_AT, "token")
    def test_unsafe_config(self):
        c = config_fixture(); c["network_allowed"] = True
        self.assertRaises(CycleAuthorizationError, build_authorization, source_fixture(), c, ISSUED_AT, "token")
    def test_bad_ttl(self):
        c = config_fixture(); c["authorization_token_ttl_seconds"] = 1
        self.assertRaises(CycleAuthorizationError, build_authorization, source_fixture(), c, ISSUED_AT, "token")
    def test_main_success_failure(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            (p/"s.json").write_text(json.dumps(source_fixture()), encoding="utf-8")
            (p/"c.json").write_text(json.dumps(config_fixture()), encoding="utf-8")
            self.assertEqual(main(["--input", str(p/"s.json"), "--config", str(p/"c.json"), "--output-dir", str(p/"out")]), 0)
            self.assertTrue((p/"out"/"offline_paper_cycle_start_authorization_v75_2i.json").is_file())
            self.assertEqual(main(["--input", str(p/"missing.json"), "--config", str(p/"c.json"), "--output-dir", str(p/"bad")]), 1)


if __name__ == "__main__":
    unittest.main()
