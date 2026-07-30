import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from tools.offline_paper_fill_receipt_archive_verifier_v75_2af import *

ARCHIVED_AT = "2026-07-30T23:30:00+00:00"


def cfg():
    return {
        "verification_scope": "OFFLINE_PAPER_FILL_RECEIPT_ARCHIVE_PACKAGE_VERIFICATION_ONLY",
        "require_archive_package_integrity": True,
        "require_archive_index_integrity": True,
        "require_archive_manifest_integrity": True,
        "require_archive_checks_integrity": True,
        "require_archive_ledger_integrity": True,
        "require_deterministic_archive_package_id": True,
        "require_receipt_notional_recalculation": True,
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
    receipt_verification_id = "FRV-AAAAAAAAAAAAAAAA"
    source_verification_hash = "a" * 64
    package_id = "FRA-" + hashlib.sha256(
        f"{receipt_verification_id}|{source_verification_hash}|{ARCHIVED_AT}|75.2AE".encode()
    ).hexdigest()[:16].upper()
    index = [{
        "archive_index": 1,
        "receipt_id": "FRC-AAAAAAAAAAAAAAAA",
        "receipt_sha256": "b" * 64,
        "fill_id": "FILL-AAAAAAAAAAAAAAAA",
        "symbol": "SPY",
        "side": "BUY",
        "filled_quantity": 2,
        "fill_price": 633.5,
        "notional_value": 1267.0,
        "archive_state": "INDEXED_VERIFIED_OFFLINE_RECEIPT",
    }]
    source_verified_receipts_hash = "c" * 64
    source_checks_hash = "d" * 64
    source_ledger_hash = "e" * 64
    manifest = [
        {"entry_index": 1, "artifact": "SOURCE_RECEIPT_VERIFICATION", "artifact_id": receipt_verification_id, "artifact_sha256": source_verification_hash, "state": "LOCKED"},
        {"entry_index": 2, "artifact": "VERIFIED_RECEIPT_COLLECTION", "artifact_id": "FRB-A", "artifact_sha256": source_verified_receipts_hash, "state": "LOCKED"},
        {"entry_index": 3, "artifact": "SOURCE_VERIFICATION_CHECKS", "artifact_id": receipt_verification_id, "artifact_sha256": source_checks_hash, "state": "LOCKED"},
        {"entry_index": 4, "artifact": "SOURCE_VERIFICATION_LEDGER", "artifact_id": receipt_verification_id, "artifact_sha256": source_ledger_hash, "state": "LOCKED"},
    ]
    checks = [
        {"check_index": i, "check": f"CHECK_{i}", "state": "PASS" if i < 8 else ("LOCKED" if i == 8 else "ENFORCED")}
        for i in range(1, 13)
    ]
    ledger = [
        {"ledger_index": i, "event": f"EVENT_{i}", "state": "PASS", "archive_package_id": package_id}
        for i in range(1, 7)
    ]
    source = {
        "status": "PASS",
        "decision": "offline_paper_fill_receipt_archive_package_created",
        "fill_receipt_archive_package_id": package_id,
        "fill_receipt_verification_id": receipt_verification_id,
        "receipt_batch_id": "FRB-A",
        "archive_scope": "OFFLINE_PAPER_FILL_RECEIPT_ARCHIVE_PACKAGE_ONLY",
        "archive_state": "ARCHIVED_VERIFIED_OFFLINE_RECEIPTS",
        "archived_at": ARCHIVED_AT,
        "archived_receipt_count": 1,
        "archive_index": index,
        "archive_index_sha256": sha256_of(index),
        "archive_manifest": manifest,
        "archive_manifest_sha256": sha256_of(manifest),
        "archive_checks": checks,
        "archive_checks_sha256": sha256_of(checks),
        "archive_ledger": ledger,
        "archive_ledger_sha256": sha256_of(ledger),
        "archive_gate": {
            "archive_package_created": True,
            "archive_package_immutable": True,
            "settlement_execution_allowed": False,
            "position_update_allowed": False,
            "cash_update_allowed": False,
            "portfolio_update_allowed": False,
            "external_order_submission_allowed": False,
            "broker_routing_allowed": False,
            "paper_broker_allowed": False,
            "live_orders_allowed": False,
            "network_allowed": False,
            "next_version": "75.2AF",
        },
        "source_fill_receipt_verification_sha256": source_verification_hash,
        "source_verified_receipts_sha256": source_verified_receipts_hash,
        "source_verification_checks_sha256": source_checks_hash,
        "source_verification_ledger_sha256": source_ledger_hash,
        "session_id": "PAPER-A",
        "cycle_id": "PCS-A",
        "cycle_sequence": 1,
        "champion_candidate_id": "CAND-A",
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
        "schema_version": "v75.2ae.offline_paper_fill_receipt_archive_package.1",
        "version": "75.2AE",
    }
    source["offline_paper_fill_receipt_archive_package_sha256"] = sha256_of(source)
    return source


class TestV752AF(unittest.TestCase):
    def build(self):
        return build_verification(src(), cfg())

    def rehash(self, source):
        source.pop("offline_paper_fill_receipt_archive_package_sha256", None)
        source["offline_paper_fill_receipt_archive_package_sha256"] = sha256_of(source)

    def test_pass(self):
        self.assertEqual(self.build()["status"], "PASS")

    def test_verification_state(self):
        self.assertEqual(self.build()["verification_state"], "VERIFIED_OFFLINE_FILL_RECEIPT_ARCHIVE_PACKAGE")

    def test_verified_count(self):
        self.assertEqual(self.build()["verified_archived_receipt_count"], 1)

    def test_verified_index(self):
        self.assertEqual(self.build()["verified_archive_index"][0]["verification_state"], "VERIFIED_ARCHIVED_OFFLINE_RECEIPT")

    def test_verified_index_hash(self):
        output = self.build()
        self.assertEqual(output["verified_archive_index_sha256"], sha256_of(output["verified_archive_index"]))

    def test_output_hash(self):
        output = self.build()
        observed = output.pop("offline_paper_fill_receipt_archive_verification_sha256")
        self.assertEqual(observed, sha256_of(output))

    def test_deterministic_verification_id(self):
        self.assertEqual(self.build()["fill_receipt_archive_verification_id"], self.build()["fill_receipt_archive_verification_id"])

    def test_no_mutations(self):
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

    def test_tampered_package_rejected(self):
        source = src()
        source["cycle_id"] = "BAD"
        self.assertRaises(OfflinePaperFillReceiptArchiveVerificationError, build_verification, source, cfg())

    def test_tampered_index_rejected(self):
        source = src()
        source["archive_index"][0]["notional_value"] = 1
        source["archive_index_sha256"] = sha256_of(source["archive_index"])
        self.rehash(source)
        self.assertRaises(OfflinePaperFillReceiptArchiveVerificationError, build_verification, source, cfg())

    def test_tampered_manifest_rejected(self):
        source = src()
        source["archive_manifest"][0]["artifact_sha256"] = "0" * 64
        source["archive_manifest_sha256"] = sha256_of(source["archive_manifest"])
        self.rehash(source)
        self.assertRaises(OfflinePaperFillReceiptArchiveVerificationError, build_verification, source, cfg())

    def test_wrong_package_id_rejected(self):
        source = src()
        source["fill_receipt_archive_package_id"] = "FRA-BAD"
        for item in source["archive_ledger"]:
            item["archive_package_id"] = "FRA-BAD"
        source["archive_ledger_sha256"] = sha256_of(source["archive_ledger"])
        self.rehash(source)
        self.assertRaises(OfflinePaperFillReceiptArchiveVerificationError, build_verification, source, cfg())

    def test_settlement_rejected(self):
        source = src()
        source["settlements_created"] = 1
        self.rehash(source)
        self.assertRaises(OfflinePaperFillReceiptArchiveVerificationError, build_verification, source, cfg())

    def test_unsafe_config_rejected(self):
        config = cfg()
        config["network_allowed"] = True
        self.assertRaises(OfflinePaperFillReceiptArchiveVerificationError, build_verification, src(), config)

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
            self.assertTrue((path/"out/offline_paper_fill_receipt_archive_verification_v75_2af.json").exists())
            self.assertTrue((path/"out/offline_paper_verified_fill_receipt_archive_index_v75_2af.json").exists())

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
