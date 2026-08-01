from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from risk_engine import RuntimeRiskManager, RuntimeRiskState, RiskLimits

assert RuntimeRiskManager
assert RuntimeRiskState
assert RiskLimits

source = ROOT / "release" / "v107_00" / "output" / "portfolio_fill_accounting_result.json"
if not source.is_file():
    raise SystemExit(f"MISSING V107 PORTFOLIO RESULT: {source}")

print("V107.01-V108.00 RUNTIME RISK MANAGER INSTALL CHECK PASS")
