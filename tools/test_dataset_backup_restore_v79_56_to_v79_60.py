from pathlib import Path
from tempfile import TemporaryDirectory
import json,unittest,zipfile
from alpaca_market_data import BackupRestoreConfig,build_backup_plan,create_backup_archive,restore_backup,run_backup_restore,verify_backup_restore_manifest,sha256_backup_json,build_backup_restore_certificate,validate_backup_recovery_certificate

def env(root):
 v='hist-a'; base=root/'recovery'/v; base.mkdir(parents=True); (base/'alpaca_historical_bars.recovered.jsonl').write_text('{"x":1}\n'); (base/'recovered_version_metadata.json').write_text('{"version_id":"hist-a"}')
 cert={'stage':'V79.55','status':'PASS','recovery_summary':{'selected_version_id':v,'source_preserved':True}}; cert['certificate_sha256']=sha256_backup_json(cert); cp=root/'historical_dataset_recovery_certificate_v79_55.json'; cp.write_text(json.dumps(cert)); return cp
class T(unittest.TestCase):
 def setUp(self): self.c=BackupRestoreConfig()
 def test_config(self): self.c.validate(); self.assertRaises(ValueError,BackupRestoreConfig(overwrite_existing_backup=True).validate)
 def test_plan(self):
  with TemporaryDirectory() as t: r=Path(t); cp=env(r); p=build_backup_plan(r,validate_backup_recovery_certificate(cp),self.c); self.assertEqual(p.row_count,1)
 def test_archive(self):
  with TemporaryDirectory() as t: r=Path(t); cp=env(r); p=build_backup_plan(r,validate_backup_recovery_certificate(cp),self.c); b=create_backup_archive(r,p,self.c,r/'out/backups'); self.assertTrue(b['created'])
 def test_archive_reuse(self):
  with TemporaryDirectory() as t: r=Path(t); cp=env(r); p=build_backup_plan(r,validate_backup_recovery_certificate(cp),self.c); create_backup_archive(r,p,self.c,r/'out/backups'); b=create_backup_archive(r,p,self.c,r/'out/backups'); self.assertTrue(b['reused_existing_backup'])
 def test_restore(self):
  with TemporaryDirectory() as t: r=Path(t); cp=env(r); p=build_backup_plan(r,validate_backup_recovery_certificate(cp),self.c); b=create_backup_archive(r,p,self.c,r/'out/backups'); x=restore_backup(b,p,self.c,r/'out/restore'); self.assertEqual(x['row_count'],1)
 def test_restore_reuse(self):
  with TemporaryDirectory() as t: r=Path(t); cp=env(r); p=build_backup_plan(r,validate_backup_recovery_certificate(cp),self.c); b=create_backup_archive(r,p,self.c,r/'out/backups'); restore_backup(b,p,self.c,r/'out/restore'); x=restore_backup(b,p,self.c,r/'out/restore'); self.assertTrue(x['reused_existing_restore'])
 def test_tamper(self):
  with TemporaryDirectory() as t: r=Path(t); cp=env(r); p=build_backup_plan(r,validate_backup_recovery_certificate(cp),self.c); b=create_backup_archive(r,p,self.c,r/'out/backups'); Path(b['archive_path']).write_bytes(b'bad'); self.assertRaises(zipfile.BadZipFile,restore_backup,b,p,self.c,r/'out/restore')
 def test_manifest(self):
  with TemporaryDirectory() as t: r=Path(t); cp=env(r); x=run_backup_restore(r,cp,self.c,r/'out'); self.assertTrue(verify_backup_restore_manifest(r/'out',x['manifest']))
 def test_manifest_tamper(self):
  with TemporaryDirectory() as t: r=Path(t); cp=env(r); x=run_backup_restore(r,cp,self.c,r/'out'); (r/'out/dataset_backup_plan.json').write_text('{}'); self.assertRaises(ValueError,verify_backup_restore_manifest,r/'out',x['manifest'])
 def test_bad_cert(self):
  with TemporaryDirectory() as t: p=Path(t)/'c'; p.write_text('{}'); self.assertRaises(ValueError,validate_backup_recovery_certificate,p)
 def test_certificate(self):
  with TemporaryDirectory() as t: root=Path(t); prev=root/'release/v79_55/output'; prev.mkdir(parents=True); cp=env(prev); out=root/'release/v79_60/output'; x=run_backup_restore(prev,cp,self.c,out); c=build_backup_restore_certificate(root,out,self.c,x); self.assertEqual(c['status'],'PASS')
 def test_unsafe_member(self):
  with TemporaryDirectory() as t:
   r=Path(t); cp=env(r); p=build_backup_plan(r,validate_backup_recovery_certificate(cp),self.c); b=create_backup_archive(r,p,self.c,r/'out/backups');
   with zipfile.ZipFile(b['archive_path'],'a') as z: z.writestr('../evil','x')
   self.assertRaises(ValueError,restore_backup,b,p,self.c,r/'out/restore')
 def test_safety_source(self):
  s=(Path(__file__).resolve().parents[1]/'alpaca_market_data/dataset_backup_restore_v79_56_60.py').read_text().lower(); self.assertNotIn('submit_order(',s); self.assertNotIn('tradingclient(',s); self.assertNotIn('api_secret',s)
if __name__=='__main__': unittest.main()
