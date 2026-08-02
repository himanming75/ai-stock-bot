from __future__ import annotations
import json, tempfile, unittest
from pathlib import Path
from autonomous_paper_runtime.ultra_fast_cycle_finalization import UltraFastCycleFinalization


class Tests(unittest.TestCase):
    def completion(self):
        return {
            "status": "PASS",
            "state": "CYCLE_COMPLETED",
            "completion_id": "completion-001",
            "client_order_id": "client-001",
            "broker_order_id": "broker-001",
            "final_order_status": "FILLED",
            "cycle_completed": True,
            "next_cycle_handoff_ready": True,
            "safe_mode_engaged": False,
        }

    def completion_token(self):
        return {"completion_id": "completion-001", "cycle_completed": True}

    def terminal_token(self):
        return {"completion_id": "completion-001", "terminal_commit_verified": True}

    def portfolio(self):
        return {
            "starting_equity": 10000,
            "local_cash": 10100,
            "broker_cash": 10100,
            "local_equity": 10100,
            "broker_equity": 10100,
            "local_position_quantity": 0,
            "broker_position_quantity": 0,
            "fees": 1,
            "tolerance": 0.01,
        }

    def run_case(self, completion, ctoken=None, ttoken=None, portfolio=None):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        paths = {name: root / name for name in [
            "completion.json", "ctoken.json", "ttoken.json", "portfolio.json",
            "recon.json", "pnl.json", "ledger.jsonl", "archive.json",
            "bootstrap.json", "result.json"
        ]}
        paths["completion.json"].write_text(json.dumps(completion), encoding="utf-8")
        if ctoken is not None:
            paths["ctoken.json"].write_text(json.dumps(ctoken), encoding="utf-8")
        if ttoken is not None:
            paths["ttoken.json"].write_text(json.dumps(ttoken), encoding="utf-8")
        if portfolio is not None:
            paths["portfolio.json"].write_text(json.dumps(portfolio), encoding="utf-8")
        result = UltraFastCycleFinalization().run(
            completion_result_path=paths["completion.json"],
            completion_token_path=paths["ctoken.json"],
            terminal_token_path=paths["ttoken.json"],
            portfolio_snapshot_path=paths["portfolio.json"],
            reconciliation_result_path=paths["recon.json"],
            pnl_result_path=paths["pnl.json"],
            execution_ledger_path=paths["ledger.jsonl"],
            archive_manifest_path=paths["archive.json"],
            bootstrap_token_path=paths["bootstrap.json"],
            result_path=paths["result.json"],
        )
        return result, paths

    def test_waits_before_cycle_completion(self):
        result, paths = self.run_case({
            "status": "PASS",
            "state": "WAIT_TERMINAL",
            "cycle_completed": False,
            "next_cycle_handoff_ready": False,
            "safe_mode_engaged": False,
        })
        self.assertEqual(result["state"], "WAIT_CYCLE_COMPLETION")
        self.assertFalse(paths["bootstrap.json"].exists())

    def test_full_ultra_fast_finalization(self):
        result, paths = self.run_case(
            self.completion(), self.completion_token(),
            self.terminal_token(), self.portfolio()
        )
        self.assertEqual(result["state"], "NEXT_CYCLE_BOOTSTRAP_READY")
        self.assertTrue(result["portfolio_reconciled"])
        self.assertTrue(result["pnl_settled"])
        self.assertTrue(result["execution_ledger_finalized"])
        self.assertTrue(result["archive_created"])
        self.assertTrue(result["next_cycle_bootstrap_ready"])
        self.assertTrue(paths["bootstrap.json"].exists())

    def test_cash_mismatch_blocks(self):
        portfolio = self.portfolio()
        portfolio["broker_cash"] = 10000
        result, _ = self.run_case(
            self.completion(), self.completion_token(),
            self.terminal_token(), portfolio
        )
        self.assertEqual(result["status"], "BLOCKED")

    def test_position_mismatch_blocks(self):
        portfolio = self.portfolio()
        portfolio["broker_position_quantity"] = 2
        result, _ = self.run_case(
            self.completion(), self.completion_token(),
            self.terminal_token(), portfolio
        )
        self.assertEqual(result["status"], "BLOCKED")

    def test_missing_terminal_token_blocks(self):
        result, _ = self.run_case(
            self.completion(), self.completion_token(),
            None, self.portfolio()
        )
        self.assertEqual(result["status"], "BLOCKED")

    def test_duplicate_bootstrap_is_idempotent(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            files = {
                "completion": root / "completion.json",
                "ctoken": root / "ctoken.json",
                "ttoken": root / "ttoken.json",
                "portfolio": root / "portfolio.json",
                "recon": root / "recon.json",
                "pnl": root / "pnl.json",
                "ledger": root / "ledger.jsonl",
                "archive": root / "archive.json",
                "bootstrap": root / "bootstrap.json",
                "result": root / "result.json",
            }
            files["completion"].write_text(json.dumps(self.completion()), encoding="utf-8")
            files["ctoken"].write_text(json.dumps(self.completion_token()), encoding="utf-8")
            files["ttoken"].write_text(json.dumps(self.terminal_token()), encoding="utf-8")
            files["portfolio"].write_text(json.dumps(self.portfolio()), encoding="utf-8")
            runner = UltraFastCycleFinalization()
            kwargs = dict(
                completion_result_path=files["completion"],
                completion_token_path=files["ctoken"],
                terminal_token_path=files["ttoken"],
                portfolio_snapshot_path=files["portfolio"],
                reconciliation_result_path=files["recon"],
                pnl_result_path=files["pnl"],
                execution_ledger_path=files["ledger"],
                archive_manifest_path=files["archive"],
                bootstrap_token_path=files["bootstrap"],
                result_path=files["result"],
            )
            first = runner.run(**kwargs)
            second = runner.run(**kwargs)
            self.assertTrue(first["next_cycle_bootstrap_ready"])
            self.assertTrue(second["duplicate_bootstrap"])
            self.assertEqual(len(files["ledger"].read_text(encoding="utf-8").splitlines()), 1)


if __name__ == "__main__":
    unittest.main()
