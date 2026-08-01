from pathlib import Path
from tempfile import TemporaryDirectory
import hashlib,json,shutil,unittest
from alpaca_market_data import RecoveryConfig,build_recovery_certificate,discover_recovery_points,execute_recovery,load_recovery_registry,run_dataset_recovery,select_recovery_point,sha256_recovery_json,validate_recovery_retention_certificate,validate_recovery_source,verify_recovery_manifest
def env(root,vid="hist-a"):
 vd=root/"versions"/vid;vd.mkdir(parents=True);db=b'{"symbol":"AAPL"}\n';(vd/"alpaca_historical_bars.jsonl").write_bytes(db);m={"stage":"V79.42","version_id":vid,"dataset_sha256":hashlib.sha256(db).hexdigest()};m["metadata_sha256"]=sha256_recovery_json(m);(vd/"version_metadata.json").write_text(json.dumps(m));r={"stage":"V79.43","versions":[{"version_id":vid,"dataset_sha256":hashlib.sha256(db).hexdigest(),"metadata_sha256":m["metadata_sha256"],"row_count":1,"byte_size":len(db),"status":"ACTIVE"}],"version_count":1,"active_version_id":vid};r["registry_sha256"]=sha256_recovery_json(r);rp=root/"dataset_version_registry.json";rp.write_text(json.dumps(r));return rp,root/"versions"
def cert(p):
 c={"stage":"V79.50","status":"PASS","retention_summary":{"deleted_version_count":0,"source_versions_preserved":True}};c["certificate_sha256"]=sha256_recovery_json(c);p.write_text(json.dumps(c))
class T(unittest.TestCase):
 def setUp(self):self.c=RecoveryConfig()
 def test_config(self):
  self.c.validate()
  with self.assertRaises(ValueError):RecoveryConfig(overwrite_existing_recovery=True).validate()
 def test_discover(self):
  with TemporaryDirectory() as t:r,v=env(Path(t));self.assertTrue(discover_recovery_points(load_recovery_registry(r),v,None,self.c)[0].is_active)
 def test_missing(self):
  with TemporaryDirectory() as t:
   r,v=env(Path(t));shutil.rmtree(v/"hist-a")
   with self.assertRaises(ValueError):discover_recovery_points(load_recovery_registry(r),v,None,self.c)
 def test_select(self):
  with TemporaryDirectory() as t:r,v=env(Path(t));p=discover_recovery_points(load_recovery_registry(r),v,None,self.c);self.assertEqual(select_recovery_point(p,self.c).version_id,"hist-a")
 def test_validate(self):
  with TemporaryDirectory() as t:r,v=env(Path(t));p=discover_recovery_points(load_recovery_registry(r),v,None,self.c)[0];self.assertEqual(validate_recovery_source(p,v,None,self.c)["status"],"PASS")
 def test_tamper(self):
  with TemporaryDirectory() as t:
   r,v=env(Path(t));p=discover_recovery_points(load_recovery_registry(r),v,None,self.c)[0];(v/"hist-a/alpaca_historical_bars.jsonl").write_text("bad")
   with self.assertRaises(ValueError):validate_recovery_source(p,v,None,self.c)
 def test_execute(self):
  with TemporaryDirectory() as t:r,v=env(Path(t));p=discover_recovery_points(load_recovery_registry(r),v,None,self.c)[0];x=execute_recovery(validate_recovery_source(p,v,None,self.c),Path(t)/"rec",self.c);self.assertTrue(x["created"])
 def test_reuse(self):
  with TemporaryDirectory() as t:r,v=env(Path(t));p=discover_recovery_points(load_recovery_registry(r),v,None,self.c)[0];z=validate_recovery_source(p,v,None,self.c);execute_recovery(z,Path(t)/"rec",self.c);self.assertTrue(execute_recovery(z,Path(t)/"rec",self.c)["reused_existing_recovery"])
 def test_manifest(self):
  with TemporaryDirectory() as t:r,v=env(Path(t));cp=Path(t)/"c.json";cert(cp);x=run_dataset_recovery(r,v,None,cp,self.c,Path(t)/"out");self.assertTrue(verify_recovery_manifest(Path(t)/"out",x["manifest"]))
 def test_manifest_tamper(self):
  with TemporaryDirectory() as t:
   r,v=env(Path(t));cp=Path(t)/"c.json";cert(cp);x=run_dataset_recovery(r,v,None,cp,self.c,Path(t)/"out");(Path(t)/"out/dataset_recovery_points.json").write_text("{}")
   with self.assertRaises(ValueError):verify_recovery_manifest(Path(t)/"out",x["manifest"])
 def test_certificate(self):
  with TemporaryDirectory() as t:
   root=Path(t);p45=root/"release/v79_45/output";p45.mkdir(parents=True);r,v=env(p45);p50=root/"release/v79_50/output";p50.mkdir(parents=True);cp=p50/"historical_dataset_retention_certificate_v79_50.json";cert(cp);x=run_dataset_recovery(r,v,None,cp,self.c,root/"release/v79_55/output");self.assertEqual(build_recovery_certificate(root,root/"release/v79_55/output",self.c,x)["status"],"PASS")
 def test_bad_cert(self):
  with TemporaryDirectory() as t:
   p=Path(t)/"c";p.write_text(json.dumps({"stage":"V79.50","status":"FAIL"}))
   with self.assertRaises(ValueError):validate_recovery_retention_certificate(p)
 def test_safety_source(self):
  s=(Path(__file__).resolve().parents[1]/"alpaca_market_data/dataset_recovery_v79_51_55.py").read_text().lower();self.assertNotIn("submit_order(",s);self.assertNotIn("tradingclient(",s);self.assertNotIn("api_secret",s)
if __name__=="__main__":unittest.main()
