import json
import tempfile
import unittest
from pathlib import Path

from tools.offline_paper_signal_generation_authorization_v75_2n import (
    SignalGenerationAuthorizationError,
    authorization_id,
    build_authorization,
    main,
    sha256_of,
)

ISSUED_AT = "2026-07-30T21:20:00+00:00"
NONCE = "0123456789abcdef0123456789abcdef"


def source_fixture():
    evidence = {
        "validation_id": "SIV-A",
        "preparation_id": "SIP-A",
        "signal_input_package_sha256": "b" * 64,
        "market_summary": {
            "mode": "STATIC_OFFLINE_FIXTURE",
            "symbol_count": 1,
            "symbols": ["SPY"],
            "bar_count": 3,
            "first_timestamp_by_symbol": {"SPY": "2026-07-29T20:00:00+00:00"},
            "last_timestamp_by_symbol": {"SPY": "2026-07-30T15:30:00+00:00"},
            "bar_count_by_symbol": {"SPY": 3},
            "strict_time_order": True,
            "duplicate_symbol_timestamps": 0,
            "network_source": False,
            "immutable": True,
        },
        "strategy_summary": {
            "strategy_id": "CHAMPION_OFFLINE_V1",
            "price_field": "close",
            "fast_window": 2,
            "slow_window": 3,
            "minimum_history_bars": 3,
            "history_sufficient": True,
            "window_consistency": True,
            "immutable": True,
        },
        "validated_at": "2026-07-30T21:13:00+00:00",
    }
    checks = [{"check_index": 1, "check": "A", "state": "PASS"}]
    ledger = [{"ledger_index": 1, "event": "A", "state": "PASS", "validation_id": "SIV-A"}]
    source = {
        "status": "PASS",
        "decision": "offline_paper_signal_input_validated",
        "validation_id": "SIV-A",
        "validation_state": "READY_FOR_SIGNAL_GENERATION_AUTHORIZATION",
        "preparation_id": "SIP-A",
        "certificate_id": "PBC-A",
        "execution_id": "PCS-A",
        "session_id": "PAPER-A",
        "cycle_id": "PCS-A",
        "cycle_sequence": 1,
        "champion_candidate_id": "CAND-A",
        "validation_evidence": evidence,
        "validation_evidence_sha256": sha256_of(evidence),
        "validation_checks": checks,
        "validation_checks_sha256": sha256_of(checks),
        "validation_ledger": ledger,
        "validation_ledger_sha256": sha256_of(ledger),
        "source_signal_input_preparation_sha256": "a" * 64,
        "source_signal_input_package_sha256": "b" * 64,
        "validation_gate": {
            "signal_input_validated": True,
            "signal_generation_authorization_allowed": True,
            "signal_generation_allowed": False,
            "order_generation_allowed": False,
            "fill_simulation_allowed": False,
            "paper_orders_allowed": False,
            "live_orders_allowed": False,
            "network_allowed": False,
            "next_version": "75.2N",
        },
        "paper_orders_allowed": False,
        "live_orders_allowed": False,
        "network_allowed": False,
        "broker_connection_allowed": False,
        "orders_submitted": 0,
        "approved_for_live": False,
        "network_used": False,
        "safety_lock": {
            "broker_connected": False,
            "broker_credentials_required": False,
            "external_side_effects_allowed": False,
            "live_orders_enabled": False,
            "live_trading_approval_allowed": False,
            "lock_state": "ENFORCED",
            "network_enabled": False,
        },
        "validated_at": "2026-07-30T21:13:00+00:00",
        "schema_version": "v75.2m.offline_paper_signal_input_validation.1",
        "version": "75.2M",
    }
    source["offline_paper_signal_input_validation_sha256"] = sha256_of(source)
    return source


def config_fixture():
    return {
        "authorization_ttl_seconds": 900,
        "authorization_scope": "OFFLINE_PAPER_SIGNAL_GENERATION_ONLY",
        "require_single_use_token": True,
        "require_source_integrity": True,
        "require_validated_inputs": True,
        "require_safety_lock": True,
        "require_zero_orders": True,
        "signal_generation_allowed": False,
        "order_generation_allowed": False,
        "fill_simulation_allowed": False,
        "paper_orders_allowed": False,
        "live_orders_allowed": False,
        "network_allowed": False,
        "broker_connection_allowed": False,
        "external_side_effects_allowed": False,
    }


