import json
import tempfile
import unittest
from pathlib import Path

from tools.offline_paper_cycle_runtime_baseline_certificate_v75_2k import (
    BaselineCertificateError,
    build_certificate,
    certificate_id,
    main,
    sha256_of,
)


CERTIFIED_AT = "2026-07-30T21:05:00+00:00"


def source_fixture():
    checks = [{"check_index": 1, "check": "A", "state": "PASS"}]
    ledger = [{"ledger_index": 1, "event": "A", "state": "ACTIVE", "execution_id": "PCS-A"}]
    token = {
        "authorization_id": "PCA-A", "certificate_id": "PRC-A",
        "consumed": True, "consumed_at": "2026-07-30T21:00:00+00:00",
        "consumed_by_execution_id": "PCS-A", "expires_at": "2026-07-30T22:00:00+00:00",
        "issued_at": "2026-07-30T20:00:00+00:00", "session_id": "PAPER-A",
        "single_use": True, "token_sha256": "a" * 64, "ttl_seconds": 7200,
    }
    state = {
        "broker_connected": False, "champion_candidate_id": "CAND-A",
        "cycle_id": "PCS-A", "cycle_sequence": 1, "fill_simulation_started": False,
        "live_orders_enabled": False, "mode": "OFFLINE_PAPER", "network_enabled": False,
        "order_generation_started": False, "order_queue": [], "orders_submitted": 0,
        "positions_mutated": False, "session_id": "PAPER-A",
        "signal_generation_started": False, "started_at": "2026-07-30T21:00:00+00:00",
        "state": "ACTIVE",
    }
    source = {
        "status": "PASS", "decision": "offline_paper_cycle_started",
        "execution_id": "PCS-A", "execution_state": "OFFLINE_PAPER_CYCLE_ACTIVE",
        "authorization_id": "PCA-A", "authorization_state": "CONSUMED",
        "authorization_scope": "OFFLINE_PAPER_CYCLE_START_ONLY",
        "certificate_id": "PRC-A", "activation_id": "OPA-A", "session_id": "PAPER-A",
        "champion_candidate_id": "CAND-A", "cycle_id": "PCS-A", "cycle_sequence": 1,
        "cycle_start_authorized": True, "cycle_started": True,
        "consumed_cycle_start_token": token,
        "consumed_cycle_start_token_sha256": sha256_of(token),
        "cycle_state": state, "cycle_state_sha256": sha256_of(state),
        "execution_checks": checks, "execution_checks_sha256": sha256_of(checks),
        "execution_ledger": ledger, "execution_ledger_sha256": sha256_of(ledger),
        "execution_gate": {
            "cycle_active": True, "signal_generation_allowed": False,
            "order_generation_allowed": False, "fill_simulation_allowed": False,
            "paper_orders_allowed": False, "live_orders_allowed": False,
            "network_allowed": False, "next_version": "75.2K",
        },
        "paper_orders_allowed": False, "live_orders_allowed": False,
        "network_allowed": False, "broker_connection_allowed": False,
        "orders_submitted": 0, "approved_for_live": False, "network_used": False,
        "safety_lock": {
            "broker_connected": False, "broker_credentials_required": False,
            "external_side_effects_allowed": False, "live_orders_enabled": False,
            "live_trading_approval_allowed": False, "network_enabled": False,
            "lock_state": "ENFORCED",
        },
        "schema_version": "v75.2j.offline_paper_cycle_start_execution.1",
        "version": "75.2J",
    }
    source["offline_paper_cycle_start_execution_sha256"] = sha256_of(source)
    return source


def config_fixture():
    return {
        "require_active_cycle": True,
        "require_consumed_start_token": True,
        "require_empty_order_queue": True,
        "require_zero_orders": True,
        "require_unmutated_positions": True,
        "require_signal_generation_not_started": True,
        "require_order_generation_not_started": True,
        "require_fill_simulation_not_started": True,
        "signal_generation_allowed": False,
        "order_generation_allowed": False,
        "fill_simulation_allowed": False,
        "paper_orders_allowed": False,
        "live_orders_allowed": False,
        "network_allowed": False,
        "broker_connection_allowed": False,
        "external_side_effects_allowed": False,
    }


