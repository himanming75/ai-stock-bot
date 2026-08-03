import json,tempfile,unittest
from pathlib import Path
from paper_pilot.paper_trading_completion import PaperTradingCompletionPackage
class Tests(unittest.TestCase):
 def write(self,p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v),encoding='utf-8')
 def run_case(self,days=1,complete=False):
  td=tempfile.TemporaryDirectory();self.addCleanup(td.cleanup);r=Path(td.name)
  d={'policy':{'paper_only':True,'read_only':True,'broker_write_enabled':False,'live_trading_enabled':False,'minimum_validation_days':5},'pilot':{'pilot_started':True,'state':'CONTROLLED_PAPER_PILOT_RUNNING','pilot_id':'p','session_id':'s'},'session':{'health_status':'HEALTHY'},'performance':{'sample_count':1},'risk':{'state':'PAPER_RISK_HEALTHY','emergency_stop_required':False},'automation':{'cycle_ready':True,'recovery_gate_clear':True},'validation':{'validation_days':days,'validation_complete':complete},'analytics':{'state':'VALIDATION_ANALYTICS_COMPLETE' if complete else 'VALIDATION_ANALYTICS_IN_PROGRESS'},'certificate':{'certificate_verified':complete},'promotion':{'promotion_ready':complete},'approval':{'certification_gate_clear':complete}}
  paths={}
  for n,v in d.items():paths[n]=r/f'{n}.json';self.write(paths[n],v)
  out=PaperTradingCompletionPackage().run(policy_path=paths['policy'],pilot_result_path=paths['pilot'],session_result_path=paths['session'],performance_result_path=paths['performance'],risk_result_path=paths['risk'],automation_result_path=paths['automation'],validation_result_path=paths['validation'],analytics_result_path=paths['analytics'],certificate_result_path=paths['certificate'],promotion_result_path=paths['promotion'],approval_result_path=paths['approval'],completion_manifest_path=r/'manifest.json',integrity_manifest_path=r/'integrity.json',dashboard_state_path=r/'dashboard.json',result_path=r/'result.json');return out,r
 def test_wait_multi_day_validation(self):
  x,_=self.run_case();self.assertEqual(x['state'],'WAIT_MULTI_DAY_VALIDATION');self.assertEqual(x['completion_progress_pct'],20)
 def test_wait_final_gates(self):self.assertEqual(self.run_case(5,False)[0]['state'],'WAIT_FINAL_CERTIFICATION_GATES')
 def test_completion_ready(self):self.assertTrue(self.run_case(5,True)[0]['completion_ready'])
 def test_manifest_written(self):x,r=self.run_case();self.assertTrue((r/'manifest.json').exists())
 def test_integrity_written(self):x,r=self.run_case();self.assertTrue((r/'integrity.json').exists())
 def test_read_only_contract(self):x,_=self.run_case();self.assertEqual(x['network_requests_executed'],0);self.assertFalse(x['broker_write_enabled'])
if __name__=='__main__':unittest.main()
