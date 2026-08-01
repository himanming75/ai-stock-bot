from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from alpaca_broker import AlpacaPaperClient, AlpacaPaperConfig, BrokerPortfolioReconciler

assert AlpacaPaperClient
assert AlpacaPaperConfig
assert BrokerPortfolioReconciler

source = ROOT / "release" / "v109_00" / "output" / "end_to_end_paper_runtime_result.json"
if not source.is_file():
    raise SystemExit(f"MISSING V109 END-TO-END RESULT: {source}")

print("V109.01-V110.00 ALPACA PAPER BROKER INTEGRATION INSTALL CHECK PASS")
