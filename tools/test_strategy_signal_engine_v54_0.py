import json
import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path

from tools.strategy_signal_engine_v54_0 import (
    RawSignal,
    StrategyDefinition,
    StrategySignalEngine,
    canonical_hash,
    load_payload,
)


def strategy(
    sid="momentum_v1",
    name="Momentum",
    version="1.0",
    enabled=True,
    weight="1",
    actions=None,
):
    return StrategyDefinition(
        strategy_id=sid,
        strategy_name=name,
        strategy_version=version,
        enabled=enabled,
        weight=weight,
        allowed_actions=actions or ["BUY", "SELL", "HOLD"],
        metadata={},
    )


def signal(
    sid="momentum_v1",
    symbol="AAPL",
    action="BUY",
    confidence="0.9",
    priority=50,
    created="2026-07-29T18:00:00Z",
    expires="2026-07-29T20:00:00Z",
):
    return RawSignal(
        strategy_id=sid,
        symbol=symbol,
        action=action,
        confidence=confidence,
        priority=priority,
        created_at=created,
        expires_at=expires,
        rationale="test",
        source_sha256="a" * 64,
        metadata={},
    )


AS_OF = "2026-07-29T19:00:00Z"


class StrategySignalEngineV540Tests(unittest.TestCase):
    def engine(self):
        e = StrategySignalEngine(mode="paper")
        e.register_strategy(strategy())
        return e

    def test_register(self):
        self.assertIn("momentum_v1", self.engine().registry)

    def test_duplicate_strategy(self):
        e = self.engine()
        with self.assertRaises(ValueError):
            e.register_strategy(strategy())

    def test_empty_strategy_id(self):
        with self.assertRaises(ValueError):
            StrategySignalEngine().register_strategy(strategy(sid=""))

    def test_empty_strategy_name(self):
        with self.assertRaises(ValueError):
            StrategySignalEngine().register_strategy(strategy(name=""))

    def test_empty_strategy_version(self):
        with self.assertRaises(ValueError):
            StrategySignalEngine().register_strategy(strategy(version=""))

    def test_bad_weight_low(self):
        with self.assertRaises(ValueError):
            StrategySignalEngine().register_strategy(strategy(weight="-0.1"))

    def test_bad_weight_high(self):
        with self.assertRaises(ValueError):
            StrategySignalEngine().register_strategy(strategy(weight="1.1"))

    def test_bad_weight_text(self):
        with self.assertRaises(ValueError):
            StrategySignalEngine().register_strategy(strategy(weight="x"))

    def test_empty_actions(self):
        s = strategy()
        s = StrategyDefinition(**{**asdict(s), "allowed_actions": []})
        with self.assertRaises(ValueError):
            StrategySignalEngine().register_strategy(s)

    def test_invalid_action_registry(self):
        with self.assertRaises(ValueError):
            StrategySignalEngine().register_strategy(strategy(actions=["BUY", "WAIT"]))

    def test_single_pass(self):
        self.assertEqual("PASS", self.engine().process([signal()], as_of=AS_OF).status)

    def test_decision(self):
        self.assertEqual("signals_selected", self.engine().process([signal()], as_of=AS_OF).decision)

    def test_counts(self):
        r = self.engine().process([signal()], as_of=AS_OF)
        self.assertEqual((1, 1, 1), (r.raw_signal_count, r.normalized_signal_count, r.selected_signal_count))

    def test_symbol_uppercase(self):
        r = self.engine().process([signal(symbol="aapl")], as_of=AS_OF)
        self.assertEqual("AAPL", r.normalized_signals[0]["symbol"])

    def test_action_uppercase(self):
        r = self.engine().process([signal(action="buy")], as_of=AS_OF)
        self.assertEqual("BUY", r.normalized_signals[0]["action"])

    def test_confidence_format(self):
        r = self.engine().process([signal(confidence="0.9")], as_of=AS_OF)
        self.assertEqual("0.900000", r.normalized_signals[0]["confidence"])

    def test_weighted_confidence(self):
        e = StrategySignalEngine()
        e.register_strategy(strategy(weight="0.5"))
        r = e.process([signal(confidence="0.8")], as_of=AS_OF)
        self.assertEqual("0.400000", r.normalized_signals[0]["weighted_confidence"])

    def test_signal_hash(self):
        r = self.engine().process([signal()], as_of=AS_OF)
        self.assertEqual(64, len(r.normalized_signals[0]["signal_sha256"]))

    def test_selection_hash(self):
        r = self.engine().process([signal()], as_of=AS_OF)
        self.assertEqual(64, len(r.selected_signals[0]["selection_sha256"]))

    def test_result_hash(self):
        self.assertEqual(64, len(self.engine().process([signal()], as_of=AS_OF).result_sha256))

    def test_ledger(self):
        r = self.engine().process([signal()], as_of=AS_OF)
        self.assertEqual("GENESIS", r.ledger[0]["previous_entry_sha256"])

    def test_network_false(self):
        self.assertFalse(self.engine().process([signal()], as_of=AS_OF).network_used)

    def test_no_registry_fail(self):
        r = StrategySignalEngine().process([signal()], as_of=AS_OF)
        self.assertEqual("FAIL", r.status)

    def test_empty_as_of_fail(self):
        self.assertEqual("FAIL", self.engine().process([signal()], as_of="").status)

    def test_unregistered_rejected(self):
        r = self.engine().process([signal(sid="other")], as_of=AS_OF)
        self.assertIn("strategy_not_registered", r.rejected_signals[0]["reasons"])

    def test_disabled_rejected(self):
        e = StrategySignalEngine()
        e.register_strategy(strategy(enabled=False))
        r = e.process([signal()], as_of=AS_OF)
        self.assertEqual(1, r.disabled_strategy_signal_count)

    def test_empty_symbol_rejected(self):
        r = self.engine().process([signal(symbol="")], as_of=AS_OF)
        self.assertIn("symbol_required", r.rejected_signals[0]["reasons"])

    def test_invalid_action_rejected(self):
        r = self.engine().process([signal(action="WAIT")], as_of=AS_OF)
        self.assertIn("invalid_action", r.rejected_signals[0]["reasons"])

    def test_disallowed_action_rejected(self):
        e = StrategySignalEngine()
        e.register_strategy(strategy(actions=["BUY"]))
        r = e.process([signal(action="SELL")], as_of=AS_OF)
        self.assertIn("action_not_allowed_for_strategy", r.rejected_signals[0]["reasons"])

    def test_confidence_low_rejected(self):
        r = self.engine().process([signal(confidence="-0.1")], as_of=AS_OF)
        self.assertIn("confidence_out_of_range", r.rejected_signals[0]["reasons"])

    def test_confidence_high_rejected(self):
        r = self.engine().process([signal(confidence="1.1")], as_of=AS_OF)
        self.assertIn("confidence_out_of_range", r.rejected_signals[0]["reasons"])

    def test_confidence_text_rejected(self):
        r = self.engine().process([signal(confidence="x")], as_of=AS_OF)
        self.assertIn("confidence_invalid", r.rejected_signals[0]["reasons"])

    def test_priority_low_rejected(self):
        r = self.engine().process([signal(priority=-1)], as_of=AS_OF)
        self.assertIn("priority_out_of_range", r.rejected_signals[0]["reasons"])

    def test_priority_high_rejected(self):
        r = self.engine().process([signal(priority=101)], as_of=AS_OF)
        self.assertIn("priority_out_of_range", r.rejected_signals[0]["reasons"])

    def test_priority_bool_rejected(self):
        r = self.engine().process([signal(priority=True)], as_of=AS_OF)
        self.assertIn("priority_must_be_integer", r.rejected_signals[0]["reasons"])

    def test_empty_created_rejected(self):
        r = self.engine().process([signal(created="")], as_of=AS_OF)
        self.assertIn("created_at_required", r.rejected_signals[0]["reasons"])

    def test_empty_expiry_rejected(self):
        r = self.engine().process([signal(expires="")], as_of=AS_OF)
        self.assertIn("expires_at_required", r.rejected_signals[0]["reasons"])

    def test_bad_expiry_order(self):
        r = self.engine().process([signal(expires="2026-07-29T17:00:00Z")], as_of="2026-07-29T16:00:00Z")
        self.assertIn("expires_at_must_be_after_created_at", r.rejected_signals[0]["reasons"])

    def test_expired_signal(self):
        r = self.engine().process([signal(expires="2026-07-29T18:30:00Z")], as_of=AS_OF)
        self.assertEqual(1, r.expired_signal_count)

    def test_bad_source_hash(self):
        s = signal()
        s = RawSignal(**{**asdict(s), "source_sha256": "bad"})
        r = self.engine().process([s], as_of=AS_OF)
        self.assertIn("source_sha256_invalid", r.rejected_signals[0]["reasons"])

    def test_duplicate_signal(self):
        s = signal()
        r = self.engine().process([s, s], as_of=AS_OF)
        self.assertEqual(1, r.duplicate_signal_count)

    def test_priority_wins(self):
        e = StrategySignalEngine()
        e.register_many([strategy("a"), strategy("b")])
        a = signal(sid="a", action="BUY", priority=80)
        b = signal(sid="b", action="SELL", priority=20, created="2026-07-29T18:01:00Z")
        r = e.process([b, a], as_of=AS_OF)
        self.assertEqual("BUY", r.selected_signals[0]["selected_action"])

    def test_weighted_confidence_breaks_tie(self):
        e = StrategySignalEngine()
        e.register_many([strategy("a", weight="1"), strategy("b", weight="0.5")])
        a = signal(sid="a", action="BUY", confidence="0.6", priority=50)
        b = signal(sid="b", action="SELL", confidence="0.9", priority=50, created="2026-07-29T18:01:00Z")
        r = e.process([b, a], as_of=AS_OF)
        self.assertEqual("BUY", r.selected_signals[0]["selected_action"])

    def test_conflict_detected(self):
        e = StrategySignalEngine()
        e.register_many([strategy("a"), strategy("b")])
        r = e.process([
            signal(sid="a", action="BUY"),
            signal(sid="b", action="SELL", created="2026-07-29T18:01:00Z")
        ], as_of=AS_OF)
        self.assertTrue(r.selected_signals[0]["conflict_detected"])

    def test_no_conflict_same_action(self):
        e = StrategySignalEngine()
        e.register_many([strategy("a"), strategy("b")])
        r = e.process([
            signal(sid="a", action="BUY"),
            signal(sid="b", action="BUY", created="2026-07-29T18:01:00Z")
        ], as_of=AS_OF)
        self.assertFalse(r.selected_signals[0]["conflict_detected"])

    def test_multiple_symbols(self):
        r = self.engine().process([
            signal(symbol="AAPL"),
            signal(symbol="MSFT", created="2026-07-29T18:01:00Z")
        ], as_of=AS_OF)
        self.assertEqual(2, r.selected_signal_count)

    def test_sorted_symbols(self):
        r = self.engine().process([
            signal(symbol="MSFT"),
            signal(symbol="AAPL", created="2026-07-29T18:01:00Z")
        ], as_of=AS_OF)
        self.assertEqual("AAPL", r.normalized_signals[0]["symbol"])

    def test_deterministic(self):
        a = self.engine().process([signal()], as_of=AS_OF)
        b = self.engine().process([signal()], as_of=AS_OF)
        self.assertEqual(a.result_sha256, b.result_sha256)

    def test_invalid_mode(self):
        with self.assertRaises(ValueError):
            StrategySignalEngine(mode="bad")

    def test_live_gate(self):
        with self.assertRaises(PermissionError):
            StrategySignalEngine(mode="live").process([], as_of=AS_OF)

    def test_live_not_implemented(self):
        with self.assertRaises(NotImplementedError):
            StrategySignalEngine(mode="live", enable_live=True).process([], as_of=AS_OF)

    def test_export(self):
        e = self.engine()
        r = e.process([signal()], as_of=AS_OF)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "out.json"
            e.export(path, r)
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual("PASS", payload["result"]["status"])

    def test_load_payload(self):
        payload = {
            "as_of": AS_OF,
            "strategies": [asdict(strategy())],
            "signals": [asdict(signal())],
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "input.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            strategies, signals, as_of = load_payload(path)
            self.assertEqual((1, 1, AS_OF), (len(strategies), len(signals), as_of))


if __name__ == "__main__":
    unittest.main()
