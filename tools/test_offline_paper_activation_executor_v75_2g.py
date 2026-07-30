import copy
import json
import tempfile
import unittest
from pathlib import Path

from tools.offline_paper_activation_executor_v75_2g import (
    OfflinePaperActivationError,
    execute_activation,
    main,
    sha256_of,
)


def source_fixture():
    token_payload = {
        "authorization_id": "PAA-0123456789ABCDEF",
        "decision_id": "POD-0123456789ABCDEF",
        "session_id": "PAPER-0123456789ABCDEF",
        "scope": "OFFLINE_PAPER_ACTIVATION_ONLY",
        "single_use": True,
        "issued_at": "2026-07-30T20:00:00+00:00",
        "ttl_seconds": 3600,
    }
    checks = [
        {"check_index": 1, "check": "A", "state": "PASS"},
        {"check_index": 2, "check": "B", "state": "ENFORCED"},
        {"check_index": 3, "check": "C", "state": "NOT_EXECUTED"},
    ]
    ledger = [
        {"ledger_index": 1, "event": "A", "state": "PASS", "authorization_id": "PAA-0123456789ABCDEF"},
        {"ledger_index": 2, "event": "B", "state": "ISSUED_NOT_CONSUMED", "authorization_id": "PAA-0123456789ABCDEF"},
    ]
    source = {
        "status": "PASS",
        "decision": "paper_activation_authorization_created",
        "authorization_id": token_payload["authorization_id"],
        "decision_id": token_payload["decision_id"],
        "review_id": "POR-A",
        "preflight_id": "PDP-A",
        "bundle_id": "PDB-A",
        "session_id": token_payload["session_id"],
        "champion_candidate_id": "CAND-A",
        "authorization_scope": token_payload["scope"],
        "authorization_state": "AUTHORIZED_NOT_ACTIVATED",
        "activation_token": {
            "token_sha256": sha256_of(token_payload),
            "single_use": True,
            "consumed": False,
            "issued_at": token_payload["issued_at"],
            "ttl_seconds": token_payload["ttl_seconds"],
        },
        "authorization_checks": checks,
        "authorization_checks_sha256": sha256_of(checks),
        "authorization_ledger": ledger,
        "authorization_ledger_sha256": sha256_of(ledger),
        "activation_gate": {
            "paper_activation_authorized": True,
            "activation_allowed": False,
            "activation_executed": False,
            "token_consumed": False,
            "live_activation_allowed": False,
            "next_version": "75.2G",
        },
        "runtime_policy": {
            "mode": "OFFLINE_PAPER",
            "network_enabled": False,
            "live_orders_enabled": False,
            "broker_credentials_required": False,
            "external_side_effects_allowed": False,
        },
        "safety_lock": {
            "network_enabled": False,
            "live_orders_enabled": False,
            "broker_credentials_required": False,
            "external_side_effects_allowed": False,
            "automatic_activation_allowed": False,
            "lock_state": "ENFORCED",
        },
        "approved_for_live": False,
        "network_used": False,
        "schema_version": "v75.2f.paper_activation_authorization.1",
        "version": "75.2F",
    }
    source["paper_activation_authorization_sha256"] = sha256_of(source)
    return source


def config_fixture():
    return {
        "require_valid_single_use_token": True,
        "require_unexpired_token": True,
        "consume_token_on_success": True,
        "initialize_offline_runtime": True,
        "require_empty_order_queue": True,
        "network_enabled": False,
        "live_orders_enabled": False,
        "broker_credentials_required": False,
        "external_side_effects_allowed": False,
        "live_trading_approval_allowed": False,
    }


EXECUTED_AT = "2026-07-30T20:30:00+00:00"


