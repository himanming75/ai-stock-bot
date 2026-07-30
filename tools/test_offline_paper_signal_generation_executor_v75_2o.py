import json
import tempfile
import unittest
from pathlib import Path

from tools.offline_paper_signal_generation_executor_v75_2o import (
    SignalGenerationExecutionError,
    build_execution,
    execution_id,
    main,
    sha256_of,
)

EXECUTED_AT = "2026-07-30T21:25:00+00:00"


def preparation_fixture():
    package = {
        "preparation_id": "SIP-A",
        "cycle_id": "PCS-A",
        "cycle_sequence": 1,
        "session_id": "PAPER-A",
        "champion_candidate_id": "CAND-A",
        "prepared_at": "2026-07-30T21:07:40+00:00",
        "market_data": {
            "bar_count": 3,
            "bars": [
                {"symbol": "SPY", "timestamp": "2026-07-29T20:00:00+00:00", "open": 630.0, "high": 632.0, "low": 629.0, "close": 631.0, "volume": 1000000},
                {"symbol": "SPY", "timestamp": "2026-07-30T14:30:00+00:00", "open": 631.0, "high": 633.0, "low": 630.5, "close": 632.5, "volume": 1200000},
                {"symbol": "SPY", "timestamp": "2026-07-30T15:30:00+00:00", "open": 632.5, "high": 634.0, "low": 632.0, "close": 633.5, "volume": 900000},
            ],
            "immutable": True,
            "mode": "STATIC_OFFLINE_FIXTURE",
            "network_source": False,
            "symbols": ["SPY"],
        },
        "strategy_inputs": {
            "fast_window": 2,
            "immutable": True,
            "minimum_history_bars": 3,
            "price_field": "close",
            "slow_window": 3,
            "strategy_id": "CHAMPION_OFFLINE_V1",
        },
    }
    checks = [{"check_index": 1, "check": "A", "state": "PASS"}]
    ledger = [{"ledger_index": 1, "event": "A", "state": "PASS"}]
    source = {
        "status": "PASS",
        "preparation_id": "SIP-A",
        "certificate_id": "PBC-A",
        "execution_id": "PCS-A",
        "session_id": "PAPER-A",
        "cycle_id": "PCS-A",
        "cycle_sequence": 1,
        "champion_candidate_id": "CAND-A",
        "signal_input_package": package,
        "signal_input_package_sha256": sha256_of(package),
        "preparation_checks": checks,
        "preparation_checks_sha256": sha256_of(checks),
        "preparation_ledger": ledger,
        "preparation_ledger_sha256": sha256_of(ledger),
        "schema_version": "v75.2l.offline_paper_signal_input_preparation.1",
        "version": "75.2L",
    }
    source["offline_paper_signal_input_preparation_sha256"] = sha256_of(source)
    return source


