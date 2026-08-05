import tempfile,unittest
from pathlib import Path
from multi_broker_etrade_sandbox_cert.service import ETradeSandboxReadCertificationService
from multi_broker_etrade_sandbox_cert.validation import classify_error
class Tests(unittest.TestCase):
    def result(self):
        td=tempfile.TemporaryDirectory(); self.addCleanup(td.cleanup)
        return ETradeSandboxReadCertificationService().evaluate(output_dir=Path(td.name))
    def test_pass(self): self.assertEqual(self.result()["status"],"PASS")
    def test_contract(self): self.assertTrue(self.result()["fixture_contract_passed"])
    def test_deferred(self): self.assertIn(self.result()["actual_sandbox_validation_status"],{"READY_BLOCKED_BY_ETRADE_KEY_ISSUANCE","READY_FOR_EXPLICIT_SANDBOX_READ"})
    def test_errors(self): self.assertEqual(classify_error("503 unavailable"),"ETRADE_SERVER_ERROR")
    def test_zero_orders(self):
        r=self.result(); self.assertFalse(r["actual_broker_write_performed"]); self.assertEqual(r["actual_paper_orders_submitted"],0); self.assertEqual(r["actual_live_orders_submitted"],0)
if __name__=="__main__": unittest.main(verbosity=2)
