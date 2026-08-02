from pathlib import Path
import tempfile
import unittest

from autonomous_paper_runtime.next_order_cycle import (
    ControlledAutonomousNextOrderCycle,
    NextOrderCycleState,
)


def readiness(state="BLOCKED_ACTIVE_ORDER", **overrides):
    value = {
        "state": state,
        "ready": state == "READY",
        "next_order_allowed": state == "READY",
        "safe_mode_engaged": False,
        "open_order_count": 1 if state == "BLOCKED_ACTIVE_ORDER" else 0,
    }
    value.update(overrides)
    return value


class NextOrderCycleTests(unittest.TestCase):
    def evaluate(self, data, **kwargs):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "cycle.json"
            cycle = ControlledAutonomousNextOrderCycle(
                cycle_token_path=path
            )
            result = cycle.evaluate(
                readiness_result=data,
                symbol=kwargs.get("symbol", "AAPL"),
                side=kwargs.get("side", "BUY"),
                quantity=kwargs.get("quantity", "1"),
                estimated_price=kwargs.get("estimated_price", "50"),
                created_at="2026-08-02T12:00:00+00:00",
                max_quantity=kwargs.get("max_quantity", "1"),
                max_notional=kwargs.get("max_notional", "100"),
                network_requests_executed=kwargs.get("network", 0),
            )
            exists = path.exists()
        return result, exists

    def test_active_order_waits(self):
        r,e=self.evaluate(readiness())
        self.assertEqual(r.state,NextOrderCycleState.WAIT_ACTIVE_ORDER)
        self.assertFalse(r.preview_ready)
        self.assertFalse(e)

    def test_market_closed_waits(self):
        r,_=self.evaluate(readiness("BLOCKED_MARKET_CLOSED"))
        self.assertEqual(r.state,NextOrderCycleState.WAIT_MARKET_CLOSED)

    def test_risk_waits(self):
        r,_=self.evaluate(readiness("BLOCKED_RISK"))
        self.assertEqual(r.state,NextOrderCycleState.WAIT_RISK)

    def test_account_waits(self):
        r,_=self.evaluate(readiness("BLOCKED_ACCOUNT"))
        self.assertEqual(r.state,NextOrderCycleState.WAIT_ACCOUNT)

    def test_exposure_waits(self):
        r,_=self.evaluate(readiness("BLOCKED_EXPOSURE"))
        self.assertEqual(r.state,NextOrderCycleState.WAIT_EXPOSURE)

    def test_terminal_commit_waits(self):
        r,_=self.evaluate(
            readiness("BLOCKED_TERMINAL_NOT_COMMITTED")
        )
        self.assertEqual(r.state,NextOrderCycleState.WAIT_TERMINAL_COMMIT)

    def test_upstream_safe_mode(self):
        r,_=self.evaluate(readiness(
            "SAFE_MODE",
            safe_mode_engaged=True,
        ))
        self.assertEqual(r.state,NextOrderCycleState.SAFE_MODE)

    def test_inconsistent_ready_safe_mode(self):
        r,_=self.evaluate(readiness(
            "READY",
            ready=False,
            next_order_allowed=True,
        ))
        self.assertTrue(r.safe_mode_engaged)

    def test_ready_creates_cycle_token(self):
        r,e=self.evaluate(readiness("READY"))
        self.assertEqual(
            r.state,
            NextOrderCycleState.READY_FOR_SINGLE_ORDER_PREVIEW,
        )
        self.assertTrue(r.cycle_created)
        self.assertTrue(r.preview_ready)
        self.assertTrue(e)

    def test_quantity_cap(self):
        r,_=self.evaluate(
            readiness("READY"),
            quantity="2",
            max_quantity="1",
        )
        self.assertEqual(r.state,NextOrderCycleState.SAFE_MODE)

    def test_notional_cap(self):
        r,_=self.evaluate(
            readiness("READY"),
            estimated_price="150",
            max_notional="100",
        )
        self.assertTrue(r.safe_mode_engaged)

    def test_invalid_side(self):
        r,_=self.evaluate(readiness("READY"),side="SHORT")
        self.assertTrue(r.safe_mode_engaged)

    def test_duplicate_cycle(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/"cycle.json"
            cycle=ControlledAutonomousNextOrderCycle(
                cycle_token_path=path
            )
            kwargs=dict(
                readiness_result=readiness("READY"),
                symbol="AAPL",
                side="BUY",
                quantity="1",
                estimated_price="50",
                created_at="now",
            )
            one=cycle.evaluate(**kwargs)
            two=cycle.evaluate(**kwargs)
            self.assertTrue(one.cycle_created)
            self.assertEqual(
                two.state,
                NextOrderCycleState.DUPLICATE_CYCLE,
            )
            self.assertTrue(two.duplicate_cycle)

    def test_zero_writes(self):
        r,_=self.evaluate(readiness(),network=4)
        self.assertEqual(r.network_requests_executed,4)
        self.assertEqual(r.write_requests_executed,0)
        self.assertEqual(r.actual_paper_orders_submitted,0)
        self.assertEqual(r.live_orders_submitted,0)

    def test_json(self):
        r,_=self.evaluate(readiness())
        self.assertEqual(
            r.to_json_dict()["state"],
            "WAIT_ACTIVE_ORDER",
        )


if __name__=="__main__":
    unittest.main()
