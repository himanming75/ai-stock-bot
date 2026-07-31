from pathlib import Path
from tempfile import TemporaryDirectory
import json, unittest

from alpaca_market_data import (
    DatasetVersionConfig, build_version_certificate, fingerprint_dataset,
    run_dataset_versioning, sha256_version_json, validate_quality_certificate,
    verify_version_manifest,
)

def write_dataset(path):
    path.write_text(
        '{"symbol":"AAPL","timestamp":"2026-01-05T14:31:00Z"}\n'
        '{"symbol":"AAPL","timestamp":"2026-01-05T14:32:00Z"}\n',
        encoding="utf-8",
    )

def write_cert(path):
    cert={
        "stage":"V79.40","status":"PASS",
        "quality_summary":{"issue_count":0,"pending_repair_count":0},
    }
    cert["certificate_sha256"]=sha256_version_json(cert)
    path.write_text(json.dumps(cert),encoding="utf-8")

class Tests(unittest.TestCase):
    def setUp(self): self.config=DatasetVersionConfig()

    def test_v79_41_config_safety(self):
        self.config.validate()
        with self.assertRaises(ValueError):
            DatasetVersionConfig(allow_network=True).validate()

    def test_v79_41_deterministic_fingerprint(self):
        with TemporaryDirectory() as tmp:
            path=Path(tmp)/"data.jsonl"; write_dataset(path)
            one=fingerprint_dataset(path,self.config)
            two=fingerprint_dataset(path,self.config)
            self.assertEqual(one.version_id,two.version_id)
            self.assertEqual(one.sha256,two.sha256)

    def test_v79_41_changed_data_changes_version(self):
        with TemporaryDirectory() as tmp:
            path=Path(tmp)/"data.jsonl"; write_dataset(path)
            one=fingerprint_dataset(path,self.config)
            path.write_text(path.read_text()+"{}\n",encoding="utf-8")
            two=fingerprint_dataset(path,self.config)
            self.assertNotEqual(one.version_id,two.version_id)

    def test_v79_42_quality_certificate_required(self):
        with TemporaryDirectory() as tmp:
            with self.assertRaises(FileNotFoundError):
                validate_quality_certificate(Path(tmp)/"missing.json")

    def test_v79_42_rejects_failed_quality_certificate(self):
        with TemporaryDirectory() as tmp:
            path=Path(tmp)/"cert.json"
            cert={"stage":"V79.40","status":"FAIL",
                  "quality_summary":{"issue_count":1,"pending_repair_count":1}}
            cert["certificate_sha256"]=sha256_version_json(cert)
            path.write_text(json.dumps(cert),encoding="utf-8")
            with self.assertRaises(ValueError): validate_quality_certificate(path)

    def test_v79_43_creates_registry_and_version(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp); dataset=root/"data.jsonl"; cert=root/"cert.json"
            write_dataset(dataset); write_cert(cert)
            result=run_dataset_versioning(dataset,cert,self.config,root/"output")
            self.assertEqual(result["registry"]["version_count"],1)
            self.assertTrue(result["version_result"]["created"])

    def test_v79_43_reexecution_reuses_version(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp); dataset=root/"data.jsonl"; cert=root/"cert.json"
            write_dataset(dataset); write_cert(cert)
            run_dataset_versioning(dataset,cert,self.config,root/"output")
            result=run_dataset_versioning(dataset,cert,self.config,root/"output")
            self.assertFalse(result["version_result"]["created"])
            self.assertTrue(result["version_result"]["reused_existing_version"])
            self.assertEqual(result["registry"]["version_count"],1)

    def test_v79_43_immutable_conflict_detected(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp); dataset=root/"data.jsonl"; cert=root/"cert.json"
            write_dataset(dataset); write_cert(cert)
            result=run_dataset_versioning(dataset,cert,self.config,root/"output")
            version_id=result["fingerprint"]["version_id"]
            target=root/"output/versions"/version_id/"alpaca_historical_bars.jsonl"
            target.write_text("tampered\n",encoding="utf-8")
            with self.assertRaises(ValueError):
                run_dataset_versioning(dataset,cert,self.config,root/"output")

    def test_v79_44_manifest_verifies(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp); dataset=root/"data.jsonl"; cert=root/"cert.json"
            write_dataset(dataset); write_cert(cert)
            result=run_dataset_versioning(dataset,cert,self.config,root/"output")
            self.assertTrue(verify_version_manifest(root/"output",result["manifest"]))

    def test_v79_44_manifest_tamper_detected(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp); dataset=root/"data.jsonl"; cert=root/"cert.json"
            write_dataset(dataset); write_cert(cert)
            result=run_dataset_versioning(dataset,cert,self.config,root/"output")
            registry=root/"output/dataset_version_registry.json"
            registry.write_text("{}\n",encoding="utf-8")
            with self.assertRaises(ValueError):
                verify_version_manifest(root/"output",result["manifest"])

    def test_v79_45_certificate(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp)
            prior=root/"release/v79_40/output"; prior.mkdir(parents=True)
            dataset=prior/"quality/alpaca_historical_bars.quality_snapshot.jsonl"
            dataset.parent.mkdir(parents=True); write_dataset(dataset)
            cert_path=prior/"historical_quality_certificate_v79_40.json"; write_cert(cert_path)
            result=run_dataset_versioning(dataset,cert_path,self.config,root/"release/v79_45/output")
            cert=build_version_certificate(root,root/"release/v79_45/output",self.config,result)
            self.assertEqual(cert["status"],"PASS")
            self.assertEqual(cert["version_summary"]["registry_version_count"],1)

    def test_invalid_jsonl_rejected(self):
        with TemporaryDirectory() as tmp:
            path=Path(tmp)/"data.jsonl"; path.write_text("not-json\n")
            with self.assertRaises(ValueError):
                fingerprint_dataset(path,self.config)

    def test_no_order_submission_or_credentials(self):
        source=(Path(__file__).resolve().parents[1]/"alpaca_market_data/dataset_versioning_v79_41_45.py").read_text().lower()
        self.assertNotIn("submit_order(",source)
        self.assertNotIn("tradingclient(",source)
        self.assertNotIn("api_secret",source)

if __name__=="__main__": unittest.main()
