from dataclasses import dataclass
from datetime import datetime,timezone
from enum import Enum
from pathlib import Path
import tempfile,unittest
from autonomous_paper_runtime import AutonomousOrderLedgerRecovery,BrokerOrderNormalizer,LedgerRecoveryStatus
class Side(Enum): BUY='buy'
class Typ(Enum): LIMIT='limit'
@dataclass
class Raw: id:str='broker-1'; client_order_id:str='single-legacy-1'; symbol:str='AAPL'; side:Side=Side.BUY; qty:str='1'; type:Typ=Typ.LIMIT; time_in_force:str='day'; status:str='accepted'; submitted_at:datetime=datetime(2026,8,1,tzinfo=timezone.utc); filled_qty:str='0'; limit_price:str='50'
class Wrap:
 def __init__(self): self.raw=Raw()
class T(unittest.TestCase):
 def test_nested_object(self):
  x=BrokerOrderNormalizer().normalize(Wrap()); self.assertEqual((x.broker_order_id,x.quantity,x.order_type,x.time_in_force),('broker-1','1','LIMIT','DAY'))
 def test_nested_dict(self):
  x=BrokerOrderNormalizer().normalize({'data':{'id':'b2','client_order_id':'c2','symbol':'SPY','side':'sell','qty':'2','type':'market','time_in_force':'day','status':'new'}}); self.assertEqual((x.broker_order_id,x.side,x.quantity),('b2','SELL','2'))
 def test_direct_recovery(self):
  with tempfile.TemporaryDirectory() as d:r=AutonomousOrderLedgerRecovery().recover(Path(d),[Raw()],[{'client_order_id':'single-legacy-1'}]); self.assertEqual(r.status,LedgerRecoveryStatus.RECOVERED)
 def test_evidence_recovery(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d); (p/'execution_ledger.json').write_text('{"client_order_id":"single-legacy-1"}'); r=AutonomousOrderLedgerRecovery().recover(p,[Raw()],[]); self.assertEqual(r.entries[0].owner,'LEGACY_BOT')
 def test_low_confidence_not_enough(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d); (p/'notes.txt').write_text('single-legacy-1'); r=AutonomousOrderLedgerRecovery().recover(p,[Raw()],[]); self.assertEqual(r.status,LedgerRecoveryStatus.EXTERNAL_ORDER)
 def test_external(self):
  with tempfile.TemporaryDirectory() as d:r=AutonomousOrderLedgerRecovery().recover(Path(d),[Raw(client_order_id='manual')],[]); self.assertTrue(r.safe_mode_engaged)
 def test_unknown(self):
  with tempfile.TemporaryDirectory() as d:r=AutonomousOrderLedgerRecovery().recover(Path(d),[Raw(client_order_id='')],[]); self.assertEqual(r.status,LedgerRecoveryStatus.UNKNOWN_ORDER)
 def test_no_orders(self):
  with tempfile.TemporaryDirectory() as d:r=AutonomousOrderLedgerRecovery().recover(Path(d),[],[]); self.assertEqual(r.status,LedgerRecoveryStatus.NO_OPEN_ORDERS)
 def test_exclude_self_evidence(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'release/v123_00/actual_read'; p.mkdir(parents=True); (p/'actual_open_order_identity_result.json').write_text('single-legacy-1'); r=AutonomousOrderLedgerRecovery().recover(Path(d),[Raw()],[]); self.assertEqual(r.status,LedgerRecoveryStatus.EXTERNAL_ORDER)
 def test_zero_counters(self):
  with tempfile.TemporaryDirectory() as d:r=AutonomousOrderLedgerRecovery().recover(Path(d),[Raw(client_order_id='manual')],[]); self.assertEqual((r.read_requests_executed,r.write_requests_executed,r.actual_paper_orders_submitted,r.live_orders_submitted),(0,0,0,0))
 def test_json(self):
  with tempfile.TemporaryDirectory() as d:r=AutonomousOrderLedgerRecovery().recover(Path(d),[Raw(client_order_id='manual')],[]); self.assertEqual(r.to_json_dict()['status'],'EXTERNAL_ORDER')
if __name__=='__main__':unittest.main()
