from __future__ import annotations
from decimal import Decimal
import unittest

from feature_optimization.ensemble import EnsembleScorer
from feature_optimization.processing import CorrelationFilter, FeatureNormalizer
from feature_optimization.optimization import ChampionCandidatePreview


class Tests(unittest.TestCase):
    def test_normalizer(self):
        result = FeatureNormalizer().min_max([
            {"x": Decimal("1")},
            {"x": Decimal("3")},
        ])
        self.assertEqual(result[0]["x"], Decimal("0"))
        self.assertEqual(result[1]["x"], Decimal("1"))

    def test_correlation_filter(self):
        result = CorrelationFilter().select(
            correlations={
                "a": {"b": Decimal("0.9")},
                "b": {"a": Decimal("0.9")},
                "c": {},
            },
            threshold=Decimal("0.85"),
        )
        self.assertEqual(len(result["dropped"]), 1)

    def test_ensemble_no_order(self):
        result = EnsembleScorer().score(
            strategy_scores={
                "a": Decimal("0.8"),
                "b": Decimal("0.6"),
            },
            weights={
                "a": Decimal("1"),
                "b": Decimal("1"),
            },
        )
        self.assertFalse(result["order_created"])

    def test_champion_preview(self):
        result = ChampionCandidatePreview().evaluate(
            current_score=Decimal("0.7"),
            candidate_score=Decimal("0.8"),
            minimum_margin=Decimal("0.05"),
        )
        self.assertTrue(result["promotion_eligible"])
        self.assertFalse(result["actual_promotion_performed"])

    def test_zero_weight_rejected(self):
        with self.assertRaises(ValueError):
            EnsembleScorer().score(
                strategy_scores={"a": Decimal("0.8")},
                weights={"a": Decimal("0")},
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
