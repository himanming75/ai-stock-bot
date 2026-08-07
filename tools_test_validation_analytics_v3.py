import tempfile, unittest, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from validation_analytics_v3 import metric,monte_carlo,out_of_sample_split,walk_forward_trade_windows

class Tests(unittest.TestCase):
    def test_metrics(self):
        m=metric([2,-1,3,-1])
        self.assertEqual(m["count"],4)
        self.assertEqual(m["profit_factor"],2.5)
    def test_monte_carlo_guard(self):
        self.assertEqual(monte_carlo([1]*5)["status"],"INSUFFICIENT_DATA")
    def test_oos(self):
        self.assertEqual(out_of_sample_split([1]*20)["status"],"PASS")
    def test_walk_forward(self):
        self.assertEqual(walk_forward_trade_windows([1]*60)["status"],"PASS")
if __name__=="__main__":unittest.main(verbosity=2)
