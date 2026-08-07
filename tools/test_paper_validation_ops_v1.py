import json, tempfile, unittest
from pathlib import Path
from paper_validation_ops import ValidationOperationsService

class Tests(unittest.TestCase):
    def test_empty_data_passes(self):
        with tempfile.TemporaryDirectory() as d:
            r=ValidationOperationsService(Path(d)).build()
            self.assertEqual(r["status"],"PASS")
            self.assertEqual(r["progress"]["closed_trades"],0)
            self.assertFalse(r["broker_write_performed"])

    def test_metrics(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            p=root/"runtime/paper_full_auto_lifecycle/closed_round_trips.jsonl"
            p.parent.mkdir(parents=True)
            rows=[
                {"symbol":"AAPL","realized_pl":2.0,"exit_time":"2026-08-01T15:00:00+00:00"},
                {"symbol":"AAPL","realized_pl":-1.0,"exit_time":"2026-08-02T15:00:00+00:00"},
                {"symbol":"MSFT","realized_pl":3.0,"exit_time":"2026-08-02T16:00:00+00:00"},
            ]
            p.write_text("\n".join(json.dumps(x) for x in rows))
            r=ValidationOperationsService(root).build()
            self.assertEqual(r["progress"]["closed_trades"],3)
            self.assertEqual(r["progress"]["trading_days"],2)
            self.assertEqual(r["metrics"]["profit_factor"],5.0)
            self.assertAlmostEqual(r["metrics"]["expectancy"],4/3,places=6)

    def test_read_only_contract(self):
        with tempfile.TemporaryDirectory() as d:
            r=ValidationOperationsService(Path(d)).build()
            self.assertEqual(r["mode"],"READ_ONLY")
            self.assertFalse(r["trading_configuration_changed"])
            self.assertFalse(r["broker_write_performed"])

if __name__=="__main__":
    unittest.main(verbosity=2)
