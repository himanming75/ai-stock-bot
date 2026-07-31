import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from tools.registry_snapshot_seal_cert_archive_seal_certificate_builder_v75_2bc import *


def cfg():
    return {
        "certificate_scope": (
            "OFFLINE_PAPER_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_CERTIFICATE_"
            "ARCHIVE_SEAL_CERTIFICATE_ONLY"
        ),
        "require_archive_seal_verification_integrity": True,
        "require_deterministic_archive_seal_certificate_id": True,
        "require_receipt_linkage_and_notional_preservation": True,
        "require_zero_settlement_and_account_mutations": True,
        "create_archive_seal_certificate_manifest": True,
        "create_certified_verified_sealed_archived_snapshot_index": True,
        "create_archive_seal_certificate_checks": True,
        "create_archive_seal_certificate_ledger": True,
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
    index = [{
        "archive_seal_verification_record_index": 1,
        "archive_seal_record_index": 1,
        "archive_verification_record_index": 1,
        "archive_record_index": 1,
        "verification_record_index": 1,
        "certificate_record_index": 1,
        "seal_verification_record_index": 1,
        "seal_record_index": 1,
        "snapshot_record_index": 1,
        "registry_record_index": 1,
        "receipt_id": "FRC-AAAAAAAAAAAAAAAA",
        "receipt_sha256": "a" * 64,
        "fill_id": "FILL-AAAAAAAAAAAAAAAA",
        "symbol": "SPY",
        "side": "BUY",
        "filled_quantity": 2,
        "fill_price": 633.5,
        "notional_value": 1267.0,
        "archive_seal_verification_state": (
            "VERIFIED_SEALED_ARCHIVED_CERTIFIED_SEALED_SNAPSHOTTED_"
            "REGISTERED_OFFLINE_RECEIPT"
        ),
    }]
    checks = [{"check_index": i, "check": f"C{i}", "state": "PASS"} for i in range(1, 13)]
    ledger = [{"ledger_index": i, "event": f"E{i}", "state": "PASS"} for i in range(1, 7)]
    value = {
        "status": "PASS",
        "decision": (
            "offline_paper_certificate_registry_snapshot_seal_certificate_"
            "archive_seal_verified"
        ),
        "certificate_registry_snapshot_seal_certificate_archive_seal_verification_id":
            "CRSCASX-AAAAAAAAAAAAAAAA",
        "certificate_registry_snapshot_seal_certificate_archive_seal_id":
            "CRSCAS-AAAAAAAAAAAAAAAA",
        "certificate_registry_snapshot_seal_certificate_archive_verification_id":
            "CRSCAX-AAAAAAAAAAAAAAAA",
        "certificate_registry_snapshot_seal_certificate_archive_id":
            "CRSCA-AAAAAAAAAAAAAAAA",
        "receipt_batch_id": "FRB-A",
        "verification_state": (
            "VERIFIED_OFFLINE_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_CERTIFICATE_"
            "ARCHIVE_SEAL"
        ),
        "verified_sealed_archived_receipt_count": 1,
        "verified_sealed_archived_certified_snapshot_index": index,
        "verified_sealed_archived_certified_snapshot_index_sha256": sha256_of(index),
        "archive_seal_verification_checks": checks,
        "archive_seal_verification_checks_sha256": sha256_of(checks),
        "archive_seal_verification_ledger": ledger,
        "archive_seal_verification_ledger_sha256": sha256_of(ledger),
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
        "schema_version": (
            "v75.2bb.offline_paper_certificate_registry_snapshot_seal_"
            "certificate_archive_seal_verification.1"
        ),
        "version": "75.2BB",
    }
    value[
        "offline_paper_certificate_registry_snapshot_seal_certificate_"
        "archive_seal_verification_sha256"
    ] = sha256_of(value)
    return value


class TestV752BC(unittest.TestCase):
    def build(self):
        return build_archive_seal_certificate(src(), cfg())

    def test_pass(self):
        self.assertEqual(self.build()["status"], "PASS")

    def test_state(self):
        self.assertEqual(
            self.build()["archive_seal_certificate_state"],
            (
                "CERTIFIED_VERIFIED_OFFLINE_CERTIFICATE_REGISTRY_SNAPSHOT_"
                "SEAL_CERTIFICATE_ARCHIVE_SEAL"
            ),
        )

    def test_count(self):
        self.assertEqual(self.build()["certified_archived_receipt_count"], 1)

    def test_deterministic_id(self):
        self.assertEqual(
            self.build()[
                "certificate_registry_snapshot_seal_certificate_archive_seal_certificate_id"
            ],
            self.build()[
                "certificate_registry_snapshot_seal_certificate_archive_seal_certificate_id"
            ],
        )

    def test_manifest(self):
        out = self.build()
        self.assertEqual(
            out["archive_seal_certificate_manifest_sha256"],
            sha256_of(out["archive_seal_certificate_manifest"]),
        )

    def test_index_hash(self):
        out = self.build()
        self.assertEqual(
            out["certified_verified_sealed_archived_snapshot_index_sha256"],
            sha256_of(out["certified_verified_sealed_archived_snapshot_index"]),
        )

    def test_checks_ledger(self):
        out = self.build()
        self.assertEqual(len(out["archive_seal_certificate_checks"]), 12)
        self.assertEqual(len(out["archive_seal_certificate_ledger"]), 6)

    def test_output_hash(self):
        out = self.build()
        observed = out.pop(
            "offline_paper_certificate_registry_snapshot_seal_certificate_"
            "archive_seal_certificate_sha256"
        )
        self.assertEqual(observed, sha256_of(out))

    def test_no_mutations(self):
        out = self.build()
        for key in (
            "settlements_created",
            "positions_updated",
            "cash_updates_created",
            "portfolio_updates_created",
            "external_orders_submitted",
            "broker_routes_created",
        ):
            self.assertEqual(out[key], 0)

    def test_no_live(self):
        out = self.build()
        self.assertFalse(out["network_used"])
        self.assertFalse(out["approved_for_live"])

    def test_source_not_mutated(self):
        value = src()
        original = copy.deepcopy(value)
        build_archive_seal_certificate(value, cfg())
        self.assertEqual(value, original)

    def test_tampered_source(self):
        value = src()
        value["cycle_id"] = "BAD"
        with self.assertRaises(ArchiveSealCertificateBuilderError):
            build_archive_seal_certificate(value, cfg())

    def test_tampered_index(self):
        value = src()
        value["verified_sealed_archived_certified_snapshot_index"][0]["notional_value"] = 1
        value["verified_sealed_archived_certified_snapshot_index_sha256"] = sha256_of(
            value["verified_sealed_archived_certified_snapshot_index"]
        )
        value.pop(
            "offline_paper_certificate_registry_snapshot_seal_certificate_"
            "archive_seal_verification_sha256"
        )
        value[
            "offline_paper_certificate_registry_snapshot_seal_certificate_"
            "archive_seal_verification_sha256"
        ] = sha256_of(value)
        with self.assertRaises(ArchiveSealCertificateBuilderError):
            build_archive_seal_certificate(value, cfg())

    def test_mutation_rejected(self):
        value = src()
        value["settlements_created"] = 1
        value.pop(
            "offline_paper_certificate_registry_snapshot_seal_certificate_"
            "archive_seal_verification_sha256"
        )
        value[
            "offline_paper_certificate_registry_snapshot_seal_certificate_"
            "archive_seal_verification_sha256"
        ] = sha256_of(value)
        with self.assertRaises(ArchiveSealCertificateBuilderError):
            build_archive_seal_certificate(value, cfg())

    def test_unsafe_config(self):
        value = cfg()
        value["network_allowed"] = True
        with self.assertRaises(ArchiveSealCertificateBuilderError):
            build_archive_seal_certificate(src(), value)

    def test_main_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory)
            (p / "source.json").write_text(json.dumps(src()), encoding="utf-8")
            (p / "config.json").write_text(json.dumps(cfg()), encoding="utf-8")
            rc = main([
                "--input", str(p / "source.json"),
                "--config", str(p / "config.json"),
                "--output-dir", str(p / "out"),
            ])
            self.assertEqual(rc, 0)
            self.assertTrue(
                (p / "out/registry_snapshot_seal_certificate_archive_seal_certificate_v75_2bc.json").exists()
            )

    def test_missing_input(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory)
            (p / "config.json").write_text(json.dumps(cfg()), encoding="utf-8")
            rc = main([
                "--input", str(p / "missing.json"),
                "--config", str(p / "config.json"),
                "--output-dir", str(p / "out"),
            ])
            self.assertEqual(rc, 1)


if __name__ == "__main__":
    unittest.main()
