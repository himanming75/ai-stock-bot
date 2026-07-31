import tempfile,unittest
from dataclasses import replace
from pathlib import Path
from paper_event.paper_event_pipeline_v78_6_10 import *

class Tests(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory();self.r=Path(self.t.name)
        self.cert=self.r/"cert.json";self.cfg=self.r/"cfg.json"
        write_json(self.cert,{"stage":"V78.5","status":"PASS",
          "certification_scope":"OFFLINE_PAPER_BROKER_RUNTIME_ONLY",
          "champion_candidate":{"candidate_id":"abc"}})
        write_json(self.cfg,{"paper_event":{"stream_id":"TEST","starting_cash":100000.0,
          "allowed_event_types":["ORDER_CREATED","ORDER_ACCEPTED","ORDER_FILLED","ORDER_CANCELED"],
          "hash_algorithm":"sha256"}})
    def tearDown(self):self.t.cleanup()
    def chain(self):
        o6=self.r/"o6";a=build_paper_event_engine(self.cert,self.cfg,o6)
        o7=self.r/"o7";b=build_order_fill_event_ledger(o6/"paper_event_engine_v78_6.json",o7)
        o8=self.r/"o8";c=run_event_replay_recovery(
          o6/"paper_event_engine_v78_6.json",
          o7/"order_fill_event_ledger_v78_7.json",o8)
        o9=self.r/"o9";d=run_paper_event_safety_gate(
          o6/"paper_event_engine_v78_6.json",
          o7/"order_fill_event_ledger_v78_7.json",
          o8/"event_replay_recovery_v78_8.json",o9)
        o10=self.r/"o10";e=issue_paper_event_certificate(
          o6/"paper_event_engine_verification_v78_6.json",
          o7/"order_fill_event_ledger_verification_v78_7.json",
          o8/"event_replay_recovery_verification_v78_8.json",
          o9/"paper_event_safety_gate_verification_v78_9.json",
          o6/"paper_event_engine_v78_6.json",o10)
        return a,b,c,d,e
    def test_full_chain(self):self.assertTrue(all(x["status"]=="PASS" for x in self.chain()))
    def test_event_ids_unique(self):
        events=self.chain()[1]["events"]
        self.assertEqual(len(events),len({x["event_id"] for x in events}))
    def test_sequence_contiguous(self):
        self.assertEqual([x["sequence"] for x in self.chain()[1]["events"]],list(range(1,9)))
    def test_replay_expected_state(self):
        state=self.chain()[2]["recovered_state"]
        self.assertEqual(state["cash"],99440.0)
        self.assertEqual(state["positions"],[{"symbol":"AAPL","quantity":6,"average_price":100.0}])
    def test_append_rejects_sequence_gap(self):
        f=PaperEventFactory("X");l=AppendOnlyEventLedger("X")
        e=f.create(2,"ORDER_CREATED","O",{"symbol":"AAPL","side":"buy","quantity":1},"GENESIS")
        with self.assertRaises(ValueError):l.append(e)
    def test_append_rejects_hash_tamper(self):
        f=PaperEventFactory("X");l=AppendOnlyEventLedger("X")
        e=f.create(1,"ORDER_CREATED","O",{"symbol":"AAPL","side":"buy","quantity":1},"GENESIS")
        bad=replace(e,payload={"symbol":"MSFT","side":"buy","quantity":1})
        with self.assertRaises(ValueError):l.append(bad)
    def test_duplicate_event_rejected(self):
        f=PaperEventFactory("X");l=AppendOnlyEventLedger("X")
        e=f.create(1,"ORDER_CREATED","O",{"symbol":"AAPL","side":"buy","quantity":1},"GENESIS")
        l.append(e)
        with self.assertRaises(ValueError):l.append(e)
    def test_replay_rejects_duplicate_event(self):
        f=PaperEventFactory("X")
        e=f.create(1,"ORDER_CREATED","O",{"symbol":"AAPL","side":"buy","quantity":1},"GENESIS")
        with self.assertRaises(ValueError):replay_events([e,e])
    def test_replay_rejects_gap(self):
        f=PaperEventFactory("X")
        e=f.create(2,"ORDER_CREATED","O",{"symbol":"AAPL","side":"buy","quantity":1},"GENESIS")
        with self.assertRaises(ValueError):replay_events([e])
    def test_invalid_certificate_rejected(self):
        write_json(self.cert,{"stage":"V78.5","status":"FAIL"})
        self.assertEqual(build_paper_event_engine(self.cert,self.cfg,self.r/"bad")["status"],"FAIL")
    def test_certificate_scope(self):
        c=self.chain()[4]
        self.assertEqual(c["certification_scope"],"OFFLINE_EVENT_BUS_FOUNDATION_ONLY")
        self.assertFalse(c["actual_order_submission_approved"])
    def test_safety_invariants(self):
        for x in self.chain():
            self.assertEqual(x["actual_orders_submitted"],0)
            self.assertFalse(x["network_allowed"]);self.assertFalse(x["broker_connected"])
    def test_ledger_deterministic(self):
        self.assertEqual(self.chain()[1]["ledger_verification"]["ledger_sha256"],
                         self.chain()[1]["ledger_verification"]["ledger_sha256"])
    def test_deterministic_digest(self):
        self.assertEqual(digest_json({"b":2,"a":1}),digest_json({"a":1,"b":2}))
if __name__=="__main__":unittest.main()
