import tempfile,unittest
from pathlib import Path
from risk_engine_v2.config import load,validate
from risk_engine_v2.metrics import drawdown,daily_loss,position_size
from risk_engine_v2.kill_switch import load as load_kill,set_state
from risk_engine_v2.gate import evaluate as gate
from risk_engine_v2.engine import evaluate

class Tests(unittest.TestCase):
    def test_drawdown(self):self.assertEqual(drawdown(100,90),10)
    def test_daily_loss(self):self.assertEqual(daily_loss(100,98),2)
    def test_position_size(self):
        r=position_size(10000,1,100,95,100,10000)
        self.assertEqual(r["quantity"],20)
    def test_policy_safe(self):
        with tempfile.TemporaryDirectory() as t:
            c=load(Path(t));self.assertFalse(c["broker_write_enabled"])
    def test_validate(self):
        with tempfile.TemporaryDirectory() as t:self.assertTrue(validate(load(Path(t)))["valid"])
    def test_default_kill_switch_on(self):
        with tempfile.TemporaryDirectory() as t:self.assertTrue(load_kill(Path(t))["enabled"])
    def test_gate_blocked_by_kill(self):
        with tempfile.TemporaryDirectory() as t:
            p=load(Path(t))
            s={"peak_equity":100,"current_equity":100,"day_start_equity":100,"consecutive_losses":0}
            c={"entry_price":10,"stop_price":9,"atr_pct":1,"projected_symbol_weight_pct":1,"projected_sector_weight_pct":1,"maximum_correlation":0}
            self.assertFalse(gate(p,s,c,{"enabled":True})["passed"])
    def test_engine_live_zero(self):
        with tempfile.TemporaryDirectory() as t:self.assertEqual(evaluate(Path(t))["actual_live_orders_submitted"],0)

if __name__=="__main__":unittest.main()
