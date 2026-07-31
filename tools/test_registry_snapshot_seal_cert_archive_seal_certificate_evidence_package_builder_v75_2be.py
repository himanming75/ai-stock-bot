import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from tools.registry_snapshot_seal_cert_archive_seal_certificate_evidence_package_builder_v75_2be import *


def config():
    return {
        "package_scope": (
            "OFFLINE_PAPER_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_CERTIFICATE_"
            "ARCHIVE_SEAL_CERTIFICATE_EVIDENCE_PACKAGE_ONLY"
        ),
        "require_archive_seal_certificate_verification_integrity": True,
        "require_verified_certificate_index_integrity": True,
        "require_verification_checks_integrity": True,
        "require_verification_ledger_integrity": True,
        "require_deterministic_evidence_package_id": True,
        "require_receipt_linkage_and_notional_preservation": True,
        "require_zero_settlement_and_account_mutations": True,
        "create_evidence_package_manifest": True,
        "create_evidence_component_hash_map": True,
        "create_packaged_verified_certificate_index": True,
        "create_evidence_package_checks": True,
        "create_evidence_package_ledger": True,
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


def source():
    cert_id = "CRSCASC-AAAAAAAAAAAAAAAA"
    cert_hash = "c" * 64
    verification_id = "CRSCASCX-" + hashlib.sha256(
        f"{cert_id}|{cert_hash}|75.2BD".encode("utf-8")
    ).hexdigest()[:16].upper()

    index = [{
        "archive_seal_certificate_verification_record_index": 1,
        "archive_seal_certificate_record_index": 1,
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
        "archive_seal_certificate_state": (
            "CERTIFIED_VERIFIED_SEALED_ARCHIVED_CERTIFIED_SEALED_"
            "SNAPSHOTTED_REGISTERED_OFFLINE_RECEIPT"
        ),
        "archive_seal_certificate_verification_state": (
            "VERIFIED_CERTIFIED_VERIFIED_SEALED_ARCHIVED_CERTIFIED_"
            "SEALED_SNAPSHOTTED_REGISTERED_OFFLINE_RECEIPT"
        ),
    }]
    checks = [
        {"check_index": i, "check": f"C{i}", "state": "PASS"}
        for i in range(1, 13)
    ]
    ledger = [
        {
            "ledger_index": i,
            "event": f"E{i}",
            "state": "PASS",
            "archive_seal_certificate_verification_id": verification_id,
        }
        for i in range(1, 7)
    ]

    value = {
        "status": "PASS",
        "decision": (
            "offline_paper_certificate_registry_snapshot_seal_certificate_"
            "archive_seal_certificate_verified"
        ),
        "certificate_registry_snapshot_seal_certificate_archive_"
        "seal_certificate_verification_id": verification_id,
        "certificate_registry_snapshot_seal_certificate_archive_"
        "seal_certificate_id": cert_id,
        "certificate_registry_snapshot_seal_certificate_archive_"
        "seal_verification_id": "CRSCASX-AAAAAAAAAAAAAAAA",
        "certificate_registry_snapshot_seal_certificate_archive_seal_id":
            "CRSCAS-AAAAAAAAAAAAAAAA",
        "certificate_registry_snapshot_seal_certificate_"
        "archive_verification_id": "CRSCAX-AAAAAAAAAAAAAAAA",
        "certificate_registry_snapshot_seal_certificate_archive_id":
            "CRSCA-AAAAAAAAAAAAAAAA",
        "receipt_batch_id": "FRB-A",
        "verification_scope": (
            "OFFLINE_PAPER_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_CERTIFICATE_"
            "ARCHIVE_SEAL_CERTIFICATE_VERIFICATION_ONLY"
        ),
        "archive_seal_certificate_verification_state": (
            "VERIFIED_CERTIFIED_OFFLINE_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_"
            "CERTIFICATE_ARCHIVE_SEAL"
        ),
        "archive_seal_certificate_verified": True,
        "verified_certified_archived_receipt_count": 1,
        "verified_archive_seal_certificate_index": index,
        "verified_archive_seal_certificate_index_sha256": sha256_of(index),
        "archive_seal_certificate_verification_checks": checks,
        "archive_seal_certificate_verification_checks_sha256":
            sha256_of(checks),
        "archive_seal_certificate_verification_ledger": ledger,
        "archive_seal_certificate_verification_ledger_sha256":
            sha256_of(ledger),
        "verification_gate": {
            "archive_seal_certificate_verified": True,
            "archive_seal_certificate_immutable": True,
            "verification_effect": (
                "OFFLINE_FINAL_EVIDENCE_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_"
                "CERTIFICATE_ARCHIVE_SEAL_CERTIFICATE_VERIFICATION_ONLY"
            ),
            "settlement_execution_allowed": False,
            "position_update_allowed": False,
            "cash_update_allowed": False,
            "portfolio_update_allowed": False,
            "external_order_submission_allowed": False,
            "broker_routing_allowed": False,
            "paper_broker_allowed": False,
            "live_orders_allowed": False,
            "network_allowed": False,
            "next_version": "75.2BE",
        },
        "source_archive_seal_certificate_sha256": cert_hash,
        "source_archive_seal_certificate_manifest_sha256": "d" * 64,
        "source_certified_verified_sealed_archived_snapshot_index_sha256":
            "e" * 64,
        "source_archive_seal_certificate_checks_sha256": "f" * 64,
        "source_archive_seal_certificate_ledger_sha256": "1" * 64,
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
            "v75.2bd.offline_paper_certificate_registry_snapshot_seal_"
            "certificate_archive_seal_certificate_verification.1"
        ),
        "version": "75.2BD",
    }
    value[
        "offline_paper_certificate_registry_snapshot_seal_certificate_"
        "archive_seal_certificate_verification_sha256"
    ] = sha256_of(value)
    return value


