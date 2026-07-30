import copy
import json
import tempfile
import unittest
from pathlib import Path

from tools.offline_paper_fill_simulation_execution_verifier_v75_2ab import *


def cfg():
    return {
        "verification_scope": "OFFLINE_PAPER_FILL_SIMULATION_EXECUTION_VERIFICATION_ONLY",
        "require_execution_integrity": True,
        "require_fill_objects_integrity": True,
        "require_each_fill_object_integrity": True,
        "require_consumed_token_integrity": True,
        "require_execution_checks_integrity": True,
        "require_execution_ledger_integrity": True,
        "require_deterministic_fill_ids": True,
        "require_zero_account_mutations": True,
        "position_update_allowed": False,
        "cash_update_allowed": False,
        "portfolio_update_allowed": False,
        "external_order_submission_allowed": False,
        "broker_routing_allowed": False,
        "paper_broker_allowed": False,
        "live_orders_allowed": False,
        "network_allowed": False,
        "broker_connection_allowed": False,
        "external_side_effects_allowed": False,
    }


def execution():
    executed_at = "2026-07-30T22:25:00+00:00"
    authorization_id = "FSA-A"
    token_sha = "a" * 64
    execution_id = "FSE-" + __import__("hashlib").sha256(
        f"{authorization_id}|{token_sha}|{executed_at}|75.2AA".encode()
    ).hexdigest()[:16].upper()
    fill = {
        "fill_index": 1, "fill_id": "FILL-" + __import__("hashlib").sha256(
            f"{authorization_id}|PORD-AAAAAAAAAAAAAAAA|OSUB-AAAAAAAAAAAAAAAA|75.2AA".encode()
        ).hexdigest()[:16].upper(),
        "fill_simulation_execution_id": execution_id,
        "fill_simulation_authorization_id": authorization_id,
        "offline_submission_id": "OSUB-AAAAAAAAAAAAAAAA",
        "paper_order_id": "PORD-AAAAAAAAAAAAAAAA",
        "order_intent_id": "INT-A", "authorization_id": "OSA-A",
        "symbol": "SPY", "side": "BUY", "filled_quantity": 2,
        "fill_price": 633.5, "notional_value": 1267.0, "currency": "USD",
        "fill_type": "OFFLINE_PAPER_REFERENCE_FILL",
        "fill_state": "FILLED_OFFLINE_OBJECT_ONLY",
        "fill_price_policy": "REFERENCE_PRICE_ONLY",
        "fill_quantity_policy": "FULL_QUANTITY_ONLY",
        "simulated_at": executed_at, "offline_only": True,
        "broker_connected": False, "broker_routed": False,
        "external_submission": False, "network_used": False,
        "position_updated": False, "cash_updated": False,
        "portfolio_updated": False, "approved_for_live": False,
    }
    fill["fill_object_sha256"] = sha256_of(fill)
    token = {
        "fill_simulation_authorization_id": authorization_id,
        "submission_validation_id": "OSV-A", "issued_at": "2026-07-30T22:20:00+00:00",
        "expires_at": "2026-07-30T22:35:00+00:00", "nonce": "b" * 32,
        "scope": "OFFLINE_PAPER_FILL_SIMULATION_EXECUTION_ONLY",
        "authorized_offline_submission_ids": ["OSUB-AAAAAAAAAAAAAAAA"],
        "authorized_paper_order_ids": ["PORD-AAAAAAAAAAAAAAAA"],
        "fill_price_policy": "REFERENCE_PRICE_ONLY",
        "fill_quantity_policy": "FULL_QUANTITY_ONLY", "token_sha256": token_sha,
        "single_use": True, "consumed": True, "consumed_at": executed_at,
        "token_state": "CONSUMED_BY_OFFLINE_FILL_SIMULATION",
        "consumed_by_execution_id": execution_id,
    }
    checks = [{"check_index": i, "check": f"CHECK_{i}", "state": "PASS"} for i in range(1, 13)]
    ledger = [{"ledger_index": i, "event": f"EVENT_{i}", "state": "PASS", "execution_id": execution_id} for i in range(1, 7)]
    source = {
        "status": "PASS", "decision": "offline_paper_fill_simulation_executed_object_only",
        "fill_simulation_execution_id": execution_id,
        "fill_simulation_authorization_id": authorization_id,
        "execution_scope": "OFFLINE_PAPER_FILL_OBJECT_CREATION_ONLY",
        "execution_state": "EXECUTED_FILL_OBJECT_ONLY",
        "fill_simulation_authorized": True, "fill_simulation_executed": True,
        "fill_object_creation_executed": True, "fill_object_count": 1,
        "fill_objects": [fill], "fill_objects_sha256": sha256_of([fill]),
        "consumed_authorization_token": token,
        "consumed_authorization_token_sha256": sha256_of(token),
        "execution_checks": checks, "execution_checks_sha256": sha256_of(checks),
        "execution_ledger": ledger, "execution_ledger_sha256": sha256_of(ledger),
        "execution_gate": {
            "fill_object_creation_completed": True, "position_update_allowed": False,
            "cash_update_allowed": False, "portfolio_update_allowed": False,
            "external_order_submission_allowed": False, "broker_routing_allowed": False,
            "paper_broker_allowed": False, "live_orders_allowed": False,
            "network_allowed": False, "next_version": "75.2AB",
        },
        "source_fill_simulation_authorization_sha256": "c" * 64,
        "source_authorized_targets_sha256": "d" * 64,
        "source_authorization_token_sha256": token_sha,
        "submission_validation_id": "OSV-A", "submission_execution_id": "OSE-A",
        "authorization_id": "OSA-A", "validation_id": "OOV-A",
        "execution_id": "OGE-A", "authorization_source_id": "OGA-A",
        "session_id": "PAPER-A", "cycle_id": "PCS-A", "cycle_sequence": 1,
        "champion_candidate_id": "CAND-A", "executed_at": executed_at,
        "fill_objects_created": 1, "fills_created": 1, "positions_updated": 0,
        "cash_updates_created": 0, "portfolio_updates_created": 0,
        "external_orders_submitted": 0, "broker_routes_created": 0,
        "position_update_allowed": False, "cash_update_allowed": False,
        "portfolio_update_allowed": False, "external_order_submission_allowed": False,
        "broker_routing_allowed": False, "paper_broker_allowed": False,
        "live_orders_allowed": False, "network_allowed": False,
        "broker_connection_allowed": False, "approved_for_live": False,
        "network_used": False,
        "safety_lock": {"lock_state": "ENFORCED", "network_enabled": False,
                        "broker_connected": False, "live_orders_enabled": False},
        "schema_version": "v75.2aa.offline_paper_fill_simulation_execution.1",
        "version": "75.2AA",
    }
    source["offline_paper_fill_simulation_execution_sha256"] = sha256_of(source)
    return source


