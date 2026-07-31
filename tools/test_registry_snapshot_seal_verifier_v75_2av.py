import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from tools.registry_snapshot_seal_verifier_v75_2av import *


def config():
    return {
        "verification_scope": "OFFLINE_PAPER_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_VERIFICATION_ONLY",
        "require_seal_integrity": True,
        "require_seal_manifest_integrity": True,
        "require_sealed_snapshot_index_integrity": True,
        "require_seal_checks_integrity": True,
        "require_seal_ledger_integrity": True,
        "require_deterministic_seal_id": True,
        "require_receipt_linkage_and_notional_preservation": True,
        "require_zero_settlement_and_account_mutations": True,
        "create_verified_sealed_snapshot_index": True,
        "create_verification_checks": True,
        "create_verification_ledger": True,
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
    sealed_at = "2026-07-31T10:00:00-07:00"
    snapshot_verification_id = "CRSX-AAAAAAAAAAAAAAAA"
    source_hash = "b" * 64
    seal_id = "CRSS-" + hashlib.sha256(
        f"{snapshot_verification_id}|{source_hash}|{sealed_at}|75.2AU".encode("utf-8")
    ).hexdigest()[:16].upper()

    index = [
        {
            "seal_record_index": 1,
            "verification_record_index": 1,
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
            "seal_state": "SEALED_VERIFIED_SNAPSHOTTED_REGISTERED_CERTIFIED_ARCHIVED_OFFLINE_RECEIPT",
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
            "seal_id": seal_id,
        }
        for i in range(1, 7)
    ]

    manifest = {
        "seal_id": seal_id,
        "snapshot_verification_id": snapshot_verification_id,
        "snapshot_id": "CRSN-AAAAAAAAAAAAAAAA",
        "registry_verification_id": "FCRX-AAAAAAAAAAAAAAAA",
        "registry_id": "FCRS-AAAAAAAAAAAAAAAA",
        "receipt_batch_id": "FRB-A",
        "sealed_receipt_count": 1,
        "seal_effect": "OFFLINE_FINAL_EVIDENCE_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_ONLY",
        "seal_state": "SEALED_VERIFIED_OFFLINE_CERTIFICATE_REGISTRY_SNAPSHOT",
        "sealed_at": sealed_at,
    }

    value = {
        "status": "PASS",
        "decision": "offline_paper_certificate_registry_snapshot_sealed",
        "certificate_registry_snapshot_seal_id": seal_id,
        "certificate_registry_snapshot_verification_id": snapshot_verification_id,
        "certificate_registry_snapshot_id": "CRSN-AAAAAAAAAAAAAAAA",
        "certificate_registry_verification_id": "FCRX-AAAAAAAAAAAAAAAA",
        "certificate_registry_id": "FCRS-AAAAAAAAAAAAAAAA",
        "receipt_batch_id": "FRB-A",
        "seal_scope": "OFFLINE_PAPER_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_ONLY",
        "seal_state": "SEALED_VERIFIED_OFFLINE_CERTIFICATE_REGISTRY_SNAPSHOT",
        "sealed_at": sealed_at,
        "seal_manifest": manifest,
        "seal_manifest_sha256": sha256_of(manifest),
        "sealed_receipt_count": 1,
        "sealed_snapshot_index": index,
        "sealed_snapshot_index_sha256": sha256_of(index),
        "seal_checks": checks,
        "seal_checks_sha256": sha256_of(checks),
        "seal_ledger": ledger,
        "seal_ledger_sha256": sha256_of(ledger),
        "seal_gate": {
            "certificate_registry_snapshot_sealed": True,
            "seal_immutable": True,
            "seal_effect": "OFFLINE_FINAL_EVIDENCE_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL_ONLY",
            "settlement_execution_allowed": False,
            "position_update_allowed": False,
            "cash_update_allowed": False,
            "portfolio_update_allowed": False,
            "external_order_submission_allowed": False,
            "broker_routing_allowed": False,
            "paper_broker_allowed": False,
            "live_orders_allowed": False,
            "network_allowed": False,
            "next_version": "75.2AV",
        },
        "source_snapshot_verification_sha256": source_hash,
        "source_verified_snapshot_index_sha256": "c" * 64,
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
        "schema_version": "v75.2au.offline_paper_certificate_registry_snapshot_seal.1",
        "version": "75.2AU",
    }

    value["offline_paper_certificate_registry_snapshot_seal_sha256"] = sha256_of(value)
    return value


class TestV752AV(unittest.TestCase):
    def build(self):
        return verify_seal(source(), config())

    @staticmethod
    def rehash(value):
        value.pop("offline_paper_certificate_registry_snapshot_seal_sha256", None)
        value["offline_paper_certificate_registry_snapshot_seal_sha256"] = sha256_of(value)

    def test_pass(self):
        self.assertEqual(self.build()["status"], "PASS")

    def test_state(self):
        self.assertEqual(
            self.build()["verification_state"],
            "VERIFIED_OFFLINE_CERTIFICATE_REGISTRY_SNAPSHOT_SEAL",
        )

    def test_count(self):
        self.assertEqual(self.build()["verified_sealed_receipt_count"], 1)

    def test_deterministic_verification_id(self):
        self.assertEqual(
            self.build()["certificate_registry_snapshot_seal_verification_id"],
            self.build()["certificate_registry_snapshot_seal_verification_id"],
        )

    def test_verified_index_state(self):
        self.assertEqual(
            self.build()["verified_sealed_snapshot_index"][0]["verification_state"],
            "VERIFIED_SEALED_SNAPSHOTTED_REGISTERED_CERTIFIED_ARCHIVED_OFFLINE_RECEIPT",
        )

    def test_hashes(self):
        output = self.build()
        self.assertEqual(
            output["verified_sealed_snapshot_index_sha256"],
            sha256_of(output["verified_sealed_snapshot_index"]),
        )
        self.assertEqual(
            output["verification_checks_sha256"],
            sha256_of(output["verification_checks"]),
        )
        self.assertEqual(
            output["verification_ledger_sha256"],
            sha256_of(output["verification_ledger"]),
        )

    def test_output_hash(self):
        output = self.build()
        observed = output.pop(
            "offline_paper_certificate_registry_snapshot_seal_verification_sha256"
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
        verify_seal(value, config())
        self.assertEqual(value, original)

    def test_tampered_source(self):
        value = source()
        value["cycle_id"] = "BAD"
        self.assertRaises(
            RegistrySnapshotSealVerificationError,
            verify_seal,
            value,
            config(),
        )

    def test_tampered_manifest(self):
        value = source()
        value["seal_manifest"]["receipt_batch_id"] = "BAD"
        value["seal_manifest_sha256"] = sha256_of(value["seal_manifest"])
        self.rehash(value)
        self.assertRaises(
            RegistrySnapshotSealVerificationError,
            verify_seal,
            value,
            config(),
        )

    def test_tampered_index(self):
        value = source()
        value["sealed_snapshot_index"][0]["notional_value"] = 1
        value["sealed_snapshot_index_sha256"] = sha256_of(value["sealed_snapshot_index"])
        self.rehash(value)
        self.assertRaises(
            RegistrySnapshotSealVerificationError,
            verify_seal,
            value,
            config(),
        )

    def test_wrong_seal_id(self):
        value = source()
        value["certificate_registry_snapshot_seal_id"] = "CRSS-BADBADBADBADBADB"
        value["seal_manifest"]["seal_id"] = value["certificate_registry_snapshot_seal_id"]
        value["seal_manifest_sha256"] = sha256_of(value["seal_manifest"])
        self.rehash(value)
        self.assertRaises(
            RegistrySnapshotSealVerificationError,
            verify_seal,
            value,
            config(),
        )

    def test_settlement_rejected(self):
        value = source()
        value["settlements_created"] = 1
        self.rehash(value)
        self.assertRaises(
            RegistrySnapshotSealVerificationError,
            verify_seal,
            value,
            config(),
        )

    def test_unsafe_config(self):
        value = config()
        value["network_allowed"] = True
        self.assertRaises(
            RegistrySnapshotSealVerificationError,
            verify_seal,
            source(),
            value,
        )

    def test_checks_ledger(self):
        output = self.build()
        self.assertEqual(len(output["verification_checks"]), 12)
        self.assertEqual(len(output["verification_ledger"]), 6)

    def test_main_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / "source.json").write_text(json.dumps(source()), encoding="utf-8")
            (path / "config.json").write_text(json.dumps(config()), encoding="utf-8")
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
                (path / "out/registry_snapshot_seal_verification_v75_2av.json").exists()
            )

    def test_missing_input(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / "config.json").write_text(json.dumps(config()), encoding="utf-8")
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
