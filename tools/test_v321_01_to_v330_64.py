from __future__ import annotations
import json, sys, tempfile, unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from long_run_qualification.config import validate
from long_run_qualification.continuity import analyze
from long_run_qualification.io import append_jsonl, load_json, read_jsonl, write_json
from long_run_qualification.qualifier import qualify
from long_run_qualification.runner import run

SAFE={"stage":"V330.64","paper_base_url":"https://paper-api.alpaca.markets","qualification_enabled":False,"cycle_interval_seconds":30,"maximum_cycles_per_run":3,"maximum_runtime_minutes":5,"stop_after_market_close":False,"minimum_successful_cycles":2,"minimum_observation_minutes":0.5,"minimum_success_ratio":0.9,"maximum_excessive_gaps":2,"maximum_duplicate_records":0,"maximum_total_errors":5,"maximum_consecutive_errors":2,"retry_delay_seconds":1,"maximum_retry_delay_seconds":2,"maximum_new_orders_per_day":0,"paper_submission_enabled":False,"live_submission_enabled":False,"live_network_enabled":False,"broker_write_enabled":False,"monitor_only":True}

class Tests(unittest.TestCase):
 def make(self):
  td=tempfile.TemporaryDirectory(); root=Path(td.name); (root/"release/v321_01_to_v330_64/config").mkdir(parents=True); write_json(root/"release/v321_01_to_v330_64/config/real_paper_long_run_policy.json",SAFE); return td,root
 def test_policy_safe(self): self.assertTrue(validate(SAFE)["valid"])
 def test_utf8_bom_policy_load(self):
  td,root=self.make(); path=root/"release/v321_01_to_v330_64/config/real_paper_long_run_policy.json"; path.write_text("\ufeff"+json.dumps(SAFE),encoding="utf-8"); self.assertEqual(load_json(path,{})["stage"],"V330.64"); td.cleanup()

 def test_live_endpoint_rejected(self):
  p=dict(SAFE); p["paper_base_url"]="https://api.alpaca.markets"; self.assertFalse(validate(p)["valid"])
 def test_continuity(self):
  t=datetime(2026,1,1,tzinfo=timezone.utc); rows=[{"observed_at":(t+timedelta(seconds=30*i)).isoformat(),"i":i} for i in range(3)]; self.assertEqual(analyze(rows,30)["excessive_gap_count"],0)
 def test_corrupt_jsonl(self):
  td,root=self.make(); p=root/"x.jsonl"; p.write_text('{"a":1}\nBAD\n'); rows,bad=read_jsonl(p); self.assertEqual((len(rows),bad),(1,1)); td.cleanup()
 def test_default_blocked(self):
  td,root=self.make(); r=qualify(root); self.assertEqual(r["state"],"REAL_PAPER_LONG_RUN_READY_BLOCKED"); td.cleanup()
 def test_runner_zero_orders(self):
  td,root=self.make(); p=dict(SAFE); p["qualification_enabled"]=True; write_json(root/"release/v321_01_to_v330_64/config/real_paper_long_run_policy.json",p)
  n={"v":0}
  def fake(root,allow_network=False):
   n["v"]+=1; return {"state":"REAL_PAPER_DATA_COLLECTION_ACTIVE","status":"PASS","blocking_reasons":[],"snapshot":{"observed_at":(datetime.now(timezone.utc)+timedelta(seconds=n["v"]*30)).isoformat(),"market_open":True},"metrics":{"equity":100000}}
  r=run(root,allow_network=True,sleep_enabled=False,collector=fake); self.assertEqual(r["actual_paper_orders_submitted"],0); self.assertEqual(r["cycles"],3); td.cleanup()
 def test_keyboard_interrupt_safe(self):
  td,root=self.make(); p=dict(SAFE); p["qualification_enabled"]=True; write_json(root/"release/v321_01_to_v330_64/config/real_paper_long_run_policy.json",p)
  def stop(root,allow_network=False): raise KeyboardInterrupt()
  r=run(root,allow_network=True,sleep_enabled=False,collector=stop); self.assertEqual(r["stop_reason"],"USER_INTERRUPTED_SAFE"); td.cleanup()
 def test_qualification(self):
  td,root=self.make(); p=dict(SAFE); p["qualification_enabled"]=True; p["minimum_observation_minutes"]=0.4; write_json(root/"release/v321_01_to_v330_64/config/real_paper_long_run_policy.json",p)
  t=datetime(2026,1,1,tzinfo=timezone.utc)
  for i in range(3): append_jsonl(root/"release/v321_01_to_v330_64/actual/long_run_cycle_ledger.jsonl",{"observed_at":(t+timedelta(seconds=30*i)).isoformat(),"cycle_success":True,"blocked":False,"i":i})
  self.assertEqual(qualify(root)["state"],"REAL_PAPER_LONG_RUN_QUALIFIED"); td.cleanup()

if __name__=="__main__": unittest.main(verbosity=2)
