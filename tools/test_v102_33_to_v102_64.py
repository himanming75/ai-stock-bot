import tempfile
import unittest
from pathlib import Path

from autonomous_decision.conflicts import detect_conflicts
from autonomous_decision.veto import evaluate_vetoes
from autonomous_decision.confidence import calculate_confidence
from autonomous_decision.decision import make_decision
from autonomous_decision.approval import build_approval_gate
from autonomous_decision.engine import evaluate

def good_signals():
    return {
        "orchestrator_ready": True,
        "regime_confidence": 66.67,
        "regime_conflict": False,
        "meta_risk_approved": True,
        "risk_gate_passed": True,
        "risk_score": 54.0,
        "risk_budget_gate_passed": True,
        "target_gross_exposure_pct": 49.0,
        "adaptive_gate_passed": True,
        "adaptive_state": "ADAPTIVE_REBALANCE_OPTIMIZATION_READY",
        "actionable_adjustment_count": 3,
        "stability_score": 76.0,
    }

class Tests(unittest.TestCase):
    def test_conflicts_clear(self):
        self.assertTrue(detect_conflicts(good_signals())["passed"])

    def test_conflict_detected(self):
        signals = good_signals()
        signals["regime_conflict"] = True
        self.assertFalse(detect_conflicts(signals)["passed"])

    def test_veto_clear(self):
        signals = good_signals()
        conflicts = detect_conflicts(signals)
        self.assertTrue(evaluate_vetoes(signals, conflicts, {})["passed"])

    def test_veto_risk(self):
        signals = good_signals()
        signals["risk_gate_passed"] = False
        veto = evaluate_vetoes(signals, detect_conflicts(signals), {})
        self.assertFalse(veto["passed"])

    def test_confidence(self):
        signals = good_signals()
        conflicts = detect_conflicts(signals)
        veto = evaluate_vetoes(signals, conflicts, {})
        self.assertGreaterEqual(
            calculate_confidence(signals, conflicts, veto)["confidence_score"],
            75,
        )

    def test_act_decision(self):
        signals = good_signals()
        conflicts = detect_conflicts(signals)
        veto = evaluate_vetoes(signals, conflicts, {})
        confidence = calculate_confidence(signals, conflicts, veto)
        decision = make_decision(
            signals, conflicts, veto, confidence,
            {"minimum_act_confidence": 75},
        )
        self.assertEqual(decision["decision"], "ACT")

    def test_approval_never_grants(self):
        gate = build_approval_gate(
            {"decision": "ACT"},
            {"confidence_score": 90},
            {"minimum_act_confidence": 75},
        )
        self.assertFalse(gate["approval_granted"])
        self.assertFalse(gate["execution_authorized"])

    def test_missing_sources_block(self):
        with tempfile.TemporaryDirectory() as temp:
            result = evaluate(Path(temp))
            self.assertEqual(result["state"], "AUTONOMOUS_DECISION_BLOCKED")

    def test_orders_zero(self):
        with tempfile.TemporaryDirectory() as temp:
            self.assertEqual(evaluate(Path(temp))["actual_orders_submitted"], 0)

if __name__ == "__main__":
    unittest.main()
