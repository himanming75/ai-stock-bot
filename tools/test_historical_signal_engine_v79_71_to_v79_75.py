from pathlib import Path
from tempfile import TemporaryDirectory
import json,unittest
from alpaca_market_data.historical_signal_engine_v79_71_75 import *

def rows():
 return [
 {"symbol":"AAPL","timeframe":"1Min","timestamp":"1","source_close":100,"indicators":{"macd":1,"macd_signal":0,"roc":2,"stochastic_k":20,"bollinger_lower":90,"bollinger_upper":110}},
 {"symbol":"AAPL","timeframe":"1Min","timestamp":"2","source_close":120,"indicators":{"macd":-1,"macd_signal":0,"roc":-2,"stochastic_k":80,"bollinger_lower":90,"bollinger_upper":110}},
 {"symbol":"AAPL","timeframe":"1Min","timestamp":"3","source_close":100,"indicators":{"macd":0,"macd_signal":0,"roc":0,"stochastic_k":50,"bollinger_lower":90,"bollinger_upper":110}}]
class T(unittest.TestCase):
 def setUp(self): self.c=SignalConfig()
 def test_config(self): self.c.validate()
 def test_network(self):
  with self.assertRaises(ValueError): SignalConfig(allow_network=True).validate()
 def test_registry(self): self.assertEqual(build_signal_registry(self.c)["rule_count"],4)
 def test_build(self): self.assertEqual([x["signal"] for x in build_signals(rows(),self.c)],["BUY","SELL","HOLD"])
 def test_confidence(self): self.assertTrue(all(0<=x["confidence"]<=1 for x in build_signals(rows(),self.c)))
 def test_validate(self): self.assertEqual(validate_signal_rows(build_signals(rows(),self.c))["signal_row_count"],3)
 def test_duplicate(self):
  x=build_signals(rows(),self.c)
  with self.assertRaises(ValueError): validate_signal_rows(x+[x[0]])
 def test_bad_load(self):
  with TemporaryDirectory() as t:
   p=Path(t)/"x"; p.write_text("bad")
   with self.assertRaises(ValueError): load_indicator_rows(p)
 def test_cache_reuse(self):
  with TemporaryDirectory() as t:
   r=Path(t); src=r/"src"; src.write_text("{}"); reg=build_signal_registry(self.c); x=build_signals(rows(),self.c); st=validate_signal_rows(x)
   store_signals(r/"out",src,reg,x,st); self.assertTrue(store_signals(r/"out",src,reg,x,st)["reused_existing_cache"])
 def test_manifest(self):
  with TemporaryDirectory() as t:
   r=Path(t); src=r/"src"; src.write_text("{}"); reg=build_signal_registry(self.c); x=build_signals(rows(),self.c); st=validate_signal_rows(x)
   z=store_signals(r/"out",src,reg,x,st); self.assertTrue(verify_signal_manifest(r/"out",z["manifest"]))
 def test_tamper(self):
  with TemporaryDirectory() as t:
   r=Path(t); src=r/"src"; src.write_text("{}"); reg=build_signal_registry(self.c); x=build_signals(rows(),self.c); st=validate_signal_rows(x)
   z=store_signals(r/"out",src,reg,x,st); (r/"out/signal_rule_registry.json").write_text("{}")
   with self.assertRaises(ValueError): verify_signal_manifest(r/"out",z["manifest"])
 def test_bad_cert(self):
  with TemporaryDirectory() as t:
   p=Path(t)/"c"; p.write_text("{}")
   with self.assertRaises(ValueError): validate_indicator_certificate(p)
 def test_safety(self):
  s=(Path(__file__).resolve().parents[1]/"alpaca_market_data/historical_signal_engine_v79_71_75.py").read_text().lower()
  self.assertNotIn("submit_order(",s); self.assertNotIn("tradingclient(",s); self.assertNotIn("api_secret",s)
if __name__=="__main__": unittest.main()
