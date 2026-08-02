from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from autonomous_paper_runtime import AutonomousOrderLedgerRecovery,BrokerOrderNormalizer,LedgerRecoveryStatus
assert AutonomousOrderLedgerRecovery and BrokerOrderNormalizer and LedgerRecoveryStatus
if not (ROOT/'release/v123_00/actual_read/actual_open_order_identity_result.json').is_file() and not (ROOT/'release/v123_00/output/autonomous_paper_order_identity_reconciliation_result.json').is_file():raise SystemExit('MISSING V123 ORDER IDENTITY RESULT')
print('V123.01-V124.00 AUTONOMOUS ORDER LEDGER RECOVERY INSTALL CHECK PASS')
