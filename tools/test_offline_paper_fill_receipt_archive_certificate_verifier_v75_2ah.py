import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from tools.offline_paper_fill_receipt_archive_certificate_verifier_v75_2ah import *

CERTIFIED_AT = "2026-07-31T00:00:00+00:00"


def cfg():
    return {
        "verification_scope": "OFFLINE_PAPER_FILL_RECEIPT_ARCHIVE_CERTIFICATE_VERIFICATION_ONLY",
        "require_certificate_integrity": True,
        "require_certificate_summary_integrity": True,
        "require_certified_receipts_integrity": True,
        "require_certificate_checks_integrity": True,
        "require_certificate_ledger_integrity": True,
        "require_deterministic_certificate_id": True,
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
    archive_verification_id = "FAV-AAAAAAAAAAAAAAAA"
    source_archive_verification_hash = "a" * 64
    certificate_id = "FAC-" + hashlib.sha256(
        f"{archive_verification_id}|{source_archive_verification_hash}|{CERTIFIED_AT}|75.2AG".encode()
    ).hexdigest()[:16].upper()
    receipts = [{
        "certificate_index": 1,
        "archive_index": 1,
        "receipt_id": "FRC-AAAAAAAAAAAAAAAA",
        "receipt_sha256": "b" * 64,
        "fill_id": "FILL-AAAAAAAAAAAAAAAA",
        "symbol": "SPY",
        "side": "BUY",
        "filled_quantity": 2,
        "fill_price": 633.5,
        "notional_value": 1267.0,
        "certificate_state": "CERTIFIED_VERIFIED_ARCHIVED_OFFLINE_RECEIPT",
    }]
    summary = {
        "certificate_id": certificate_id,
        "archive_verification_id": archive_verification_id,
        "archive_package_id": "FRA-AAAAAAAAAAAAAAAA",
        "receipt_batch_id": "FRB-A",
        "certified_receipt_count": 1,
        "certificate_result": "CERTIFIED_VERIFIED_OFFLINE_ARCHIVE",
        "certificate_effect": "INFORMATIONAL_ARCHIVE_ATTESTATION_ONLY",
        "certified_at": CERTIFIED_AT,
    }
    checks = [
        {"check_index": i, "check": f"CHECK_{i}", "state": "PASS" if i < 9 else ("LOCKED" if i == 9 else "ENFORCED")}
        for i in range(1, 13)
    ]
    ledger = [
        {"ledger_index": i, "event": f"EVENT_{i}", "state": "PASS", "certificate_id": certificate_id}
        for i in range(1, 7)
    ]
    source = {
        "status": "PASS",
        "decision": "offline_paper_fill_receipt_archive_certificate_issued",
        "fill_receipt_archive_certificate_id": certificate_id,
        "fill_receipt_archive_verification_id": archive_verification_id,
        "fill_receipt_archive_package_id": "FRA-AAAAAAAAAAAAAAAA",
        "fill_receipt_verification_id": "FRV-AAAAAAAAAAAAAAAA",
        "receipt_batch_id": "FRB-A",
        "certificate_scope": "OFFLINE_PAPER_FILL_RECEIPT_ARCHIVE_CERTIFICATE_ONLY",
        "certificate_state": "ISSUED_VERIFIED_OFFLINE_FILL_RECEIPT_ARCHIVE_CERTIFICATE",
        "certified_at": CERTIFIED_AT,
        "certificate_summary": summary,
        "certificate_summary_sha256": sha256_of(summary),
        "certified_receipt_count": 1,
        "certified_receipts": receipts,
        "certified_receipts_sha256": sha256_of(receipts),
        "certificate_checks": checks,
        "certificate_checks_sha256": sha256_of(checks),
        "certificate_ledger": ledger,
        "certificate_ledger_sha256": sha256_of(ledger),
        "certificate_gate": {
            "archive_certificate_issued": True,
            "archive_certificate_immutable": True,
            "certificate_effect": "INFORMATIONAL_ARCHIVE_ATTESTATION_ONLY",
            "settlement_execution_allowed": False,
            "position_update_allowed": False,
            "cash_update_allowed": False,
            "portfolio_update_allowed": False,
            "external_order_submission_allowed": False,
            "broker_routing_allowed": False,
            "paper_broker_allowed": False,
            "live_orders_allowed": False,
            "network_allowed": False,
            "next_version": "75.2AH",
        },
        "source_archive_verification_sha256": source_archive_verification_hash,
        "source_verified_archive_index_sha256": "c" * 64,
        "source_verification_checks_sha256": "d" * 64,
        "source_verification_ledger_sha256": "e" * 64,
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
        "schema_version": "v75.2ag.offline_paper_fill_receipt_archive_certificate.1",
        "version": "75.2AG",
    }
    source["offline_paper_fill_receipt_archive_certificate_sha256"] = sha256_of(source)
    return source


class TestV752AH(unittest.TestCase):
    def build(self):
        return build_verification(src(), cfg())

    def rehash(self, source):
        source.pop("offline_paper_fill_receipt_archive_certificate_sha256", None)
        source["offline_paper_fill_receipt_archive_certificate_sha256"] = sha256_of(source)

    def test_pass(self):
        self.assertEqual(self.build()["status"], "PASS")

    def test_verification_state(self):
        self.assertEqual(self.build()["verification_state"], "VERIFIED_OFFLINE_FILL_RECEIPT_ARCHIVE_CERTIFICATE")

    def test_verified_count(self):
        self.assertEqual(self.build()["verified_certified_receipt_count"], 1)

    def test_verified_receipts(self):
        self.assertEqual(
            self.build()["verified_certified_receipts"][0]["verification_state"],
            "VERIFIED_CERTIFIED_ARCHIVED_OFFLINE_RECEIPT",
        )

    def test_verified_receipts_hash(self):
        output = self.build()
        self.assertEqual(output["verified_certified_receipts_sha256"], sha256_of(output["verified_certified_receipts"]))

    def test_output_hash(self):
        output = self.build()
        observed = output.pop("offline_paper_fill_receipt_archive_certificate_verification_sha256")
        self.assertEqual(observed, sha256_of(output))

    def test_deterministic_verification_id(self):
        self.assertEqual(
            self.build()["fill_receipt_archive_certificate_verification_id"],
            self.build()["fill_receipt_archive_certificate_verification_id"],
        )

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

    def test_tampered_source_rejected(self):
        source = src()
        source["cycle_id"] = "BAD"
        self.assertRaises(OfflinePaperFillReceiptArchiveCertificateVerificationError, build_verification, source, cfg())

    def test_tampered_summary_rejected(self):
        source = src()
        source["certificate_summary"]["certificate_result"] = "BAD"
        source["certificate_summary_sha256"] = sha256_of(source["certificate_summary"])
        self.rehash(source)
        self.assertRaises(OfflinePaperFillReceiptArchiveCertificateVerificationError, build_verification, source, cfg())

    def test_tampered_receipt_rejected(self):
        source = src()
        source["certified_receipts"][0]["notional_value"] = 1
        source["certified_receipts_sha256"] = sha256_of(source["certified_receipts"])
        self.rehash(source)
        self.assertRaises(OfflinePaperFillReceiptArchiveCertificateVerificationError, build_verification, source, cfg())

    def test_wrong_certificate_id_rejected(self):
        source = src()
        source["fill_receipt_archive_certificate_id"] = "FAC-BAD"
        source["certificate_summary"]["certificate_id"] = "FAC-BAD"
        for item in source["certificate_ledger"]:
            item["certificate_id"] = "FAC-BAD"
        source["certificate_summary_sha256"] = sha256_of(source["certificate_summary"])
        source["certificate_ledger_sha256"] = sha256_of(source["certificate_ledger"])
        self.rehash(source)
        self.assertRaises(OfflinePaperFillReceiptArchiveCertificateVerificationError, build_verification, source, cfg())

    def test_settlement_rejected(self):
        source = src()
        source["settlements_created"] = 1
        self.rehash(source)
        self.assertRaises(OfflinePaperFillReceiptArchiveCertificateVerificationError, build_verification, source, cfg())

    def test_unsafe_config_rejected(self):
        config = cfg()
        config["network_allowed"] = True
        self.assertRaises(OfflinePaperFillReceiptArchiveCertificateVerificationError, build_verification, src(), config)

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
            self.assertTrue((path/"out/offline_paper_fill_receipt_archive_certificate_verification_v75_2ah.json").exists())
            self.assertTrue((path/"out/offline_paper_verified_fill_receipt_archive_certificate_receipts_v75_2ah.json").exists())

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
