import copy
import json
import tempfile
import unittest
from pathlib import Path

from tools.offline_paper_fill_receipt_builder_v75_2ac import *

ISSUED_AT = "2026-07-30T22:40:00+00:00"


def cfg():
    return {
        "receipt_scope": "OFFLINE_PAPER_FILL_RECEIPT_ARTIFACT_ONLY",
        "require_verification_integrity": True,
        "require_verified_fill_objects_integrity": True,
        "require_verification_checks_integrity": True,
        "require_verification_ledger_integrity": True,
        "require_verified_execution_state": True,
        "require_zero_account_mutations": True,
        "create_receipt_artifacts": True,
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
    execution_hash = "a" * 64
    execution_id = "FSE-AAAAAAAAAAAAAAAA"
    verification_id = "FSV-" + hashlib.sha256(
        f"{execution_id}|{execution_hash}|75.2AB".encode()
    ).hexdigest()[:16].upper()
    fills = [{
        "fill_index": 1,
        "fill_id": "FILL-AAAAAAAAAAAAAAAA",
        "fill_object_sha256": "b" * 64,
        "paper_order_id": "PORD-AAAAAAAAAAAAAAAA",
        "offline_submission_id": "OSUB-AAAAAAAAAAAAAAAA",
        "symbol": "SPY",
        "side": "BUY",
        "filled_quantity": 2,
        "fill_price": 633.5,
        "verification_state": "VERIFIED_OFFLINE_FILL_OBJECT_ONLY",
    }]
    checks = [
        {"check_index": i, "check": f"CHECK_{i}", "state": "PASS" if i < 8 else ("LOCKED" if i == 8 else "ENFORCED")}
        for i in range(1, 13)
    ]
    ledger = [
        {"ledger_index": i, "event": f"EVENT_{i}", "state": "PASS", "verification_id": verification_id}
        for i in range(1, 7)
    ]
    source = {
        "status": "PASS",
        "decision": "offline_paper_fill_simulation_execution_verified",
        "fill_simulation_execution_verification_id": verification_id,
        "fill_simulation_execution_id": execution_id,
        "fill_simulation_authorization_id": "FSA-A",
        "verification_scope": "OFFLINE_PAPER_FILL_SIMULATION_EXECUTION_VERIFICATION_ONLY",
        "verification_state": "VERIFIED_OFFLINE_FILL_OBJECT_EXECUTION",
        "execution_verified": True,
        "verified_fill_object_count": 1,
        "verified_fill_objects": fills,
        "verified_fill_objects_sha256": sha256_of(fills),
        "verification_checks": checks,
        "verification_checks_sha256": sha256_of(checks),
        "verification_ledger": ledger,
        "verification_ledger_sha256": sha256_of(ledger),
        "verification_gate": {
            "execution_verified": True,
            "position_update_allowed": False,
            "cash_update_allowed": False,
            "portfolio_update_allowed": False,
            "external_order_submission_allowed": False,
            "broker_routing_allowed": False,
            "paper_broker_allowed": False,
            "live_orders_allowed": False,
            "network_allowed": False,
            "next_version": "75.2AC",
        },
        "source_fill_simulation_execution_sha256": execution_hash,
        "source_fill_objects_sha256": "c" * 64,
        "source_consumed_authorization_token_sha256": "d" * 64,
        "source_execution_checks_sha256": "e" * 64,
        "source_execution_ledger_sha256": "f" * 64,
        "session_id": "PAPER-A",
        "cycle_id": "PCS-A",
        "cycle_sequence": 1,
        "champion_candidate_id": "CAND-A",
        "fill_objects_created": 1,
        "fills_created": 1,
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
            "lock_state": "ENFORCED",
            "network_enabled": False,
            "live_orders_enabled": False,
            "external_side_effects_allowed": False,
        },
        "schema_version": "v75.2ab.offline_paper_fill_simulation_execution_verification.1",
        "version": "75.2AB",
    }
    source["offline_paper_fill_simulation_execution_verification_sha256"] = sha256_of(source)
    return source


