import tempfile, unittest
from pathlib import Path
from paper_operational_reliability import OperationalReliabilityService

class Tests(unittest.TestCase):
    def test_lock_read_only(self):
        with tempfile.TemporaryDirectory() as d:
            s=OperationalReliabilityService(Path(d))
            self.assertFalse(s.lock_status()["automatic_lock_deletion"])

    def test_ledger_safe(self):
        with tempfile.TemporaryDirectory() as d:
            s=OperationalReliabilityService(Path(d))
            self.assertEqual(s.ledger_health()["malformed_total"],0)

    def test_recovery_advisory(self):
        with tempfile.TemporaryDirectory() as d:
            s=OperationalReliabilityService(Path(d))
            r=s.recovery_decision(
                {"State":"READY"},{"Count":0},{"stale_candidate_count":0},
                {"status":"PASS","market_open":True,"trading_blocked":False,
                 "open_order_count":0,"position_count":0}
            )
            self.assertTrue(r["safe_to_restart_task"])
            self.assertFalse(r["automatic_restart_performed"])

    def test_report_contract(self):
        with tempfile.TemporaryDirectory() as d:
            s=OperationalReliabilityService(Path(d))
            s.task_status=lambda:{"State":"READY"}
            s.process_status=lambda:{"Count":0,"Processes":[]}
            s.broker_read_only=lambda:{
                "status":"PASS","paper_only":True,"market_open":False,
                "trading_blocked":False,"position_count":0,"open_order_count":0,
                "broker_write_performed":False
            }
            r=s.build()
            self.assertFalse(r["broker_write_performed"])
            self.assertFalse(r["automatic_repair_performed"])
            self.assertFalse(r["trading_configuration_changed"])

if __name__=="__main__": unittest.main(verbosity=2)
