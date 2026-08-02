from decimal import Decimal
from pathlib import Path
import tempfile
import unittest

from autonomous_paper_runtime.next_order_readiness import (
    AutonomousNextOrderReadinessGate,
    NextOrderReadinessState,
)


def terminal_result(**overrides):
    value = {
        "terminal_observed": False,
        "terminal_committed": False,
        "safe_mode_engaged": False,
        "monitor_report": {
            "final_status": "ACCEPTED",
            "terminal": False,
            "safe_mode_engaged": False,
        },
        "commit_report": {
            "committed": False,
            "duplicate_commit": False,
            "safe_mode_engaged": False,
        },
    }
    value.update(overrides)
    return value


class ReadinessTests(unittest.TestCase):
    def evaluate(
        self,
        *,
        terminal=None,
        account=None,
        orders=(),
        positions=(),
        market=True,
        risk=True,
        max_positions=3,
        max_value=Decimal("1000"),
    ):
        with tempfile.TemporaryDirectory() as temp:
            gate=AutonomousNextOrderReadinessGate(
                readiness_snapshot_path=Path(temp)/"readiness.json"
            )
            report=gate.evaluate(
                terminal_monitor_result=terminal or terminal_result(),
                account=account or {
                    "status":"ACTIVE",
                    "trading_blocked":False,
                },
                open_orders=list(orders),
                positions=list(positions),
                market_is_open=market,
                risk_approved=risk,
                max_positions=max_positions,
                max_total_market_value=max_value,
                network_requests_executed=4,
            )
            snapshot=(Path(temp)/"readiness.json").exists()
        return report,snapshot

    def test_active_order_blocks(self):
        r,s=self.evaluate()
        self.assertEqual(r.state,NextOrderReadinessState.BLOCKED_ACTIVE_ORDER)
        self.assertFalse(r.ready)
        self.assertTrue(s)

    def test_open_order_blocks(self):
        t=terminal_result(
            terminal_observed=True,
            terminal_committed=True,
            monitor_report={"final_status":"FILLED","terminal":True},
            commit_report={"committed":True},
        )
        r,_=self.evaluate(terminal=t,orders=[{"symbol":"AAPL"}])
        self.assertEqual(r.state,NextOrderReadinessState.BLOCKED_ACTIVE_ORDER)

    def test_terminal_not_committed_blocks(self):
        t=terminal_result(
            terminal_observed=True,
            terminal_committed=False,
            monitor_report={"final_status":"CANCELED","terminal":True},
        )
        r,_=self.evaluate(terminal=t)
        self.assertEqual(
            r.state,
            NextOrderReadinessState.BLOCKED_TERMINAL_NOT_COMMITTED,
        )

    def test_account_inactive_blocks(self):
        t=terminal_result(
            terminal_observed=True,
            terminal_committed=True,
            monitor_report={"final_status":"FILLED","terminal":True},
            commit_report={"committed":True},
        )
        r,_=self.evaluate(
            terminal=t,
            account={"status":"INACTIVE","trading_blocked":False},
        )
        self.assertEqual(r.state,NextOrderReadinessState.BLOCKED_ACCOUNT)

    def test_trading_blocked(self):
        t=terminal_result(
            terminal_observed=True,
            terminal_committed=True,
            monitor_report={"final_status":"FILLED","terminal":True},
            commit_report={"committed":True},
        )
        r,_=self.evaluate(
            terminal=t,
            account={"status":"ACTIVE","trading_blocked":True},
        )
        self.assertEqual(r.state,NextOrderReadinessState.BLOCKED_ACCOUNT)

    def test_market_closed(self):
        t=terminal_result(
            terminal_observed=True,
            terminal_committed=True,
            monitor_report={"final_status":"FILLED","terminal":True},
            commit_report={"committed":True},
        )
        r,_=self.evaluate(terminal=t,market=False)
        self.assertEqual(
            r.state,
            NextOrderReadinessState.BLOCKED_MARKET_CLOSED,
        )

    def test_risk_not_approved(self):
        t=terminal_result(
            terminal_observed=True,
            terminal_committed=True,
            monitor_report={"final_status":"FILLED","terminal":True},
            commit_report={"committed":True},
        )
        r,_=self.evaluate(terminal=t,risk=False)
        self.assertEqual(r.state,NextOrderReadinessState.BLOCKED_RISK)

    def test_position_count_cap(self):
        t=terminal_result(
            terminal_observed=True,
            terminal_committed=True,
            monitor_report={"final_status":"FILLED","terminal":True},
            commit_report={"committed":True},
        )
        positions=[{"market_value":"10"}]*4
        r,_=self.evaluate(terminal=t,positions=positions,max_positions=3)
        self.assertEqual(r.state,NextOrderReadinessState.BLOCKED_EXPOSURE)

    def test_market_value_cap(self):
        t=terminal_result(
            terminal_observed=True,
            terminal_committed=True,
            monitor_report={"final_status":"FILLED","terminal":True},
            commit_report={"committed":True},
        )
        r,_=self.evaluate(
            terminal=t,
            positions=[{"market_value":"1200"}],
            max_value=Decimal("1000"),
        )
        self.assertEqual(r.state,NextOrderReadinessState.BLOCKED_EXPOSURE)

    def test_safe_mode(self):
        t=terminal_result(
            safe_mode_engaged=True,
            monitor_report={
                "final_status":"MYSTERY",
                "terminal":False,
                "safe_mode_engaged":True,
            },
        )
        r,_=self.evaluate(terminal=t)
        self.assertEqual(r.state,NextOrderReadinessState.SAFE_MODE)

    def test_ready(self):
        t=terminal_result(
            terminal_observed=True,
            terminal_committed=True,
            monitor_report={"final_status":"FILLED","terminal":True},
            commit_report={"committed":True},
        )
        r,_=self.evaluate(
            terminal=t,
            orders=[],
            positions=[{"market_value":"100"}],
            market=True,
            risk=True,
        )
        self.assertEqual(r.state,NextOrderReadinessState.READY)
        self.assertTrue(r.next_order_allowed)

    def test_zero_broker_writes(self):
        r,_=self.evaluate()
        self.assertEqual(r.network_requests_executed,4)
        self.assertEqual(r.write_requests_executed,0)
        self.assertEqual(r.actual_paper_orders_submitted,0)
        self.assertEqual(r.live_orders_submitted,0)

    def test_validation(self):
        with tempfile.TemporaryDirectory() as temp:
            gate=AutonomousNextOrderReadinessGate(
                readiness_snapshot_path=Path(temp)/"x.json"
            )
            with self.assertRaises(ValueError):
                gate.evaluate(
                    terminal_monitor_result=terminal_result(),
                    account={"status":"ACTIVE"},
                    open_orders=[],
                    positions=[],
                    market_is_open=True,
                    risk_approved=True,
                    max_positions=-1,
                    max_total_market_value=Decimal("1"),
                )

    def test_json(self):
        r,_=self.evaluate()
        self.assertEqual(
            r.to_json_dict()["state"],
            "BLOCKED_ACTIVE_ORDER",
        )


if __name__=="__main__":
    unittest.main()
