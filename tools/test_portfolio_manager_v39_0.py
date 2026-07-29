import importlib.util, sys, unittest
from pathlib import Path
from decimal import Decimal
P=Path(__file__).with_name("portfolio_manager_v39_0.py")
S=importlib.util.spec_from_file_location("portfolio_manager_v39_0",P)
M=importlib.util.module_from_spec(S); sys.modules[S.name]=M; S.loader.exec_module(M)

class Tests(unittest.TestCase):
    def test_empty(self):
        m=M.PortfolioManager(starting_cash="100000"); s=m.snapshot()
        self.assertEqual((s.cash,s.market_value,s.equity,s.position_count),("100000","0","100000",0))
    def test_add_first(self):
        m=M.PortfolioManager(starting_cash="100000"); m.upsert_position(symbol="AAPL",side="long",quantity="10",average_price="200",market_price="210")
        s=m.snapshot(); self.assertEqual((s.position_count,s.market_value,s.equity),(1,"2100","102100"))
    def test_multiple(self):
        m=M.PortfolioManager(starting_cash="100000")
        m.upsert_position(symbol="AAPL",side="long",quantity="10",average_price="200",market_price="210")
        m.upsert_position(symbol="MSFT",side="long",quantity="5",average_price="300",market_price="320")
        self.assertEqual(m.snapshot().position_count,2)
    def test_long_unrealized(self):
        m=M.PortfolioManager(starting_cash="100000"); m.upsert_position(symbol="AAPL",side="long",quantity="10",average_price="200",market_price="212")
        self.assertEqual(m.snapshot().unrealized_pnl,"120")
    def test_short_unrealized(self):
        m=M.PortfolioManager(starting_cash="100000"); m.upsert_position(symbol="AAPL",side="short",quantity="10",average_price="200",market_price="190")
        self.assertEqual(m.snapshot().unrealized_pnl,"100")
    def test_realized(self):
        m=M.PortfolioManager(starting_cash="100000"); m.upsert_position(symbol="AAPL",side="long",quantity="10",average_price="200",market_price="210",realized_pnl="50")
        self.assertEqual((m.snapshot().realized_pnl,m.snapshot().total_pnl),("50","150"))
    def test_cash(self):
        m=M.PortfolioManager(starting_cash="100000"); m.adjust_cash("-10000","settlement")
        self.assertEqual(m.snapshot().cash,"90000")
    def test_negative_cash(self):
        m=M.PortfolioManager(starting_cash="1000")
        with self.assertRaises(ValueError): m.adjust_cash("-2000","bad")
    def test_remove(self):
        m=M.PortfolioManager(starting_cash="100000"); m.upsert_position(symbol="AAPL",side="long",quantity="10",average_price="200",market_price="210"); m.remove_position("AAPL")
        self.assertEqual(m.snapshot().position_count,0)
    def test_buying_power(self):
        m=M.PortfolioManager(starting_cash="100000",buying_power_multiplier="2")
        self.assertEqual(m.snapshot().buying_power,"200000")
    def test_hashes(self):
        m=M.PortfolioManager(starting_cash="100000")
        self.assertEqual(len(m.snapshot().snapshot_sha256),64); self.assertEqual(len(m.ledger()[0].event_sha256),64)
    def test_no_network(self):
        m=M.PortfolioManager(starting_cash="100000"); self.assertFalse(m.export()["network_used"])
    def test_parser(self):
        p=M.parse_position_spec("AAPL:10:200:210:long:5"); self.assertEqual(p["realized_pnl"],"5")
    def test_demo_values(self):
        m=M.PortfolioManager(starting_cash="100000")
        for x in ["AAPL:100:200:212","MSFT:50:350:360","NVDA:20:900:925"]: m.upsert_position(**M.parse_position_spec(x))
        s=m.snapshot()
        self.assertEqual(s.market_value,"57700"); self.assertEqual(s.equity,"157700"); self.assertEqual(s.unrealized_pnl,"2200")

if __name__=="__main__": unittest.main(verbosity=2)