class TestV752AC(unittest.TestCase):
    def build(self):
        return build_receipts(src(), cfg(), ISSUED_AT)

    def rehash(self, source):
        source.pop("offline_paper_fill_simulation_execution_verification_sha256", None)
        source["offline_paper_fill_simulation_execution_verification_sha256"] = sha256_of(source)

    def test_pass(self):
        self.assertEqual(self.build()["status"], "PASS")

    def test_receipt_count(self):
        self.assertEqual(self.build()["receipt_count"], 1)

    def test_receipt_state(self):
        self.assertEqual(self.build()["receipt_batch_state"], "ISSUED_OFFLINE_RECEIPTS_ONLY")

    def test_receipt_object(self):
        receipt = self.build()["receipts"][0]
        self.assertEqual(receipt["receipt_type"], "OFFLINE_PAPER_FILL_RECEIPT")
        self.assertTrue(receipt["offline_only"])
        self.assertTrue(receipt["informational_only"])

    def test_notional(self):
        self.assertEqual(self.build()["receipts"][0]["notional_value"], 1267.0)

    def test_receipt_hash(self):
        receipt = copy.deepcopy(self.build()["receipts"][0])
        observed = receipt.pop("receipt_sha256")
        self.assertEqual(observed, sha256_of(receipt))

    def test_receipts_hash(self):
        output = self.build()
        self.assertEqual(output["receipts_sha256"], sha256_of(output["receipts"]))

    def test_output_hash(self):
        output = self.build()
        observed = output.pop("offline_paper_fill_receipt_batch_sha256")
        self.assertEqual(observed, sha256_of(output))

    def test_deterministic_ids(self):
        a, b = self.build(), self.build()
        self.assertEqual(a["receipt_batch_id"], b["receipt_batch_id"])
        self.assertEqual(a["receipts"][0]["receipt_id"], b["receipts"][0]["receipt_id"])

    def test_no_account_mutation(self):
        output = self.build()
        for key in ("settlements_created", "positions_updated", "cash_updates_created", "portfolio_updates_created"):
            self.assertEqual(output[key], 0)

    def test_no_broker_network_live(self):
        output = self.build()
        for key in ("broker_routing_allowed", "network_allowed", "approved_for_live", "network_used"):
            self.assertFalse(output[key])

    def test_source_not_mutated(self):
        source = src()
        before = copy.deepcopy(source)
        build_receipts(source, cfg(), ISSUED_AT)
        self.assertEqual(source, before)

    def test_tampered_source_rejected(self):
        source = src()
        source["cycle_id"] = "BAD"
        self.assertRaises(OfflinePaperFillReceiptError, build_receipts, source, cfg(), ISSUED_AT)

    def test_tampered_verified_fills_rejected(self):
        source = src()
        source["verified_fill_objects"][0]["fill_price"] = 1
        self.rehash(source)
        self.assertRaises(OfflinePaperFillReceiptError, build_receipts, source, cfg(), ISSUED_AT)

    def test_position_update_rejected(self):
        source = src()
        source["positions_updated"] = 1
        self.rehash(source)
        self.assertRaises(OfflinePaperFillReceiptError, build_receipts, source, cfg(), ISSUED_AT)

    def test_bad_verification_state_rejected(self):
        source = src()
        source["verification_state"] = "BAD"
        self.rehash(source)
        self.assertRaises(OfflinePaperFillReceiptError, build_receipts, source, cfg(), ISSUED_AT)

    def test_unsafe_config_rejected(self):
        config = cfg()
        config["network_allowed"] = True
        self.assertRaises(OfflinePaperFillReceiptError, build_receipts, src(), config, ISSUED_AT)

    def test_main_and_outputs(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td)
            (path / "source.json").write_text(json.dumps(src()), encoding="utf-8")
            (path / "config.json").write_text(json.dumps(cfg()), encoding="utf-8")
            rc = main([
                "--input", str(path / "source.json"),
                "--config", str(path / "config.json"),
                "--output-dir", str(path / "out"),
                "--issued-at", ISSUED_AT,
            ])
            self.assertEqual(rc, 0)
            self.assertTrue((path / "out/offline_paper_fill_receipt_batch_v75_2ac.json").exists())
            self.assertTrue((path / "out/offline_paper_fill_receipts_v75_2ac.json").exists())

    def test_main_missing_input(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td)
            (path / "config.json").write_text(json.dumps(cfg()), encoding="utf-8")
            rc = main([
                "--input", str(path / "missing.json"),
                "--config", str(path / "config.json"),
                "--output-dir", str(path / "out"),
            ])
            self.assertEqual(rc, 1)


if __name__ == "__main__":
    unittest.main()
