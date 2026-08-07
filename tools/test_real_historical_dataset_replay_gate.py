from pathlib import Path
import json,tempfile,unittest
from tools.audit_real_historical_dataset_replay_gate import build

class Tests(unittest.TestCase):
    def test_fixture_is_not_trusted(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            p=root/"release/v1/fixtures/historical_bars.json"
            p.parent.mkdir(parents=True)
            rows=[{"symbol":"AAPL","timestamp":f"2026-01-01T00:{i%60:02d}:00Z","open":1,"high":2,"low":.5,"close":1.5,"volume":100} for i in range(250)]
            p.write_text(json.dumps({"rows":rows}),encoding="utf-8")
            r=build(root)
            self.assertEqual(r["trusted_dataset_count"],0)
            self.assertFalse(r["contracts"]["candidate_replay_executed"])

    def test_read_only_contract(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            r=build(root)
            self.assertFalse(r["contracts"]["dataset_files_modified"])
            self.assertFalse(r["contracts"]["broker_write_performed"])
            self.assertFalse(r["contracts"]["paper_task_modified"])

if __name__=="__main__":
    unittest.main()
