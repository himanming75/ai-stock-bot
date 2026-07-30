import json
import tempfile
import unittest
from pathlib import Path

from tools.offline_paper_order_intent_authorization_v75_2q import (
    OrderIntentAuthorizationError,
    authorization_id,
    build_authorization,
    main,
    sha256_of,
)

ISSUED_AT = "2026-07-30T21:35:00+00:00"
NONCE = "0123456789abcdef0123456789abcdef"


def source_fixture():
    signals = [{
        "action": "BUY",
        "as_of": "2026-07-30T15:30:00+00:00",
        "fast_sma": 633.0,
        "fast_window": 2,
        "latest_price": 633.5,
        "order_created": False,
        "order_submitted": False,
        "price_field": "close",
        "signal_id": "SIG-AB05F6CBC6D960C9",
        "signal_method": "SIMPLE_MOVING_AVERAGE_CROSSOVER",
        "slow_sma": 632.3333333333,
        "slow_window": 3,
        "strategy_id": "CHAMPION_OFFLINE_V1",
        "symbol": "SPY",
    }]
    summary = {
        "buy_count": 1,
        "hold_count": 0,
        "sell_count": 0,
        "signal_count": 1,
        "signal_method": "SIMPLE_MOVING_AVERAGE_CROSSOVER",
        "strategy_id": "CHAMPION_OFFLINE_V1",
        "symbols": ["SPY"],
    }
    checks = [{"check_index": 1, "check": "A", "state": "PASS"}]
    ledger = [{"ledger_index": 1, "event": "A", "state": "PASS"}]
    source = {
        "status": "PASS",
        "decision": "offline_paper_signal_output_validated",
        "validation_id": "SOV-A",
        "validation_state": "READY_FOR_ORDER_INTENT_AUTHORIZATION",
        "signal_execution_id": "SGE-A",
        "authorization_id": "SGA-A",
        "session_id": "PAPER-A",
        "cycle_id": "PCS-A",
        "cycle_sequence": 1,
        "champion_candidate_id": "CAND-A",
        "validated_signal_summary": summary,
        "validated_signals": signals,
        "validation_checks": checks,
        "validation_checks_sha256": sha256_of(checks),
        "validation_ledger": ledger,
        "validation_ledger_sha256": sha256_of(ledger),
        "source_signal_generation_execution_sha256": "a" * 64,
        "source_signal_output_package_sha256": "b" * 64,
        "validation_gate": {
            "signal_output_validated": True,
            "order_intent_authorization_allowed": True,
            "order_generation_allowed": False,
            "fill_simulation_allowed": False,
            "paper_orders_allowed": False,
            "live_orders_allowed": False,
            "network_allowed": False,
            "next_version": "75.2Q",
        },
        "order_generation_allowed": False,
        "fill_simulation_allowed": False,
        "paper_orders_allowed": False,
        "live_orders_allowed": False,
        "network_allowed": False,
        "broker_connection_allowed": False,
        "orders_created": 0,
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
        "schema_version": "v75.2p.offline_paper_signal_output_validation.1",
        "version": "75.2P",
    }
    source["offline_paper_signal_output_validation_sha256"] = sha256_of(source)
    return source


def config_fixture():
    return {
        "authorization_ttl_seconds": 900,
        "authorization_scope": "OFFLINE_PAPER_ORDER_INTENT_CREATION_ONLY",
        "allowed_signal_actions": ["BUY", "SELL", "HOLD"],
        "require_single_use_token": True,
        "require_source_integrity": True,
        "require_validated_signals": True,
        "require_signal_identity_lock": True,
        "require_zero_orders": True,
        "require_safety_lock": True,
        "order_intent_creation_allowed": False,
        "order_generation_allowed": False,
        "fill_simulation_allowed": False,
        "paper_orders_allowed": False,
        "live_orders_allowed": False,
        "network_allowed": False,
        "broker_connection_allowed": False,
        "external_side_effects_allowed": False,
    }


