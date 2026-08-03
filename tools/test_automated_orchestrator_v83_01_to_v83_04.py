import json,tempfile,unittest
from pathlib import Path
from paper_runtime.automated_orchestrator_v83_01_04 import decide_next_action,run_automated_paper_orchestrator
class Tests(unittest.TestCase):
 def test_start_session(self): self.assertEqual(decide_next_action(session={'state':'PAPER_SESSION_READY_TO_START','market_open':True,'session_active':False},scheduler={},intraday={},end_of_day={},multi_day={})['action'],'START_PAPER_SESSION')
 def test_tick(self): self.assertEqual(decide_next_action(session={'state':'PAPER_SESSION_RUNNING','market_open':True,'session_active':True},scheduler={'state':'PAPER_SCHEDULER_TICK_DUE'},intraday={},end_of_day={},multi_day={})['action'],'AUTHORIZE_SCHEDULER_TICK')
 def test_intraday(self): self.assertEqual(decide_next_action(session={'state':'PAPER_SESSION_RUNNING','market_open':True,'session_active':True},scheduler={'state':'PAPER_SCHEDULER_TICK_AUTHORIZED'},intraday={'state':'INTRADAY_LOOP_READY'},end_of_day={},multi_day={})['action'],'EXECUTE_INTRADAY_LOOP')
 def test_end_session(self): self.assertEqual(decide_next_action(session={'market_closed':True,'session_active':True},scheduler={},intraday={},end_of_day={},multi_day={})['action'],'END_PAPER_SESSION')
 def test_certify(self): self.assertEqual(decide_next_action(session={'market_closed':True,'session_active':False},scheduler={},intraday={},end_of_day={'state':'END_OF_DAY_READY_TO_CERTIFY'},multi_day={})['action'],'CERTIFY_TRADING_DAY')
 def run_case(self,authorize=False,complete=False,active=False):
  t=tempfile.TemporaryDirectory(); self.addCleanup(t.cleanup); r=Path(t.name)
  data={'session':{'state':'PAPER_SESSION_READY_TO_START','market_open':True,'market_closed':False,'session_active':False},'scheduler':{'state':'WAIT_PAPER_SESSION_RUNNING'},'intraday':{'state':'INTRADAY_LOOP_WAIT_GATES'},'eod':{'state':'END_OF_DAY_WAIT_GATES'},'multi':{'state':'WAIT_DAILY_CERTIFICATION'},'policy':{'paper_only':True,'read_only':True,'broker_write_enabled':False,'order_submission_enabled':False,'live_trading_enabled':False,'continuous_loop_enabled':False,'automatic_action_execution_enabled':False}}
  for n,v in data.items(): (r/f'{n}.json').write_text(json.dumps(v),encoding='utf-8')
  if active: (r/'lock.json').write_text(json.dumps({'active':True,'action_id':'x','action':'START_PAPER_SESSION'}),encoding='utf-8')
  out=run_automated_paper_orchestrator(session_result_path=r/'session.json',scheduler_result_path=r/'scheduler.json',intraday_result_path=r/'intraday.json',end_of_day_result_path=r/'eod.json',multi_day_result_path=r/'multi.json',policy_path=r/'policy.json',action_lock_path=r/'lock.json',action_plan_path=r/'plan.json',action_ledger_path=r/'ledger.jsonl',recovery_path=r/'recovery.json',dashboard_path=r/'dashboard.json',result_path=r/'result.json',authorize_action=authorize,complete_action=complete)
  return out,r
 def test_ready(self): self.assertEqual(self.run_case()[0]['state'],'ORCHESTRATOR_ACTION_READY')
 def test_authorize(self):
  o,r=self.run_case(authorize=True); self.assertTrue(o['action_authorized']); self.assertTrue((r/'plan.json').exists())
 def test_duplicate(self): self.assertEqual(self.run_case(authorize=True,active=True)[0]['status'],'BLOCKED')
 def test_complete(self): self.assertTrue(self.run_case(complete=True,active=True)[0]['action_completed'])
 def test_contract(self):
  o,_=self.run_case(authorize=True); self.assertFalse(o['broker_write_enabled']); self.assertFalse(o['order_submission_enabled']); self.assertEqual(o['network_requests_executed'],0); self.assertEqual(o['actual_paper_orders_submitted'],0)
if __name__=='__main__': unittest.main()
