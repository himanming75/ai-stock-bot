from pathlib import Path
import tempfile,unittest
from tools.audit_paper_strategy_lineage import build

class Tests(unittest.TestCase):
    def test_read_only_contract(self):
        with tempfile.TemporaryDirectory() as td:
            r=build(Path(td))
            c=r["contracts"]
            self.assertFalse(c["paper_task_modified"])
            self.assertFalse(c["candidate_producer_executed"])
            self.assertFalse(c["historical_replay_executed"])
            self.assertFalse(c["broker_write_performed"])
            self.assertFalse(c["order_submission_performed"])

    def test_producer_detection(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            p=root/"ai/build_report.py";p.parent.mkdir(parents=True)
            p.write_text(
                'import json\n'
                'def build(historical_bars):\n'
                '    analyses=[]\n'
                '    confidence_calibration={}\n'
                '    reward_risk=1\n'
                '    consensus_score=1\n'
                '    open("multi_timeframe_ai_report_bilingual.json","w").write(json.dumps({"analyses":analyses}))\n',
                encoding="utf-8"
            )
            r=build(root)
            self.assertGreaterEqual(r["safe_producer_candidate_count"],1)

if __name__=="__main__":
    unittest.main()
