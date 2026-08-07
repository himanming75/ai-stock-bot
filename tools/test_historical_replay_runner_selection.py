from pathlib import Path
import tempfile
import unittest

from tools.select_historical_replay_runner import build


class Tests(unittest.TestCase):

    def test_static_only_contract(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            p = root / "tools" / "run_historical_backtest.py"
            p.parent.mkdir(parents=True)

            sample = (
                "import argparse\n"
                "def main():\n"
                "    p=argparse.ArgumentParser()\n"
                "    p.add_argument('--symbol')\n"
                "    p.add_argument('--start-date')\n"
                "    p.add_argument('--end-date')\n"
                "    print('closed_trades realized_pl trade_results.jsonl historical_data')\n"
                "if __name__=='__main__':\n"
                "    main()\n"
            )

            p.write_text(sample, encoding="utf-8")

            r = build(root)

            self.assertFalse(r["contracts"]["candidate_runner_executed"])
            self.assertFalse(r["contracts"]["existing_source_modified"])
            self.assertGreaterEqual(r["python_candidate_count"], 1)

    def test_dangerous_runner_not_recommended(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            p = root / "tools" / "run_historical_replay.py"
            p.parent.mkdir(parents=True)

            sample = (
                "def submit_order():\n"
                "    pass\n"
                "if __name__=='__main__':\n"
                "    submit_order()\n"
            )

            p.write_text(sample, encoding="utf-8")

            r = build(root)

            safe_paths = [
                x["path"]
                for x in r["recommended_candidates"]
                if x["recommended_for_execution"]
            ]

            self.assertNotIn(
                "tools/run_historical_replay.py",
                safe_paths,
            )


if __name__ == "__main__":
    unittest.main()
