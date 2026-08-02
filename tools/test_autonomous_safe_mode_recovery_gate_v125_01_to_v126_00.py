from __future__ import annotations

import unittest

from autonomous_paper_runtime.safe_mode_gate import (
    AutonomousSafeModeRecoveryGate,
    RecoveryGateState,
)


def states():
    return {
        "account_state": {
            "account_status": "ACTIVE",
            "trading_blocked": False,
        },
        "ledger_state": {
            "ledger_recovery_status": "RECOVERED",
            "unknown_count": 0,
            "external_count": 0,
        },
        "portfolio_state": {
            "reconciliation_status": "MATCHED",
            "blocking_mismatch_count": 0,
        },
        "recovery_state": {"recovery_valid": True},
        "runtime_state": {
            "runtime_state": "STOPPED",
            "live_trading_enabled": False,
        },
        "risk_state": {
            "risk_ready": True,
            "kill_switch_engaged": False,
            "emergency_stop_engaged": False,
        },
    }


class SafeModeRecoveryGateTests(unittest.TestCase):
    def setUp(self):
        self.gate = AutonomousSafeModeRecoveryGate()

    def test_default_read_only_ready(self):
        report = self.gate.evaluate(**states())
        self.assertEqual(report.state, RecoveryGateState.READ_ONLY_READY)
        self.assertFalse(report.autonomous_order_allowed)

    def test_paper_write_ready_requires_exact_approval(self):
        report = self.gate.evaluate(
            **states(),
            write_enablement_requested=True,
            approval_text=self.gate.APPROVAL_TEXT,
        )
        self.assertEqual(report.state, RecoveryGateState.PAPER_WRITE_READY)
        self.assertTrue(report.autonomous_order_allowed)

    def test_wrong_approval_stays_read_only(self):
        report = self.gate.evaluate(
            **states(),
            write_enablement_requested=True,
            approval_text="WRONG",
        )
        self.assertEqual(report.state, RecoveryGateState.READ_ONLY_READY)

    def test_inactive_account_safe_mode(self):
        data = states()
        data["account_state"]["account_status"] = "INACTIVE"
        self.assertEqual(
            self.gate.evaluate(**data).state,
            RecoveryGateState.SAFE_MODE,
        )

    def test_trading_blocked_safe_mode(self):
        data = states()
        data["account_state"]["trading_blocked"] = True
        self.assertTrue(self.gate.evaluate(**data).safe_mode_engaged)

    def test_ledger_not_recovered(self):
        data = states()
        data["ledger_state"]["ledger_recovery_status"] = "EXTERNAL_ORDER"
        self.assertEqual(
            self.gate.evaluate(**data).state,
            RecoveryGateState.SAFE_MODE,
        )

    def test_unknown_order_blocks(self):
        data = states()
        data["ledger_state"]["unknown_count"] = 1
        self.assertTrue(self.gate.evaluate(**data).safe_mode_engaged)

    def test_external_order_blocks(self):
        data = states()
        data["ledger_state"]["external_count"] = 1
        self.assertTrue(self.gate.evaluate(**data).safe_mode_engaged)

    def test_portfolio_mismatch_blocks(self):
        data = states()
        data["portfolio_state"]["reconciliation_status"] = "SAFE_MODE"
        self.assertTrue(self.gate.evaluate(**data).safe_mode_engaged)

    def test_invalid_recovery_blocks(self):
        data = states()
        data["recovery_state"]["recovery_valid"] = False
        self.assertTrue(self.gate.evaluate(**data).safe_mode_engaged)

    def test_bad_runtime_state_blocks(self):
        data = states()
        data["runtime_state"]["runtime_state"] = "RUNNING_UNVERIFIED"
        self.assertTrue(self.gate.evaluate(**data).safe_mode_engaged)

    def test_risk_not_ready_blocks(self):
        data = states()
        data["risk_state"]["risk_ready"] = False
        self.assertTrue(self.gate.evaluate(**data).safe_mode_engaged)

    def test_kill_switch_blocks(self):
        data = states()
        data["risk_state"]["kill_switch_engaged"] = True
        self.assertTrue(self.gate.evaluate(**data).safe_mode_engaged)

    def test_emergency_stop_blocks(self):
        data = states()
        data["risk_state"]["emergency_stop_engaged"] = True
        self.assertTrue(self.gate.evaluate(**data).safe_mode_engaged)

    def test_live_enabled_blocks(self):
        data = states()
        data["runtime_state"]["live_trading_enabled"] = True
        self.assertTrue(self.gate.evaluate(**data).safe_mode_engaged)

    def test_failure_overrides_approval(self):
        data = states()
        data["risk_state"]["kill_switch_engaged"] = True
        report = self.gate.evaluate(
            **data,
            write_enablement_requested=True,
            approval_text=self.gate.APPROVAL_TEXT,
        )
        self.assertEqual(report.state, RecoveryGateState.SAFE_MODE)
        self.assertFalse(report.autonomous_order_allowed)

    def test_zero_counters(self):
        report = self.gate.evaluate(**states())
        self.assertEqual(report.network_requests_executed, 0)
        self.assertEqual(report.write_requests_executed, 0)
        self.assertEqual(report.actual_paper_orders_submitted, 0)
        self.assertEqual(report.live_orders_submitted, 0)

    def test_json(self):
        raw = self.gate.evaluate(**states()).to_json_dict()
        self.assertEqual(raw["state"], "READ_ONLY_READY")
        self.assertEqual(len(raw["checks"]), 12)


if __name__ == "__main__":
    unittest.main()
