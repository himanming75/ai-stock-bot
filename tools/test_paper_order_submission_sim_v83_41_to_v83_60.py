from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from alpaca_market_data.paper_order_submission_sim_v83_41_60 import *

class T(unittest.TestCase):
 def setUp(self): self.c=PaperOrderSubmissionSimulationConfig()
 def test_config(self): self.c.validate()
 def test_network_rejected(self):
  with self.assertRaises(ValueError):PaperOrderSubmissionSimulationConfig(allow_network=True).validate()
 def test_policy(self): self.assertTrue(submission_policy()["simulation_only"])
 def test_intent(self): self.assertFalse(make_submission_intent("AAPL","BUY",1,100)["actual_submission_authorized"])
 def test_bad_intent(self):
  with self.assertRaises(ValueError):make_submission_intent("AAPL","BUY",0,100)
 def test_idempotency(self): self.assertTrue(submission_idempotency(make_submission_intent("AAPL","BUY",1,100))["idempotency_key"].startswith("submit-idem-"))
 def test_queue(self):
  i=make_submission_intent("AAPL","BUY",1,100);self.assertEqual(submission_queue(i,submission_idempotency(i))["queue_status"],"QUEUED_FOR_SIMULATION")
 def test_duplicate(self): self.assertTrue(duplicate_submission_guard(["x","x"])["duplicate_detected"])
 def test_serialize(self): self.assertTrue(serialize_submission(make_submission_intent("AAPL","BUY",1,100))["simulation_payload"])
 def test_response_accept(self): self.assertEqual(broker_response_simulator(make_submission_intent("AAPL","BUY",5,100),"ACCEPTED",self.c)["filled_quantity"],5)
 def test_response_partial(self): self.assertGreater(broker_response_simulator(make_submission_intent("AAPL","BUY",8,100),"PARTIAL",self.c)["filled_quantity"],0)
 def test_response_reject(self): self.assertEqual(broker_response_simulator(make_submission_intent("AAPL","BUY",5,100),"REJECTED",self.c)["filled_quantity"],0)
 def test_retry(self): self.assertEqual(retry_policy(self.c)["network_retry_enabled"],False)
 def test_retry_sim(self):
  r=broker_response_simulator(make_submission_intent("AAPL","BUY",5,100),"REJECTED",self.c)
  self.assertEqual(retry_simulation(r,self.c)["simulated_retry_attempts"],3)
 def test_receipt(self):
  i=make_submission_intent("AAPL","BUY",5,100);idem=submission_idempotency(i);q=submission_queue(i,idem)
  r=broker_response_simulator(i,"ACCEPTED",self.c);rt=retry_simulation(r,self.c)
  self.assertEqual(submission_receipt(i,q,r,rt)["status"],"SIM_ACCEPTED")
 def test_replay_guard(self):
  i=make_submission_intent("AAPL","BUY",5,100);idem=submission_idempotency(i);q=submission_queue(i,idem)
  r=broker_response_simulator(i,"ACCEPTED",self.c);rt=retry_simulation(r,self.c);receipt=submission_receipt(i,q,r,rt)
  self.assertTrue(replay_guard([receipt,receipt])["replay_detected"])
 def test_deterministic(self): self.assertTrue(deterministic_replay(make_submission_intent("AAPL","BUY",5,100),"ACCEPTED",self.c)["deterministic"])
 def test_scenarios(self):
  d=build_scenarios(self.c);self.assertEqual(d["scenario_count"],4);self.assertGreater(d["partial_count"],0)
 def test_state_machine(self): self.assertFalse(submission_state_machine()["network_submit_state_present"])
 def test_store_reuse(self):
  with TemporaryDirectory() as t:
   out=Path(t);store_package(out,{"a":{"x":1}});self.assertTrue(store_package(out,{"a":{"x":1}})["reused"])
 def test_manifest(self):
  with TemporaryDirectory() as t:
   out=Path(t);z=store_package(out,{"a":{"x":1}});m=build_manifest(out,z["ledger"]);self.assertTrue(verify_manifest(out,m))
 def test_manifest_tamper(self):
  with TemporaryDirectory() as t:
   out=Path(t);z=store_package(out,{"a":{"x":1}});m=build_manifest(out,z["ledger"]);(out/"packages"/z["package_id"]/"a.json").write_text("{}")
   with self.assertRaises(ValueError):verify_manifest(out,m)
 def test_bad_cert(self):
  with TemporaryDirectory() as t:
   p=Path(t)/"c";p.write_text("{}")
   with self.assertRaises(ValueError):validate_authorization_certificate(p)
 def test_safety(self):
  s=(Path(__file__).resolve().parents[1]/"alpaca_market_data/paper_order_submission_sim_v83_41_60.py").read_text().lower()
  for x in ("submit_order(","cancel_order(","replace_order(","tradingclient(","api_secret","api_key","os.getenv","requests.","httpx."):self.assertNotIn(x,s)
 def test_stage_count(self): self.assertEqual(len([f"V83.{i:02d}" for i in range(41,61)]),20)
if __name__=="__main__":unittest.main()
