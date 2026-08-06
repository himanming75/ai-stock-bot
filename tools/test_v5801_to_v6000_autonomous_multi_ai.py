from __future__ import annotations
import tempfile
import unittest
from pathlib import Path

from autonomous_multi_ai.champion import (
    compare_champion_challenger,
)
from autonomous_multi_ai.fixtures import (
    CHALLENGER,
    CHAMPION,
    VETO_VOTES,
    VOTES,
    WEAK_CHALLENGER,
)
from autonomous_multi_ai.service import (
    AutonomousMultiAICertificationService,
)
from autonomous_multi_ai.voting import (
    aggregate_votes,
)


class Tests(unittest.TestCase):
    def test_weighted_vote_buy(self):
        result = aggregate_votes(VOTES)
        self.assertEqual(
            result.final_action,
            "BUY",
        )

    def test_safety_veto(self):
        result = aggregate_votes(VETO_VOTES)
        self.assertEqual(
            result.final_action,
            "WAIT",
        )
        self.assertTrue(result.veto_applied)

    def test_challenger_recommended(self):
        result = compare_champion_challenger(
            CHAMPION,
            CHALLENGER,
        )
        self.assertTrue(
            result["promotion_recommended"]
        )
        self.assertFalse(
            result[
                "automatic_promotion_performed"
            ]
        )

    def test_weak_challenger_rejected(self):
        result = compare_champion_challenger(
            CHAMPION,
            WEAK_CHALLENGER,
        )
        self.assertFalse(
            result["promotion_recommended"]
        )

    def test_certification(self):
        with tempfile.TemporaryDirectory() as directory:
            result = (
                AutonomousMultiAICertificationService()
                .evaluate(
                    output_dir=Path(directory)
                )
            )
            self.assertEqual(
                result["status"],
                "PASS",
            )

    def test_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            AutonomousMultiAICertificationService().evaluate(
                output_dir=root
            )
            self.assertTrue(
                (
                    root
                    / "autonomous_champion_challenger.json"
                ).exists()
            )
            self.assertTrue(
                (
                    root
                    / "autonomous_multi_ai_ledger.jsonl"
                ).exists()
            )

    def test_zero_order_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            result = (
                AutonomousMultiAICertificationService()
                .evaluate(
                    output_dir=Path(directory)
                )
            )
            self.assertFalse(
                result[
                    "actual_broker_write_performed"
                ]
            )
            self.assertEqual(
                result[
                    "actual_paper_orders_submitted"
                ],
                0,
            )
            self.assertEqual(
                result[
                    "actual_live_orders_submitted"
                ],
                0,
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
