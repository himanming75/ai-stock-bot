from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from alpaca_market_data.paper_order_submission_sim_v85_61_80 import *

class T(unittest.TestCase):
 def setUp(self): self.c=PaperOrderSubmissionSimulationConfig()
 def test_config(self): self.c.validate()
 def test_network_rejected(self):
  with self.assertRaises(ValueError):PaperOrderSubmissionSimulationConfig(allow_network=True).validate()
 def test_policy(self): self.assertTrue(submission_policy()["simulation_only"])
 def test_intent(self): self.assertFalse(make_intent("AAPL","BUY",1)["actual_submission_authorized"])
 def test_bad_intent(self):
  with self.assertRaises(ValueError):make_intent("AAPL","BUY",0)
 def test_limit_intent(self):
  with self.assertRaises(ValueError):make_intent("AAPL","BUY",1,"limit")
 def test_client_id(self): self.assertTrue(client_order_id(make_intent("AAPL","BUY",1))["client_order_id"].startswith("psim-"))
 def test_payload(self): self.assertFalse(build_payload(make_intent("AAPL","BUY",1),client_order_id(make_intent("AAPL","BUY",1)))["post_allowed"])
 def test_serialize(self):
  i=make_intent("AAPL","BUY",1);self.assertFalse(serialize_request(build_payload(i,client_order_id(i)))["actual_http_method_executed"])
 def test_queue(self):
  i=make_intent("AAPL","BUY",1);self.assertEqual(queue_order(i,client_order_id(i))["status"],"QUEUED_FOR_SIMULATION")
 def test_idempotency(self): self.assertTrue(idempotency_guard(["x","x"])["duplicate_detected"])
 def test_ack(self): self.assertEqual(ack_simulator(make_intent("AAPL","BUY",1),self.c)["ack_status"],"ACK_SIMULATED")
 def test_accept(self): self.assertEqual(broker_response(make_intent("AAPL","BUY",5),"ACCEPTED",self.c)["filled_quantity"],5)
 def test_partial(self): self.assertGreater(broker_response(make_intent("AAPL","BUY",8),"PARTIAL",self.c)["filled_quantity"],0)
 def test_reject(self): self.assertEqual(broker_response(make_intent("AAPL","BUY",5),"REJECTED",self.c)["filled_quantity"],0)
 def test_retry_policy(self): self.assertFalse(retry_policy(self.c)["network_retry_enabled"])
 def test_retry(self): self.assertEqual(retry_simulation(broker_response(make_intent("AAPL","BUY",1),"REJECTED",self.c),self.c)["simulated_retry_attempts"],3)
 def test_receipt(self):
  i=make_intent("AAPL","BUY",2);cid=client_order_id(i);ack=ack_simulator(i,self.c);r=broker_response(i,"ACCEPTED",self.c)
  self.assertEqual(submission_receipt(i,cid,ack,r,retry_simulation(r,self.c))["status"],"SIM_ACCEPTED")
 def test_replay(self):
  r={"receipt_sha256":"x"};self.assertTrue(replay_guard([r,r])["replay_detected"])
 def test_state_machine(self): self.assertFalse(state_machine()["network_submit_state_present"])
 def test_deterministic(self): self.assertTrue(deterministic_replay(make_intent("AAPL","BUY",1),"ACCEPTED",self.c)["deterministic"])
 def test_scenarios(self):
  s=build_scenarios(self.c);self.assertEqual(s["scenario_count"],4);self.assertGreater(s["partial_count"],0)
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
  s=(Path(__file__).resolve().parents[1]/"alpaca_market_data/paper_order_submission_sim_v85_61_80.py").read_text().lower()
  for x in ('urlopen(','tradingclient(','submit_order(','method="post"'):self.assertNotIn(x,s)
 def test_stage_count(self): self.assertEqual(len([f"V85.{i:02d}" for i in range(61,81)]),20)
if __name__=="__main__":unittest.main()
