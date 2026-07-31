import tempfile,unittest
from dataclasses import replace
from pathlib import Path
from event_bus.event_bus_pipeline_v78_11_15 import *

class Tests(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory();self.r=Path(self.t.name)
        self.cert=self.r/"cert.json";self.cfg=self.r/"cfg.json"
        write_json(self.cert,{"stage":"V78.10","status":"PASS",
          "certification_scope":"OFFLINE_EVENT_BUS_FOUNDATION_ONLY",
          "champion_candidate":{"candidate_id":"abc"}})
        write_json(self.cfg,{"event_bus":{"mode":"offline","max_retries":2,
          "topics":["order.events","fill.events","system.events"],
          "delivery_policy":"at_least_once_with_idempotency"}})
    def tearDown(self):self.t.cleanup()
    def chain(self):
        o11=self.r/"o11";a=build_event_bus_foundation(self.cert,self.cfg,o11)
        o12=self.r/"o12";b=build_subscriber_registry(o11/"event_bus_foundation_v78_11.json",o12)
        o13=self.r/"o13";c=run_event_dispatch_retry_dlq(o11/"event_bus_foundation_v78_11.json",o13)
        o14=self.r/"o14";d=run_event_bus_safety_gate(
          o11/"event_bus_foundation_v78_11.json",
          o12/"subscriber_registry_v78_12.json",
          o13/"event_dispatch_retry_dlq_v78_13.json",o14)
        o15=self.r/"o15";e=issue_event_bus_certificate(
          o11/"event_bus_foundation_verification_v78_11.json",
          o12/"subscriber_registry_verification_v78_12.json",
          o13/"event_dispatch_retry_dlq_verification_v78_13.json",
          o14/"event_bus_safety_gate_verification_v78_14.json",
          o11/"event_bus_foundation_v78_11.json",o15)
        return a,b,c,d,e
    def test_full_chain(self):self.assertTrue(all(x["status"]=="PASS" for x in self.chain()))
    def test_registry_duplicate_blocked(self):
        r=SubscriberRegistry();r.register("x",["a"],lambda e:None)
        with self.assertRaises(ValueError):r.register("x",["a"],lambda e:None)
    def test_registry_wildcard(self):
        r=SubscriberRegistry();r.register("x",["*"],lambda e:None)
        self.assertEqual([x[0] for x in r.matching("any")],["x"])
    def test_duplicate_publish_blocked(self):
        b=OfflineEventBus();e=b.make_event("a","T",{})
        b.publish(e)
        with self.assertRaises(ValueError):b.publish(e)
    def test_hash_tamper_blocked(self):
        b=OfflineEventBus();e=b.make_event("a","T",{})
        bad=replace(e,payload={"x":1})
        with self.assertRaises(ValueError):b.publish(bad)
    def test_retry_then_success(self):
        b=OfflineEventBus(max_retries=2);state={"n":0}
        def h(e):
            state["n"]+=1
            if state["n"]<2:raise RuntimeError("x")
        b.registry.register("s",["a"],h);e=b.make_event("a","T",{});records=b.publish(e)
        self.assertEqual(state["n"],2);self.assertEqual(records[-1].status,"DELIVERED")
    def test_dead_letter_created(self):
        b=OfflineEventBus(max_retries=1)
        b.registry.register("s",["a"],lambda e:(_ for _ in ()).throw(RuntimeError("x")))
        b.publish(b.make_event("a","T",{}))
        self.assertEqual(len(b.dead_letter_queue),1)
    def test_dead_letter_replay(self):
        b=OfflineEventBus(max_retries=0);state={"fail":True}
        def h(e):
            if state["fail"]:raise RuntimeError("x")
        b.registry.register("s",["a"],h);b.publish(b.make_event("a","T",{}))
        state["fail"]=False
        rec=b.replay_dead_letter(0)
        self.assertEqual(rec.status,"DELIVERED_FROM_DLQ")
        self.assertEqual(b.dead_letter_queue[0]["status"],"RECOVERED")
    def test_delivery_ids_unique(self):
        records=self.chain()[2]["delivery_records"]
        self.assertEqual(len(records),len({x["delivery_id"] for x in records}))
    def test_certificate_scope(self):
        c=self.chain()[4]
        self.assertEqual(c["certification_scope"],"OFFLINE_SESSION_MANAGER_DEVELOPMENT_ONLY")
        self.assertFalse(c["actual_order_submission_approved"])
    def test_invalid_certificate_rejected(self):
        write_json(self.cert,{"stage":"V78.10","status":"FAIL"})
        self.assertEqual(build_event_bus_foundation(self.cert,self.cfg,self.r/"bad")["status"],"FAIL")
    def test_safety_invariants(self):
        for x in self.chain():
            self.assertEqual(x["actual_orders_submitted"],0)
            self.assertFalse(x["network_allowed"]);self.assertFalse(x["broker_connected"])
    def test_sequence_monotonic(self):
        b=OfflineEventBus()
        self.assertEqual([b.make_event("a","T",{}).sequence for _ in range(3)],[1,2,3])
    def test_deterministic_digest(self):
        self.assertEqual(digest_json({"b":2,"a":1}),digest_json({"a":1,"b":2}))
if __name__=="__main__":unittest.main()
