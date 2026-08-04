import tempfile,unittest
from pathlib import Path

from final_system_integration.pipeline import build_pipeline
from final_system_integration.safety import evaluate_safety
from final_system_integration.readiness import calculate_readiness
from final_system_integration.dashboard import build_dashboard
from final_system_integration.engine import evaluate

def modules(ready=True):
    ids=[
        "MARKET_REGIME","META_STRATEGY","BACKTEST_BATCH","PORTFOLIO_MANAGER",
        "AI_RISK_MANAGER","RISK_BUDGET","ADAPTIVE_REBALANCE",
        "AUTONOMOUS_DECISION","AUTONOMOUS_CYCLE","MULTI_DAY_SCHEDULER",
        "CONTINUOUS_ENGINE","CONTINUOUS_RUNTIME","PAPER_EXECUTION",
        "POSITION_LIFECYCLE","ACCOUNT_RECONCILIATION",
        "BROKER_RECONCILIATION","MASTER_ORCHESTRATOR",
    ]
    return [{
        "module_id":x,
        "ready":ready,
        "actual_orders_submitted":0,
        "execution_authorized":False,
        "paper_only":True,
    } for x in ids]

class Tests(unittest.TestCase):
    def test_pipeline(self):
        self.assertTrue(build_pipeline(modules())["passed"])

    def test_pipeline_block(self):
        rows=modules()
        rows[0]["ready"]=False
        self.assertFalse(build_pipeline(rows)["passed"])

    def test_safety(self):
        self.assertTrue(evaluate_safety(modules())["passed"])

    def test_safety_order(self):
        rows=modules()
        rows[0]["actual_orders_submitted"]=1
        self.assertFalse(evaluate_safety(rows)["passed"])

    def test_readiness(self):
        rows=modules()
        pipeline=build_pipeline(rows)
        safety=evaluate_safety(rows)
        value=calculate_readiness(rows,pipeline,safety)
        self.assertEqual(value["readiness_score"],100)
        self.assertTrue(value["passed"])

    def test_dashboard(self):
        rows=modules()
        pipeline=build_pipeline(rows)
        safety=evaluate_safety(rows)
        readiness=calculate_readiness(rows,pipeline,safety)
        value=build_dashboard(rows,pipeline,safety,readiness)
        self.assertEqual(value["system_status"],"READY")

    def test_missing_sources_review(self):
        with tempfile.TemporaryDirectory() as temp:
            result=evaluate(Path(temp))
            self.assertEqual(
                result["state"],
                "FINAL_SYSTEM_INTEGRATION_REVIEW_REQUIRED",
            )

    def test_orders_zero(self):
        with tempfile.TemporaryDirectory() as temp:
            self.assertEqual(evaluate(Path(temp))["actual_orders_submitted"],0)

    def test_release_not_created(self):
        with tempfile.TemporaryDirectory() as temp:
            self.assertFalse(evaluate(Path(temp))["production_release_created"])

if __name__=="__main__":
    unittest.main()
