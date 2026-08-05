from __future__ import annotations
import unittest

from autonomous_paper_cycle.qualification import (
    qualify_fully_autonomous_paper_trading,
)
from autonomous_paper_cycle.qualification_guard import run_full_qualification


def cycle_report():
    return {
        "cycle_id": "cycle-001",
        "cycle_hash": "a" * 64,
        "portfolio_hash": "b" * 64,
        "registry_hash": "c" * 64,
        "accounting_event_hash": "d" * 64,
        "stage_summaries": [
            {"name": name, "status": "PASS"}
            for name in [
                "risk", "authorization", "dispatch",
                "simulation", "accounting", "reconciliation"
            ]
        ],
    }


def cycle_result():
    return {
        "stage": "V392.14A",
        "state": "AUTONOMOUS_PAPER_CYCLE_ORCHESTRATOR_READY",
        "status": "PASS",
        "cycle_completed": True,
        "final_qualification_allowed": True,
        "single_cycle_replay_protection_enabled": True,
        "fail_closed_enabled": True,
        "broker_adapter_enabled": False,
        "broker_network_enabled": False,
        "broker_write_enabled": False,
        "paper_submission_enabled": False,
        "live_submission_enabled": False,
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
        "evaluation": {"cycle_hash": "a" * 64},
    }


def ledger():
    return [{
        "evaluation": {
            "cycle_hash": "a" * 64,
            "cycle_report": {"cycle_id": "cycle-001"},
        }
    }]


def registry():
    return {"completed_cycle_ids": ["cycle-001"]}


def reconciliation():
    return {
        "stage": "V392.13A",
        "portfolio_reconciled": True,
        "evaluation": {"valid": True},
    }


def risk():
    return {
        "status": "PASS",
        "risk_operations_allowed": True,
        "broker_write_enabled": False,
        "paper_submission_enabled": False,
        "live_submission_enabled": False,
    }


def qualification_registry():
    return {"qualified_cycle_ids": []}


class Tests(unittest.TestCase):
    def test_qualified(self):
        result = qualify_fully_autonomous_paper_trading(
            cycle_result(), cycle_report(), ledger(), registry(),
            reconciliation(), risk(), qualification_registry()
        )
        self.assertTrue(result["qualified"])

    def test_replay_rejected(self):
        q = {"qualified_cycle_ids": ["cycle-001"]}
        result = qualify_fully_autonomous_paper_trading(
            cycle_result(), cycle_report(), ledger(), registry(),
            reconciliation(), risk(), q
        )
        self.assertTrue(result["replay_detected"])
        self.assertFalse(result["qualified"])

    def test_cycle_hash_mismatch(self):
        value = cycle_result()
        value["evaluation"]["cycle_hash"] = "e" * 64
        result = qualify_fully_autonomous_paper_trading(
            value, cycle_report(), ledger(), registry(),
            reconciliation(), risk(), qualification_registry()
        )
        self.assertFalse(result["qualified"])

    def test_ledger_missing(self):
        result = qualify_fully_autonomous_paper_trading(
            cycle_result(), cycle_report(), [], registry(),
            reconciliation(), risk(), qualification_registry()
        )
        self.assertFalse(result["qualified"])

    def test_registry_missing_cycle(self):
        result = qualify_fully_autonomous_paper_trading(
            cycle_result(), cycle_report(), ledger(),
            {"completed_cycle_ids": []},
            reconciliation(), risk(), qualification_registry()
        )
        self.assertFalse(result["qualified"])

    def test_reconciliation_blocked(self):
        value = reconciliation()
        value["portfolio_reconciled"] = False
        result = qualify_fully_autonomous_paper_trading(
            cycle_result(), cycle_report(), ledger(), registry(),
            value, risk(), qualification_registry()
        )
        self.assertFalse(result["qualified"])

    def test_risk_blocked(self):
        value = risk()
        value["risk_operations_allowed"] = False
        result = qualify_fully_autonomous_paper_trading(
            cycle_result(), cycle_report(), ledger(), registry(),
            reconciliation(), value, qualification_registry()
        )
        self.assertFalse(result["qualified"])

    def test_zero_orders(self):
        result = run_full_qualification(
            cycle_result(), cycle_report(), ledger(), registry(),
            reconciliation(), risk(), qualification_registry()
        )
        self.assertEqual(result["actual_paper_orders_submitted"], 0)
        self.assertEqual(result["actual_live_orders_submitted"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
