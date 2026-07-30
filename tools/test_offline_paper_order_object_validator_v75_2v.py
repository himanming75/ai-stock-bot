import json, tempfile, unittest
from pathlib import Path
from tools.offline_paper_order_object_validator_v75_2v import *

TS = "2026-07-30T22:00:00+00:00"

def config_fixture():
    return {
        "validation_scope": "OFFLINE_PAPER_ORDER_OBJECT_VALIDATION_ONLY",
        "required_order_type": "MARKET_REFERENCE_ONLY",
        "required_time_in_force": "DAY",
        "required_order_state": "CREATED_NOT_SUBMITTED",
        "minimum_reference_price": 0.01,
        "require_execution_integrity": True,
        "require_package_integrity": True,
        "require_consumed_token_integrity": True,
        "require_order_id_recalculation": True,
        "require_zero_submissions": True,
        "require_zero_fills": True,
        "require_safety_lock": True,
        "order_submission_allowed": False,
        "fill_simulation_allowed": False,
        "paper_broker_allowed": False,
        "live_orders_allowed": False,
        "network_allowed": False,
        "broker_connection_allowed": False,
        "external_side_effects_allowed": False,
    }

def source_fixture():
    created = "2026-07-30T21:55:00+00:00"
    oid = expected_order_id("OGA-A", "INT-A", created)
    order = {
        "paper_order_id": oid, "authorization_id": "OGA-A", "order_intent_id": "INT-A",
        "symbol": "SPY", "side": "BUY", "quantity": 1,
        "order_type": "MARKET_REFERENCE_ONLY", "time_in_force": "DAY",
        "reference_price": 633.5, "created_at": created,
        "order_state": "CREATED_NOT_SUBMITTED", "offline_paper_object": True,
        "submitted": False, "filled": False, "fill_simulated": False,
        "broker_routed": False, "network_used": False, "external_side_effects": False,
    }
    package = {
        "execution_id": "OGE-A", "authorization_id": "OGA-A",
        "validation_id": "OIV-A", "source_execution_id": "OIE-A",
        "session_id": "PAPER-A", "cycle_id": "PCS-A", "cycle_sequence": 1,
        "champion_candidate_id": "CAND-A", "created_at": created,
        "immutable": True, "offline_only": True, "paper_order_count": 1,
        "paper_orders": [order], "orders_submitted": 0, "fills_created": 0,
        "network_source": False,
    }
    token = {
        "authorization_id": "OGA-A", "authorized_order_intent_ids": ["INT-A"],
        "consumed": True, "consumed_at": created,
        "expires_at": "2026-07-30T22:10:00+00:00",
        "issued_at": "2026-07-30T21:50:00+00:00",
        "nonce": "n", "scope": "OFFLINE_PAPER_ORDER_OBJECT_CREATION_ONLY",
        "single_use": True, "token_sha256": "x", "token_state": "CONSUMED",
        "validation_id": "OIV-A",
    }
    checks = [{"check_index": 1, "check": "A", "state": "PASS"}]
    ledger = [{"ledger_index": 1, "event": "A", "state": "PASS"}]
    s = {
        "status": "PASS", "execution_id": "OGE-A",
        "execution_state": "READY_FOR_ORDER_OBJECT_VALIDATION",
        "authorization_id": "OGA-A", "authorization_state": "CONSUMED",
        "order_generation_authorized": True, "order_generation_executed": True,
        "order_objects_created": 1, "token_consumed": True,
        "consumed_authorization_token": token,
        "consumed_authorization_token_sha256": sha256_of(token),
        "paper_order_package": package, "paper_order_package_sha256": sha256_of(package),
        "execution_checks": checks, "execution_checks_sha256": sha256_of(checks),
        "execution_ledger": ledger, "execution_ledger_sha256": sha256_of(ledger),
        "source_order_generation_authorization_sha256": "a"*64,
        "source_order_intent_validation_sha256": "b"*64,
        "source_order_intent_execution_sha256": "c"*64,
        "source_order_intent_package_sha256": "d"*64,
        "validation_id": "OIV-A", "source_execution_id": "OIE-A",
        "session_id": "PAPER-A", "cycle_id": "PCS-A", "cycle_sequence": 1,
        "champion_candidate_id": "CAND-A",
        "execution_gate": {
            "order_objects_created": True, "order_object_validation_allowed": True,
            "order_submission_allowed": False, "fill_simulation_allowed": False,
            "paper_broker_allowed": False, "live_orders_allowed": False,
            "network_allowed": False, "next_version": "75.2V",
        },
        "order_submission_allowed": False, "fill_simulation_allowed": False,
        "paper_broker_allowed": False, "live_orders_allowed": False,
        "network_allowed": False, "broker_connection_allowed": False,
        "orders_submitted": 0, "fills_created": 0,
        "approved_for_live": False, "network_used": False,
        "safety_lock": {
            "broker_connected": False, "broker_credentials_required": False,
            "external_side_effects_allowed": False, "live_orders_enabled": False,
            "live_trading_approval_allowed": False, "lock_state": "ENFORCED",
            "network_enabled": False,
        },
        "schema_version": "v75.2u.offline_paper_order_generation_execution.1",
        "version": "75.2U",
    }
    s["offline_paper_order_generation_execution_sha256"] = sha256_of(s)
    return s

