from __future__ import annotations
import json, tempfile, unittest
from pathlib import Path
from autonomous_paper_runtime.actual_terminal_monitor_continuation import ActualSavedStateTerminalMonitorContinuation

class Tests(unittest.TestCase):
    def run_case(self, readiness):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); rp=root/'readiness.json'; cp=root/'cycle.json'; out=root/'result.json'
            rp.write_text(json.dumps(readiness), encoding='utf-8')
            cp.write_text(json.dumps({'status':'PASS'}), encoding='utf-8')
            report=ActualSavedStateTerminalMonitorContinuation().run(readiness_path=rp, cycle_result_path=cp, result_path=out)
            self.assertTrue(out.exists()); return report
    def test_active_order_continues(self):
        r=self.run_case({'active_order_present':True,'open_order_count':1,'active_order_status':'ACCEPTED','terminal_commit_verified':False})
        self.assertEqual(r.state,'WAIT_ACTIVE_ORDER'); self.assertTrue(r.continue_monitoring); self.assertFalse(r.next_order_allowed)
    def test_terminal_requires_commit(self):
        r=self.run_case({'active_order_present':False,'open_order_count':0,'order_status':'FILLED','terminal_commit_verified':False})
        self.assertEqual(r.state,'TERMINAL_OBSERVED'); self.assertFalse(r.next_order_allowed)
    def test_terminal_commit_unlocks(self):
        r=self.run_case({'active_order_present':False,'open_order_count':0,'order_status':'CANCELED','terminal_commit_verified':True})
        self.assertTrue(r.next_order_allowed)
    def test_conflict_safe_mode(self):
        r=self.run_case({'active_order_present':True,'open_order_count':1,'order_status':'FILLED'})
        self.assertTrue(r.safe_mode_engaged); self.assertEqual(r.status,'BLOCKED')

if __name__=='__main__': unittest.main()
