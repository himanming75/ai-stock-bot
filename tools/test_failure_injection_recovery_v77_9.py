from __future__ import annotations
import json,tempfile,unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch
from broker.broker_state_checkpoint_v77_5 import BrokerStateCheckpointManager
from broker.contracts_v77_1 import BrokerOrderRequest,OrderSide,OrderType,TimeInForce
from broker.failure_injection_recovery_v77_9 import FailureInjectionRecovery
from broker.order_lifecycle_simulator_v77_3 import OrderLifecycleSimulator
from tools.failure_injection_recovery_v77_9 import verify,summary
from tools.verify_failure_injection_recovery_v77_9 import verify_output
class Tests(unittest.TestCase):
 def cp(self):
  s=OrderLifecycleSimulator();o=s.submit_order(BrokerOrderRequest(client_order_id="seed",symbol="AAPL",side=OrderSide.BUY,quantity=Decimal("10"),order_type=OrderType.MARKET,time_in_force=TimeInForce.DAY));s.apply_fill(o.broker_order_id,quantity=Decimal("10"),price=Decimal("100"));return BrokerStateCheckpointManager().create(s,checkpoint_id="SEED")
 def test_failures_and_recovery(self):
  s,r=FailureInjectionRecovery().run(self.cp());self.assertEqual(r.status,"PASS");self.assertEqual(r.blocked_failure_count,4);self.assertEqual(r.detected_corruption_count,4);self.assertEqual(s.actual_orders_submitted,0)
 def test_hash_recovered(self):
  _,r=FailureInjectionRecovery().run(self.cp());self.assertEqual(r.source_state_sha256,r.recovered_state_sha256)
 def test_all_checks_true(self):
  _,r=FailureInjectionRecovery().run(self.cp());self.assertTrue(all(r.checks.values()))
 def test_outputs(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);o5=root/"release/v77_5/output";o8=root/"release/v77_8/output";o5.mkdir(parents=True);o8.mkdir(parents=True)
   BrokerStateCheckpointManager().write(self.cp(),o5/"sample_broker_state_checkpoint_v77_5.json")
   (o8/"multi_order_continuation_stress_verification_v77_8.json").write_text(json.dumps({"status":"PASS","multi_order_continuation_stress_sha256":"b"*64,"stress_report":{"stressed_state_sha256":"c"*64},"verification_sha256":"d"*64,"next_phase":"V77_9_FAILURE_INJECTION_RECOVERY"}))
   cfg={"expected_framework_commit_sha":"a","expected_v77_8_stress_sha256":"b"*64,"expected_v77_8_stressed_state_sha256":"c"*64,"expected_v77_8_verification_sha256":"d"*64}
   with patch("tools.failure_injection_recovery_v77_9.git",side_effect=["e"*40,"e"*40,"main"]),patch("tools.failure_injection_recovery_v77_9.anc",return_value=True):r=verify(root,cfg)
   out=root/"release/v77_9/output";out.mkdir(parents=True)
   (out/"failure_injection_recovery_verification_v77_9.json").write_text(json.dumps(r,indent=2,sort_keys=True))
   (out/"failure_injection_recovery_summary_v77_9.json").write_text(json.dumps(summary(r),indent=2,sort_keys=True))
   self.assertTrue(verify_output(out)["verified"])
if __name__=="__main__":unittest.main()
