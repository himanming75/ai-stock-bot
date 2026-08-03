import tempfile, unittest
from pathlib import Path
from portfolio_rebalance.models import (
    target_weights,
    current_weights,
    merge_weight_rows,
)
from portfolio_rebalance.mapping import strategy_symbol_map
from portfolio_rebalance.planner import build_trade_intents
from portfolio_rebalance.turnover import apply_turnover_limit
from portfolio_rebalance.dedup import deduplicate_intents
from portfolio_rebalance.risk import evaluate_rebalance_risk
from portfolio_rebalance.engine import evaluate

class Tests(unittest.TestCase):
    def test_target_weights(self):
        value=target_weights({
            "allocation":{
                "allocations":[{"strategy_id":"A","target_weight_pct":40}],
                "cash_weight_pct":10,
            }
        })
        self.assertEqual(value["A"],40)
        self.assertEqual(value["CASH"],10)

    def test_current_weights(self):
        value=current_weights(
            1000,100,[{"strategy_id":"A","market_value":400}]
        )
        self.assertEqual(value["A"],40)
        self.assertEqual(value["CASH"],10)

    def test_merge(self):
        rows=merge_weight_rows({"A":40},{"A":30})
        self.assertEqual(rows[0]["weight_gap_pct"],10)

    def test_mapping(self):
        value=strategy_symbol_map({
            "strategy_symbol_map":[
                {"strategy_id":"A","symbol":"aapl"}
            ]
        })
        self.assertEqual(value["A"],"AAPL")

    def test_planner(self):
        intents=build_trade_intents(
            [{"strategy_id":"A","target_weight_pct":40,
              "current_weight_pct":20,"weight_gap_pct":20}],
            100000,
            {"A":"AAPL"},
            {"AAPL":200},
            {"minimum_rebalance_gap_pct":2,
             "minimum_trade_notional":100,
             "maximum_trade_notional":50000},
        )
        self.assertEqual(intents[0]["side"],"BUY")
        self.assertFalse(intents[0]["submission_allowed"])

    def test_turnover(self):
        value=apply_turnover_limit(
            [
                {
                    "side":"BUY",
                    "weight_gap_pct":20,
                    "planned_notional":20000,
                    "quantity":100,
                },
                {
                    "side":"BUY",
                    "weight_gap_pct":10,
                    "planned_notional":10000,
                    "quantity":50,
                },
            ],
            100000,
            30000,
            {
                "maximum_turnover_pct":25,
                "minimum_projected_cash_pct":10,
            },
        )
        self.assertAlmostEqual(value["used_total_notional"],20000)
        self.assertAlmostEqual(
            value["projected_cash_pct_after_limits"],10.0
        )

    def test_sell_first_preserves_cash(self):
        value=apply_turnover_limit(
            [
                {
                    "side":"BUY","weight_gap_pct":20,
                    "planned_notional":20000,"quantity":100,
                },
                {
                    "side":"SELL","weight_gap_pct":-8,
                    "planned_notional":8000,"quantity":20,
                },
            ],
            100000,
            12000,
            {
                "maximum_turnover_pct":25,
                "minimum_projected_cash_pct":10,
            },
        )
        self.assertGreaterEqual(
            value["projected_cash_pct_after_limits"],10
        )
        self.assertLessEqual(value["used_turnover_pct"],25)

    def test_dedup(self):
        value=deduplicate_intents(
            [{"intent_key":"a"},{"intent_key":"a"}],
            [],
        )
        self.assertEqual(value["duplicate_count"],1)

    def test_risk(self):
        value=evaluate_rebalance_risk(
            [{
                "side":"BUY",
                "planned_notional":1000,
                "submission_allowed":False,
            }],
            10,
            10000,
            3000,
            {"minimum_projected_cash_pct":10,
             "maximum_intent_count":5},
        )
        self.assertTrue(value["passed"])

    def test_missing_source(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(
                evaluate(Path(t))["state"],
                "PORTFOLIO_REBALANCE_SOURCE_REQUIRED",
            )

    def test_safety(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertFalse(evaluate(Path(t))["order_submission_enabled"])

if __name__=="__main__":
    unittest.main()
