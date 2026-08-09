from pathlib import Path
import sys,unittest

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from broker_integration_v1.historical_bootstrap_diagnostic_status_v2_1_8_1 import (
    build_v2_1_8_1_status,
)

class TestV2181(unittest.TestCase):
    def test_status(self):
        s=build_v2_1_8_1_status()
        self.assertTrue(s["pagination_supported"])
        self.assertTrue(s["symbol_raw_counts_visible"])
        self.assertFalse(s["broker_order_submission"])
        self.assertFalse(s["production_order_post_allowed"])
        self.assertFalse(s["live_trading_enabled"])

if __name__=="__main__":
    unittest.main()
