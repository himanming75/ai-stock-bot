import tempfile,unittest,json
from pathlib import Path
from multi_broker_production.config import load,validate
from multi_broker_production.health import evaluate as health
from multi_broker_production.portfolio import aggregate
from multi_broker_production.failover import build
from multi_broker_production.engine import evaluate

SNAPS=[
 {"broker_id":"A","account_id_masked":"*1","status":"ACTIVE","cash":50,"equity":100,"buying_power":50,"positions":[],"orders":[],"read_latency_ms":1,"read_only":True,"supports_orders":False},
 {"broker_id":"B","account_id_masked":"*2","status":"ACTIVE","cash":100,"equity":200,"buying_power":100,"positions":[],"orders":[],"read_latency_ms":1,"read_only":True,"supports_orders":False},
]
POL={"maximum_read_latency_ms":1000,"minimum_healthy_brokers":1,"failover_enabled":True}

class Tests(unittest.TestCase):
    def test_policy_safe(self):
        with tempfile.TemporaryDirectory() as t:
            c=load(Path(t))
            self.assertFalse(c["broker_write_enabled"])
            self.assertFalse(c["automatic_failover_write_enabled"])
    def test_validate(self):
        with tempfile.TemporaryDirectory() as t:self.assertTrue(validate(load(Path(t)))["valid"])
    def test_health(self):self.assertEqual(health(SNAPS,POL)["healthy_broker_count"],2)
    def test_portfolio(self):self.assertEqual(aggregate(SNAPS)["summary"]["total_equity"],300)
    def test_failover(self):self.assertTrue(build(health(SNAPS,POL),POL)["read_failover_ready"])
    def test_engine_live_zero(self):
        with tempfile.TemporaryDirectory() as t:self.assertEqual(evaluate(Path(t))["actual_live_orders_submitted"],0)

if __name__=="__main__":unittest.main()
