import copy, json, tempfile, unittest
from pathlib import Path
from tools.handoff_adapter_v58_2 import *

V54 = {
 "status":"PASS","version":"54.0","network_used":False,
 "selected_signals":[
  {"symbol":"MSFT","selected_action":"HOLD","selected_priority":100,"selected_weighted_confidence":"1","selected_signal_sha256":"1"*64,"selection_sha256":"2"*64},
  {"symbol":"AAPL","selected_action":"BUY","selected_priority":80,"selected_weighted_confidence":"0.9","selected_signal_sha256":"a"*64,"selection_sha256":"b"*64}
 ]}
V55 = {"status":"PASS","decision":"size_approved","symbol":"AAPL","action":"BUY","shares":"100.000000","entry_price":"200.00","estimated_risk_amount":"1000.00","sizing_sha256":"c"*64,"request_id":"r55","network_used":False}
V56 = {"status":"PASS","decision":"risk_approved","symbol":"AAPL","action":"BUY","quantity":"100.000000","entry_price":"200.00","risk_sha256":"d"*64,"request_id":"r56","risk_reward_ratio":"2.5","network_used":False}
T55={"account":{},"request":{"entry_price":"200.00","method":"fixed_risk","metadata":{}},"config":{}}
T56={"state":{},"request":{"stop_price":"190","take_profit_price":"225","requested_at_utc":"2026-07-29T16:00:00Z","metadata":{}},"config":{}}
T57={"request":{"submitted_at_utc":"2026-07-29T16:00:00Z","metadata":{}},"config":{},"broker_events":[],"seen_execution_keys":[]}

class Tests(unittest.TestCase):
 def setUp(self): self.a=HandoffAdapterV582()
 def test_v54_symbol(self): self.assertEqual("AAPL",self.a.v54_to_v55(V54,T55)["request"]["symbol"])
 def test_v54_action(self): self.assertEqual("BUY",self.a.v54_to_v55(V54,T55)["request"]["action"])
 def test_v54_hash(self): self.assertEqual("a"*64,self.a.v54_to_v55(V54,T55)["request"]["signal_sha256"])
 def test_v54_preserve(self): self.assertEqual("200.00",self.a.v54_to_v55(V54,T55)["request"]["entry_price"])
 def test_v54_no_orderable(self):
  x=copy.deepcopy(V54);x["selected_signals"]=[x["selected_signals"][0]]
  with self.assertRaises(ValueError):self.a.v54_to_v55(x,T55)
 def test_v55_quantity(self): self.assertEqual("100.000000",self.a.v55_to_v56(V55,T56)["request"]["quantity"])
 def test_v55_risk_hash(self): self.assertEqual("c"*64,self.a.v55_to_v56(V55,T56)["request"]["position_sizing_sha256"])
 def test_v55_order_key(self): self.assertEqual("AAPL-BUY-100-200",self.a.v55_to_v56(V55,T56)["request"]["order_key"])
 def test_v55_preserve_stop(self): self.assertEqual("190",self.a.v55_to_v56(V55,T56)["request"]["stop_price"])
 def test_v55_reject(self):
  x=copy.deepcopy(V55);x["status"]="FAIL"
  with self.assertRaises(ValueError):self.a.v55_to_v56(x,T56)
 def test_v56_quantity(self): self.assertEqual("100.000000",self.a.v56_to_v57(V56,T57)["request"]["quantity"])
 def test_v56_hash(self): self.assertEqual("d"*64,self.a.v56_to_v57(V56,T57)["request"]["risk_approval_sha256"])
 def test_v56_key(self): self.assertEqual("AAPL-BUY-100-200",self.a.v56_to_v57(V56,T57)["request"]["execution_key"])
 def test_v56_preserve_events(self): self.assertEqual([],self.a.v56_to_v57(V56,T57)["broker_events"])
 def test_v56_reject(self):
  x=copy.deepcopy(V56);x["decision"]="reject"
  with self.assertRaises(ValueError):self.a.v56_to_v57(x,T57)
 def test_network_rejected(self):
  x=copy.deepcopy(V54);x["network_used"]=True
  with self.assertRaises(ValueError):self.a.v54_to_v55(x,T55)
 def test_bad_hash(self):
  x=copy.deepcopy(V55);x["sizing_sha256"]="bad"
  with self.assertRaises(ValueError):self.a.v55_to_v56(x,T56)
 def test_handoff_hash(self): self.assertEqual(64,len(self.a.v56_to_v57(V56,T57)["handoff"]["handoff_sha256"]))
 def test_transform(self): self.assertEqual("AAPL",self.a.transform("v55_to_v56",V55,T56)["request"]["symbol"])
 def test_bad_transform(self):
  with self.assertRaises(ValueError):self.a.transform("bad",V55,T56)
 def test_export(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/"x.json";self.a.export(p,self.a.v55_to_v56(V55,T56));self.assertTrue(p.exists())
 def test_template_not_mutated(self):
  before=copy.deepcopy(T56);self.a.v55_to_v56(V55,T56);self.assertEqual(before,T56)
 def test_unwrap(self): self.assertEqual("PASS",unwrap_result({"result":V55})["status"])
 def test_canonical_deterministic(self): self.assertEqual(canonical_hash({"a":1,"b":2}),canonical_hash({"b":2,"a":1}))
if __name__=="__main__":unittest.main()
