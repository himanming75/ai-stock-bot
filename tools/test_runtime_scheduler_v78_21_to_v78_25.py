import tempfile,unittest
from pathlib import Path
from runtime_scheduler.runtime_scheduler_pipeline_v78_21_25 import *
class Tests(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory();self.r=Path(self.t.name)
        self.cert=self.r/"cert.json";self.cfg=self.r/"cfg.json"
        write_json(self.cert,{"stage":"V78.20","status":"PASS",
          "certification_scope":"OFFLINE_RUNTIME_SCHEDULER_DEVELOPMENT_ONLY",
          "champion_candidate":{"candidate_id":"abc"}})
        write_json(self.cfg,{"runtime_scheduler":{"mode":"deterministic_offline","final_tick":7,
          "checkpoint_enabled":True,"jobs":[
          {"job_id":"heartbeat","interval_ticks":2,"start_tick":0,"max_retries":0,"enabled":True},
          {"job_id":"market_clock","interval_ticks":3,"start_tick":0,"max_retries":1,"enabled":True},
          {"job_id":"portfolio_snapshot","interval_ticks":5,"start_tick":5,"max_retries":0,"enabled":True}]}})
    def tearDown(self):self.t.cleanup()
    def chain(self):
        o21=self.r/"o21";a=build_runtime_scheduler_foundation(self.cert,self.cfg,o21)
        o22=self.r/"o22";b=build_scheduled_job_registry(o21/"runtime_scheduler_foundation_v78_21.json",o22)
        o23=self.r/"o23";c=run_deterministic_tick_job_execution(o21/"runtime_scheduler_foundation_v78_21.json",o23)
        o24=self.r/"o24";d=run_runtime_scheduler_safety_gate(
          o21/"runtime_scheduler_foundation_v78_21.json",
          o22/"scheduled_job_registry_v78_22.json",
          o23/"deterministic_tick_job_execution_v78_23.json",o24)
        o25=self.r/"o25";e=issue_runtime_scheduler_certificate(
          o21/"runtime_scheduler_foundation_verification_v78_21.json",
          o22/"scheduled_job_registry_verification_v78_22.json",
          o23/"deterministic_tick_job_execution_verification_v78_23.json",
          o24/"runtime_scheduler_safety_gate_verification_v78_24.json",
          o21/"runtime_scheduler_foundation_v78_21.json",o25)
        return a,b,c,d,e
    def test_full_chain(self):self.assertTrue(all(x["status"]=="PASS" for x in self.chain()))
    def test_duplicate_job_blocked(self):
        r=JobRegistry();j=ScheduledJob("x",1,0,0);r.register(j,lambda t:t)
        with self.assertRaises(ValueError):r.register(j,lambda t:t)
    def test_due_jobs(self):
        r=JobRegistry();r.register(ScheduledJob("x",2,0,0),lambda t:t)
        self.assertEqual([j.job_id for j in r.due_jobs(4)],["x"])
        self.assertEqual(r.due_jobs(3),[])
    def test_non_contiguous_tick_blocked(self):
        s=DeterministicTickScheduler(JobRegistry())
        with self.assertRaises(ValueError):s.run_tick(1)
    def test_retry_then_success(self):
        r=JobRegistry();state={"n":0}
        def h(t):
            state["n"]+=1
            if state["n"]==1:raise RuntimeError("x")
            return {"t":t}
        r.register(ScheduledJob("x",1,0,1),h);s=DeterministicTickScheduler(r);recs=s.run_tick(0)
        self.assertEqual([x.status for x in recs],["RETRY","SUCCESS"])
    def test_checkpoint_restore(self):
        r=JobRegistry();r.register(ScheduledJob("x",1,0,0),lambda t:{"t":t})
        s=DeterministicTickScheduler(r);s.run_tick(0);cp=s.checkpoint();restored=DeterministicTickScheduler.restore(r,cp)
        self.assertEqual(restored.current_tick,0)
    def test_checkpoint_tamper_blocked(self):
        s=DeterministicTickScheduler(JobRegistry());cp=s.checkpoint();cp["current_tick"]=9
        with self.assertRaises(ValueError):DeterministicTickScheduler.restore(JobRegistry(),cp)
    def test_certificate_scope(self):
        c=self.chain()[4];self.assertEqual(c["certification_scope"],"OFFLINE_MARKET_CLOCK_DEVELOPMENT_ONLY")
        self.assertFalse(c["actual_order_submission_approved"])
    def test_invalid_certificate_rejected(self):
        write_json(self.cert,{"stage":"V78.20","status":"FAIL"})
        self.assertEqual(build_runtime_scheduler_foundation(self.cert,self.cfg,self.r/"bad")["status"],"FAIL")
    def test_safety_invariants(self):
        for x in self.chain():
            self.assertEqual(x["actual_orders_submitted"],0);self.assertFalse(x["network_allowed"]);self.assertFalse(x["broker_connected"])
    def test_deterministic_digest(self):
        self.assertEqual(digest_json({"b":2,"a":1}),digest_json({"a":1,"b":2}))
if __name__=="__main__":unittest.main()
