import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from tools.registry_snapshot_seal_cert_archive_seal_certificate_verifier_v75_2bd import *


def config():
    return {
        "verification_scope": (
            "OFFLINE_PAPER_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_CERTIFICATE_"
            "ARCHIVE_SEAL_CERTIFICATE_VERIFICATION_ONLY"
        ),
        "require_archive_seal_certificate_integrity": True,
        "require_archive_seal_certificate_manifest_integrity": True,
        "require_certified_verified_sealed_archived_snapshot_index_integrity": True,
        "require_archive_seal_certificate_checks_integrity": True,
        "require_archive_seal_certificate_ledger_integrity": True,
        "require_deterministic_archive_seal_certificate_id": True,
        "require_receipt_linkage_and_notional_preservation": True,
        "require_zero_settlement_and_account_mutations": True,
        "create_verified_archive_seal_certificate_index": True,
        "create_archive_seal_certificate_verification_checks": True,
        "create_archive_seal_certificate_verification_ledger": True,
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
    source_verification_id = "CRSCASX-AAAAAAAAAAAAAAAA"
    source_verification_hash = "b" * 64
    certificate_id = "CRSCASC-" + hashlib.sha256(
        (
            f"{source_verification_id}|{source_verification_hash}|75.2BC"
        ).encode("utf-8")
    ).hexdigest()[:16].upper()

    index = [{
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
    }]

    checks = [
        {"check_index": i, "check": f"CHECK_{i}", "state": "PASS"}
        for i in range(1, 13)
    ]
    ledger = [
        {
            "ledger_index": i,
            "event": f"EVENT_{i}",
            "state": "PASS",
            "archive_seal_certificate_id": certificate_id,
        }
        for i in range(1, 7)
    ]

    manifest = {
        "archive_seal_certificate_id": certificate_id,
        "archive_seal_verification_id": source_verification_id,
        "archive_seal_id": "CRSCAS-AAAAAAAAAAAAAAAA",
        "archive_verification_id": "CRSCAX-AAAAAAAAAAAAAAAA",
        "archive_id": "CRSCA-AAAAAAAAAAAAAAAA",
        "receipt_batch_id": "FRB-A",
        "certified_archived_receipt_count": 1,
        "certificate_effect": (
            "OFFLINE_FINAL_EVIDENCE_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_"
            "CERTIFICATE_ARCHIVE_SEAL_CERTIFICATE_ONLY"
        ),
        "certificate_state": (
            "CERTIFIED_VERIFIED_OFFLINE_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_"
            "CERTIFICATE_ARCHIVE_SEAL"
        ),
    }

    value = {
        "status": "PASS",
        "decision": (
            "offline_paper_certificate_registry_snapshot_seal_certificate_"
            "archive_seal_certificate_built"
        ),
        "certificate_registry_snapshot_seal_certificate_archive_"
        "seal_certificate_id": certificate_id,
        "certificate_registry_snapshot_seal_certificate_archive_"
        "seal_verification_id": source_verification_id,
        "certificate_registry_snapshot_seal_certificate_archive_seal_id":
            "CRSCAS-AAAAAAAAAAAAAAAA",
        "certificate_registry_snapshot_seal_certificate_"
        "archive_verification_id": "CRSCAX-AAAAAAAAAAAAAAAA",
        "certificate_registry_snapshot_seal_certificate_archive_id":
            "CRSCA-AAAAAAAAAAAAAAAA",
        "receipt_batch_id": "FRB-A",
        "certificate_scope": (
            "OFFLINE_PAPER_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_CERTIFICATE_"
            "ARCHIVE_SEAL_CERTIFICATE_ONLY"
        ),
        "archive_seal_certificate_state": (
            "CERTIFIED_VERIFIED_OFFLINE_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_"
            "CERTIFICATE_ARCHIVE_SEAL"
        ),
        "archive_seal_certificate_manifest": manifest,
        "archive_seal_certificate_manifest_sha256": sha256_of(manifest),
        "certified_archived_receipt_count": 1,
        "certified_verified_sealed_archived_snapshot_index": index,
        "certified_verified_sealed_archived_snapshot_index_sha256":
            sha256_of(index),
        "archive_seal_certificate_checks": checks,
        "archive_seal_certificate_checks_sha256": sha256_of(checks),
        "archive_seal_certificate_ledger": ledger,
        "archive_seal_certificate_ledger_sha256": sha256_of(ledger),
        "certificate_gate": {
            "archive_seal_certificate_built": True,
            "archive_seal_certificate_immutable": True,
            "settlement_execution_allowed": False,
            "position_update_allowed": False,
            "cash_update_allowed": False,
            "portfolio_update_allowed": False,
            "external_order_submission_allowed": False,
            "broker_routing_allowed": False,
            "paper_broker_allowed": False,
            "live_orders_allowed": False,
            "network_allowed": False,
            "next_version": "75.2BD",
        },
        "source_archive_seal_verification_sha256": source_verification_hash,
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
            "v75.2bc.offline_paper_certificate_registry_snapshot_seal_"
            "certificate_archive_seal_certificate.1"
        ),
        "version": "75.2BC",
    }

    value[
        "offline_paper_certificate_registry_snapshot_seal_certificate_"
        "archive_seal_certificate_sha256"
    ] = sha256_of(value)
    return value


