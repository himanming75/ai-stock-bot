import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from tools.offline_paper_fill_receipt_verifier_v75_2ad import *

ISSUED_AT = "2026-07-30T22:40:00+00:00"


def cfg():
    return {
        "verification_scope": "OFFLINE_PAPER_FILL_RECEIPT_VERIFICATION_ONLY",
        "require_receipt_batch_integrity": True,
        "require_receipts_integrity": True,
        "require_each_receipt_integrity": True,
        "require_receipt_checks_integrity": True,
        "require_receipt_ledger_integrity": True,
        "require_deterministic_receipt_ids": True,
        "require_notional_recalculation": True,
        "require_zero_settlement_and_account_mutations": True,
        "settlement_execution_allowed": False,
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
    source_verification_hash = "a" * 64
    verification_id = "FSV-AAAAAAAAAAAAAAAA"
    batch_id = "FRB-" + hashlib.sha256(
        f"{verification_id}|{source_verification_hash}|{ISSUED_AT}|75.2AC".encode()
    ).hexdigest()[:16].upper()
    fill_id = "FILL-AAAAAAAAAAAAAAAA"
    fill_hash = "b" * 64
    receipt_id = "FRC-" + hashlib.sha256(
        f"{batch_id}|{fill_id}|{fill_hash}|75.2AC".encode()
    ).hexdigest()[:16].upper()
    receipt = {
        "receipt_index": 1,
        "receipt_id": receipt_id,
        "receipt_batch_id": batch_id,
        "fill_simulation_execution_verification_id": verification_id,
        "fill_simulation_execution_id": "FSE-A",
        "fill_simulation_authorization_id": "FSA-A",
        "fill_id": fill_id,
        "fill_object_sha256": fill_hash,
        "paper_order_id": "PORD-A",
        "offline_submission_id": "OSUB-A",
        "symbol": "SPY",
        "side": "BUY",
        "filled_quantity": 2,
        "fill_price": 633.5,
        "notional_value": 1267.0,
        "currency": "USD",
        "receipt_type": "OFFLINE_PAPER_FILL_RECEIPT",
        "receipt_state": "ISSUED_OFFLINE_ARTIFACT_ONLY",
        "issued_at": ISSUED_AT,
        "offline_only": True,
        "informational_only": True,
        "settlement_executed": False,
        "position_updated": False,
        "cash_updated": False,
        "portfolio_updated": False,
        "broker_connected": False,
        "broker_routed": False,
        "external_submission": False,
        "network_used": False,
        "approved_for_live": False,
    }
    receipt["receipt_sha256"] = sha256_of(receipt)
    receipts = [receipt]
    checks = [
        {"check_index": i, "check": f"CHECK_{i}", "state": "PASS" if i < 8 else "ENFORCED"}
        for i in range(1, 13)
    ]
    ledger = [
        {"ledger_index": i, "event": f"EVENT_{i}", "state": "PASS", "receipt_batch_id": batch_id}
        for i in range(1, 7)
    ]
    source = {
        "status": "PASS",
        "decision": "offline_paper_fill_receipts_issued_artifact_only",
        "receipt_batch_id": batch_id,
        "fill_simulation_execution_verification_id": verification_id,
        "fill_simulation_execution_id": "FSE-A",
        "fill_simulation_authorization_id": "FSA-A",
        "receipt_scope": "OFFLINE_PAPER_FILL_RECEIPT_ARTIFACT_ONLY",
        "receipt_batch_state": "ISSUED_OFFLINE_RECEIPTS_ONLY",
        "receipt_count": 1,
        "receipts": receipts,
        "receipts_sha256": sha256_of(receipts),
        "receipt_checks": checks,
        "receipt_checks_sha256": sha256_of(checks),
        "receipt_ledger": ledger,
        "receipt_ledger_sha256": sha256_of(ledger),
        "receipt_gate": {
            "receipt_artifacts_created": True,
            "settlement_execution_allowed": False,
            "position_update_allowed": False,
            "cash_update_allowed": False,
            "portfolio_update_allowed": False,
            "external_order_submission_allowed": False,
            "broker_routing_allowed": False,
            "paper_broker_allowed": False,
            "live_orders_allowed": False,
            "network_allowed": False,
            "next_version": "75.2AD",
        },
        "source_fill_simulation_execution_verification_sha256": source_verification_hash,
        "source_verified_fill_objects_sha256": "c" * 64,
        "source_verification_checks_sha256": "d" * 64,
        "source_verification_ledger_sha256": "e" * 64,
        "session_id": "PAPER-A",
        "cycle_id": "PCS-A",
        "cycle_sequence": 1,
        "champion_candidate_id": "CAND-A",
        "issued_at": ISSUED_AT,
        "receipts_created": 1,
        "settlements_created": 0,
        "positions_updated": 0,
        "cash_updates_created": 0,
        "portfolio_updates_created": 0,
        "external_orders_submitted": 0,
        "broker_routes_created": 0,
        "settlement_execution_allowed": False,
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
        "safety_lock": {"lock_state": "ENFORCED"},
        "schema_version": "v75.2ac.offline_paper_fill_receipt.1",
        "version": "75.2AC",
    }
    source["offline_paper_fill_receipt_batch_sha256"] = sha256_of(source)
    return source


class TestV752AD(unittest.TestCase):
    def build(self):
        return build_verification(src(), cfg())

    def rehash(self, source):
        source.pop("offline_paper_fill_receipt_batch_sha256", None)
        source["offline_paper_fill_receipt_batch_sha256"] = sha256_of(source)

    def test_pass(self):
        self.assertEqual(self.build()["status"], "PASS")

    def test_state(self):
        self.assertEqual(self.build()["verification_state"], "VERIFIED_OFFLINE_FILL_RECEIPTS")

    def test_receipt_count(self):
        self.assertEqual(self.build()["verified_receipt_count"], 1)

    def test_verified_receipt(self):
        item = self.build()["verified_receipts"][0]
        self.assertEqual(item["verification_state"], "VERIFIED_OFFLINE_FILL_RECEIPT_ONLY")

    def test_verified_receipts_hash(self):
        output = self.build()
        self.assertEqual(output["verified_receipts_sha256"], sha256_of(output["verified_receipts"]))

    def test_output_hash(self):
        output = self.build()
        observed = output.pop("offline_paper_fill_receipt_verification_sha256")
        self.assertEqual(observed, sha256_of(output))

    def test_no_mutation(self):
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
        build_verification(source, cfg())
        self.assertEqual(source, before)

    def test_tampered_batch_rejected(self):
        source = src()
        source["cycle_id"] = "BAD"
        self.assertRaises(OfflinePaperFillReceiptVerificationError, build_verification, source, cfg())

    def test_tampered_receipt_hash_rejected(self):
        source = src()
        source["receipts"][0]["receipt_sha256"] = "0" * 64
        source["receipts_sha256"] = sha256_of(source["receipts"])
        self.rehash(source)
        self.assertRaises(OfflinePaperFillReceiptVerificationError, build_verification, source, cfg())

    def test_wrong_receipt_id_rejected(self):
        source = src()
        receipt = source["receipts"][0]
        receipt["receipt_id"] = "FRC-BAD"
        clone = copy.deepcopy(receipt)
        clone.pop("receipt_sha256")
        receipt["receipt_sha256"] = sha256_of(clone)
        source["receipts_sha256"] = sha256_of(source["receipts"])
        self.rehash(source)
        self.assertRaises(OfflinePaperFillReceiptVerificationError, build_verification, source, cfg())

    def test_notional_mismatch_rejected(self):
        source = src()
        receipt = source["receipts"][0]
        receipt["notional_value"] = 1
        clone = copy.deepcopy(receipt)
        clone.pop("receipt_sha256")
        receipt["receipt_sha256"] = sha256_of(clone)
        source["receipts_sha256"] = sha256_of(source["receipts"])
        self.rehash(source)
        self.assertRaises(OfflinePaperFillReceiptVerificationError, build_verification, source, cfg())

    def test_settlement_rejected(self):
        source = src()
        source["settlements_created"] = 1
        self.rehash(source)
        self.assertRaises(OfflinePaperFillReceiptVerificationError, build_verification, source, cfg())

    def test_unsafe_receipt_rejected(self):
        source = src()
        receipt = source["receipts"][0]
        receipt["network_used"] = True
        clone = copy.deepcopy(receipt)
        clone.pop("receipt_sha256")
        receipt["receipt_sha256"] = sha256_of(clone)
        source["receipts_sha256"] = sha256_of(source["receipts"])
        self.rehash(source)
        self.assertRaises(OfflinePaperFillReceiptVerificationError, build_verification, source, cfg())

    def test_unsafe_config_rejected(self):
        config = cfg()
        config["network_allowed"] = True
        self.assertRaises(OfflinePaperFillReceiptVerificationError, build_verification, src(), config)

    def test_main_and_outputs(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td)
            (path/"source.json").write_text(json.dumps(src()), encoding="utf-8")
            (path/"config.json").write_text(json.dumps(cfg()), encoding="utf-8")
            rc = main([
                "--input", str(path/"source.json"),
                "--config", str(path/"config.json"),
                "--output-dir", str(path/"out"),
            ])
            self.assertEqual(rc, 0)
            self.assertTrue((path/"out/offline_paper_fill_receipt_verification_v75_2ad.json").exists())
            self.assertTrue((path/"out/offline_paper_verified_fill_receipts_v75_2ad.json").exists())

    def test_main_missing_input(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td)
            (path/"config.json").write_text(json.dumps(cfg()), encoding="utf-8")
            rc = main([
                "--input", str(path/"missing.json"),
                "--config", str(path/"config.json"),
                "--output-dir", str(path/"out"),
            ])
            self.assertEqual(rc, 1)


if __name__ == "__main__":
    unittest.main()