def authorization_fixture(package_hash):
    token_material = {
        "authorization_id": "SGA-A",
        "validation_id": "SIV-A",
        "issued_at": "2026-07-30T21:20:00+00:00",
        "expires_at": "2026-07-30T21:35:00+00:00",
        "nonce": "0123456789abcdef0123456789abcdef",
        "scope": "OFFLINE_PAPER_SIGNAL_GENERATION_ONLY",
    }
    token = {
        **token_material,
        "token_sha256": sha256_of(token_material),
        "single_use": True,
        "consumed": False,
        "consumed_at": None,
        "token_state": "ISSUED_NOT_CONSUMED",
    }
    checks = [{"check_index": 1, "check": "A", "state": "PASS"}]
    ledger = [{"ledger_index": 1, "event": "A", "state": "PASS"}]
    source = {
        "status": "PASS",
        "authorization_id": "SGA-A",
        "authorization_scope": "OFFLINE_PAPER_SIGNAL_GENERATION_ONLY",
        "authorization_state": "AUTHORIZED_NOT_EXECUTED",
        "signal_generation_authorized": True,
        "signal_generation_executed": False,
        "token_consumed": False,
        "authorization_token": token,
        "authorization_token_sha256": sha256_of(token),
        "authorization_checks": checks,
        "authorization_checks_sha256": sha256_of(checks),
        "authorization_ledger": ledger,
        "authorization_ledger_sha256": sha256_of(ledger),
        "source_signal_input_package_sha256": package_hash,
        "validation_id": "SIV-A",
        "preparation_id": "SIP-A",
        "certificate_id": "PBC-A",
        "execution_id": "PCS-A",
        "session_id": "PAPER-A",
        "cycle_id": "PCS-A",
        "cycle_sequence": 1,
        "champion_candidate_id": "CAND-A",
        "authorization_gate": {
            "signal_generation_authorized": True,
            "signal_generation_execution_allowed": True,
            "signal_generation_allowed": False,
            "order_generation_allowed": False,
            "fill_simulation_allowed": False,
            "paper_orders_allowed": False,
            "live_orders_allowed": False,
            "network_allowed": False,
            "next_version": "75.2O",
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
        "schema_version": "v75.2n.offline_paper_signal_generation_authorization.1",
        "version": "75.2N",
    }
    source["offline_paper_signal_generation_authorization_sha256"] = sha256_of(source)
    return source


def config_fixture():
    return {
        "execution_scope": "OFFLINE_PAPER_SIGNAL_GENERATION_ONLY",
        "signal_method": "SIMPLE_MOVING_AVERAGE_CROSSOVER",
        "buy_when_fast_above_slow": True,
        "sell_when_fast_below_slow": True,
        "hold_when_equal": True,
        "require_authorization_integrity": True,
        "require_input_package_integrity": True,
        "require_single_use_token": True,
        "require_token_unconsumed": True,
        "require_token_unexpired": True,
        "require_static_offline_fixture": True,
        "require_immutable_inputs": True,
        "prevent_output_overwrite": True,
        "order_generation_allowed": False,
        "fill_simulation_allowed": False,
        "paper_orders_allowed": False,
        "live_orders_allowed": False,
        "network_allowed": False,
        "broker_connection_allowed": False,
        "external_side_effects_allowed": False,
    }


class TestV752O(unittest.TestCase):
    def fixtures(self):
        p = preparation_fixture()
        a = authorization_fixture(p["signal_input_package_sha256"])
        return a, p, config_fixture()

    def build(self):
        a, p, c = self.fixtures()
        return build_execution(a, p, c, EXECUTED_AT)

    @staticmethod
    def rehash_auth(auth):
        auth.pop("offline_paper_signal_generation_authorization_sha256", None)
        auth["offline_paper_signal_generation_authorization_sha256"] = sha256_of(auth)

    def test_pass(self): self.assertEqual(self.build()["status"], "PASS")
    def test_version_schema(self):
        x = self.build()
        self.assertEqual(x["version"], "75.2O")
        self.assertEqual(x["schema_version"], "v75.2o.offline_paper_signal_generation_execution.1")
    def test_state(self): self.assertEqual(self.build()["execution_state"], "READY_FOR_SIGNAL_OUTPUT_VALIDATION")
    def test_executed(self): self.assertTrue(self.build()["signal_generation_executed"])
    def test_token_consumed(self): self.assertTrue(self.build()["token_consumed"])
    def test_consumed_token_state(self): self.assertEqual(self.build()["consumed_authorization_token"]["token_state"], "CONSUMED")
    def test_signal_count(self): self.assertEqual(self.build()["signal_output_package"]["signal_summary"]["signal_count"], 1)
    def test_buy_signal(self):
        signal = self.build()["signal_output_package"]["signals"][0]
        self.assertEqual(signal["action"], "BUY")
        self.assertEqual(signal["fast_sma"], 633.0)
        self.assertAlmostEqual(signal["slow_sma"], 632.3333333333)
    def test_no_order(self):
        x = self.build()
        self.assertEqual(x["orders_created"], 0)
        self.assertEqual(x["orders_submitted"], 0)
        self.assertFalse(x["order_generation_allowed"])
    def test_network_blocked(self): self.assertFalse(self.build()["network_allowed"])
    def test_output_validation_allowed(self): self.assertTrue(self.build()["execution_gate"]["signal_output_validation_allowed"])
    def test_checks(self): self.assertEqual(len(self.build()["execution_checks"]), 12)
    def test_ledger(self): self.assertEqual(len(self.build()["execution_ledger"]), 6)
    def test_hash(self):
        x = self.build()
        observed = x.pop("offline_paper_signal_generation_execution_sha256")
        self.assertEqual(observed, sha256_of(x))
    def test_package_hash(self):
        x = self.build()
        self.assertEqual(x["signal_output_package_sha256"], sha256_of(x["signal_output_package"]))
    def test_deterministic_id(self): self.assertEqual(execution_id("A", "B"), execution_id("A", "B"))
    def test_expired(self):
        a, p, c = self.fixtures()
        self.assertRaises(SignalGenerationExecutionError, build_execution, a, p, c, "2026-07-30T21:36:00+00:00")
    def test_before_issuance(self):
        a, p, c = self.fixtures()
        self.assertRaises(SignalGenerationExecutionError, build_execution, a, p, c, "2026-07-30T21:19:59+00:00")
    def test_consumed_source_token(self):
        a, p, c = self.fixtures()
        a["authorization_token"]["consumed"] = True
        a["authorization_token"]["token_state"] = "CONSUMED"
        a["authorization_token_sha256"] = sha256_of(a["authorization_token"])
        self.rehash_auth(a)
        self.assertRaises(SignalGenerationExecutionError, build_execution, a, p, c, EXECUTED_AT)
    def test_bad_auth_integrity(self):
        a, p, c = self.fixtures(); a["cycle_id"] = "BAD"
        self.assertRaises(SignalGenerationExecutionError, build_execution, a, p, c, EXECUTED_AT)
    def test_package_hash_mismatch(self):
        a, p, c = self.fixtures(); a["source_signal_input_package_sha256"] = "f" * 64; self.rehash_auth(a)
        self.assertRaises(SignalGenerationExecutionError, build_execution, a, p, c, EXECUTED_AT)
    def test_identity_mismatch(self):
        a, p, c = self.fixtures(); p["session_id"] = "BAD"
        p.pop("offline_paper_signal_input_preparation_sha256")
        p["offline_paper_signal_input_preparation_sha256"] = sha256_of(p)
        self.assertRaises(SignalGenerationExecutionError, build_execution, a, p, c, EXECUTED_AT)
    def test_unsafe_config(self):
        a, p, c = self.fixtures(); c["order_generation_allowed"] = True
        self.assertRaises(SignalGenerationExecutionError, build_execution, a, p, c, EXECUTED_AT)
    def test_main_success_and_overwrite_failure(self):
        with tempfile.TemporaryDirectory() as td:
            pth = Path(td)
            a, p, c = self.fixtures()
            (pth/"a.json").write_text(json.dumps(a), encoding="utf-8")
            (pth/"p.json").write_text(json.dumps(p), encoding="utf-8")
            (pth/"c.json").write_text(json.dumps(c), encoding="utf-8")
            args = [
                "--authorization", str(pth/"a.json"),
                "--signal-input", str(pth/"p.json"),
                "--config", str(pth/"c.json"),
                "--output-dir", str(pth/"out"),
                "--executed-at", EXECUTED_AT,
            ]
            self.assertEqual(main(args), 0)
            self.assertEqual(main(args), 1)
    def test_main_missing(self):
        with tempfile.TemporaryDirectory() as td:
            pth = Path(td)
            (pth/"c.json").write_text(json.dumps(config_fixture()), encoding="utf-8")
            self.assertEqual(main([
                "--authorization", str(pth/"missing.json"),
                "--signal-input", str(pth/"missing2.json"),
                "--config", str(pth/"c.json"),
                "--output-dir", str(pth/"out"),
            ]), 1)


if __name__ == "__main__":
    unittest.main()
