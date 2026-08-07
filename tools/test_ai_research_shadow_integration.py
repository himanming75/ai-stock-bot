from __future__ import annotations
import inspect, unittest
from pathlib import Path
from autonomous_ai_brain.research_integration import AIResearchShadowIntegration

class Tests(unittest.TestCase):
    def test_module_contract(self):
        names=[x[0] for x in AIResearchShadowIntegration.MODULES]
        self.assertEqual(names,[
            "market_context","market_regime","strategy_ensemble",
            "decision_robustness","shadow_intelligence","counterfactual",
            "performance_intelligence","market_memory_exit",
        ])

    def test_no_broker_write_surface(self):
        src=inspect.getsource(AIResearchShadowIntegration).lower()
        banned=(
            "submit_order(", "submit_market", "close_position(",
            "cancel_order", "tradingclient(", "etrade",
        )
        for token in banned:
            self.assertNotIn(token,src)

    def test_failure_is_advisory(self):
        class Bad:
            def __init__(self, root): pass
            def run(self): raise RuntimeError("boom")
        svc=AIResearchShadowIntegration(Path("."))
        row=svc._run_module("bad",Bad)
        self.assertEqual(row["status"],"ADVISORY_ERROR")

    def test_contract_literals(self):
        src=inspect.getsource(AIResearchShadowIntegration.run)
        self.assertIn('"broker_write_performed": False',src)
        self.assertIn('"actual_paper_decision_path_changed": False',src)

if __name__=="__main__":
    unittest.main()
