import importlib.util
from pathlib import Path
import unittest
P=Path(__file__).resolve().parents[1]/"dashboard"/"strategy_improvement_candidates_v3_18.py"
S=importlib.util.spec_from_file_location("v318",P);M=importlib.util.module_from_spec(S);S.loader.exec_module(M)
class T(unittest.TestCase):
 def b(self,n,issues): return M.build_strategy_improvement_candidates({"historical":{"numeric_trade_count":n},"strategy_weakness_map":{"issues":issues}})
 def test_sample(self):
  r=self.b(2,[{"code":"SAMPLE_SIZE_INSUFFICIENT","category":"SAMPLE","weakness_type":"EVIDENCE_GAP","severity":"CRITICAL"}]);self.assertEqual(r["mode"],"EVIDENCE_COLLECTION_ONLY");self.assertEqual(r["candidates"][0]["proposal_type"],"COLLECT_MORE_EVIDENCE")
 def test_regime(self):
  r=self.b(2,[{"code":"REGIME_EVIDENCE_UNOBSERVED","category":"REGIME","weakness_type":"EVIDENCE_GAP","severity":"HIGH"}]);self.assertEqual(r["candidates"][0]["proposal_type"],"CAPTURE_REGIME_METADATA")
 def test_performance(self):
  r=self.b(12,[{"code":"PROFIT_FACTOR_BELOW_ONE","category":"PROFITABILITY","weakness_type":"PERFORMANCE_RISK","severity":"CRITICAL"}]);self.assertEqual(r["mode"],"SHADOW_CANDIDATES_AVAILABLE");self.assertEqual(r["candidates"][0]["proposal_type"],"EXIT_RULE_CANDIDATE")
 def test_no_apply(self):
  c=self.b(20,[{"code":"X","category":"RISK","weakness_type":"PERFORMANCE_RISK","severity":"HIGH"}])["candidates"][0];self.assertFalse(c["auto_apply"]);self.assertFalse(c["paper_parameter_change_allowed"]);self.assertFalse(c["live_change_allowed"])
 def test_contracts(self):
  c=self.b(2,[])["contracts"];self.assertTrue(c["diagnostic_proposal_only"]);self.assertFalse(c["automatic_strategy_change"]);self.assertFalse(c["broker_write_performed"])
if __name__=="__main__":unittest.main()