class TestV752V(unittest.TestCase):
    def build(self):
        return build_validation(source_fixture(), config_fixture(), TS)
    def rehash(self, s):
        s.pop("offline_paper_order_generation_execution_sha256", None)
        s["offline_paper_order_generation_execution_sha256"] = sha256_of(s)
    def rehash_package(self, s):
        s["paper_order_package_sha256"] = sha256_of(s["paper_order_package"])
        self.rehash(s)

    def test_pass(self): self.assertEqual(self.build()["status"], "PASS")
    def test_state(self): self.assertEqual(self.build()["validation_state"], "READY_FOR_ORDER_SUBMISSION_AUTHORIZATION")
    def test_count(self): self.assertEqual(self.build()["validated_order_count"], 1)
    def test_order(self):
        x = self.build()["validated_orders"][0]
        self.assertEqual((x["symbol"], x["side"], x["quantity"]), ("SPY", "BUY", 1))
        self.assertEqual(x["order_state"], "CREATED_NOT_SUBMITTED")
    def test_gate(self): self.assertTrue(self.build()["validation_gate"]["order_submission_authorization_allowed"])
    def test_submission_blocked(self): self.assertFalse(self.build()["order_submission_allowed"])
    def test_hash(self):
        x = self.build()
        h = x.pop("offline_paper_order_object_validation_sha256")
        self.assertEqual(h, sha256_of(x))
    def test_validated_hash(self):
        x = self.build()
        self.assertEqual(x["validated_orders_sha256"], sha256_of(x["validated_orders"]))
    def test_checks(self): self.assertEqual(len(self.build()["validation_checks"]), 12)
    def test_ledger(self): self.assertEqual(len(self.build()["validation_ledger"]), 6)
    def test_bad_integrity(self):
        s = source_fixture(); s["cycle_id"] = "BAD"
        self.assertRaises(OrderObjectValidationError, build_validation, s, config_fixture(), TS)
    def test_bad_order_id(self):
        s = source_fixture(); s["paper_order_package"]["paper_orders"][0]["paper_order_id"] = "PORD-" + "0"*16
        self.rehash_package(s)
        self.assertRaises(OrderObjectValidationError, build_validation, s, config_fixture(), TS)
    def test_bad_symbol(self):
        s = source_fixture(); s["paper_order_package"]["paper_orders"][0]["symbol"] = "QQQ"
        self.rehash_package(s)
        self.assertRaises(OrderObjectValidationError, build_validation, s, config_fixture(), TS)
    def test_bad_quantity(self):
        s = source_fixture(); s["paper_order_package"]["paper_orders"][0]["quantity"] = 2
        self.rehash_package(s)
        self.assertRaises(OrderObjectValidationError, build_validation, s, config_fixture(), TS)
    def test_bad_order_type(self):
        s = source_fixture(); s["paper_order_package"]["paper_orders"][0]["order_type"] = "LIMIT"
        self.rehash_package(s)
        self.assertRaises(OrderObjectValidationError, build_validation, s, config_fixture(), TS)
    def test_bad_tif(self):
        s = source_fixture(); s["paper_order_package"]["paper_orders"][0]["time_in_force"] = "GTC"
        self.rehash_package(s)
        self.assertRaises(OrderObjectValidationError, build_validation, s, config_fixture(), TS)
    def test_submitted(self):
        s = source_fixture(); s["paper_order_package"]["paper_orders"][0]["submitted"] = True
        self.rehash_package(s)
        self.assertRaises(OrderObjectValidationError, build_validation, s, config_fixture(), TS)
    def test_filled(self):
        s = source_fixture(); s["paper_order_package"]["paper_orders"][0]["filled"] = True
        self.rehash_package(s)
        self.assertRaises(OrderObjectValidationError, build_validation, s, config_fixture(), TS)
    def test_token_not_consumed(self):
        s = source_fixture(); s["consumed_authorization_token"]["consumed"] = False
        s["consumed_authorization_token_sha256"] = sha256_of(s["consumed_authorization_token"]); self.rehash(s)
        self.assertRaises(OrderObjectValidationError, build_validation, s, config_fixture(), TS)
    def test_unsafe_config(self):
        c = config_fixture(); c["order_submission_allowed"] = True
        self.assertRaises(OrderObjectValidationError, build_validation, source_fixture(), c, TS)
    def test_main(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            (p/"s.json").write_text(json.dumps(source_fixture()))
            (p/"c.json").write_text(json.dumps(config_fixture()))
            self.assertEqual(main(["--input", str(p/"s.json"), "--config", str(p/"c.json"), "--output-dir", str(p/"out"), "--validated-at", TS]), 0)
            self.assertTrue((p/"out"/"offline_paper_order_object_validation_v75_2v.json").exists())
    def test_main_missing(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td); (p/"c.json").write_text(json.dumps(config_fixture()))
            self.assertEqual(main(["--input", str(p/"missing"), "--config", str(p/"c.json"), "--output-dir", str(p/"out")]), 1)

if __name__ == "__main__":
    unittest.main()
