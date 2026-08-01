from pathlib import Path
from tempfile import TemporaryDirectory
import json,unittest
from alpaca_market_data.historical_feature_store_v79_61_65 import *
def ds(p):
 p.parent.mkdir(parents=True,exist_ok=True); rows=[]
 for s,b in [('AAPL',100),('MSFT',200),('SPY',500)]:
  for i in range(4): rows.append({'symbol':s,'timeframe':'1Min','timestamp':f'2026-01-05T14:3{i}:00Z','open':b+i,'high':b+i+1,'low':b+i-1,'close':b+i+.5,'volume':100+i})
 p.write_text(''.join(json.dumps(x)+'\n' for x in rows))
class T(unittest.TestCase):
 def setUp(self): self.c=FeatureStoreConfig()
 def test_config(self): self.c.validate()
 def test_network(self):
  with self.assertRaises(ValueError): FeatureStoreConfig(allow_network=True).validate()
 def test_registry(self): self.assertEqual(registry(self.c)['feature_count'],7)
 def test_bad_load(self):
  with TemporaryDirectory() as t:
   p=Path(t)/'x';p.write_text('x')
   with self.assertRaises(ValueError): load(p)
 def test_build(self):
  with TemporaryDirectory() as t:
   p=Path(t)/'x';ds(p);self.assertEqual(len(build(load(p),self.c)),12)
 def test_rsi(self):
  with TemporaryDirectory() as t:
   p=Path(t)/'x';ds(p);v=[x['features']['rsi_2'] for x in build(load(p),self.c) if x['features']['rsi_2'] is not None];self.assertTrue(all(0<=x<=100 for x in v))
 def test_validate(self):
  with TemporaryDirectory() as t:
   p=Path(t)/'x';ds(p);r=registry(self.c);self.assertEqual(validate(build(load(p),self.c),r)['feature_row_count'],12)
 def test_duplicate(self):
  with TemporaryDirectory() as t:
   p=Path(t)/'x';ds(p);r=registry(self.c);x=build(load(p),self.c)
   with self.assertRaises(ValueError): validate(x+[x[0]],r)
 def test_reuse(self):
  with TemporaryDirectory() as t:
   q=Path(t);p=q/'x';ds(p);r=registry(self.c);x=build(load(p),self.c);s=validate(x,r);store(q/'o',p,r,x,s);self.assertTrue(store(q/'o',p,r,x,s)['reused_existing_cache'])
 def test_manifest(self):
  with TemporaryDirectory() as t:
   q=Path(t);p=q/'x';ds(p);r=registry(self.c);x=build(load(p),self.c);z=store(q/'o',p,r,x,validate(x,r));self.assertTrue(verify(q/'o',z['manifest']))
 def test_tamper(self):
  with TemporaryDirectory() as t:
   q=Path(t);p=q/'x';ds(p);r=registry(self.c);x=build(load(p),self.c);z=store(q/'o',p,r,x,validate(x,r));(q/'o/feature_registry.json').write_text('{}')
   with self.assertRaises(ValueError):verify(q/'o',z['manifest'])
 def test_cert(self):
  with TemporaryDirectory() as t:
   q=Path(t);o=q/'release/v79_65/output';o.mkdir(parents=True);r={'status':'PASS','registry':registry(self.c),'stats':{'feature_row_count':1,'unique_feature_key_count':1,'invalid_feature_value_count':0},'cache_id':'x','created':True,'reused_existing_cache':False,'source_preserved':True,'network_requests_executed':0,'credentials_used':0,'trading_client_created':False,'actual_orders_submitted':0};(q/'release/v79_60/output').mkdir(parents=True);(q/'release/v79_60/output/historical_dataset_backup_restore_certificate_v79_60.json').write_text('{}');self.assertEqual(certificate(q,o,self.c,r)['status'],'PASS')
 def test_safety(self):
  s=(Path(__file__).resolve().parents[1]/'alpaca_market_data/historical_feature_store_v79_61_65.py').read_text().lower();self.assertNotIn('submit_order(',s);self.assertNotIn('tradingclient(',s)
if __name__=='__main__':unittest.main()
