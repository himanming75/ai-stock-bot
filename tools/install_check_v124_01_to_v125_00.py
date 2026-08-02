from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autonomous_paper_runtime import (
    BrokerPortfolioReconciler,
    BrokerPortfolioReconciliationPolicy,
    BrokerPortfolioStatus,
)

assert BrokerPortfolioReconciler
assert BrokerPortfolioReconciliationPolicy
assert BrokerPortfolioStatus

ledger = (
    ROOT / "release/v124_00/actual_read"
    / "actual_order_ledger_recovery_result.json"
)
fixture = (
    ROOT / "release/v124_00/output"
    / "autonomous_order_ledger_recovery_result.json"
)
if not ledger.is_file() and not fixture.is_file():
    raise SystemExit("MISSING V124 ACTUAL OR FIXTURE LEDGER RECOVERY RESULT")

print("V124.01-V125.00 BROKER PORTFOLIO RECONCILIATION INSTALL CHECK PASS")
