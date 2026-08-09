from pathlib import Path
import unittest
class TestV294(unittest.TestCase):
 def test_existing_certifier_reused(self): self.assertTrue(Path('tools/certify_runtime_shadow_v2_9.py').exists())
 def test_runner_exists(self): self.assertTrue(Path('paper_daily_session/runner.py').exists())
 def test_no_new_engine(self): self.assertFalse(Path('tools/run_regime_aware_shadow_v2_9_4.py').exists())
 def test_gate_tool_exists(self): self.assertTrue(Path('tools/certify_runtime_observation_gate_v2_9_4.py').exists())
 def test_safety(self):
  t=Path('tools/certify_runtime_observation_gate_v2_9_4.py').read_text(encoding='utf-8'); self.assertIn("'broker_write_performed':False",t)
if __name__=='__main__': unittest.main()
