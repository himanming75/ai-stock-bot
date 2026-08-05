from pathlib import Path
import tempfile
import unittest

from autonomous_paper_runtime.cycle_continuation import (
    AutonomousCycleContinuationOrchestrator,
)
from autonomous_paper_runtime.final_submission_approval import (
    FinalPaperSubmissionApprovalGate,
)


def terminal(status="ACCEPTED", observed=False, committed=False, safe=False):
    return {
        "terminal_observed": observed,
        "terminal_committed": committed,
        "safe_mode_engaged": safe,
        "monitor_report": {
            "final_status": status,
            "terminal": observed,
            "safe_mode_engaged": safe,
        },
        "commit_report": {
            "committed": committed,
            "duplicate_commit": False,
            "safe_mode_engaged": safe,
        },
    }


class T(unittest.TestCase):
    def run_case(
        self,
        *,
        terminal_result=None,
        orders=None,
        market=True,
        risk=True,
        phrase="",
    ):
        with tempfile.TemporaryDirectory() as temp:
            o=AutonomousCycleContinuationOrchestrator(
                root=Path(temp)
            )
            return o.run(
                terminal_monitor_result=terminal_result or terminal(),
                account={"status":"ACTIVE","trading_blocked":False},
                open_orders=orders if orders is not None else [{"status":"ACCEPTED"}],
                positions=[],
                market_is_open=market,
                risk_approved=risk,
                symbol="AAPL",
                side="BUY",
                quantity="1",
                estimated_price="50",
                approval_phrase=phrase,
                created_at="2026-08-02T15:00:00+00:00",
                network_requests_executed=4,
            )

    def test_active_order_stops_at_cycle(self):
        r=self.run_case()
        self.assertEqual(r.final_state,"WAIT_ACTIVE_ORDER")
        self.assertEqual(r.stopped_at,"CYCLE_GATE")
        self.assertFalse(r.actual_submission_allowed)

    def test_market_closed_wait(self):
        r=self.run_case(
            terminal_result=terminal("FILLED",True,True),
            orders=[],
            market=False,
        )
        self.assertEqual(r.final_state,"WAIT_MARKET_CLOSED")

    def test_risk_wait(self):
        r=self.run_case(
            terminal_result=terminal("FILLED",True,True),
            orders=[],
            risk=False,
        )
        self.assertEqual(r.final_state,"WAIT_RISK")

    def test_safe_mode(self):
        r=self.run_case(
            terminal_result=terminal("MYSTERY",False,False,True),
            orders=[],
        )
        self.assertTrue(r.safe_mode_engaged)

    def test_ready_reaches_human_approval(self):
        r=self.run_case(
            terminal_result=terminal("FILLED",True,True),
            orders=[],
        )
        self.assertEqual(r.final_state,"READY_FOR_HUMAN_APPROVAL")
        self.assertFalse(r.actual_submission_allowed)
        self.assertEqual(r.stopped_at,"FINAL_APPROVAL_GATE")

    def test_exact_phrase_allows_submission_flag_only(self):
        r=self.run_case(
            terminal_result=terminal("FILLED",True,True),
            orders=[],
            phrase=FinalPaperSubmissionApprovalGate.REQUIRED_PHRASE,
        )
        self.assertEqual(
            r.final_state,
            "APPROVED_FOR_SINGLE_PAPER_SUBMISSION",
        )
        self.assertTrue(r.actual_submission_allowed)
        self.assertEqual(r.actual_paper_orders_submitted,0)

    def test_no_broker_writes(self):
        r=self.run_case()
        self.assertEqual(r.network_requests_executed,4)
        self.assertEqual(r.write_requests_executed,0)
        self.assertEqual(r.actual_paper_orders_submitted,0)
        self.assertEqual(r.live_orders_submitted,0)

    def test_json(self):
        r=self.run_case()
        raw=r.to_json_dict()
        self.assertIn("readiness_result",raw)
        self.assertEqual(raw["final_state"],"WAIT_ACTIVE_ORDER")


if __name__=="__main__":
    unittest.main()
