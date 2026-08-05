from __future__ import annotations
import unittest

from autonomous_paper_cycle.orchestrator import build_cycle_report
from autonomous_paper_cycle.guard import run_autonomous_paper_cycle


def risk():
    return {
        "status": "PASS",
        "risk_operations_allowed": True,
        "broker_write_enabled": False,
        "paper_submission_enabled": False,
        "live_submission_enabled": False,
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
    }


def authorization():
    return {
        "stage": "V392.09A",
        "status": "PASS",
        "dispatch_context_created": True,
        "broker_write_enabled": False,
        "paper_submission_enabled": False,
        "live_submission_enabled": False,
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
    }


def dispatch():
    return {
        "stage": "V392.10A",
        "state": "LOCAL_PAPER_DISPATCH_ENGINE_READY",
        "status": "PASS",
        "local_dispatch_accepted": True,
        "broker_write_enabled": False,
        "paper_submission_enabled": False,
        "live_submission_enabled": False,
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
    }


def simulator():
    return {
        "stage": "V392.11A",
        "state": "PAPER_EXECUTION_SIMULATOR_READY",
        "status": "PASS",
        "simulated_fill_created": True,
        "broker_write_enabled": False,
        "paper_submission_enabled": False,
        "live_submission_enabled": False,
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
    }


def accounting():
    return {
        "stage": "V392.12A",
        "state": "FILL_ACCOUNTING_POSITION_UPDATE_READY",
        "status": "PASS",
        "portfolio_updated": True,
        "broker_write_enabled": False,
        "paper_submission_enabled": False,
        "live_submission_enabled": False,
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
    }


def reconciliation():
    return {
        "stage": "V392.13A",
        "state": "PAPER_PORTFOLIO_RECONCILIATION_READY",
        "status": "PASS",
        "portfolio_reconciled": True,
        "evaluation": {
            "portfolio_hash": "a" * 64,
            "registry_hash": "b" * 64,
            "accounting_event_hash": "c" * 64,
        },
        "broker_write_enabled": False,
        "paper_submission_enabled": False,
        "live_submission_enabled": False,
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
    }


class Tests(unittest.TestCase):
    def test_cycle_completed(self):
        result = build_cycle_report(
            risk(), authorization(), dispatch(), simulator(),
            accounting(), reconciliation(), "cycle-001", set()
        )
        self.assertTrue(result["approved"])

    def test_replay_rejected(self):
        result = build_cycle_report(
            risk(), authorization(), dispatch(), simulator(),
            accounting(), reconciliation(), "cycle-001", {"cycle-001"}
        )
        self.assertTrue(result["replay_detected"])
        self.assertFalse(result["approved"])

    def test_risk_blocked(self):
        value = risk()
        value["risk_operations_allowed"] = False
        result = build_cycle_report(
            value, authorization(), dispatch(), simulator(),
            accounting(), reconciliation(), "cycle-001", set()
        )
        self.assertFalse(result["approved"])

    def test_dispatch_blocked(self):
        value = dispatch()
        value["state"] = "LOCAL_PAPER_DISPATCH_ENGINE_BLOCKED"
        result = build_cycle_report(
            risk(), authorization(), value, simulator(),
            accounting(), reconciliation(), "cycle-001", set()
        )
        self.assertFalse(result["approved"])

    def test_simulation_missing(self):
        value = simulator()
        value["simulated_fill_created"] = False
        result = build_cycle_report(
            risk(), authorization(), dispatch(), value,
            accounting(), reconciliation(), "cycle-001", set()
        )
        self.assertFalse(result["approved"])

    def test_accounting_missing(self):
        value = accounting()
        value["portfolio_updated"] = False
        result = build_cycle_report(
            risk(), authorization(), dispatch(), simulator(),
            value, reconciliation(), "cycle-001", set()
        )
        self.assertFalse(result["approved"])

    def test_reconciliation_blocked(self):
        value = reconciliation()
        value["portfolio_reconciled"] = False
        result = build_cycle_report(
            risk(), authorization(), dispatch(), simulator(),
            accounting(), value, "cycle-001", set()
        )
        self.assertFalse(result["approved"])

    def test_zero_orders(self):
        result = run_autonomous_paper_cycle(
            risk(), authorization(), dispatch(), simulator(),
            accounting(), reconciliation(), "cycle-001", set()
        )
        self.assertEqual(result["actual_paper_orders_submitted"], 0)
        self.assertEqual(result["actual_live_orders_submitted"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
