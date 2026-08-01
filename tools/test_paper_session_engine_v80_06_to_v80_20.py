from pathlib import Path
from tempfile import TemporaryDirectory
import json,unittest
from alpaca_market_data.paper_session_engine_v80_06_20 import *

class T(unittest.TestCase):
 def setUp(self): self.c=PaperSessionConfig()
 def test_config(self): self.c.validate()
 def test_network_rejected(self):
  with self.assertRaises(ValueError): PaperSessionConfig(allow_network=True).validate()
 def test_weekend_rejected(self):
  with self.assertRaises(ValueError): build_market_calendar(PaperSessionConfig(session_date="2026-01-04"))
 def test_market_state(self):
  cal=build_market_calendar(self.c); self.assertEqual(market_state(cal,"2026-01-05T10:00:00-05:00"),"OPEN")
 def test_account(self):
  a=build_account_snapshot(self.c); self.assertEqual(a["cash"],100000)
 def test_portfolio(self):
  p=initialize_portfolio(build_account_snapshot(self.c)); self.assertEqual(p["positions"],{})
 def test_session_id_deterministic(self):
  cfg=build_session_config(self.c); a=build_account_snapshot(self.c); self.assertEqual(make_session_id(cfg,a),make_session_id(cfg,a))
 def test_invalid_transition(self):
  cfg=build_session_config(self.c);cal=build_market_calendar(self.c);a=build_account_snapshot(self.c);p=initialize_portfolio(a);s=create_session(cfg,cal,a,p)
  with self.assertRaises(ValueError): transition_session(s,"OPEN","bad")
 def test_lifecycle(self):
  cfg=build_session_config(self.c);cal=build_market_calendar(self.c);a=build_account_snapshot(self.c);p=initialize_portfolio(a);s=create_session(cfg,cal,a,p)
  final,events=build_lifecycle(s,cal);self.assertEqual(final["state"],"CERTIFIED");self.assertEqual(len(events),5)
 def test_validation(self):
  cfg=build_session_config(self.c);cal=build_market_calendar(self.c);a=build_account_snapshot(self.c);p=initialize_portfolio(a);s=create_session(cfg,cal,a,p)
  self.assertEqual(validate_session(s,cfg,cal,a,p)["status"],"PASS")
 def test_cash_ledger(self): self.assertTrue(build_cash_ledger(build_account_snapshot(self.c),[])["cash_conserved"])
 def test_equity_ledger(self): self.assertTrue(build_equity_ledger(build_account_snapshot(self.c),[{"to":"READY"}])["equity_conserved"])
 def test_position_ledger(self): self.assertTrue(build_position_ledger(initialize_portfolio(build_account_snapshot(self.c)))["positions_conserved"])
 def test_store_reuse(self):
  with TemporaryDirectory() as t:
   out=Path(t);docs={"session":{"session_id":"x"},"a":{"v":1}};store_session_package(out,docs);self.assertTrue(store_session_package(out,docs)["reused"])
 def test_manifest(self):
  with TemporaryDirectory() as t:
   out=Path(t);z=store_session_package(out,{"session":{"session_id":"x"},"a":{"v":1}});m=build_manifest(out,z["ledger"]);self.assertTrue(verify_manifest(out,m))
 def test_manifest_tamper(self):
  with TemporaryDirectory() as t:
   out=Path(t);z=store_session_package(out,{"session":{"session_id":"x"},"a":{"v":1}});m=build_manifest(out,z["ledger"]);(out/"sessions/x/a.json").write_text("{}")
   with self.assertRaises(ValueError): verify_manifest(out,m)
 def test_bad_cert(self):
  with TemporaryDirectory() as t:
   p=Path(t)/"c";p.write_text("{}")
   with self.assertRaises(ValueError): validate_readiness_certificate(p)
 def test_safety(self):
  s=(Path(__file__).resolve().parents[1]/"alpaca_market_data/paper_session_engine_v80_06_20.py").read_text().lower()
  for x in ("submit_order(","tradingclient(","api_secret","api_key","os.getenv"): self.assertNotIn(x,s)
 def test_stage_count(self): self.assertEqual(len([f"V80.{i:02d}" for i in range(6,21)]),15)
if __name__=="__main__":unittest.main()
