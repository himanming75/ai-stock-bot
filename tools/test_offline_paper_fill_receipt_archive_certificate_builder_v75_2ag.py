import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from tools.offline_paper_fill_receipt_archive_certificate_builder_v75_2ag import *

CERTIFIED_AT = "2026-07-31T00:00:00+00:00"


def cfg():
    return {
        "certificate_scope": "OFFLINE_PAPER_FILL_RECEIPT_ARCHIVE_CERTIFICATE_ONLY",
        "require_archive_verification_integrity": True,
        "require_verified_archive_index_integrity": True,
        "require_verification_checks_integrity": True,
        "require_verification_ledger_integrity": True,
        "require_zero_settlement_and_account_mutations": True,
        "create_certificate_summary": True,
        "create_certificate_checks": True,
        "create_certificate_ledger": True,
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
    verification_id = "FAV-AAAAAAAAAAAAAAAA"
    index = [{
        "archive_index": 1,
        "receipt_id": "FRC-AAAAAAAAAAAAAAAA",
        "receipt_sha256": "a" * 64,
        "fill_id": "FILL-AAAAAAAAAAAAAAAA",
        "symbol": "SPY",
        "side": "BUY",
        "filled_quantity": 2,
        "fill_price": 633.5,
        "notional_value": 1267.0,
        "verification_state": "VERIFIED_ARCHIVED_OFFLINE_RECEIPT",
    }]
    checks = [
        {"check_index": i, "check": f"CHECK_{i}", "state": "PASS" if i < 9 else ("LOCKED" if i == 9 else "ENFORCED")}
        for i in range(1, 13)
    ]
    ledger = [
        {"ledger_index": i, "event": f"EVENT_{i}", "state": "PASS", "archive_verification_id": verification_id}
        for i in range(1, 7)
    ]
    source = {
        "status": "PASS",
        "decision": "offline_paper_fill_receipt_archive_package_verified",
        "fill_receipt_archive_verification_id": verification_id,
        "fill_receipt_archive_package_id": "FRA-AAAAAAAAAAAAAAAA",
        "fill_receipt_verification_id": "FRV-AAAAAAAAAAAAAAAA",
        "receipt_batch_id": "FRB-A",
        "verification_scope": "OFFLINE_PAPER_FILL_RECEIPT_ARCHIVE_PACKAGE_VERIFICATION_ONLY",
        "verification_state": "VERIFIED_OFFLINE_FILL_RECEIPT_ARCHIVE_PACKAGE",
        "archive_package_verified": True,
        "verified_archived_receipt_count": 1,
        "verified_archive_index": index,
        "verified_archive_index_sha256": sha256_of(index),
        "verification_checks": checks,
        "verification_checks_sha256": sha256_of(checks),
        "verification_ledger": ledger,
        "verification_ledger_sha256": sha256_of(ledger),
        "verification_gate": {
            "archive_package_verified": True,
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
            "next_version": "75.2AG",
        },
        "source_archive_package_sha256": "b" * 64,
        "source_archive_index_sha256": "c" * 64,
        "source_archive_manifest_sha256": "d" * 64,
        "source_archive_checks_sha256": "e" * 64,
        "source_archive_ledger_sha256": "f" * 64,
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
        "schema_version": "v75.2af.offline_paper_fill_receipt_archive_package_verification.1",
        "version": "75.2AF",
    }
    source["offline_paper_fill_receipt_archive_verification_sha256"] = sha256_of(source)
    return source


class TestV752AG(unittest.TestCase):
    def build(self):
        return build_certificate(src(), cfg(), CERTIFIED_AT)

    def rehash(self, source):
        source.pop("offline_paper_fill_receipt_archive_verification_sha256", None)
        source["offline_paper_fill_receipt_archive_verification_sha256"] = sha256_of(source)

    def test_pass(self):
        self.assertEqual(self.build()["status"], "PASS")

    def test_certificate_state(self):
        self.assertEqual(
            self.build()["certificate_state"],
            "ISSUED_VERIFIED_OFFLINE_FILL_RECEIPT_ARCHIVE_CERTIFICATE",
        )

    def test_certificate_count(self):
        self.assertEqual(self.build()["certified_receipt_count"], 1)

    def test_certificate_summary(self):
        output = self.build()
        self.assertEqual(
            output["certificate_summary"]["certificate_result"],
            "CERTIFIED_VERIFIED_OFFLINE_ARCHIVE",
        )

    def test_certified_receipts(self):
        self.assertEqual(
            self.build()["certified_receipts"][0]["certificate_state"],
            "CERTIFIED_VERIFIED_ARCHIVED_OFFLINE_RECEIPT",
        )

    def test_summary_hash(self):
        output = self.build()
        self.assertEqual(output["certificate_summary_sha256"], sha256_of(output["certificate_summary"]))

    def test_receipts_hash(self):
        output = self.build()
        self.assertEqual(output["certified_receipts_sha256"], sha256_of(output["certified_receipts"]))

    def test_output_hash(self):
        output = self.build()
        observed = output.pop("offline_paper_fill_receipt_archive_certificate_sha256")
        self.assertEqual(observed, sha256_of(output))

    def test_deterministic_certificate_id(self):
        self.assertEqual(self.build()["fill_receipt_archive_certificate_id"], self.build()["fill_receipt_archive_certificate_id"])

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
        build_certificate(source, cfg(), CERTIFIED_AT)
        self.assertEqual(source, before)

    def test_tampered_source_rejected(self):
        source = src()
        source["cycle_id"] = "BAD"
        self.assertRaises(OfflinePaperFillReceiptArchiveCertificateError, build_certificate, source, cfg(), CERTIFIED_AT)

    def test_tampered_index_rejected(self):
        source = src()
        source["verified_archive_index"][0]["notional_value"] = 1
        source["verified_archive_index_sha256"] = sha256_of(source["verified_archive_index"])
        self.rehash(source)
        self.assertRaises(OfflinePaperFillReceiptArchiveCertificateError, build_certificate, source, cfg(), CERTIFIED_AT)

    def test_settlement_rejected(self):
        source = src()
        source["settlements_created"] = 1
        self.rehash(source)
        self.assertRaises(OfflinePaperFillReceiptArchiveCertificateError, build_certificate, source, cfg(), CERTIFIED_AT)

    def test_unsafe_config_rejected(self):
        config = cfg()
        config["network_allowed"] = True
        self.assertRaises(OfflinePaperFillReceiptArchiveCertificateError, build_certificate, src(), config, CERTIFIED_AT)

    def test_main_and_outputs(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td)
            (path / "source.json").write_text(json.dumps(src()), encoding="utf-8")
            (path / "config.json").write_text(json.dumps(cfg()), encoding="utf-8")
            rc = main([
                "--input", str(path / "source.json"),
                "--config", str(path / "config.json"),
                "--output-dir", str(path / "out"),
                "--certified-at", CERTIFIED_AT,
            ])
            self.assertEqual(rc, 0)
            self.assertTrue((path / "out/offline_paper_fill_receipt_archive_certificate_v75_2ag.json").exists())
            self.assertTrue((path / "out/offline_paper_fill_receipt_archive_certificate_summary_v75_2ag.json").exists())

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