class TestV752K(unittest.TestCase):
    def build(self):
        return build_certificate(source_fixture(), config_fixture(), CERTIFIED_AT)

    @staticmethod
    def rehash(source):
        source.pop("offline_paper_cycle_start_execution_sha256", None)
        source["offline_paper_cycle_start_execution_sha256"] = sha256_of(source)

    def test_pass(self): self.assertEqual(self.build()["status"], "PASS")
    def test_version_schema(self):
        x = self.build()
        self.assertEqual(x["version"], "75.2K")
        self.assertEqual(x["schema_version"], "v75.2k.offline_paper_cycle_runtime_baseline_certificate.1")
    def test_state(self): self.assertEqual(self.build()["certificate_state"], "READY_FOR_SIGNAL_INPUT_PREPARATION")
    def test_cycle_active(self): self.assertTrue(self.build()["cycle_active"])
    def test_baseline_certified(self): self.assertTrue(self.build()["baseline_gate"]["runtime_baseline_certified"])
    def test_signal_input_allowed(self): self.assertTrue(self.build()["baseline_gate"]["signal_input_preparation_allowed"])
    def test_signal_generation_blocked(self): self.assertFalse(self.build()["baseline_gate"]["signal_generation_allowed"])
    def test_order_generation_blocked(self): self.assertFalse(self.build()["baseline_gate"]["order_generation_allowed"])
    def test_fill_blocked(self): self.assertFalse(self.build()["baseline_gate"]["fill_simulation_allowed"])
    def test_paper_orders_blocked(self): self.assertFalse(self.build()["paper_orders_allowed"])
    def test_live_orders_blocked(self): self.assertFalse(self.build()["live_orders_allowed"])
    def test_network_blocked(self): self.assertFalse(self.build()["network_allowed"])
    def test_orders_zero(self): self.assertEqual(self.build()["orders_submitted"], 0)
    def test_snapshot_active(self): self.assertEqual(self.build()["baseline_snapshot"]["state"], "ACTIVE")
    def test_checks(self): self.assertEqual(len(self.build()["baseline_checks"]), 12)
    def test_ledger(self): self.assertEqual(len(self.build()["baseline_ledger"]), 5)
    def test_hash(self):
        x = self.build()
        observed = x.pop("offline_paper_cycle_runtime_baseline_certificate_sha256")
        self.assertEqual(observed, sha256_of(x))
    def test_deterministic_id(self):
        self.assertEqual(certificate_id("A", "B"), certificate_id("A", "B"))
    def test_bad_source_integrity(self):
        s = source_fixture(); s["execution_id"] = "BAD"
        self.assertRaises(BaselineCertificateError, build_certificate, s, config_fixture(), CERTIFIED_AT)
    def test_cycle_not_active(self):
        s = source_fixture(); s["cycle_state"]["state"] = "STOPPED"
        s["cycle_state_sha256"] = sha256_of(s["cycle_state"]); self.rehash(s)
        self.assertRaises(BaselineCertificateError, build_certificate, s, config_fixture(), CERTIFIED_AT)
    def test_signal_already_started(self):
        s = source_fixture(); s["cycle_state"]["signal_generation_started"] = True
        s["cycle_state_sha256"] = sha256_of(s["cycle_state"]); self.rehash(s)
        self.assertRaises(BaselineCertificateError, build_certificate, s, config_fixture(), CERTIFIED_AT)
    def test_nonempty_queue(self):
        s = source_fixture(); s["cycle_state"]["order_queue"] = [{"id": 1}]
        s["cycle_state_sha256"] = sha256_of(s["cycle_state"]); self.rehash(s)
        self.assertRaises(BaselineCertificateError, build_certificate, s, config_fixture(), CERTIFIED_AT)
    def test_positions_mutated(self):
        s = source_fixture(); s["cycle_state"]["positions_mutated"] = True
        s["cycle_state_sha256"] = sha256_of(s["cycle_state"]); self.rehash(s)
        self.assertRaises(BaselineCertificateError, build_certificate, s, config_fixture(), CERTIFIED_AT)
    def test_token_not_consumed(self):
        s = source_fixture(); s["consumed_cycle_start_token"]["consumed"] = False
        s["consumed_cycle_start_token_sha256"] = sha256_of(s["consumed_cycle_start_token"]); self.rehash(s)
        self.assertRaises(BaselineCertificateError, build_certificate, s, config_fixture(), CERTIFIED_AT)
    def test_unsafe_config(self):
        c = config_fixture(); c["signal_generation_allowed"] = True
        self.assertRaises(BaselineCertificateError, build_certificate, source_fixture(), c, CERTIFIED_AT)
    def test_main_success_failure(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            (p/"s.json").write_text(json.dumps(source_fixture()), encoding="utf-8")
            (p/"c.json").write_text(json.dumps(config_fixture()), encoding="utf-8")
            self.assertEqual(main([
                "--input", str(p/"s.json"), "--config", str(p/"c.json"),
                "--output-dir", str(p/"out"), "--certified-at", CERTIFIED_AT,
            ]), 0)
            self.assertTrue((p/"out"/"offline_paper_cycle_runtime_baseline_certificate_v75_2k.json").is_file())
            self.assertEqual(main([
                "--input", str(p/"missing.json"), "--config", str(p/"c.json"),
                "--output-dir", str(p/"bad"),
            ]), 1)


if __name__ == "__main__":
    unittest.main()
