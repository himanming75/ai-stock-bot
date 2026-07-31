from __future__ import annotations
import json,tempfile,unittest,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from broker.recovery_release_pipeline_v77_11_15 import *

class Tests(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.r=Path(self.t.name)
  (self.r/"broker").mkdir();(self.r/"tools").mkdir()
  for rel in ["broker/recovery_release_pipeline_v77_11_15.py","tools/recovery_release_manifest_v77_11.py",
              "tools/recovery_bundle_builder_v77_12.py","tools/recovery_bundle_integrity_v77_13.py",
              "tools/recovery_installation_validator_v77_14.py"]:
   p=self.r/rel;p.write_text(rel,encoding="utf-8")
  self.cert=self.r/"cert.json"
  cert={"certificate_id":"RECOVERY-AUDIT-V77.10","certificate_sha256":"abc","status":"PASS"}
  write_json(self.cert,cert)
 def tearDown(self):self.t.cleanup()
 def test_full_chain(self):
  o11=self.r/"o11";s11=build_manifest(self.r,self.cert,o11,sha256_file(self.cert));self.assertEqual(s11.status,"PASS")
  m=o11/"recovery_release_manifest_v77_11.json";o12=self.r/"o12";s12=build_bundle(self.r,m,o12);self.assertEqual(s12.status,"PASS")
  b=o12/"recovery_bundle_v77_12.zip";o13=self.r/"o13";self.assertEqual(verify_bundle(b,m,o13).status,"PASS")
  o14=self.r/"o14";self.assertEqual(validate_installation(b,m,o14).status,"PASS")
  o15=self.r/"o15";s15=issue_release_certificate(
   o11/"recovery_release_manifest_verification_v77_11.json",
   o12/"recovery_bundle_builder_verification_v77_12.json",
   o13/"recovery_bundle_integrity_verification_v77_13.json",
   o14/"recovery_installation_validator_verification_v77_14.json",o15)
  self.assertEqual(s15.status,"PASS")
 def test_certificate_hash_guard(self):
  with self.assertRaises(RecoveryReleaseError):build_manifest(self.r,self.cert,self.r/"x","bad")
 def test_bundle_tamper_detection(self):
  o11=self.r/"o11";build_manifest(self.r,self.cert,o11,sha256_file(self.cert));m=o11/"recovery_release_manifest_v77_11.json"
  o12=self.r/"o12";build_bundle(self.r,m,o12);b=o12/"recovery_bundle_v77_12.zip"
  import zipfile
  with zipfile.ZipFile(b,"a") as z:z.writestr("broker/recovery_release_pipeline_v77_11_15.py","tampered")
  self.assertEqual(verify_bundle(b,m,self.r/"o13").status,"FAIL")
 def test_deterministic_digest(self):self.assertEqual(digest_json({"b":2,"a":1}),digest_json({"a":1,"b":2}))
if __name__=="__main__":unittest.main()
