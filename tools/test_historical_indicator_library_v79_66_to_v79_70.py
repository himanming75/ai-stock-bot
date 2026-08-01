from pathlib import Path
from tempfile import TemporaryDirectory
import json,unittest
from alpaca_market_data.historical_indicator_library_v79_66_70 import *
def rows():
 out=[]
 for s,p in [('AAPL',100),('MSFT',200),('SPY',500)]:
  for i in range(4):out.append({'symbol':s,'timeframe':'1Min','timestamp':f'2026-01-05T14:3{i}:00Z','source_close':p+i,'features':{}})
 return out
class T(unittest.TestCase):
 def setUp(self):self.c=IndicatorConfig()
 def test_config(self):self.c.validate()
 def test_network(self):
  with self.assertRaises(ValueError):IndicatorConfig(allow_network=True).validate()
 def test_registry(self):self.assertEqual(build_indicator_registry(self.c)['indicator_count'],9)
 def test_build(self):self.assertEqual(len(build_indicators(rows(),self.c)),12)
 def test_stochastic(self):
  vals=[x['indicators']['stochastic_k'] for x in build_indicators(rows(),self.c) if x['indicators']['stochastic_k'] is not None];self.assertTrue(all(0<=v<=100 for v in vals))
 def test_validate(self):
  reg=build_indicator_registry(self.c);self.assertEqual(validate_indicator_rows(build_indicators(rows(),self.c),reg)['indicator_row_count'],12)
 def test_duplicate(self):
  reg=build_indicator_registry(self.c);x=build_indicators(rows(),self.c)
  with self.assertRaises(ValueError):validate_indicator_rows(x+[x[0]],reg)
 def test_cache_reuse(self):
  with TemporaryDirectory() as t:
   r=Path(t);src=r/'x';src.write_text('{}\n');reg=build_indicator_registry(self.c);x=build_indicators(rows(),self.c);st=validate_indicator_rows(x,reg);store_indicators(r/'o',src,reg,x,st);self.assertTrue(store_indicators(r/'o',src,reg,x,st)['reused_existing_cache'])
 def test_manifest(self):
  with TemporaryDirectory() as t:
   r=Path(t);src=r/'x';src.write_text('{}\n');reg=build_indicator_registry(self.c);x=build_indicators(rows(),self.c);st=validate_indicator_rows(x,reg);z=store_indicators(r/'o',src,reg,x,st);self.assertTrue(verify_indicator_manifest(r/'o',z['manifest']))
 def test_tamper(self):
  with TemporaryDirectory() as t:
   r=Path(t);src=r/'x';src.write_text('{}\n');reg=build_indicator_registry(self.c);x=build_indicators(rows(),self.c);st=validate_indicator_rows(x,reg);z=store_indicators(r/'o',src,reg,x,st);(r/'o/indicator_registry.json').write_text('{}')
   with self.assertRaises(ValueError):verify_indicator_manifest(r/'o',z['manifest'])
 def test_bad_load(self):
  with TemporaryDirectory() as t:
   p=Path(t)/'x';p.write_text('bad\n')
   with self.assertRaises(ValueError):load_feature_rows(p)
 def test_bad_cert(self):
  with TemporaryDirectory() as t:
   p=Path(t)/'c';p.write_text('{}')
   with self.assertRaises(ValueError):validate_feature_certificate(p)
 def test_safety(self):
  s=(Path(__file__).resolve().parents[1]/'alpaca_market_data/historical_indicator_library_v79_66_70.py').read_text().lower();self.assertNotIn('submit_order(',s);self.assertNotIn('tradingclient(',s);self.assertNotIn('api_secret',s)
if __name__=='__main__':unittest.main()
