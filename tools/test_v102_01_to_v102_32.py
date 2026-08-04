import tempfile, unittest
from pathlib import Path
from master_ai_orchestrator.dependencies import evaluate_dependencies
from master_ai_orchestrator.workflow import build_workflow
from master_ai_orchestrator.safety import evaluate_safety
from master_ai_orchestrator.health import evaluate_health
from master_ai_orchestrator.recovery import build_recovery_plan
from master_ai_orchestrator.engine import evaluate

def ready_modules():
    ids = [
        "MARKET_REGIME","META_STRATEGY","PAPER_ACCOUNT","PORTFOLIO_MANAGER",
        "AI_RISK_MANAGER","RISK_BUDGET","REBALANCE_CONTROL","ADAPTIVE_REBALANCE"
    ]
    return [
        {"module_id": x, "required": True, "present": True, "ready": True}
        for x in ids
    ]

class Tests(unittest.TestCase):
    def test_dependencies(self):
        self.assertTrue(evaluate_dependencies(ready_modules())["passed"])

    def test_workflow(self):
        value = build_workflow(ready_modules())
        self.assertTrue(value["passed"])
        self.assertEqual(value["ready_step_count"], 8)

    def test_workflow_blocks(self):
        rows = ready_modules()
        rows[1]["ready"] = False
        value = build_workflow(rows)
        self.assertFalse(value["passed"])

    def test_safety(self):
        self.assertTrue(evaluate_safety(ready_modules())["passed"])

    def test_health(self):
        modules = ready_modules()
        dependencies = evaluate_dependencies(modules)
        workflow = build_workflow(modules)
        safety = evaluate_safety(modules)
        self.assertTrue(
            evaluate_health(modules, dependencies, workflow, safety)["passed"]
        )

    def test_recovery(self):
        rows = ready_modules()
        rows[0]["present"] = False
        rows[0]["ready"] = False
        value = build_recovery_plan(rows, {"retry_limit": 3})
        self.assertTrue(value["recovery_required"])

    def test_missing_sources_review(self):
        with tempfile.TemporaryDirectory() as temp:
            result = evaluate(Path(temp))
            self.assertEqual(
                result["state"], "MASTER_AI_ORCHESTRATOR_REVIEW_REQUIRED"
            )

    def test_orders_zero(self):
        with tempfile.TemporaryDirectory() as temp:
            result = evaluate(Path(temp))
            self.assertEqual(result["actual_orders_submitted"], 0)

    def test_execution_disabled(self):
        with tempfile.TemporaryDirectory() as temp:
            self.assertFalse(evaluate(Path(temp))["execution_authorized"])

if __name__ == "__main__":
    unittest.main()