class TestV752N(unittest.TestCase):
    def build(self):
        return build_authorization(
            source_fixture(), config_fixture(), ISSUED_AT, NONCE
        )

    @staticmethod
    def rehash(source):
        source.pop("offline_paper_signal_input_validation_sha256", None)
        source["offline_paper_signal_input_validation_sha256"] = sha256_of(source)

    def test_pass(self): self.assertEqual(self.build()["status"], "PASS")
    def test_version_schema(self):
        x = self.build()
        self.assertEqual(x["version"], "75.2N")
        self.assertEqual(
            x["schema_version"],
            "v75.2n.offline_paper_signal_generation_authorization.1",
        )
    def test_state(self):
        self.assertEqual(
            self.build()["authorization_state"], "AUTHORIZED_NOT_EXECUTED"
        )
    def test_scope(self):
        self.assertEqual(
            self.build()["authorization_scope"],
            "OFFLINE_PAPER_SIGNAL_GENERATION_ONLY",
        )
    def test_authorized(self):
        self.assertTrue(self.build()["signal_generation_authorized"])
    def test_not_executed(self):
        self.assertFalse(self.build()["signal_generation_executed"])
    def test_execution_allowed(self):
        self.assertTrue(
            self.build()["authorization_gate"]["signal_generation_execution_allowed"]
        )
    def test_generation_still_blocked(self):
        self.assertFalse(
            self.build()["authorization_gate"]["signal_generation_allowed"]
        )
    def test_order_blocked(self):
        self.assertFalse(
            self.build()["authorization_gate"]["order_generation_allowed"]
        )
    def test_token_single_use(self):
        token = self.build()["authorization_token"]
        self.assertTrue(token["single_use"])
        self.assertFalse(token["consumed"])
    def test_token_state(self):
        self.assertEqual(
            self.build()["authorization_token"]["token_state"],
            "ISSUED_NOT_CONSUMED",
        )
    def test_token_hash(self):
        x = self.build()
        self.assertEqual(
            x["authorization_token_sha256"],
            sha256_of(x["authorization_token"]),
        )
    def test_checks(self): self.assertEqual(len(self.build()["authorization_checks"]), 12)
    def test_ledger(self): self.assertEqual(len(self.build()["authorization_ledger"]), 6)
    def test_hash(self):
        x = self.build()
        observed = x.pop(
            "offline_paper_signal_generation_authorization_sha256"
        )
        self.assertEqual(observed, sha256_of(x))
    def test_deterministic_id(self):
        self.assertEqual(authorization_id("A", "B"), authorization_id("A", "B"))
    def test_ttl(self):
        x = self.build()
        self.assertEqual(x["authorization_ttl_seconds"], 900)
        self.assertEqual(x["expires_at"], "2026-07-30T21:35:00+00:00")
    def test_bad_source_integrity(self):
        s = source_fixture(); s["cycle_id"] = "BAD"
        self.assertRaises(
            SignalGenerationAuthorizationError,
            build_authorization, s, config_fixture(), ISSUED_AT, NONCE
        )
    def test_bad_state(self):
        s = source_fixture(); s["validation_state"] = "BAD"; self.rehash(s)
        self.assertRaises(
            SignalGenerationAuthorizationError,
            build_authorization, s, config_fixture(), ISSUED_AT, NONCE
        )
    def test_not_validated(self):
        s = source_fixture()
        s["validation_gate"]["signal_input_validated"] = False
        self.rehash(s)
        self.assertRaises(
            SignalGenerationAuthorizationError,
            build_authorization, s, config_fixture(), ISSUED_AT, NONCE
        )
    def test_duplicate_evidence(self):
        s = source_fixture()
        s["validation_evidence"]["market_summary"]["duplicate_symbol_timestamps"] = 1
        s["validation_evidence_sha256"] = sha256_of(s["validation_evidence"])
        self.rehash(s)
        self.assertRaises(
            SignalGenerationAuthorizationError,
            build_authorization, s, config_fixture(), ISSUED_AT, NONCE
        )
    def test_insufficient_history(self):
        s = source_fixture()
        s["validation_evidence"]["strategy_summary"]["history_sufficient"] = False
        s["validation_evidence_sha256"] = sha256_of(s["validation_evidence"])
        self.rehash(s)
        self.assertRaises(
            SignalGenerationAuthorizationError,
            build_authorization, s, config_fixture(), ISSUED_AT, NONCE
        )
    def test_network_enabled(self):
        s = source_fixture(); s["safety_lock"]["network_enabled"] = True; self.rehash(s)
        self.assertRaises(
            SignalGenerationAuthorizationError,
            build_authorization, s, config_fixture(), ISSUED_AT, NONCE
        )
    def test_bad_ttl(self):
        c = config_fixture(); c["authorization_ttl_seconds"] = 30
        self.assertRaises(
            SignalGenerationAuthorizationError,
            build_authorization, source_fixture(), c, ISSUED_AT, NONCE
        )
    def test_unsafe_config(self):
        c = config_fixture(); c["signal_generation_allowed"] = True
        self.assertRaises(
            SignalGenerationAuthorizationError,
            build_authorization, source_fixture(), c, ISSUED_AT, NONCE
        )
    def test_main_success_failure(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            (p / "source.json").write_text(
                json.dumps(source_fixture()), encoding="utf-8"
            )
            (p / "config.json").write_text(
                json.dumps(config_fixture()), encoding="utf-8"
            )
            self.assertEqual(main([
                "--input", str(p / "source.json"),
                "--config", str(p / "config.json"),
                "--output-dir", str(p / "out"),
                "--issued-at", ISSUED_AT,
                "--nonce", NONCE,
            ]), 0)
            self.assertTrue(
                (p / "out" /
                 "offline_paper_signal_generation_authorization_v75_2n.json"
                ).is_file()
            )
            self.assertEqual(main([
                "--input", str(p / "missing.json"),
                "--config", str(p / "config.json"),
                "--output-dir", str(p / "bad"),
            ]), 1)


if __name__ == "__main__":
    unittest.main()
