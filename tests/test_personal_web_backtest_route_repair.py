import unittest
from pathlib import Path

class TestBacktestRouteRepair(unittest.TestCase):
    def test_server_routes_present(self):
        root=Path(r"C:\stock-bot")
        text=(root/"web_controller/server.py").read_text(encoding="utf-8")
        self.assertIn(
            "from web_controller.backtest_api import "
            "get_payload as get_backtest,action_payload as run_backtest_action",
            text,
        )
        self.assertIn('"/api/backtest":lambda:get_backtest(self.root)',text)
        self.assertIn(
            'elif p=="/api/backtest/action":r=run_backtest_action(self.root,b)',
            text,
        )

    def test_ui_files_already_installed(self):
        root=Path(r"C:\stock-bot")
        html=(root/"web_controller/static/index.html").read_text(encoding="utf-8")
        js=(root/"web_controller/static/app.js").read_text(encoding="utf-8")
        self.assertIn("Backtest Research Center",html)
        self.assertIn("/api/backtest",js)
        self.assertIn("/api/backtest/action",js)

if __name__=="__main__":
    unittest.main()
