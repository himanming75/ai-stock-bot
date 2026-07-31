import copy
import json
import tempfile
import unittest
from pathlib import Path

from tools.registry_snapshot_seal_cert_builder_v75_2aw import *


CERTIFIED_AT = "2026-07-31T11:00:00-07:00"


def config():
    return {
        "certificate_scope": (
            "OFFLINE_PAPER_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_CERTIFICATE_ONLY"
        ),
        "require_seal_verification_integrity": True,
        "require_verified_sealed_snapshot_index_integrity": True,
        "require_verification_checks_integrity": True,
        "require_verification_ledger_integrity": True,
        "require_zero_settlement_and_account_mutations": True,
        "create_certificate_manifest": True,
        "create_certified_sealed_snapshot_index": True,
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


def source():
    index = [
        {
            "verification_record_index": 1,
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
            "verification_state": (
                "VERIFIED_SEALED_SNAPSHOTTED_REGISTERED_CERTIFIED_ARCHIVED_"
                "OFFLINE_RECEIPT"
            ),
        }
    ]

    checks = [
        {"check_index": i, "check": f"CHECK_{i}", "state": "PASS"}
        for i in range(1, 13)
    ]
    ledger = [
        {
            "ledger_index": i,
            "event": f"EVENT_{i}",
            "state": "PASS",
            "seal_verification_id": "CRSSX-AAAAAAAAAAAAAAAA",
        }
        for i in range(1, 7)
    ]

    value = {
        "status": "PASS",
        "decision": (
            "offline_paper_certificate_registry_snapshot_seal_verified"
        ),
        "certificate_registry_snapshot_seal_verification_id": (
            "CRSSX-AAAAAAAAAAAAAAAA"
        ),
        "certificate_registry_snapshot_seal_id": "CRSS-AAAAAAAAAAAAAAAA",
        "certificate_registry_snapshot_verification_id": (
            "CRSX-AAAAAAAAAAAAAAAA"
        ),
        "certificate_registry_snapshot_id": "CRSN-AAAAAAAAAAAAAAAA",
        "certificate_registry_verification_id": "FCRX-AAAAAAAAAAAAAAAA",
        "certificate_registry_id": "FCRS-AAAAAAAAAAAAAAAA",
        "receipt_batch_id": "FRB-A",
        "verification_scope": (
            "OFFLINE_PAPER_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_VERIFICATION_ONLY"
        ),
        "verification_state": (
            "VERIFIED_OFFLINE_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL"
        ),
        "seal_verified": True,
        "verified_sealed_receipt_count": 1,
        "verified_sealed_snapshot_index": index,
        "verified_sealed_snapshot_index_sha256": sha256_of(index),
        "verification_checks": checks,
        "verification_checks_sha256": sha256_of(checks),
        "verification_ledger": ledger,
        "verification_ledger_sha256": sha256_of(ledger),
        "verification_gate": {
            "certificate_registry_snapshot_seal_verified": True,
            "seal_immutable": True,
            "verification_effect": (
                "OFFLINE_FINAL_EVIDENCE_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_"
                "VERIFICATION_ONLY"
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
            "next_version": "75.2AW",
        },
        "source_seal_sha256": "b" * 64,
        "source_seal_manifest_sha256": "c" * 64,
        "source_sealed_snapshot_index_sha256": "d" * 64,
        "source_seal_checks_sha256": "e" * 64,
        "source_seal_ledger_sha256": "f" * 64,
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
            "v75.2av.offline_paper_certificate_registry_snapshot_seal_"
            "verification.1"
        ),
        "version": "75.2AV",
    }

    value[
        "offline_paper_certificate_registry_snapshot_seal_verification_sha256"
    ] = sha256_of(value)
    return value


class TestV752AW(unittest.TestCase):
    def build(self):
        return build_certificate(source(), config(), CERTIFIED_AT)

    @staticmethod
    def rehash(value):
        value.pop(
            "offline_paper_certificate_registry_snapshot_seal_verification_sha256",
            None,
        )
        value[
            "offline_paper_certificate_registry_snapshot_seal_verification_sha256"
        ] = sha256_of(value)

    def test_pass(self):
        self.assertEqual(self.build()["status"], "PASS")

    def test_state(self):
        self.assertEqual(
            self.build()["certificate_state"],
            "CERTIFIED_VERIFIED_OFFLINE_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL",
        )

    def test_count(self):
        self.assertEqual(self.build()["certified_receipt_count"], 1)

    def test_manifest(self):
        self.assertEqual(
            self.build()["certificate_manifest"]["certificate_effect"],
            (
                "OFFLINE_FINAL_EVIDENCE_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_"
                "CERTIFICATE_ONLY"
            ),
        )

    def test_deterministic_id(self):
        self.assertEqual(
            self.build()[
                "certificate_registry_snapshot_seal_certificate_id"
            ],
            self.build()[
                "certificate_registry_snapshot_seal_certificate_id"
            ],
        )

    def test_index_state(self):
        self.assertEqual(
            self.build()["certified_sealed_snapshot_index"][0][
                "certificate_state"
            ],
            (
                "CERTIFIED_VERIFIED_SEALED_SNAPSHOTTED_REGISTERED_ARCHIVED_"
                "OFFLINE_RECEIPT"
            ),
        )

    def test_hashes(self):
        output = self.build()
        self.assertEqual(
            output["certificate_manifest_sha256"],
            sha256_of(output["certificate_manifest"]),
        )
        self.assertEqual(
            output["certified_sealed_snapshot_index_sha256"],
            sha256_of(output["certified_sealed_snapshot_index"]),
        )
        self.assertEqual(
            output["certificate_checks_sha256"],
            sha256_of(output["certificate_checks"]),
        )
        self.assertEqual(
            output["certificate_ledger_sha256"],
            sha256_of(output["certificate_ledger"]),
        )

    def test_output_hash(self):
        output = self.build()
        observed = output.pop(
            "offline_paper_certificate_registry_snapshot_seal_certificate_sha256"
        )
        self.assertEqual(observed, sha256_of(output))

    def test_no_mutations(self):
        output = self.build()
        for key in (
            "settlements_created",
            "positions_updated",
            "cash_updates_created",
            "portfolio_updates_created",
        ):
            self.assertEqual(output[key], 0)

    def test_no_live(self):
        output = self.build()
        for key in (
            "network_allowed",
            "broker_routing_allowed",
            "approved_for_live",
            "network_used",
        ):
            self.assertFalse(output[key])

    def test_source_not_mutated(self):
        value = source()
        original = copy.deepcopy(value)
        build_certificate(value, config(), CERTIFIED_AT)
        self.assertEqual(value, original)

    def test_tampered_source(self):
        value = source()
        value["cycle_id"] = "BAD"
        self.assertRaises(
            RegistrySnapshotSealCertificateError,
            build_certificate,
            value,
            config(),
            CERTIFIED_AT,
        )

    def test_tampered_index(self):
        value = source()
        value["verified_sealed_snapshot_index"][0]["notional_value"] = 1
        value["verified_sealed_snapshot_index_sha256"] = sha256_of(
            value["verified_sealed_snapshot_index"]
        )
        self.rehash(value)
        self.assertRaises(
            RegistrySnapshotSealCertificateError,
            build_certificate,
            value,
            config(),
            CERTIFIED_AT,
        )

    def test_bad_timestamp(self):
        self.assertRaises(
            RegistrySnapshotSealCertificateError,
            build_certificate,
            source(),
            config(),
            "2026-07-31",
        )

    def test_settlement_rejected(self):
        value = source()
        value["settlements_created"] = 1
        self.rehash(value)
        self.assertRaises(
            RegistrySnapshotSealCertificateError,
            build_certificate,
            value,
            config(),
            CERTIFIED_AT,
        )

    def test_unsafe_config(self):
        value = config()
        value["network_allowed"] = True
        self.assertRaises(
            RegistrySnapshotSealCertificateError,
            build_certificate,
            source(),
            value,
            CERTIFIED_AT,
        )

    def test_checks_ledger(self):
        output = self.build()
        self.assertEqual(len(output["certificate_checks"]), 12)
        self.assertEqual(len(output["certificate_ledger"]), 6)

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
                    "--certified-at",
                    CERTIFIED_AT,
                ]
            )
            self.assertEqual(rc, 0)
            self.assertTrue(
                (
                    path
                    / "out/registry_snapshot_seal_certificate_v75_2aw.json"
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
