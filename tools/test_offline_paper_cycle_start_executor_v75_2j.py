import copy
import json
import tempfile
import unittest
from pathlib import Path

from tools.offline_paper_cycle_start_executor_v75_2j import (
    CycleStartExecutionError,
    build_execution,
    execution_id,
    main,
    sha256_of,
)


EXECUTED_AT = "2026-07-30T21:00:00+00:00"


def source_fixture():
    checks = [{"check_index": 1, "check": "A", "state": "PASS"}]
    ledger = [{"ledger_index": 1, "event": "A", "state": "AUTHORIZED_NOT_STARTED", "authorization_id": "PCA-A"}]
    token = {
        "authorization_id": "PCA-A",
        "certificate_id": "PRC-A",
        "session_id": "PAPER-A",
        "single_use": True,
        "consumed": False,
        "issued_at": "2026-07-30T20:00:00+00:00",
        "expires_at": "2026-07-30T22:00:00+00:00",
        "ttl_seconds": 7200,
        "token_sha256": "a" * 64,
    }
    source = {
        "status": "PASS",
        "decision": "offline_paper_cycle_start_authorized",
        "authorization_id": "PCA-A",
        "authorization_state": "AUTHORIZED_NOT_STARTED",
        "authorization_scope": "OFFLINE_PAPER_CYCLE_START_ONLY",
        "certificate_id": "PRC-A",
        "activation_id": "OPA-A",
        "session_id": "PAPER-A",
        "champion_candidate_id": "CAND-A",
        "cycle_sequence": 1,
        "cycle_start_authorized": True,
        "cycle_started": False,
        "cycle_start_token": token,
        "cycle_start_token_sha256": sha256_of(token),
        "authorization_checks": checks,
        "authorization_checks_sha256": sha256_of(checks),
        "authorization_ledger": ledger,
        "authorization_ledger_sha256": sha256_of(ledger),
        "authorization_gate": {
            "cycle_start_authorized": True,
            "cycle_start_allowed": False,
            "cycle_started": False,
            "token_consumed": False,
            "paper_orders_allowed": False,
            "live_orders_allowed": False,
            "network_allowed": False,
            "next_version": "75.2J",
        },
        "paper_orders_allowed": False,
        "live_orders_allowed": False,
        "network_allowed": False,
        "broker_connection_allowed": False,
        "orders_submitted": 0,
        "approved_for_live": False,
        "network_used": False,
        "safety_lock": {
            "broker_connected": False,
            "broker_credentials_required": False,
            "external_side_effects_allowed": False,
            "live_orders_enabled": False,
            "live_trading_approval_allowed": False,
            "network_enabled": False,
            "lock_state": "ENFORCED",
        },
        "schema_version": "v75.2i.offline_paper_cycle_start_authorization.1",
        "version": "75.2I",
    }
    source["offline_paper_cycle_start_authorization_sha256"] = sha256_of(source)
    return source


def config_fixture():
    return {
        "consume_single_use_token": True,
        "require_authorized_not_started": True,
        "require_empty_order_queue": True,
        "require_zero_orders": True,
        "require_unmutated_positions": True,
        "generate_signals_on_start": False,
        "generate_orders_on_start": False,
        "simulate_fills_on_start": False,
        "paper_orders_allowed": False,
        "live_orders_allowed": False,
        "network_allowed": False,
        "broker_connection_allowed": False,
        "external_side_effects_allowed": False,
    }


