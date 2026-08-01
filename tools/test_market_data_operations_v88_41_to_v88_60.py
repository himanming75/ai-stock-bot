from pathlib import Path
from tempfile import TemporaryDirectory
from datetime import datetime, timedelta, timezone
import unittest
from alpaca_market_data.market_data_operations_v88_41_60 import *

class T(unittest.TestCase):
 def setUp(self): self.c=MarketDataOperationsConfig();self.b=fixture_bars()
 def test_config(self): self.c.validate()
 def test_network_rejected(self):
  with self.assertRaises(ValueError): MarketDataOperationsConfig(market_data_network_enabled=True).validate()
 def test_schema(self): self.assertEqual(validate_bar_schema(self.b[-1])["status"],"PASS")
 def test_freshness(self):
  now=datetime.fromisoformat(self.b[-1]["timestamp"])+timedelta(seconds=30)
  self.assertEqual(freshness_check(self.c,self.b[-1]["timestamp"],now)["status"],"PASS")
 def test_stale(self):
  now=datetime.fromisoformat(self.b[-1]["timestamp"])+timedelta(seconds=999)
  self.assertEqual(freshness_check(self.c,self.b[-1]["timestamp"],now)["status"],"FAIL")
 def test_missing(self): self.assertEqual(missing_bar_detection(self.c,self.b)["status"],"PASS")
 def test_duplicate(self): self.assertEqual(duplicate_bar_detection(self.c,self.b+[dict(self.b[-1])])["status"],"FAIL")
 def test_ordering(self): self.assertEqual(out_of_order_detection(self.c,[self.b[1],self.b[0]])["status"],"FAIL")
 def test_clock(self):
  t=datetime.now(timezone.utc);self.assertEqual(market_clock_consistency(self.c,t,t+timedelta(seconds=2))["status"],"PASS")
 def test_symbol(self): self.assertEqual(symbol_health(self.c,"AAPL",self.b)["status"],"PASS")
 def test_provider(self): self.assertEqual(provider_health(self.c,True,20)["status"],"PASS")
 def test_fallback(self): self.assertFalse(fallback_policy(self.c,"FAIL")["strategy_cycle_allowed"])
 def test_classification(self):
  clean=data_gap_classification(missing_bar_detection(self.c,self.b),duplicate_bar_detection(self.c,self.b),out_of_order_detection(self.c,self.b))
  self.assertEqual(clean["status"],"CLEAN")
 def test_incident(self):
  x={"status":"DEGRADED"};p={"status":"FAIL"}
  self.assertTrue(data_incident(x,p)["incident_required"])
 def test_recovery(self): self.assertEqual(recovery_plan({"incident_required":True})["status"],"PASS")
 def test_positive(self): self.assertEqual(positive_scenario(self.c)["status"],"PASS")
 def test_negative(self): self.assertEqual(negative_scenarios(self.c)["status"],"PASS")
 def test_store_reuse(self):
  with TemporaryDirectory() as t:
   o=Path(t);store(o,{"a":{"x":1}});self.assertTrue(store(o,{"a":{"x":1}})["reused"])
 def test_manifest(self):
  with TemporaryDirectory() as t:
   o=Path(t);z=store(o,{"a":{"x":1}});m=manifest(o,z["ledger"]);self.assertTrue(verify_manifest(o,m))
 def test_bad_source(self):
  with TemporaryDirectory() as t:
   p=Path(t)/"x";p.write_text("{}")
   with self.assertRaises(ValueError):validate_source(p)
 def test_stage_count(self): self.assertEqual(len([f"V88.{i:02d}" for i in range(41,61)]),20)

if __name__=="__main__":unittest.main()