def rehash_fill(fill):
    fill.pop("fill_object_sha256", None)
    fill["fill_object_sha256"] = sha256_of(fill)


def rehash_execution(source):
    source["fill_objects_sha256"] = sha256_of(source["fill_objects"])
    source.pop("offline_paper_fill_simulation_execution_sha256", None)
    source["offline_paper_fill_simulation_execution_sha256"] = sha256_of(source)


class TestV752AB(unittest.TestCase):
    def build(self):
        return build_verification(execution(), cfg())

    def test_pass(self):
        self.assertEqual(self.build()["status"], "PASS")

    def test_state(self):
        self.assertEqual(self.build()["verification_state"], "VERIFIED_OFFLINE_FILL_OBJECT_EXECUTION")

    def test_fill_count(self):
        self.assertEqual(self.build()["verified_fill_object_count"], 1)

    def test_verified_fill(self):
        self.assertEqual(self.build()["verified_fill_objects"][0]["verification_state"], "VERIFIED_OFFLINE_FILL_OBJECT_ONLY")

    def test_output_hash(self):
        out = self.build()
        observed = out.pop("offline_paper_fill_simulation_execution_verification_sha256")
        self.assertEqual(observed, sha256_of(out))

    def test_verified_fills_hash(self):
        out = self.build()
        self.assertEqual(out["verified_fill_objects_sha256"], sha256_of(out["verified_fill_objects"]))

    def test_no_account_mutation(self):
        out = self.build()
        self.assertEqual(out["positions_updated"], 0)
        self.assertEqual(out["cash_updates_created"], 0)
        self.assertEqual(out["portfolio_updates_created"], 0)

    def test_no_broker_network_live(self):
        out = self.build()
        self.assertFalse(out["broker_routing_allowed"])
        self.assertFalse(out["network_used"])
        self.assertFalse(out["approved_for_live"])

    def test_source_not_mutated(self):
        source = execution()
        before = copy.deepcopy(source)
        build_verification(source, cfg())
        self.assertEqual(source, before)

    def test_tampered_execution_rejected(self):
        source = execution()
        source["cycle_id"] = "BAD"
        self.assertRaises(FillSimulationExecutionVerificationError, build_verification, source, cfg())

    def test_tampered_fill_hash_rejected(self):
        source = execution()
        source["fill_objects"][0]["fill_price"] = 1
        rehash_execution(source)
        self.assertRaises(FillSimulationExecutionVerificationError, build_verification, source, cfg())

    def test_wrong_deterministic_fill_id_rejected(self):
        source = execution()
        source["fill_objects"][0]["fill_id"] = "FILL-BAD"
        rehash_fill(source["fill_objects"][0])
        rehash_execution(source)
        self.assertRaises(FillSimulationExecutionVerificationError, build_verification, source, cfg())

    def test_notional_mismatch_rejected(self):
        source = execution()
        source["fill_objects"][0]["notional_value"] = 1
        rehash_fill(source["fill_objects"][0])
        rehash_execution(source)
        self.assertRaises(FillSimulationExecutionVerificationError, build_verification, source, cfg())

    def test_token_state_rejected(self):
        source = execution()
        source["consumed_authorization_token"]["token_state"] = "BAD"
        source["consumed_authorization_token_sha256"] = sha256_of(source["consumed_authorization_token"])
        rehash_execution(source)
        self.assertRaises(FillSimulationExecutionVerificationError, build_verification, source, cfg())

    def test_position_update_rejected(self):
        source = execution()
        source["positions_updated"] = 1
        rehash_execution(source)
        self.assertRaises(FillSimulationExecutionVerificationError, build_verification, source, cfg())

    def test_unsafe_config_rejected(self):
        config = cfg()
        config["network_allowed"] = True
        self.assertRaises(FillSimulationExecutionVerificationError, build_verification, execution(), config)

    def test_main_and_outputs(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "input.json").write_text(json.dumps(execution()), encoding="utf-8")
            (root / "config.json").write_text(json.dumps(cfg()), encoding="utf-8")
            out_dir = root / "out"
            self.assertEqual(main(["--input", str(root / "input.json"), "--config", str(root / "config.json"), "--output-dir", str(out_dir)]), 0)
            self.assertTrue((out_dir / "offline_paper_fill_simulation_execution_verification_v75_2ab.json").exists())
            self.assertTrue((out_dir / "offline_paper_fill_simulation_execution_verification_v75_2ab.sha256").exists())

    def test_main_missing_input(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "config.json").write_text(json.dumps(cfg()), encoding="utf-8")
            self.assertEqual(main(["--input", str(root / "missing.json"), "--config", str(root / "config.json"), "--output-dir", str(root / "out")]), 1)


if __name__ == "__main__":
    unittest.main()
