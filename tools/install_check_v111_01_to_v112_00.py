from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from alpaca_broker import (
    ControlledPaperOrderOptIn,
    MAX_NOTIONAL,
    MAX_QUANTITY,
    WRITE_CONFIRMATION_TEXT,
)

assert ControlledPaperOrderOptIn
assert MAX_QUANTITY == 1
assert MAX_NOTIONAL == 100
assert WRITE_CONFIRMATION_TEXT == "SUBMIT ONE ALPACA PAPER ORDER ONLY"

source = ROOT / "release" / "v111_00" / "output" / "controlled_alpaca_paper_read_fixture_result.json"
if not source.is_file():
    raise SystemExit(f"MISSING V111 READ RESULT: {source}")

print("V111.01-V112.00 CONTROLLED ALPACA PAPER ORDER OPT-IN INSTALL CHECK PASS")
