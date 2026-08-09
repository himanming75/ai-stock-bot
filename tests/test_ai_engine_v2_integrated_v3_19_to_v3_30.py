from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from ai_engine_v2.shadow_challenger_v3_19 import build_shadow_challenger
from ai_engine_v2.champion_challenger_evaluation_v3_20 import evaluate_champion_vs_challenger
from ai_engine_v2.promotion_gate_v3_21 import build_promotion_gate
from ai_engine_v2.strategy_registry_v3_22 import build_strategy_registry
from ai_engine_v2.regime_selector_v3_23 import build_regime_selector
from ai_engine_v2.portfolio_intelligence_v3_24 import build_portfolio_intelligence
from ai_engine_v2.promotion_manager_v3_26 import build_promotion_manager
from ai_engine_v2.rollback_manager_v3_27 import build_rollback_manager
from ai_engine_v2.safety_supervisor_v3_29 import build_safety_supervisor
from ai_engine_v2.integrated_engine_v3_30 import build_integrated_ai_engine_v2


def strategy_candidate():
    return {
        "candidate_id":"V3.18-TEST",
        "proposal_type":"EXIT_RULE_CANDIDATE",
        "change_target":"Exit rules",
    }


def observations(n=25,delta=1.0):
    return [
        {
            "challenger_id":"CHALLENGER-001",
            "champion_pnl":1.0,
            "challenger_pnl":1.0+delta,
            "champion_drawdown":1.0,
            "challenger_drawdown":0.8,
        }
        for _ in range(n)
    ]


class TestIntegratedV2(unittest.TestCase):
    def test_v319_waits_without_strategy_candidate(self):
        s=build_shadow_challenger({"candidates":[{"proposal_type":"COLLECT_MORE_EVIDENCE"}]})
        self.assertEqual(s["status"],"WAITING_FOR_ELIGIBLE_CHALLENGER")
        self.assertEqual(s["challenger_count"],0)

    def test_v319_creates_shadow_only_challenger(self):
        s=build_shadow_challenger({"candidates":[strategy_candidate()]})
        self.assertEqual(s["challenger_count"],1)
        self.assertFalse(s["challengers"][0]["execution_enabled"])
        self.assertEqual(s["challengers"][0]["mode"],"SHADOW_ONLY")

    def test_v320_waits_for_observations(self):
        s=build_shadow_challenger({"candidates":[strategy_candidate()]})
        e=evaluate_champion_vs_challenger({},s,[])
        self.assertEqual(e["status"],"WAITING_FOR_SHADOW_OBSERVATIONS")

    def test_v321_gate_can_pass_synthetic_comparison(self):
        s=build_shadow_challenger({"candidates":[strategy_candidate()]})
        e=evaluate_champion_vs_challenger({},s,observations())
        g=build_promotion_gate(e)
        self.assertTrue(g["promotion_eligible"])
        self.assertFalse(g["automatic_promotion"])

    def test_v322_registry_keeps_champion_and_challenger_locked(self):
        s=build_shadow_challenger({"candidates":[strategy_candidate()]})
        r=build_strategy_registry(s)
        self.assertEqual(r["entry_count"],2)
        self.assertTrue(all(x["write_locked"] for x in r["entries"]))

    def test_v323_regime_selector_waits_when_evidence_missing(self):
        r=build_strategy_registry(build_shadow_challenger({"candidates":[]}))
        s=build_regime_selector({"evidence_trade_count":0,"coverage":{}},r)
        self.assertEqual(s["status"],"WAITING_FOR_REGIME_EVIDENCE")
        self.assertFalse(s["selector_enabled"])

    def test_v323_selector_is_shadow_only_when_ready(self):
        r=build_strategy_registry(build_shadow_challenger({"candidates":[]}))
        s=build_regime_selector({
            "evidence_trade_count":20,
            "coverage":{"direction_coverage":0.8,"volatility_coverage":0.8},
        },r)
        self.assertTrue(s["selector_enabled"])
        self.assertTrue(s["shadow_only"])

    def test_v324_portfolio_concentration_advisory(self):
        p=build_portfolio_intelligence({
            "broker_snapshot":{
                "positions":[
                    {"symbol":"AAPL","market_value":90},
                    {"symbol":"SPY","market_value":10},
                ]
            }
        })
        self.assertIn("CONCENTRATION_ABOVE_60_PERCENT",p["warnings"])
        self.assertFalse(p["position_change_performed"])

    def test_v326_never_auto_promotes(self):
        p=build_promotion_manager({"promotion_eligible":True})
        self.assertTrue(p["promotion_package_created"])
        self.assertFalse(p["promotion_performed"])
        self.assertFalse(p["automatic_promotion"])

    def test_v327_rollback_is_plan_only(self):
        r=build_strategy_registry(build_shadow_challenger({"candidates":[]}))
        x=build_rollback_manager(r)
        self.assertFalse(x["rollback_performed"])
        self.assertFalse(x["broker_write_performed"])

    def test_v329_safety_locks(self):
        s=build_safety_supervisor()
        self.assertTrue(s["locks"]["live_trading_locked"])
        self.assertTrue(s["locks"]["broker_write_locked"])
        self.assertTrue(s["locks"]["automatic_promotion_locked"])

    def test_v330_current_small_sample_development_complete_waiting(self):
        a=build_integrated_ai_engine_v2({
            "historical":{"numeric_trade_count":2},
            "strategy_improvement_candidates":{
                "mode":"EVIDENCE_COLLECTION_ONLY",
                "candidates":[{"proposal_type":"COLLECT_MORE_EVIDENCE"}],
            },
            "market_regime_analysis":{
                "evidence_trade_count":0,
                "coverage":{"direction_coverage":0,"volatility_coverage":0},
            },
        },{},None)
        self.assertEqual(a["development_status"],"COMPLETE")
        self.assertEqual(a["real_evidence_status"],"IN_PROGRESS")
        self.assertEqual(a["live_trading_status"],"LOCKED")
        self.assertEqual(a["automatic_promotion_status"],"LOCKED")

    def test_v330_synthetic_fixture_does_not_unlock_live(self):
        a=build_integrated_ai_engine_v2({
            "historical":{"numeric_trade_count":30},
            "strategy_improvement_candidates":{"candidates":[strategy_candidate()]},
            "market_regime_analysis":{
                "evidence_trade_count":30,
                "coverage":{"direction_coverage":1.0,"volatility_coverage":1.0},
            },
        },{},observations(25))
        self.assertTrue(a["stages"]["V3.21"]["promotion_eligible"])
        self.assertEqual(a["live_trading_status"],"LOCKED")
        self.assertEqual(a["automatic_promotion_status"],"LOCKED")
        self.assertTrue(a["contracts"]["synthetic_fixture_validates_software_not_profitability"])


if __name__=="__main__":
    unittest.main()