class TestV752G(unittest.TestCase):
    def build(self):
        return execute_activation(source_fixture(), config_fixture(), EXECUTED_AT)

    def rehash(self, source):
        source.pop("paper_activation_authorization_sha256", None)
        source["paper_activation_authorization_sha256"] = sha256_of(source)
        return source

    def test_pass(self): self.assertEqual(self.build()["status"], "PASS")
    def test_version_schema(self):
        x = self.build()
        self.assertEqual(x["version"], "75.2G")
        self.assertEqual(x["schema_version"], "v75.2g.offline_paper_activation.1")
    def test_active_state(self): self.assertEqual(self.build()["activation_state"], "OFFLINE_PAPER_SESSION_ACTIVE")
    def test_authorization_consumed(self): self.assertEqual(self.build()["authorization_state"], "CONSUMED")
    def test_token_consumed(self): self.assertTrue(self.build()["consumed_activation_token"]["consumed"])
    def test_activation_executed(self): self.assertTrue(self.build()["activation_gate"]["activation_executed"])
    def test_activation_allowed(self): self.assertTrue(self.build()["activation_gate"]["activation_allowed"])
    def test_live_false(self): self.assertFalse(self.build()["approved_for_live"])
    def test_network_false(self): self.assertFalse(self.build()["network_used"])
    def test_orders_zero(self): self.assertEqual(self.build()["orders_submitted"], 0)
    def test_runtime_active(self): self.assertEqual(self.build()["runtime_state"]["state"], "ACTIVE")
    def test_runtime_offline(self): self.assertEqual(self.build()["runtime_state"]["mode"], "OFFLINE_PAPER")
    def test_empty_queue(self): self.assertEqual(self.build()["runtime_state"]["order_queue"], [])
    def test_no_broker(self): self.assertFalse(self.build()["runtime_state"]["broker_connected"])
    def test_checks(self): self.assertEqual(len(self.build()["activation_checks"]), 7)
    def test_ledger(self): self.assertEqual(len(self.build()["activation_ledger"]), 6)
    def test_hash(self):
        x = self.build()
        h = x.pop("offline_paper_activation_sha256")
        self.assertEqual(h, sha256_of(x))
    def test_expired_token(self):
        self.assertRaises(
            OfflinePaperActivationError,
            execute_activation,
            source_fixture(), config_fixture(), "2026-07-30T22:00:01+00:00",
        )
    def test_before_issuance(self):
        self.assertRaises(
            OfflinePaperActivationError,
            execute_activation,
            source_fixture(), config_fixture(), "2026-07-30T19:59:59+00:00",
        )
    def test_already_consumed(self):
        s = source_fixture()
        s["activation_token"]["consumed"] = True
        self.rehash(s)
        self.assertRaises(OfflinePaperActivationError, execute_activation, s, config_fixture(), EXECUTED_AT)
    def test_already_executed(self):
        s = source_fixture()
        s["activation_gate"]["activation_executed"] = True
        self.rehash(s)
        self.assertRaises(OfflinePaperActivationError, execute_activation, s, config_fixture(), EXECUTED_AT)
    def test_bad_source_integrity(self):
        s = source_fixture()
        s["authorization_id"] = "BAD"
        self.assertRaises(OfflinePaperActivationError, execute_activation, s, config_fixture(), EXECUTED_AT)
    def test_bad_token_integrity(self):
        s = source_fixture()
        s["activation_token"]["token_sha256"] = "0" * 64
        self.rehash(s)
        self.assertRaises(OfflinePaperActivationError, execute_activation, s, config_fixture(), EXECUTED_AT)
    def test_unsafe_config(self):
        c = config_fixture()
        c["network_enabled"] = True
        self.assertRaises(OfflinePaperActivationError, execute_activation, source_fixture(), c, EXECUTED_AT)
    def test_main_success_failure(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            (p/"s.json").write_text(json.dumps(source_fixture()), encoding="utf-8")
            (p/"c.json").write_text(json.dumps(config_fixture()), encoding="utf-8")
            self.assertEqual(main([
                "--input", str(p/"s.json"), "--config", str(p/"c.json"),
                "--output-dir", str(p/"out"), "--executed-at", EXECUTED_AT,
            ]), 0)
            self.assertTrue((p/"out"/"offline_paper_activation_record_v75_2g.json").is_file())
            self.assertEqual(main([
                "--input", str(p/"missing.json"), "--config", str(p/"c.json"),
                "--output-dir", str(p/"bad"),
            ]), 1)


if __name__ == "__main__":
    unittest.main()
