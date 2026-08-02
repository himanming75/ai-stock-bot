from __future__ import annotations
import json, tempfile, unittest
from pathlib import Path
from autonomous_paper_runtime.runtime_control_bundle import RuntimeControlBundle

class Tests(unittest.TestCase):
    def write(self, path, payload):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")

    def run_case(self, runtime, token=None, market=None, risk=None, health=None):
        t = tempfile.TemporaryDirectory(); self.addCleanup(t.cleanup)
        root = Path(t.name)
        paths = {n: root/n for n in ["runtime.json","token.json","market.json","risk.json","health.json","result.json","control.json"]}
        self.write(paths["runtime.json"], runtime)
        if token is not None: self.write(paths["token.json"], token)
        if market is not None: self.write(paths["market.json"], market)
        if risk is not None: self.write(paths["risk.json"], risk)
        if health is not None: self.write(paths["health.json"], health)
        result = RuntimeControlBundle().run(
            runtime_result_path=paths["runtime.json"], runtime_token_path=paths["token.json"],
            market_snapshot_path=paths["market.json"], daily_risk_snapshot_path=paths["risk.json"],
            health_snapshot_path=paths["health.json"], result_path=paths["result.json"],
            control_token_path=paths["control.json"])
        return result, paths

    def ready_runtime(self):
        return {"status":"PASS","state":"AUTONOMOUS_RUNTIME_READY","runtime_ready":True,"runtime_cycle_id":"runtime-001","safe_mode_engaged":False}
    def token(self):
        return {"runtime_cycle_id":"runtime-001","runtime_ready":True,"actual_submission_allowed":False,"broker_network_allowed":False}
    def market(self):
        return {"market_phase":"TRADING_WINDOW","market_is_open":True,"new_orders_allowed":True,"holiday":False}
    def risk(self):
        return {"orders_used":1,"max_daily_orders":5,"daily_pnl":-10,"max_daily_loss":100,"current_exposure":1000,"max_exposure":5000,"consecutive_losses":0,"max_consecutive_losses":3}
    def health(self):
        return {"disk_free_mb":10000,"minimum_disk_free_mb":500,"heartbeat_age_seconds":5,"maximum_heartbeat_age_seconds":300,"filesystem_writable":True,"system_clock_synchronized":True,"runtime_process_count":1}

    def test_waits_before_runtime_ready(self):
        result,_ = self.run_case({"status":"PASS","state":"RUNTIME_WAITING","runtime_ready":False,"safe_mode_engaged":False})
        self.assertEqual(result["state"],"WAIT_RUNTIME_READY")

    def test_all_gates_ready(self):
        result,paths = self.run_case(self.ready_runtime(),self.token(),self.market(),self.risk(),self.health())
        self.assertEqual(result["state"],"RUNTIME_CONTROL_READY")
        self.assertTrue(paths["control.json"].exists())

    def test_market_closed_blocks(self):
        m=self.market(); m["market_is_open"]=False
        result,_=self.run_case(self.ready_runtime(),self.token(),m,self.risk(),self.health())
        self.assertEqual(result["status"],"BLOCKED")

    def test_daily_loss_blocks(self):
        r=self.risk(); r["daily_pnl"]=-150
        result,_=self.run_case(self.ready_runtime(),self.token(),self.market(),r,self.health())
        self.assertEqual(result["status"],"BLOCKED")

    def test_health_stale_blocks(self):
        h=self.health(); h["heartbeat_age_seconds"]=999
        result,_=self.run_case(self.ready_runtime(),self.token(),self.market(),self.risk(),h)
        self.assertEqual(result["status"],"BLOCKED")

    def test_missing_snapshot_blocks(self):
        result,_=self.run_case(self.ready_runtime(),self.token(),None,self.risk(),self.health())
        self.assertEqual(result["status"],"BLOCKED")

if __name__ == "__main__":
    unittest.main()
