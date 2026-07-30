import hashlib
import json
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from tools.multi_strategy_scenario_builder_v69_1 import (
    VERSION,
    SCHEMA_VERSION,
    V67_SCHEMA_VERSION,
    ScenarioBuilderError,
    build_bundle,
    build_v67_report,
    canonical_json,
    main,
    parse_symbols,
    write_bundle,
)


class TestV691(unittest.TestCase):
    def test_version(self):
        self.assertEqual(VERSION, "69.1")

    def test_schema(self):
        self.assertEqual(SCHEMA_VERSION, "v69.1.multi_strategy_scenario_builder.1")

    def test_v67_schema(self):
        self.assertEqual(V67_SCHEMA_VERSION, "v67.0.paper_trade_scenarios.1")

    def test_default_bundle(self):
        b = build_bundle(["momentum", "mean_reversion", "breakout"])
        self.assertEqual(b["status"], "PASS")
        self.assertEqual(b["strategy_count"], 3)

    def test_total_trade_count(self):
        b = build_bundle(["momentum", "mean_reversion", "breakout"], trade_count=100)
        self.assertEqual(b["total_trade_count"], 300)

    def test_unique_strategy_profiles(self):
        b = build_bundle(["momentum", "mean_reversion", "breakout"], trade_count=100)
        pnls = [b["reports"][s]["summary"]["net_pnl"] for s in b["strategies"]]
        self.assertEqual(len(set(pnls)), 3)

    def test_all_closed(self):
        r = build_v67_report("momentum", 10, ["AAPL"], 1, 10, Decimal("100"))
        self.assertEqual(r["closed_trade_count"], 10)
        self.assertEqual(r["open_trade_count"], 0)
        self.assertTrue(all(t["status"] == "CLOSED" for t in r["trades"]))

    def test_strategy_name(self):
        r = build_v67_report("breakout", 5, ["AAPL"], 1, 10, Decimal("100"))
        self.assertTrue(all(t["strategy"] == "breakout" for t in r["trades"]))

    def test_network_false(self):
        b = build_bundle(["momentum", "mean_reversion"])
        self.assertFalse(b["network_used"])
        self.assertTrue(all(not r["network_used"] for r in b["reports"].values()))

    def test_never_live(self):
        b = build_bundle(["momentum", "mean_reversion"])
        self.assertFalse(b["approved_for_live"])

    def test_deterministic(self):
        a = build_bundle(["momentum", "mean_reversion"], seed=99)
        b = build_bundle(["momentum", "mean_reversion"], seed=99)
        self.assertEqual(a, b)

    def test_seed_changes(self):
        a = build_bundle(["momentum"], seed=99)
        b = build_bundle(["momentum"], seed=100)
        self.assertNotEqual(a["reports"]["momentum"]["scenario_report_sha256"],
                            b["reports"]["momentum"]["scenario_report_sha256"])

    def test_trade_hashes(self):
        r = build_v67_report("momentum", 10, ["AAPL"], 1, 10, Decimal("100"))
        self.assertTrue(all(len(t["trade_sha256"]) == 64 for t in r["trades"]))

    def test_bundle_hash(self):
        b = build_bundle(["momentum", "mean_reversion"])
        c = dict(b)
        observed = c.pop("bundle_sha256")
        expected = hashlib.sha256(canonical_json(c).encode()).hexdigest()
        self.assertEqual(observed, expected)

    def test_bad_strategy(self):
        with self.assertRaises(ScenarioBuilderError):
            build_bundle(["unknown"])

    def test_duplicate_strategy(self):
        with self.assertRaises(ScenarioBuilderError):
            build_bundle(["momentum", "momentum"])

    def test_bad_trade_count(self):
        with self.assertRaises(ScenarioBuilderError):
            build_v67_report("momentum", 0, ["AAPL"], 1, 10, Decimal("100"))

    def test_bad_quantity(self):
        with self.assertRaises(ScenarioBuilderError):
            build_v67_report("momentum", 1, ["AAPL"], 1, 0, Decimal("100"))

    def test_bad_price(self):
        with self.assertRaises(ScenarioBuilderError):
            build_v67_report("momentum", 1, ["AAPL"], 1, 10, Decimal("0"))

    def test_parse_symbols(self):
        self.assertEqual(parse_symbols("aapl, msft"), ["AAPL", "MSFT"])

    def test_duplicate_symbols(self):
        with self.assertRaises(ScenarioBuilderError):
            parse_symbols("AAPL,AAPL")

    def test_write_bundle(self):
        with tempfile.TemporaryDirectory() as td:
            b = build_bundle(["momentum", "mean_reversion"], trade_count=5)
            paths = write_bundle(b, Path(td))
            self.assertTrue(paths["momentum"].exists())
            self.assertTrue(paths["mean_reversion"].exists())
            self.assertTrue(paths["manifest"].exists())

    def test_main_success(self):
        with tempfile.TemporaryDirectory() as td:
            code = main([
                "--strategies", "momentum,mean_reversion,breakout",
                "--trade-count", "10",
                "--output-dir", td,
            ])
            self.assertEqual(code, 0)
            self.assertTrue((Path(td) / "multi_strategy_scenario_manifest_v69_1.json").exists())

    def test_main_failure(self):
        with tempfile.TemporaryDirectory() as td:
            code = main([
                "--strategies", "unknown",
                "--output-dir", td,
            ])
            self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
