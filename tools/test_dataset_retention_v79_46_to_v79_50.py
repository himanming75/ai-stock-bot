from pathlib import Path
from tempfile import TemporaryDirectory
import json, unittest

from alpaca_market_data import (
    RetentionConfig, build_retention_certificate, build_retention_plan,
    inventory_versions, load_version_registry, run_dataset_retention,
    sha256_retention_json, validate_version_certificate,
    verify_retention_manifest,
)

def write_registry(root, version_ids, active_id):
    versions_dir=root/"versions"; versions_dir.mkdir()
    versions=[]
    for index,version_id in enumerate(version_ids):
        version_dir=versions_dir/version_id; version_dir.mkdir()
        data=(f'{{"version":{index}}}\n').encode()
        (version_dir/"alpaca_historical_bars.jsonl").write_bytes(data)
        (version_dir/"version_metadata.json").write_text(
            json.dumps({"version_id":version_id}),encoding="utf-8"
        )
        import hashlib
        versions.append({
            "version_id":version_id,
            "dataset_sha256":hashlib.sha256(data).hexdigest(),
            "metadata_sha256":"x"*64,
            "row_count":1,
            "byte_size":len(data),
            "status":"ACTIVE",
        })
    registry={
        "schema_version":"v79.43.dataset_version_registry.1",
        "stage":"V79.43",
        "dataset_name":"alpaca_historical_bars",
        "versions":versions,
        "version_count":len(versions),
        "active_version_id":active_id,
    }
    registry["registry_sha256"]=sha256_retention_json(registry)
    path=root/"dataset_version_registry.json"
    path.write_text(json.dumps(registry),encoding="utf-8")
    return path,versions_dir

def write_cert(path):
    cert={"stage":"V79.45","status":"PASS"}
    cert["certificate_sha256"]=sha256_retention_json(cert)
    path.write_text(json.dumps(cert),encoding="utf-8")

class Tests(unittest.TestCase):
    def setUp(self): self.config=RetentionConfig()

    def test_v79_46_config_safety(self):
        self.config.validate()
        with self.assertRaises(ValueError):
            RetentionConfig(allow_physical_delete=True).validate()

    def test_v79_46_active_preservation_required(self):
        with self.assertRaises(ValueError):
            RetentionConfig(preserve_active_version=False).validate()

    def test_v79_47_registry_inventory(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp); registry_path,versions_dir=write_registry(
                root,["hist-a"],"hist-a"
            )
            registry=load_version_registry(registry_path)
            inventory=inventory_versions(versions_dir,registry)
            self.assertEqual(inventory["version_count"],1)

    def test_v79_47_missing_version_detected(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp); registry_path,versions_dir=write_registry(
                root,["hist-a"],"hist-a"
            )
            import shutil
            shutil.rmtree(versions_dir/"hist-a")
            with self.assertRaises(ValueError):
                inventory_versions(versions_dir,load_version_registry(registry_path))

    def test_v79_48_single_active_kept(self):
        inventory={
            "active_version_id":"hist-a",
            "versions":[{"version_id":"hist-a","is_active":True}],
        }
        plan=build_retention_plan(inventory,self.config)
        self.assertEqual(plan["keep_count"],1)
        self.assertEqual(plan["archive_count"],0)

    def test_v79_48_excess_versions_archived(self):
        inventory={
            "active_version_id":"hist-6",
            "versions":[
                {"version_id":f"hist-{i}","is_active":i==6}
                for i in range(1,7)
            ],
        }
        plan=build_retention_plan(inventory,self.config)
        self.assertEqual(plan["keep_count"],5)
        self.assertEqual(plan["archive_count"],1)
        self.assertEqual(plan["delete_count"],0)

    def test_v79_49_run_single_version(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp); registry,versions=write_registry(root,["hist-a"],"hist-a")
            cert=root/"cert.json"; write_cert(cert)
            result=run_dataset_retention(
                registry,versions,cert,self.config,root/"output"
            )
            self.assertEqual(result["ledger"]["kept_version_count"],1)
            self.assertEqual(result["ledger"]["archived_version_count"],0)

    def test_v79_49_archives_without_delete(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp)
            ids=[f"hist-{i}" for i in range(1,7)]
            registry,versions=write_registry(root,ids,"hist-6")
            cert=root/"cert.json"; write_cert(cert)
            result=run_dataset_retention(
                registry,versions,cert,self.config,root/"output"
            )
            self.assertEqual(result["ledger"]["archived_version_count"],1)
            self.assertEqual(result["ledger"]["deleted_version_count"],0)
            self.assertTrue((versions/"hist-1").is_dir())

    def test_v79_49_manifest_verifies(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp); registry,versions=write_registry(root,["hist-a"],"hist-a")
            cert=root/"cert.json"; write_cert(cert)
            result=run_dataset_retention(registry,versions,cert,self.config,root/"output")
            self.assertTrue(verify_retention_manifest(root/"output",result["manifest"]))

    def test_v79_49_manifest_tamper_detected(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp); registry,versions=write_registry(root,["hist-a"],"hist-a")
            cert=root/"cert.json"; write_cert(cert)
            result=run_dataset_retention(registry,versions,cert,self.config,root/"output")
            (root/"output/dataset_retention_plan.json").write_text("{}\n")
            with self.assertRaises(ValueError):
                verify_retention_manifest(root/"output",result["manifest"])

    def test_v79_50_certificate(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp)
            prior=root/"release/v79_45/output"; prior.mkdir(parents=True)
            registry,versions=write_registry(prior,["hist-a"],"hist-a")
            version_cert=prior/"historical_dataset_version_certificate_v79_45.json"
            write_cert(version_cert)
            result=run_dataset_retention(
                registry,versions,version_cert,self.config,root/"release/v79_50/output"
            )
            cert=build_retention_certificate(
                root,root/"release/v79_50/output",self.config,result
            )
            self.assertEqual(cert["status"],"PASS")
            self.assertEqual(cert["retention_summary"]["deleted_version_count"],0)

    def test_invalid_certificate_rejected(self):
        with TemporaryDirectory() as tmp:
            path=Path(tmp)/"cert.json"
            path.write_text(json.dumps({"stage":"V79.45","status":"FAIL"}))
            with self.assertRaises(ValueError):
                validate_version_certificate(path)

    def test_no_order_submission_or_credentials(self):
        source=(Path(__file__).resolve().parents[1]/"alpaca_market_data/dataset_retention_v79_46_50.py").read_text().lower()
        self.assertNotIn("submit_order(",source)
        self.assertNotIn("tradingclient(",source)
        self.assertNotIn("api_secret",source)

if __name__=="__main__": unittest.main()
