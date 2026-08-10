import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from web_controller.backtest_api import _options,_run_selected

class TestParameterizedBacktest(unittest.TestCase):
    def _root(self):
        td=tempfile.TemporaryDirectory()
        root=Path(td.name)
        p=root/"release/v98_01_to_v98_32/input/automated_backtest_policy.json"
        p.parent.mkdir(parents=True)
        policy={
          "policy_version":"V98.01","strategies":[{"strategy_id":"S1","family":"X","parameters":{},"enabled":True}],
          "datasets":[{"dataset_id":"D1","symbol":"SPY","path":"x.csv"}],
          "windows":[{"window_id":"W1","start_index":0,"end_index":10}]
        }
        p.write_text(json.dumps(policy),encoding="utf-8")
        return td,root,p,policy

    def test_options(self):
        td,root,p,policy=self._root()
        try:
            o=_options(root)
            self.assertEqual(o["strategies"][0]["strategy_id"],"S1")
        finally: td.cleanup()

    def test_selected_restores_policy(self):
        td,root,p,policy=self._root()
        try:
            original=p.read_text(encoding="utf-8")
            fake={"status":"PASS","state":"TEST","aggregation":{"completed_count":1}}
            with patch("web_controller.backtest_api.run_existing_backtest",return_value=fake):
                r=_run_selected(root,{"strategy_id":"S1","dataset_id":"D1","window_id":"W1","force":False})
            self.assertTrue(r["ok"])
            self.assertTrue(r["original_policy_restored"])
            self.assertEqual(p.read_text(encoding="utf-8"),original)
            self.assertEqual(r["actual_orders_submitted"],0)
            self.assertFalse(r["live_trading_enabled"])
        finally: td.cleanup()

if __name__=="__main__":
    unittest.main()
