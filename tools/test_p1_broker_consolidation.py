import unittest,tempfile,warnings
from pathlib import Path
from broker_integration.registry import *
from broker_integration.paths import BrokerStatePaths
from broker_integration.compatibility import resolve_legacy_component
class Tests(unittest.TestCase):
 def test_read_only(self): self.assertTrue(all(not x["write_capable"] for x in CANONICAL_COMPONENTS.values()))
 def test_roles(self): self.assertIn("broker_read_adapter",CANONICAL_COMPONENTS)
 def test_compat(self): self.assertTrue(all(x["canonical_role"] in CANONICAL_COMPONENTS for x in COMPATIBILITY_COMPONENTS.values()))
 def test_no_delete(self): self.assertEqual(consolidation_manifest()["legacy_files_deleted"],[])
 def test_resolve(self): self.assertEqual(canonical_component("broker_read_adapter")["module"],"alpaca_paper_read.adapter")
 def test_unknown(self):
  with self.assertRaises(KeyError): canonical_component("x")
 def test_warn(self):
  with warnings.catch_warnings(record=True) as w: warnings.simplefilter("always"); resolve_legacy_component("paper_broker_adapter.boundary")
  self.assertTrue(w)
 def test_state_root(self):
  with tempfile.TemporaryDirectory() as d:self.assertEqual(BrokerStatePaths(Path(d)).order_ledger.parent,BrokerStatePaths(Path(d)).canonical_root)
 def test_replacements(self): self.assertTrue(all(x["replacement"] for x in DEPRECATED_COMPONENTS.values()))
 def test_zero_orders(self): self.assertFalse(consolidation_manifest()["broker_write_authorized"])
if __name__=="__main__": unittest.main(verbosity=2)
