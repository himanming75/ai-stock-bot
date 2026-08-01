from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from portfolio_engine import Portfolio, PortfolioAccountingEngine

assert Portfolio
assert PortfolioAccountingEngine

source = ROOT / "release" / "v106_00" / "output" / "paper_execution_adapter_result.json"
if not source.is_file():
    raise SystemExit(f"MISSING V106 EXECUTION RESULT: {source}")

print("V106.01-V107.00 PORTFOLIO FILL ACCOUNTING INSTALL CHECK PASS")
