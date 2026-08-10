import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from datetime import datetime
from validation_automation.scheduler import (
    _acquire_lock,_release_lock,_mark_past_slots_as_skipped,load_config
)

class TestSchedulerSafetyFix(unittest.TestCase):
    def test_single_run_lock(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            ok,lock=_acquire_lock(root,"test1")
            self.assertTrue(ok)
            ok2,lock2=_acquire_lock(root,"test2")
            self.assertFalse(ok2)
            self.assertEqual(lock2["phase"],"test1")
            _release_lock(root)
            ok3,_=_acquire_lock(root,"test3")
            self.assertTrue(ok3)
            _release_lock(root)

    def test_config_default_disables_catchup(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            cfg=load_config(root)
            self.assertFalse(cfg["catch_up_missed_runs"])

if __name__=="__main__":
    unittest.main()
