import hashlib
import json
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from tools.paper_trade_scenario_generator_v67_0 import (
    VERSION,
    SCHEMA_VERSION,
    ScenarioError,
    canonical_json,
    generate_report,
    main,
    parse_symbols,
    run,
)


class TestV67(unittest.TestCase):
    def test_version(self):
        self.assertEqual(VERSION, "67.0")

    def test_schema(self):
        self.assertEqual(SCHEMA_VERSION, "v67.0.paper_trade_scenarios.1")

    def test_parse_symbols(self):
        self.assertEqual(parse_symbols("aapl, msft"), ["AAPL", "MSFT"])

    def test_empty_symbols(self):
        with self.assertRaises(ScenarioError):
            parse_symbols(" , ")

    def test_invalid_symbol(self):
        with self.assertRaises(ScenarioError):
            parse_symbols("AA$L")

    def test_trade_count(self):
        r = generate_report(20, ["AAPL"], 1, "mixed", 10, Decimal("100"))
        self.assertEqual(r["trade_count"], 20)

    def test_all_closed(self):
        r = generate_report(20, ["AAPL"], 1, "mixed", 10, Decimal("100"))
        self.assertEqual(r["closed_trade_count"], 20)
        self.assertEqual(r["open_trade_count"], 0)

    def test_network_false(self):
        r = generate_report(5, ["AAPL"], 1, "mixed", 10, Decimal("100"))
        self.assertFalse(r["network_used"])

    def test_never_live(self):
        r = generate_report(5, ["AAPL"], 1, "mixed", 10, Decimal("100"))
        self.assertFalse(r["approved_for_live"])

    def test_deterministic(self):
        a = generate_report(20, ["AAPL", "MSFT"], 42, "mixed", 10, Decimal("100"))
        b = generate_report(20, ["AAPL", "MSFT"], 42, "mixed", 10, Decimal("100"))
        self.assertEqual(a, b)

    def test_seed_changes_output(self):
        a = generate_report(20, ["AAPL"], 42, "mixed", 10, Decimal("100"))
        b = generate_report(20, ["AAPL"], 43, "mixed", 10, Decimal("100"))
        self.assertNotEqual(a["scenario_report_sha256"], b["scenario_report_sha256"])

    def test_trade_hash_length(self):
        r = generate_report(1, ["AAPL"], 1, "mixed", 10, Decimal("100"))
        self.assertEqual(len(r["trades"][0]["trade_sha256"]), 64)

    def test_report_hash_length(self):
        r = generate_report(1, ["AAPL"], 1, "mixed", 10, Decimal("100"))
        self.assertEqual(len(r["scenario_report_sha256"]), 64)

    def test_report_hash_matches(self):
        r = generate_report(2, ["AAPL"], 1, "mixed", 10, Decimal("100"))
        copy = dict(r)
        observed = copy.pop("scenario_report_sha256")
        expected = hashlib.sha256(canonical_json(copy).encode()).hexdigest()
        self.assertEqual(observed, expected)

    def test_winning_scenario(self):
        r = generate_report(30, ["AAPL"], 1, "winning", 10, Decimal("100"))
        self.assertEqual(r["summary"]["win_count"], 30)

    def test_losing_scenario(self):
        r = generate_report(30, ["AAPL"], 1, "losing", 10, Decimal("100"))
        self.assertEqual(r["summary"]["loss_count"], 30)

    def test_mixed_has_wins_and_losses(self):
        r = generate_report(30, ["AAPL"], 1, "mixed", 10, Decimal("100"))
        self.assertGreater(r["summary"]["win_count"], 0)
        self.assertGreater(r["summary"]["loss_count"], 0)

    def test_volatile_supported(self):
        r = generate_report(10, ["AAPL"], 1, "volatile", 10, Decimal("100"))
        self.assertEqual(r["scenario"], "volatile")

    def test_symbol_rotation(self):
        r = generate_report(3, ["AAPL", "MSFT"], 1, "mixed", 10, Decimal("100"))
        self.assertEqual([t["symbol"] for t in r["trades"]], ["AAPL", "MSFT", "AAPL"])

    def test_unique_ids(self):
        r = generate_report(100, ["AAPL"], 1, "mixed", 10, Decimal("100"))
        ids = [t["trade_id"] for t in r["trades"]]
        self.assertEqual(len(ids), len(set(ids)))

    def test_closed_status(self):
        r = generate_report(5, ["AAPL"], 1, "mixed", 10, Decimal("100"))
        self.assertTrue(all(t["status"] == "CLOSED" for t in r["trades"]))

    def test_long_side(self):
        r = generate_report(5, ["AAPL"], 1, "mixed", 10, Decimal("100"))
        self.assertTrue(all(t["side"] == "LONG" for t in r["trades"]))

    def test_positive_quantity(self):
        with self.assertRaises(ScenarioError):
            generate_report(5, ["AAPL"], 1, "mixed", 0, Decimal("100"))

    def test_positive_price(self):
        with self.assertRaises(ScenarioError):
            generate_report(5, ["AAPL"], 1, "mixed", 10, Decimal("0"))

    def test_min_trade_count(self):
        with self.assertRaises(ScenarioError):
            generate_report(0, ["AAPL"], 1, "mixed", 10, Decimal("100"))

    def test_max_trade_count(self):
        with self.assertRaises(ScenarioError):
            generate_report(100001, ["AAPL"], 1, "mixed", 10, Decimal("100"))

    def test_run_writes(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "result.json"
            r = run(out, 10, ["AAPL"], 1, "mixed", 10, Decimal("100"))
            self.assertTrue(out.exists())
            self.assertEqual(json.loads(out.read_text()), r)

    def test_main_success(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "result.json"
            code = main(["--trade-count", "20", "--output", str(out)])
            self.assertEqual(code, 0)
            self.assertTrue(out.exists())

    def test_main_failure(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "result.json"
            code = main(["--trade-count", "0", "--output", str(out)])
            self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
