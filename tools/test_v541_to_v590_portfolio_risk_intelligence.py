from __future__ import annotations
import inspect
import tempfile
import unittest
from pathlib import Path

from portfolio_risk_intelligence.io import write_json
from portfolio_risk_intelligence.service import (
    PortfolioRiskIntelligenceService,
)

class Tests(unittest.TestCase):
    def inputs(self, root: Path, risk_level="NORMAL"):
        ai = root / "ai.json"
        write_json(ai, {
            "decision_fingerprint": "ai-1",
            "candidate_queue": [{
                "symbol": "SPY",
                "decision": "BUY",
                "final_score": "80",
            }],
        })
        portfolio = root / "portfolio.json"
        write_json(portfolio, {
            "account_equity": "100000",
            "cash": "50000",
            "positions": [],
        })
        risk = root / "risk.json"
        write_json(risk, {"risk_level": risk_level})
        metadata = root / "metadata.json"
        write_json(metadata, {
            "symbols": {"SPY": {"sector": "ETF_BROAD_MARKET"}}
        })
        corr = root / "corr.json"
        write_json(corr, {"matrix": {}})
        policy = root / "policy.json"
        write_json(policy, {
            "base_risk_budget_percent": "0.5",
            "max_single_position_percent": "5",
            "max_order_notional": "500",
            "minimum_cash_reserve_percent": "20",
            "max_sector_exposure_percent": "35",
            "maximum_pair_correlation": "0.85",
            "max_daily_new_notional": "1000",
            "allowed_risk_levels": ["NORMAL"],
            "risk_level_multiplier": {
                "NORMAL": "1",
                "WARNING": "0.5",
                "CRITICAL": "0",
                "UNKNOWN": "0",
            },
            "block_unknown_sector": True,
        })
        return ai, portfolio, risk, metadata, corr, policy

    def evaluate(self, root, risk_level="NORMAL"):
        paths = self.inputs(root, risk_level)
        return PortfolioRiskIntelligenceService().evaluate(
            ai_decision_path=paths[0],
            portfolio_path=paths[1],
            risk_path=paths[2],
            metadata_path=paths[3],
            correlation_path=paths[4],
            policy_path=paths[5],
            output_dir=root / "out",
        )

    def test_ready_allocation(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.evaluate(Path(directory))
            self.assertEqual(result["ready_allocation_count"], 1)
            self.assertEqual(
                result["allocation_queue"][0]["symbol"], "SPY"
            )

    def test_critical_risk_blocks(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.evaluate(Path(directory), "CRITICAL")
            self.assertEqual(result["ready_allocation_count"], 0)

    def test_missing_portfolio_is_honest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ai, _, risk, metadata, corr, policy = self.inputs(root)
            result = PortfolioRiskIntelligenceService().evaluate(
                ai_decision_path=ai,
                portfolio_path=root / "missing.json",
                risk_path=risk,
                metadata_path=metadata,
                correlation_path=corr,
                policy_path=policy,
                output_dir=root / "out",
            )
            self.assertEqual(
                result["status"],
                "INSUFFICIENT_PORTFOLIO_INPUT",
            )

    def test_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.evaluate(root)
            self.assertTrue(
                (root / "out/portfolio_risk_dashboard.json").exists()
            )
            self.assertTrue(
                (root / "out/allocation_plan_ledger.jsonl").exists()
            )

    def test_no_orders(self):
        source = inspect.getsource(
            PortfolioRiskIntelligenceService
        )
        self.assertIn('"actual_order_ticket_created": False', source)
        self.assertIn('"actual_paper_orders_submitted": 0', source)
        self.assertIn('"actual_live_orders_submitted": 0', source)

if __name__ == "__main__":
    unittest.main(verbosity=2)
