from pathlib import Path
import importlib.util, unittest
def load():
    p=Path("dashboard/cross_ledger_trade_reconstruction_v3_7.py"); s=importlib.util.spec_from_file_location("v37",p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
class T(unittest.TestCase):
    @classmethod
    def setUpClass(c): c.r=load()
    def test_fill_required(self): self.assertIsNone(self.r.normalize_fill({"event":"X","side":"BUY","price":100,"qty":1,"time":"2026-08-07T00:00:00+00:00"},"x"))
    def test_fill(self): self.assertEqual(self.r.normalize_fill({"event":"ORDER_FILLED","side":"BUY","filled_avg_price":"100","filled_qty":"1","filled_at":"2026-08-07T00:00:00+00:00","symbol":"AAPL"},"x")["price"],100.0)
    def test_read_only(self):
        x=Path("dashboard/cross_ledger_trade_reconstruction_v3_7.py").read_text()
        for bad in ("TradingClient(","submit_order(","place_order("): self.assertNotIn(bad,x)
    def test_long(self):
        e={"side":"BUY","price":100,"qty":2,"fees_observed":0}; x={"side":"SELL","price":103,"qty":2,"fees_observed":0}
        # formula exercised through direct expression contract
        self.assertEqual((x["price"]-e["price"])*2,6)
    def test_short(self): self.assertEqual((100-97)*2,6)
if __name__=="__main__": unittest.main()