class TestV752BD(unittest.TestCase):
    def build(self):
        return verify_archive_seal_certificate(source(), config())

    @staticmethod
    def rehash(value):
        value.pop(
            "offline_paper_certificate_registry_snapshot_seal_certificate_"
            "archive_seal_certificate_sha256",
            None,
        )
        value[
            "offline_paper_certificate_registry_snapshot_seal_certificate_"
            "archive_seal_certificate_sha256"
        ] = sha256_of(value)

    def test_pass(self):
        self.assertEqual(self.build()["status"], "PASS")

    def test_state(self):
        self.assertEqual(
            self.build()["archive_seal_certificate_verification_state"],
            (
                "VERIFIED_CERTIFIED_OFFLINE_CERTIFICATE_REGISTRY_SNAPSHOT_"
                "SEAL_CERTIFICATE_ARCHIVE_SEAL"
            ),
        )

    def test_count(self):
        self.assertEqual(
            self.build()["verified_certified_archived_receipt_count"], 1
        )

    def test_deterministic_verification_id(self):
        self.assertEqual(
            self.build()[
                "certificate_registry_snapshot_seal_certificate_archive_"
                "seal_certificate_verification_id"
            ],
            self.build()[
                "certificate_registry_snapshot_seal_certificate_archive_"
                "seal_certificate_verification_id"
            ],
        )

    def test_verified_index_state(self):
        self.assertEqual(
            self.build()["verified_archive_seal_certificate_index"][0][
                "archive_seal_certificate_verification_state"
            ],
            (
                "VERIFIED_CERTIFIED_VERIFIED_SEALED_ARCHIVED_CERTIFIED_"
                "SEALED_SNAPSHOTTED_REGISTERED_OFFLINE_RECEIPT"
            ),
        )

    def test_hashes(self):
        output = self.build()
        self.assertEqual(
            output["verified_archive_seal_certificate_index_sha256"],
            sha256_of(output["verified_archive_seal_certificate_index"]),
        )
        self.assertEqual(
            output[
                "archive_seal_certificate_verification_checks_sha256"
            ],
            sha256_of(
                output["archive_seal_certificate_verification_checks"]
            ),
        )
        self.assertEqual(
            output[
                "archive_seal_certificate_verification_ledger_sha256"
            ],
            sha256_of(
                output["archive_seal_certificate_verification_ledger"]
            ),
        )

    def test_output_hash(self):
        output = self.build()
        observed = output.pop(
            "offline_paper_certificate_registry_snapshot_seal_certificate_"
            "archive_seal_certificate_verification_sha256"
        )
        self.assertEqual(observed, sha256_of(output))

    def test_no_mutations(self):
        output = self.build()
        for key in (
            "settlements_created",
            "positions_updated",
            "cash_updates_created",
            "portfolio_updates_created",
            "external_orders_submitted",
            "broker_routes_created",
        ):
            self.assertEqual(output[key], 0)

    def test_no_live(self):
        output = self.build()
        self.assertFalse(output["network_used"])
        self.assertFalse(output["approved_for_live"])
        self.assertFalse(output["broker_routing_allowed"])

    def test_source_not_mutated(self):
        value = source()
        original = copy.deepcopy(value)
        verify_archive_seal_certificate(value, config())
        self.assertEqual(value, original)

    def test_tampered_source(self):
        value = source()
        value["cycle_id"] = "BAD"
        with self.assertRaises(ArchiveSealCertificateVerificationError):
            verify_archive_seal_certificate(value, config())

    def test_tampered_manifest(self):
        value = source()
        value["archive_seal_certificate_manifest"][
            "receipt_batch_id"
        ] = "BAD"
        value["archive_seal_certificate_manifest_sha256"] = sha256_of(
            value["archive_seal_certificate_manifest"]
        )
        self.rehash(value)
        with self.assertRaises(ArchiveSealCertificateVerificationError):
            verify_archive_seal_certificate(value, config())

    def test_tampered_index(self):
        value = source()
        value["certified_verified_sealed_archived_snapshot_index"][0][
            "notional_value"
        ] = 1
        value[
            "certified_verified_sealed_archived_snapshot_index_sha256"
        ] = sha256_of(
            value["certified_verified_sealed_archived_snapshot_index"]
        )
        self.rehash(value)
        with self.assertRaises(ArchiveSealCertificateVerificationError):
            verify_archive_seal_certificate(value, config())

    def test_wrong_certificate_id(self):
        value = source()
        value[
            "certificate_registry_snapshot_seal_certificate_archive_"
            "seal_certificate_id"
        ] = "CRSCASC-BADBADBADBADBADB"
        value["archive_seal_certificate_manifest"][
            "archive_seal_certificate_id"
        ] = value[
            "certificate_registry_snapshot_seal_certificate_archive_"
            "seal_certificate_id"
        ]
        value["archive_seal_certificate_manifest_sha256"] = sha256_of(
            value["archive_seal_certificate_manifest"]
        )
        self.rehash(value)
        with self.assertRaises(ArchiveSealCertificateVerificationError):
            verify_archive_seal_certificate(value, config())

    def test_settlement_rejected(self):
        value = source()
        value["settlements_created"] = 1
        self.rehash(value)
        with self.assertRaises(ArchiveSealCertificateVerificationError):
            verify_archive_seal_certificate(value, config())

    def test_unsafe_config(self):
        value = config()
        value["network_allowed"] = True
        with self.assertRaises(ArchiveSealCertificateVerificationError):
            verify_archive_seal_certificate(source(), value)

    def test_checks_ledger(self):
        output = self.build()
        self.assertEqual(
            len(output["archive_seal_certificate_verification_checks"]),
            12,
        )
        self.assertEqual(
            len(output["archive_seal_certificate_verification_ledger"]),
            6,
        )

    def test_main_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / "source.json").write_text(
                json.dumps(source()), encoding="utf-8"
            )
            (path / "config.json").write_text(
                json.dumps(config()), encoding="utf-8"
            )
            rc = main(
                [
                    "--input",
                    str(path / "source.json"),
                    "--config",
                    str(path / "config.json"),
                    "--output-dir",
                    str(path / "out"),
                ]
            )
            self.assertEqual(rc, 0)
            self.assertTrue(
                (
                    path
                    / "out/registry_snapshot_seal_certificate_archive_"
                    "seal_certificate_verification_v75_2bd.json"
                ).exists()
            )

    def test_missing_input(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / "config.json").write_text(
                json.dumps(config()), encoding="utf-8"
            )
            rc = main(
                [
                    "--input",
                    str(path / "missing.json"),
                    "--config",
                    str(path / "config.json"),
                    "--output-dir",
                    str(path / "out"),
                ]
            )
            self.assertEqual(rc, 1)


if __name__ == "__main__":
    unittest.main()