class TestV752BE(unittest.TestCase):
    @staticmethod
    def rehash(value):
        value.pop(
            "offline_paper_certificate_registry_snapshot_seal_certificate_"
            "archive_seal_certificate_verification_sha256",
            None,
        )
        value[
            "offline_paper_certificate_registry_snapshot_seal_certificate_"
            "archive_seal_certificate_verification_sha256"
        ] = sha256_of(value)

    def build(self):
        return build_evidence_package(source(), config())

    def test_pass(self):
        self.assertEqual(self.build()["status"], "PASS")

    def test_state(self):
        self.assertEqual(
            self.build()["evidence_package_state"],
            (
                "PACKAGED_VERIFIED_CERTIFIED_OFFLINE_CERTIFICATE_REGISTRY_"
                "SNAPSHOT_SEAL_CERTIFICATE_ARCHIVE_SEAL"
            ),
        )

    def test_count(self):
        self.assertEqual(
            self.build()["packaged_verified_receipt_count"], 1
        )

    def test_deterministic_package_id(self):
        first = self.build()[
            "certificate_registry_snapshot_seal_certificate_archive_seal_"
            "certificate_evidence_package_id"
        ]
        second = self.build()[
            "certificate_registry_snapshot_seal_certificate_archive_seal_"
            "certificate_evidence_package_id"
        ]
        self.assertEqual(first, second)

    def test_manifest_hash(self):
        out = self.build()
        self.assertEqual(
            out["evidence_package_manifest_sha256"],
            sha256_of(out["evidence_package_manifest"]),
        )

    def test_component_hash_map(self):
        out = self.build()
        self.assertEqual(
            len(out["evidence_component_hash_map"]), 9
        )
        self.assertEqual(
            out["evidence_component_hash_map_sha256"],
            sha256_of(out["evidence_component_hash_map"]),
        )

    def test_index_hash(self):
        out = self.build()
        self.assertEqual(
            out[
                "packaged_verified_archive_seal_certificate_index_sha256"
            ],
            sha256_of(
                out["packaged_verified_archive_seal_certificate_index"]
            ),
        )

    def test_checks_ledger(self):
        out = self.build()
        self.assertEqual(len(out["evidence_package_checks"]), 12)
        self.assertEqual(len(out["evidence_package_ledger"]), 6)

    def test_output_hash(self):
        out = self.build()
        observed = out.pop(
            "offline_paper_certificate_registry_snapshot_seal_certificate_"
            "archive_seal_certificate_evidence_package_sha256"
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
        value = source()
        original = copy.deepcopy(value)
        build_evidence_package(value, config())
        self.assertEqual(value, original)

    def test_tampered_source(self):
        value = source()
        value["cycle_id"] = "BAD"
        with self.assertRaises(EvidencePackageBuilderError):
            build_evidence_package(value, config())

    def test_tampered_index(self):
        value = source()
        value["verified_archive_seal_certificate_index"][0][
            "notional_value"
        ] = 1
        value["verified_archive_seal_certificate_index_sha256"] = sha256_of(
            value["verified_archive_seal_certificate_index"]
        )
        self.rehash(value)
        with self.assertRaises(EvidencePackageBuilderError):
            build_evidence_package(value, config())

    def test_wrong_verification_id(self):
        value = source()
        value[
            "certificate_registry_snapshot_seal_certificate_archive_"
            "seal_certificate_verification_id"
        ] = "CRSCASCX-BADBADBADBADBADB"
        self.rehash(value)
        with self.assertRaises(EvidencePackageBuilderError):
            build_evidence_package(value, config())

    def test_mutation_rejected(self):
        value = source()
        value["cash_updates_created"] = 1
        self.rehash(value)
        with self.assertRaises(EvidencePackageBuilderError):
            build_evidence_package(value, config())

    def test_unsafe_config(self):
        value = config()
        value["network_allowed"] = True
        with self.assertRaises(EvidencePackageBuilderError):
            build_evidence_package(source(), value)

    def test_main_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / "source.json").write_text(
                json.dumps(source()), encoding="utf-8"
            )
            (path / "config.json").write_text(
                json.dumps(config()), encoding="utf-8"
            )
            rc = main([
                "--input", str(path / "source.json"),
                "--config", str(path / "config.json"),
                "--output-dir", str(path / "out"),
            ])
            self.assertEqual(rc, 0)
            self.assertTrue(
                (
                    path
                    / "out/registry_snapshot_seal_certificate_archive_seal_"
                    "certificate_evidence_package_v75_2be.json"
                ).exists()
            )

    def test_missing_input(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / "config.json").write_text(
                json.dumps(config()), encoding="utf-8"
            )
            rc = main([
                "--input", str(path / "missing.json"),
                "--config", str(path / "config.json"),
                "--output-dir", str(path / "out"),
            ])
            self.assertEqual(rc, 1)


if __name__ == "__main__":
    unittest.main()
