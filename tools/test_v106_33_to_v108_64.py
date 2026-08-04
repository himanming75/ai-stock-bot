import tempfile,unittest
from pathlib import Path

from fast_track_paper.orders import build_orders
from fast_track_paper.fills import simulate_fills
from fast_track_paper.positions import open_positions
from fast_track_paper.lifecycle import process_tick
from fast_track_paper.close import daily_close
from fast_track_paper.analytics import calculate_analytics
from fast_track_paper.engine import evaluate

class Tests(unittest.TestCase):
    def test_orders(self):
        rows=build_orders(
            {"plans":[{
                "state":"AUTHORIZED_FOR_PAPER_SIMULATION",
                "strategy_id":"S1",
                "target_weight_pct":50,
                "plan_key":"p1",
            }]},
            100000,
            {"SPY":100},
            {"S1":"SPY"},
        )
        self.assertEqual(rows[0]["requested_quantity"],500)

    def test_fills(self):
        orders=[{
            "paper_order_id":"o1",
            "strategy_id":"S1",
            "symbol":"SPY",
            "requested_quantity":10,
            "reference_price":100,
        }]
        rows=simulate_fills(
            orders,
            {"deterministic_fill_ratios":[0.5],"slippage_bps":0},
        )
        self.assertEqual(rows[0]["filled_quantity"],5)

    def test_positions(self):
        rows=open_positions([{
            "strategy_id":"S1","symbol":"SPY",
            "filled_quantity":5,"fill_price":100,
        }])
        self.assertEqual(rows[0]["quantity"],5)

    def test_take_profit(self):
        positions=[{
            "strategy_id":"S1","symbol":"SPY","quantity":5,
            "average_cost":100,"highest_price":100,"state":"OPEN",
        }]
        value=process_tick(
            positions,{"SPY":106},
            {"stop_loss_pct":3,"take_profit_pct":5,"trailing_stop_pct":2},
        )
        self.assertEqual(value["exits"][0]["exit_reason"],"TAKE_PROFIT")

    def test_stop_loss(self):
        positions=[{
            "strategy_id":"S1","symbol":"SPY","quantity":5,
            "average_cost":100,"highest_price":100,"state":"OPEN",
        }]
        value=process_tick(
            positions,{"SPY":96},
            {"stop_loss_pct":3,"take_profit_pct":5,"trailing_stop_pct":2},
        )
        self.assertEqual(value["exits"][0]["exit_reason"],"STOP_LOSS")

    def test_close(self):
        value=daily_close(
            100000,
            [{"symbol":"SPY","quantity":5,"average_cost":100,"state":"OPEN"}],
            [{"fill_notional":500}],
            [],
            {"SPY":102},
        )
        self.assertEqual(value["ending_equity"],100010)

    def test_analytics(self):
        value=calculate_analytics([],{"ending_equity":101000},100000)
        self.assertEqual(value["daily_return_pct"],1.0)

    def test_missing_source(self):
        with tempfile.TemporaryDirectory() as temp:
            result=evaluate(Path(temp))
            self.assertEqual(result["state"],"FAST_TRACK_PAPER_SOURCE_REQUIRED")

    def test_orders_zero(self):
        with tempfile.TemporaryDirectory() as temp:
            self.assertEqual(evaluate(Path(temp))["actual_orders_submitted"],0)

if __name__=="__main__":
    unittest.main()
