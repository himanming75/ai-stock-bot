from __future__ import annotations
import tempfile, json, unittest
from pathlib import Path
import validation_analytics_v3 as a

class Tests(unittest.TestCase):
    def test_empty_ai_linkage_safe(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            rows=[]
            linked=a.link_research_to_closed_trades(root,rows)
            self.assertEqual(linked,[])
            m=a.ai_decision_outcome_metrics(linked)
            self.assertEqual(m["status"],"COLLECTING_DATA")

    def test_link_same_symbol_prior_sample(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            p=root/"runtime/ai_research_shadow_integration"
            p.mkdir(parents=True)
            sample={"generated_at_utc":"2026-08-07T14:00:00+00:00",
                    "normalized_decision":{"symbol":"AAPL","original_side":"BUY","candidate_confidence":0.91,
                                           "ensemble_decision":"SKIP_OBSERVATION","market_regime":"TRENDING_BULLISH",
                                           "market_entry_context":"UNFAVORABLE"}}
            (p/"ai_research_shadow_ledger.jsonl").write_text(json.dumps(sample)+"\n")
            trades=[{"symbol":"AAPL","entry_time_utc":"2026-08-07T14:30:00+00:00","exit_time_utc":"2026-08-07T15:00:00+00:00","realized_pl":-2.0}]
            linked=a.link_research_to_closed_trades(root,trades)
            self.assertTrue(linked[0]["linked"])
            self.assertEqual(linked[0]["ensemble_decision"],"SKIP_OBSERVATION")

    def test_no_mutation_contract(self):
        with tempfile.TemporaryDirectory() as td:
            r=a.main_report(Path(td))
            self.assertFalse(r["broker_write_performed"])
            self.assertFalse(r["trading_configuration_changed"])
            self.assertFalse(r["automatic_parameter_change"])

if __name__=="__main__":
    unittest.main()