class TestV752J(unittest.TestCase):
    def build(self):
        return build_execution(source_fixture(), config_fixture(), EXECUTED_AT)

    @staticmethod
    def rehash(source):
        source.pop("offline_paper_cycle_start_authorization_sha256", None)
        source["offline_paper_cycle_start_authorization_sha256"] = sha256_of(source)

    def test_pass(self): self.assertEqual(self.build()["status"], "PASS")
    def test_version_schema(self):
        x = self.build()
        self.assertEqual(x["version"], "75.2J")
        self.assertEqual(x["schema_version"], "v75.2j.offline_paper_cycle_start_execution.1")
    def test_execution_state(self): self.assertEqual(self.build()["execution_state"], "OFFLINE_PAPER_CYCLE_ACTIVE")
    def test_cycle_started(self): self.assertTrue(self.build()["cycle_started"])
    def test_cycle_active(self): self.assertTrue(self.build()["execution_gate"]["cycle_active"])
    def test_authorization_consumed(self): self.assertEqual(self.build()["authorization_state"], "CONSUMED")
    def test_token_consumed(self): self.assertTrue(self.build()["consumed_cycle_start_token"]["consumed"])
    def test_signal_generation_blocked(self): self.assertFalse(self.build()["execution_gate"]["signal_generation_allowed"])
    def test_order_generation_blocked(self): self.assertFalse(self.build()["execution_gate"]["order_generation_allowed"])
    def test_fill_simulation_blocked(self): self.assertFalse(self.build()["execution_gate"]["fill_simulation_allowed"])
    def test_paper_orders_blocked(self): self.assertFalse(self.build()["paper_orders_allowed"])
    def test_live_orders_blocked(self): self.assertFalse(self.build()["live_orders_allowed"])
    def test_network_blocked(self): self.assertFalse(self.build()["network_allowed"])
    def test_orders_zero(self): self.assertEqual(self.build()["orders_submitted"], 0)
    def test_cycle_state(self):
        x = self.build()["cycle_state"]
        self.assertEqual(x["state"], "ACTIVE")
        self.assertEqual(x["mode"], "OFFLINE_PAPER")
        self.assertEqual(x["order_queue"], [])
    def test_checks(self): self.assertEqual(len(self.build()["execution_checks"]), 9)
    def test_ledger(self): self.assertEqual(len(self.build()["execution_ledger"]), 5)
    def test_hash(self):
        x = self.build()
        observed = x.pop("offline_paper_cycle_start_execution_sha256")
        self.assertEqual(observed, sha256_of(x))
    def test_deterministic_id(self):
        self.assertEqual(execution_id("A", "B"), execution_id("A", "B"))
    def test_bad_source_integrity(self):
        s = source_fixture(); s["authorization_id"] = "BAD"
        self.assertRaises(CycleStartExecutionError, build_execution, s, config_fixture(), EXECUTED_AT)
    def test_already_started(self):
        s = source_fixture(); s["cycle_started"] = True; self.rehash(s)
        self.assertRaises(CycleStartExecutionError, build_execution, s, config_fixture(), EXECUTED_AT)
    def test_already_consumed(self):
        s = source_fixture(); s["cycle_start_token"]["consumed"] = True
        s["cycle_start_token_sha256"] = sha256_of(s["cycle_start_token"]); self.rehash(s)
        self.assertRaises(CycleStartExecutionError, build_execution, s, config_fixture(), EXECUTED_AT)
    def test_expired_token(self):
        self.assertRaises(
            CycleStartExecutionError,
            build_execution,
            source_fixture(),
            config_fixture(),
            "2026-07-30T23:00:00+00:00",
        )
    def test_before_issuance(self):
        self.assertRaises(
            CycleStartExecutionError,
            build_execution,
            source_fixture(),
            config_fixture(),
            "2026-07-30T19:00:00+00:00",
        )
    def test_unsafe_config(self):
        c = config_fixture(); c["generate_orders_on_start"] = True
        self.assertRaises(CycleStartExecutionError, build_execution, source_fixture(), c, EXECUTED_AT)
    def test_main_success_failure(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            (p/"s.json").write_text(json.dumps(source_fixture()), encoding="utf-8")
            (p/"c.json").write_text(json.dumps(config_fixture()), encoding="utf-8")
            self.assertEqual(main([
                "--input", str(p/"s.json"), "--config", str(p/"c.json"),
                "--output-dir", str(p/"out"), "--executed-at", EXECUTED_AT,
            ]), 0)
            self.assertTrue((p/"out"/"offline_paper_cycle_start_execution_v75_2j.json").is_file())
            self.assertEqual(main([
                "--input", str(p/"missing.json"), "--config", str(p/"c.json"),
                "--output-dir", str(p/"bad"),
            ]), 1)


if __name__ == "__main__":
    unittest.main()
