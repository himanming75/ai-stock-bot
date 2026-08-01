from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from alpaca_broker import ControlledPaperReadValidator, READ_CONFIRMATION_TEXT

assert ControlledPaperReadValidator
assert READ_CONFIRMATION_TEXT == "READ MY ALPACA PAPER ACCOUNT ONLY"

source = ROOT / "release" / "v110_00" / "output" / "alpaca_paper_broker_integration_result.json"
if not source.is_file():
    raise SystemExit(f"MISSING V110 BROKER RESULT: {source}")

print("V110.01-V111.00 CONTROLLED ALPACA PAPER READ INSTALL CHECK PASS")
