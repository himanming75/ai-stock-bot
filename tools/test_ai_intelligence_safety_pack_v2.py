import json,tempfile,unittest
from pathlib import Path
from ai_intelligence_v2 import IntelligenceSafetyPack
class Tests(unittest.TestCase):
    def setup_root(self,root):
        p=root/'runtime/paper_observability_intelligence/latest_observability_report.json'; p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps({'selected_candidate':{'symbol':'AAPL','side':'BUY','confidence':.91,'consensus_score':.95,'reward_risk':2.0,'quantity':.3,'reference_price':300}}),encoding='utf-8')
        g=root/'runtime/paper_autonomous_daily_session/latest_shadow_guard_decision.json'; g.parent.mkdir(parents=True,exist_ok=True); g.write_text(json.dumps({'issues':[{'code':'DAILY_ORDER_LIMIT'}],'warnings':[{'code':'WEAK_MARKET_REGIME_FIT'}],'market_snapshot':{'market_regime_fit':.5,'volatility_risk':.4}}),encoding='utf-8')
    def test_pack_pass(self):
        with tempfile.TemporaryDirectory() as d:
            r=Path(d); self.setup_root(r); out=IntelligenceSafetyPack(r).run(); self.assertEqual(out['status'],'PASS'); self.assertFalse(out['broker_write_performed'])
    def test_score_range(self):
        with tempfile.TemporaryDirectory() as d:
            r=Path(d); self.setup_root(r); s=IntelligenceSafetyPack(r).multi_score()['total_score']; self.assertGreaterEqual(s,0); self.assertLessEqual(s,1)
    def test_high_heat(self):
        with tempfile.TemporaryDirectory() as d:
            r=Path(d); self.setup_root(r); self.assertEqual(IntelligenceSafetyPack(r).safety_heatmap()['level'],'HIGH')
    def test_dynamic_shadow(self):
        with tempfile.TemporaryDirectory() as d:
            r=Path(d); self.setup_root(r); x=IntelligenceSafetyPack(r).dynamic_risk_shadow(); self.assertTrue(x['shadow_only']); self.assertFalse(x['enforced'])
    def test_skip_not_enforced(self):
        with tempfile.TemporaryDirectory() as d:
            r=Path(d); self.setup_root(r); self.assertFalse(IntelligenceSafetyPack(r).smart_skip()['enforced'])
    def test_missing_data(self):
        with tempfile.TemporaryDirectory() as d: self.assertEqual(IntelligenceSafetyPack(Path(d)).run()['status'],'PASS')
    def test_outputs(self):
        with tempfile.TemporaryDirectory() as d:
            r=Path(d); self.setup_root(r); IntelligenceSafetyPack(r).run(); rt=r/'runtime/ai_intelligence_safety_v2'; self.assertTrue((rt/'latest_intelligence_report.json').exists()); self.assertTrue((rt/'daily_ai_review.json').exists()); self.assertTrue((rt/'weekly_ai_review.json').exists())
    def test_live_off(self):
        with tempfile.TemporaryDirectory() as d:
            r=Path(d); self.setup_root(r); self.assertFalse(IntelligenceSafetyPack(r).run()['etrade_live_write_enabled'])
if __name__=='__main__': unittest.main(verbosity=2)
