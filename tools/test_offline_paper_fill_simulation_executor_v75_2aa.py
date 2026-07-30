import copy
import json
import tempfile
import unittest
from pathlib import Path

from tools.offline_paper_fill_simulation_executor_v75_2aa import *

ISSUED = "2026-07-30T22:20:00+00:00"
EXPIRES = "2026-07-30T22:35:00+00:00"
EXECUTED = "2026-07-30T22:25:00+00:00"


def cfg():
    return {
        "execution_scope": "OFFLINE_PAPER_FILL_OBJECT_CREATION_ONLY",
        "fill_price_policy": "REFERENCE_PRICE_ONLY",
        "fill_quantity_policy": "FULL_QUANTITY_ONLY",
        "require_authorization_integrity": True,
        "require_authorized_targets_integrity": True,
        "require_single_use_token": True,
        "require_unconsumed_token": True,
        "require_unexpired_token": True,
        "require_reference_price_lock": True,
        "require_full_quantity_lock": True,
        "create_fill_objects": True,
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


def src():
    targets = [{
        "authorization_id": "OSA-A",
        "cash_updated": False,
        "current_order_state": "SUBMITTED_OFFLINE_REFERENCE",
        "fill_object_created": False,
        "fill_price_policy": "REFERENCE_PRICE_ONLY",
        "fill_quantity_policy": "FULL_QUANTITY_ONLY",
        "fill_simulated": False,
        "fill_simulation_execution_authorized": True,
        "filled": False,
        "offline_submission_id": "OSUB-AAAAAAAAAAAAAAAA",
        "order_intent_id": "INT-A",
        "order_type": "MARKET_REFERENCE_ONLY",
        "paper_order_id": "PORD-AAAAAAAAAAAAAAAA",
        "portfolio_updated": False,
        "position_updated": False,
        "quantity": 2,
        "reference_price": 633.5,
        "side": "BUY",
        "symbol": "SPY",
        "time_in_force": "DAY",
    }]
    token_material = {
        "fill_simulation_authorization_id": "FSA-A",
        "submission_validation_id": "OSV-A",
        "issued_at": ISSUED,
        "expires_at": EXPIRES,
        "nonce": "a" * 32,
        "scope": "OFFLINE_PAPER_FILL_SIMULATION_EXECUTION_ONLY",
        "authorized_offline_submission_ids": ["OSUB-AAAAAAAAAAAAAAAA"],
        "authorized_paper_order_ids": ["PORD-AAAAAAAAAAAAAAAA"],
        "fill_price_policy": "REFERENCE_PRICE_ONLY",
        "fill_quantity_policy": "FULL_QUANTITY_ONLY",
    }
    token = {
        **token_material,
        "token_sha256": sha256_of(token_material),
        "single_use": True,
        "consumed": False,
        "consumed_at": None,
        "token_state": "ISSUED_NOT_CONSUMED",
    }
    source = {
        "status": "PASS",
        "decision": "offline_paper_fill_simulation_authorized",
        "fill_simulation_authorization_id": "FSA-A",
        "authorization_scope": "OFFLINE_PAPER_FILL_SIMULATION_EXECUTION_ONLY",
        "authorization_state": "AUTHORIZED_NOT_EXECUTED",
        "fill_simulation_authorized": True,
        "fill_simulation_executed": False,
        "fill_simulation_execution_allowed": True,
        "fill_simulation_allowed": False,
        "authorized_target_count": 1,
        "authorized_fill_simulation_targets": targets,
        "authorized_fill_simulation_targets_sha256": sha256_of(targets),
        "fill_simulation_authorization_token": token,
        "fill_simulation_authorization_token_sha256": sha256_of(token),
        "authorization_gate": {
            "fill_simulation_authorized": True,
            "fill_simulation_execution_allowed": True,
            "fill_simulation_allowed": False,
            "fill_object_creation_allowed": False,
            "position_update_allowed": False,
            "cash_update_allowed": False,
            "portfolio_update_allowed": False,
            "external_order_submission_allowed": False,
            "broker_routing_allowed": False,
            "paper_broker_allowed": False,
            "live_orders_allowed": False,
            "network_allowed": False,
            "next_version": "75.2AA",
        },
        "submission_validation_id": "OSV-A",
        "submission_execution_id": "OSE-A",
        "authorization_id": "OSA-A",
        "validation_id": "OOV-A",
        "execution_id": "OGE-A",
        "authorization_source_id": "OGA-A",
        "session_id": "PAPER-A",
        "cycle_id": "PCS-A",
        "cycle_sequence": 1,
        "champion_candidate_id": "CAND-A",
        "fill_objects_created": 0,
        "fills_created": 0,
        "positions_updated": 0,
        "cash_updates_created": 0,
        "portfolio_updates_created": 0,
        "external_orders_submitted": 0,
        "broker_routes_created": 0,
        "position_update_allowed": False,
        "cash_update_allowed": False,
        "portfolio_update_allowed": False,
        "external_order_submission_allowed": False,
        "broker_routing_allowed": False,
        "paper_broker_allowed": False,
        "live_orders_allowed": False,
        "network_allowed": False,
        "broker_connection_allowed": False,
        "approved_for_live": False,
        "network_used": False,
        "safety_lock": {
            "broker_connected": False,
            "broker_credentials_required": False,
            "external_side_effects_allowed": False,
            "live_orders_enabled": False,
            "live_trading_approval_allowed": False,
            "lock_state": "ENFORCED",
            "network_enabled": False,
        },
        "schema_version": "v75.2z.offline_paper_fill_simulation_authorization.1",
        "version": "75.2Z",
    }
    source["offline_paper_fill_simulation_authorization_sha256"] = sha256_of(source)
    return source


def rehash(source):
    source.pop("offline_paper_fill_simulation_authorization_sha256", None)
    source["offline_paper_fill_simulation_authorization_sha256"] = sha256_of(source)


class TestV752AA(unittest.TestCase):
    def build(self):
        return build_execution(src(), cfg(), EXECUTED)

    def test_pass(self):
        self.assertEqual(self.build()["status"], "PASS")

    def test_execution_state(self):
        self.assertEqual(self.build()["execution_state"], "EXECUTED_FILL_OBJECT_ONLY")

    def test_fill_object_created(self):
        output = self.build()
        self.assertEqual(output["fill_object_count"], 1)
        self.assertEqual(output["fill_objects"][0]["fill_state"], "FILLED_OFFLINE_OBJECT_ONLY")

    def test_reference_price_and_full_quantity(self):
        fill = self.build()["fill_objects"][0]
        self.assertEqual(fill["fill_price"], 633.5)
        self.assertEqual(fill["filled_quantity"], 2)
        self.assertEqual(fill["notional_value"], 1267.0)

    def test_no_account_mutation(self):
        output = self.build()
        self.assertEqual(output["positions_updated"], 0)
        self.assertEqual(output["cash_updates_created"], 0)
        self.assertEqual(output["portfolio_updates_created"], 0)
        fill = output["fill_objects"][0]
        self.assertFalse(fill["position_updated"])
        self.assertFalse(fill["cash_updated"])
        self.assertFalse(fill["portfolio_updated"])

    def test_no_broker_network_live(self):
        output = self.build()
        self.assertFalse(output["network_used"])
        self.assertFalse(output["approved_for_live"])
        self.assertEqual(output["broker_routes_created"], 0)
        self.assertEqual(output["external_orders_submitted"], 0)

    def test_token_consumed_in_output_only(self):
        source = src()
        output = build_execution(source, cfg(), EXECUTED)
        self.assertFalse(source["fill_simulation_authorization_token"]["consumed"])
        self.assertTrue(output["consumed_authorization_token"]["consumed"])
        self.assertEqual(output["consumed_authorization_token"]["consumed_at"], EXECUTED)

    def test_deterministic_fill_id(self):
        self.assertEqual(self.build()["fill_objects"][0]["fill_id"], self.build()["fill_objects"][0]["fill_id"])

    def test_fill_hash(self):
        fill = self.build()["fill_objects"][0]
        observed = fill["fill_object_sha256"]
        clone = copy.deepcopy(fill)
        clone.pop("fill_object_sha256")
        self.assertEqual(observed, sha256_of(clone))

    def test_output_hash(self):
        output = self.build()
        observed = output.pop("offline_paper_fill_simulation_execution_sha256")
        self.assertEqual(observed, sha256_of(output))

    def test_expired_token_rejected(self):
        with self.assertRaises(FillSimulationExecutionError):
            build_execution(src(), cfg(), "2026-07-30T22:36:00+00:00")

    def test_consumed_token_rejected(self):
        source = src()
        source["fill_simulation_authorization_token"]["consumed"] = True
        source["fill_simulation_authorization_token"]["consumed_at"] = EXECUTED
        source["fill_simulation_authorization_token"]["token_state"] = "CONSUMED_BY_OFFLINE_FILL_SIMULATION"
        source["fill_simulation_authorization_token_sha256"] = sha256_of(source["fill_simulation_authorization_token"])
        rehash(source)
        with self.assertRaises(FillSimulationExecutionError):
            build_execution(source, cfg(), EXECUTED)

    def test_tampered_authorization_rejected(self):
        source = src()
        source["cycle_id"] = "BAD"
        with self.assertRaises(FillSimulationExecutionError):
            build_execution(source, cfg(), EXECUTED)

    def test_tampered_target_rejected(self):
        source = src()
        source["authorized_fill_simulation_targets"][0]["reference_price"] = 1.0
        rehash(source)
        with self.assertRaises(FillSimulationExecutionError):
            build_execution(source, cfg(), EXECUTED)

    def test_unsafe_config_rejected(self):
        config = cfg()
        config["position_update_allowed"] = True
        with self.assertRaises(FillSimulationExecutionError):
            build_execution(src(), config, EXECUTED)

    def test_existing_fill_rejected(self):
        source = src()
        source["authorized_fill_simulation_targets"][0]["filled"] = True
        source["authorized_fill_simulation_targets_sha256"] = sha256_of(source["authorized_fill_simulation_targets"])
        rehash(source)
        with self.assertRaises(FillSimulationExecutionError):
            build_execution(source, cfg(), EXECUTED)

    def test_main_and_outputs(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td)
            (path / "source.json").write_text(json.dumps(src()), encoding="utf-8")
            (path / "config.json").write_text(json.dumps(cfg()), encoding="utf-8")
            result = main([
                "--input", str(path / "source.json"),
                "--config", str(path / "config.json"),
                "--output-dir", str(path / "out"),
                "--executed-at", EXECUTED,
            ])
            self.assertEqual(result, 0)
            self.assertTrue((path / "out" / "offline_paper_fill_simulation_execution_v75_2aa.json").exists())
            self.assertTrue((path / "out" / "offline_paper_fill_objects_v75_2aa.json").exists())

    def test_main_missing_input(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td)
            (path / "config.json").write_text(json.dumps(cfg()), encoding="utf-8")
            self.assertEqual(main([
                "--input", str(path / "missing.json"),
                "--config", str(path / "config.json"),
                "--output-dir", str(path / "out"),
            ]), 1)


if __name__ == "__main__":
    unittest.main()