class TestV752Q(unittest.TestCase):
    def build(self):
        return build_authorization(
            source_fixture(), config_fixture(), ISSUED_AT, NONCE
        )

    @staticmethod
    def rehash(source):
        source.pop("offline_paper_signal_output_validation_sha256", None)
        source["offline_paper_signal_output_validation_sha256"] = sha256_of(source)

    def test_pass(self): self.assertEqual(self.build()["status"], "PASS")
    def test_version_schema(self):
        x = self.build()
        self.assertEqual(x["version"], "75.2Q")
        self.assertEqual(
            x["schema_version"],
            "v75.2q.offline_paper_order_intent_authorization.1",
        )
    def test_state(self):
        self.assertEqual(
            self.build()["authorization_state"], "AUTHORIZED_NOT_EXECUTED"
        )
    def test_scope(self):
        self.assertEqual(
            self.build()["authorization_scope"],
            "OFFLINE_PAPER_ORDER_INTENT_CREATION_ONLY",
        )
    def test_authorized(self): self.assertTrue(self.build()["order_intent_authorized"])
    def test_not_created(self): self.assertFalse(self.build()["order_intent_created"])
    def test_execution_allowed(self):
        self.assertTrue(
            self.build()["authorization_gate"][
                "order_intent_creation_execution_allowed"
            ]
        )
    def test_creation_still_blocked(self):
        self.assertFalse(
            self.build()["authorization_gate"]["order_intent_creation_allowed"]
        )
    def test_orders_blocked(self):
        x = self.build()
        self.assertFalse(x["order_generation_allowed"])
        self.assertEqual(x["orders_created"], 0)
        self.assertEqual(x["orders_submitted"], 0)
    def test_signal_manifest(self):
        manifest = self.build()["authorized_signal_manifest"]
        self.assertEqual(len(manifest), 1)
        self.assertEqual(manifest[0]["action"], "BUY")
        self.assertEqual(manifest[0]["symbol"], "SPY")
    def test_token_single_use(self):
        token = self.build()["authorization_token"]
        self.assertTrue(token["single_use"])
        self.assertFalse(token["consumed"])
    def test_token_signal_lock(self):
        self.assertEqual(
            self.build()["authorization_token"]["authorized_signal_ids"],
            ["SIG-AB05F6CBC6D960C9"],
        )
    def test_token_hash(self):
        x = self.build()
        self.assertEqual(
            x["authorization_token_sha256"],
            sha256_of(x["authorization_token"]),
        )
    def test_manifest_hash(self):
        x = self.build()
        self.assertEqual(
            x["authorized_signal_manifest_sha256"],
            sha256_of(x["authorized_signal_manifest"]),
        )
    def test_checks(self): self.assertEqual(len(self.build()["authorization_checks"]), 12)
    def test_ledger(self): self.assertEqual(len(self.build()["authorization_ledger"]), 6)
    def test_hash(self):
        x = self.build()
        observed = x.pop("offline_paper_order_intent_authorization_sha256")
        self.assertEqual(observed, sha256_of(x))
    def test_deterministic_id(self):
        self.assertEqual(authorization_id("A", "B"), authorization_id("A", "B"))
    def test_ttl(self):
        x = self.build()
        self.assertEqual(x["expires_at"], "2026-07-30T21:50:00+00:00")
    def test_bad_source_integrity(self):
        s = source_fixture(); s["cycle_id"] = "BAD"
        self.assertRaises(
            OrderIntentAuthorizationError,
            build_authorization, s, config_fixture(), ISSUED_AT, NONCE
        )
    def test_bad_state(self):
        s = source_fixture(); s["validation_state"] = "BAD"; self.rehash(s)
        self.assertRaises(
            OrderIntentAuthorizationError,
            build_authorization, s, config_fixture(), ISSUED_AT, NONCE
        )
    def test_bad_signal_count(self):
        s = source_fixture()
        s["validated_signal_summary"]["signal_count"] = 2
        self.rehash(s)
        self.assertRaises(
            OrderIntentAuthorizationError,
            build_authorization, s, config_fixture(), ISSUED_AT, NONCE
        )
    def test_duplicate_signal_id(self):
        s = source_fixture()
        s["validated_signals"].append(dict(s["validated_signals"][0]))
        s["validated_signal_summary"]["signal_count"] = 2
        s["validated_signal_summary"]["buy_count"] = 2
        self.rehash(s)
        self.assertRaises(
            OrderIntentAuthorizationError,
            build_authorization, s, config_fixture(), ISSUED_AT, NONCE
        )
    def test_order_side_effect(self):
        s = source_fixture()
        s["validated_signals"][0]["order_created"] = True
        self.rehash(s)
        self.assertRaises(
            OrderIntentAuthorizationError,
            build_authorization, s, config_fixture(), ISSUED_AT, NONCE
        )
    def test_network_enabled(self):
        s = source_fixture(); s["safety_lock"]["network_enabled"] = True; self.rehash(s)
        self.assertRaises(
            OrderIntentAuthorizationError,
            build_authorization, s, config_fixture(), ISSUED_AT, NONCE
        )
    def test_bad_ttl(self):
        c = config_fixture(); c["authorization_ttl_seconds"] = 30
        self.assertRaises(
            OrderIntentAuthorizationError,
            build_authorization, source_fixture(), c, ISSUED_AT, NONCE
        )
    def test_unsafe_config(self):
        c = config_fixture(); c["order_generation_allowed"] = True
        self.assertRaises(
            OrderIntentAuthorizationError,
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
                 "offline_paper_order_intent_authorization_v75_2q.json"
                ).is_file()
            )
            self.assertEqual(main([
                "--input", str(p / "missing.json"),
                "--config", str(p / "config.json"),
                "--output-dir", str(p / "bad"),
            ]), 1)


if __name__ == "__main__":
    unittest.main()
