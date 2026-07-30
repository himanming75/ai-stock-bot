import json
import tempfile
import unittest
from pathlib import Path

from tools.offline_paper_signal_input_validator_v75_2m import (
    SignalInputValidationError,
    build_validation,
    main,
    sha256_of,
    validation_id,
)

VALIDATED_AT = "2026-07-30T21:15:00+00:00"


def source_fixture():
    checks = [{"check_index": 1, "check": "A", "state": "PASS"}]
    ledger = [{"ledger_index": 1, "event": "A", "state": "READY", "preparation_id": "SIP-A"}]
    package = {
        "preparation_id": "SIP-A",
        "cycle_id": "PCS-A",
        "cycle_sequence": 1,
        "session_id": "PAPER-A",
        "champion_candidate_id": "CAND-A",
        "market_data": {
            "mode": "STATIC_OFFLINE_FIXTURE",
            "symbols": ["SPY"],
            "bars": [
                {"symbol": "SPY", "timestamp": "2026-07-29T20:00:00+00:00", "open": 630.0, "high": 632.0, "low": 629.0, "close": 631.0, "volume": 1000000},
                {"symbol": "SPY", "timestamp": "2026-07-30T14:30:00+00:00", "open": 631.0, "high": 633.0, "low": 630.5, "close": 632.5, "volume": 1200000},
                {"symbol": "SPY", "timestamp": "2026-07-30T15:30:00+00:00", "open": 632.5, "high": 634.0, "low": 632.0, "close": 633.5, "volume": 900000},
            ],
            "bar_count": 3,
            "network_source": False,
            "immutable": True,
        },
        "strategy_inputs": {
            "strategy_id": "CHAMPION_OFFLINE_V1",
            "fast_window": 2,
            "slow_window": 3,
            "price_field": "close",
            "minimum_history_bars": 3,
            "immutable": True,
        },
        "prepared_at": "2026-07-30T21:07:40+00:00",
    }
    source = {
        "status": "PASS",
        "decision": "offline_paper_signal_input_prepared",
        "preparation_id": "SIP-A",
        "preparation_state": "READY_FOR_SIGNAL_INPUT_VALIDATION",
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
        "source_runtime_baseline_certificate_sha256": "a" * 64,
        "preparation_gate": {
            "signal_input_prepared": True,
            "signal_input_validation_allowed": True,
            "signal_generation_allowed": False,
            "order_generation_allowed": False,
            "fill_simulation_allowed": False,
            "paper_orders_allowed": False,
            "live_orders_allowed": False,
            "network_allowed": False,
            "next_version": "75.2M",
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
        "prepared_at": "2026-07-30T21:07:40+00:00",
        "schema_version": "v75.2l.offline_paper_signal_input_preparation.1",
        "version": "75.2L",
    }
    source["offline_paper_signal_input_preparation_sha256"] = sha256_of(source)
    return source


def config_fixture():
    return {
        "required_input_mode": "STATIC_OFFLINE_FIXTURE",
        "require_package_immutable": True,
        "require_strategy_immutable": True,
        "require_network_source_false": True,
        "require_strict_time_order": True,
        "require_unique_symbol_timestamps": True,
        "require_valid_ohlc": True,
        "require_nonnegative_volume": True,
        "require_strategy_window_consistency": True,
        "require_minimum_history": True,
        "allowed_price_fields": ["open", "high", "low", "close"],
        "signal_generation_allowed": False,
        "order_generation_allowed": False,
        "fill_simulation_allowed": False,
        "paper_orders_allowed": False,
        "live_orders_allowed": False,
        "network_allowed": False,
        "broker_connection_allowed": False,
        "external_side_effects_allowed": False,
    }


class TestV752M(unittest.TestCase):
    def build(self):
        return build_validation(source_fixture(), config_fixture(), VALIDATED_AT)

    @staticmethod
    def rehash(source):
        source["signal_input_package_sha256"] = sha256_of(source["signal_input_package"])
        source.pop("offline_paper_signal_input_preparation_sha256", None)
        source["offline_paper_signal_input_preparation_sha256"] = sha256_of(source)

    def test_pass(self): self.assertEqual(self.build()["status"], "PASS")
    def test_version_schema(self):
        x = self.build()
        self.assertEqual(x["version"], "75.2M")
        self.assertEqual(x["schema_version"], "v75.2m.offline_paper_signal_input_validation.1")
    def test_state(self): self.assertEqual(self.build()["validation_state"], "READY_FOR_SIGNAL_GENERATION_AUTHORIZATION")
    def test_validated(self): self.assertTrue(self.build()["validation_gate"]["signal_input_validated"])
    def test_authorization_allowed(self): self.assertTrue(self.build()["validation_gate"]["signal_generation_authorization_allowed"])
    def test_signal_blocked(self): self.assertFalse(self.build()["validation_gate"]["signal_generation_allowed"])
    def test_order_blocked(self): self.assertFalse(self.build()["validation_gate"]["order_generation_allowed"])
    def test_network_blocked(self): self.assertFalse(self.build()["network_allowed"])
    def test_orders_zero(self): self.assertEqual(self.build()["orders_submitted"], 0)
    def test_market_summary(self):
        s = self.build()["validation_evidence"]["market_summary"]
        self.assertEqual(s["bar_count"], 3)
        self.assertTrue(s["strict_time_order"])
    def test_strategy_summary(self):
        s = self.build()["validation_evidence"]["strategy_summary"]
        self.assertTrue(s["history_sufficient"])
        self.assertTrue(s["window_consistency"])
    def test_checks(self): self.assertEqual(len(self.build()["validation_checks"]), 15)
    def test_ledger(self): self.assertEqual(len(self.build()["validation_ledger"]), 6)
    def test_hash(self):
        x = self.build()
        observed = x.pop("offline_paper_signal_input_validation_sha256")
        self.assertEqual(observed, sha256_of(x))
    def test_evidence_hash(self):
        x = self.build()
        self.assertEqual(x["validation_evidence_sha256"], sha256_of(x["validation_evidence"]))
    def test_deterministic_id(self):
        self.assertEqual(validation_id("A", "B"), validation_id("A", "B"))
    def test_bad_source_integrity(self):
        s = source_fixture(); s["cycle_id"] = "BAD"
        self.assertRaises(SignalInputValidationError, build_validation, s, config_fixture(), VALIDATED_AT)
    def test_bad_ohlc(self):
        s = source_fixture(); s["signal_input_package"]["market_data"]["bars"][0]["high"] = 620
        self.rehash(s)
        self.assertRaises(SignalInputValidationError, build_validation, s, config_fixture(), VALIDATED_AT)
    def test_duplicate_bar(self):
        s = source_fixture()
        s["signal_input_package"]["market_data"]["bars"].append(
            dict(s["signal_input_package"]["market_data"]["bars"][0])
        )
        s["signal_input_package"]["market_data"]["bar_count"] = 4
        self.rehash(s)
        self.assertRaises(SignalInputValidationError, build_validation, s, config_fixture(), VALIDATED_AT)
    def test_out_of_order(self):
        s = source_fixture()
        bars = s["signal_input_package"]["market_data"]["bars"]
        bars[0], bars[1] = bars[1], bars[0]
        self.rehash(s)
        self.assertRaises(SignalInputValidationError, build_validation, s, config_fixture(), VALIDATED_AT)
    def test_insufficient_history(self):
        s = source_fixture()
        s["signal_input_package"]["market_data"]["bars"].pop()
        s["signal_input_package"]["market_data"]["bar_count"] = 2
        self.rehash(s)
        self.assertRaises(SignalInputValidationError, build_validation, s, config_fixture(), VALIDATED_AT)
    def test_bad_window_order(self):
        s = source_fixture()
        s["signal_input_package"]["strategy_inputs"]["fast_window"] = 3
        self.rehash(s)
        self.assertRaises(SignalInputValidationError, build_validation, s, config_fixture(), VALIDATED_AT)
    def test_bad_price_field(self):
        s = source_fixture()
        s["signal_input_package"]["strategy_inputs"]["price_field"] = "adjusted_close"
        self.rehash(s)
        self.assertRaises(SignalInputValidationError, build_validation, s, config_fixture(), VALIDATED_AT)
    def test_network_source(self):
        s = source_fixture()
        s["signal_input_package"]["market_data"]["network_source"] = True
        self.rehash(s)
        self.assertRaises(SignalInputValidationError, build_validation, s, config_fixture(), VALIDATED_AT)
    def test_unsafe_config(self):
        c = config_fixture(); c["signal_generation_allowed"] = True
        self.assertRaises(SignalInputValidationError, build_validation, source_fixture(), c, VALIDATED_AT)
    def test_main_success_failure(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            (p / "source.json").write_text(json.dumps(source_fixture()), encoding="utf-8")
            (p / "config.json").write_text(json.dumps(config_fixture()), encoding="utf-8")
            self.assertEqual(main([
                "--input", str(p / "source.json"),
                "--config", str(p / "config.json"),
                "--output-dir", str(p / "out"),
                "--validated-at", VALIDATED_AT,
            ]), 0)
            self.assertTrue(
                (p / "out" / "offline_paper_signal_input_validation_v75_2m.json").is_file()
            )
            self.assertEqual(main([
                "--input", str(p / "missing.json"),
                "--config", str(p / "config.json"),
                "--output-dir", str(p / "bad"),
            ]), 1)


if __name__ == "__main__":
    unittest.main()
