from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from paper_scheduler import (
    AlpacaPaperSessionScheduler,
    AtomicSchedulerStateStore,
    TradingCalendarPolicy,
)

assert AlpacaPaperSessionScheduler
assert AtomicSchedulerStateStore
assert TradingCalendarPolicy

source = (
    ROOT / "release" / "v114_00" / "output"
    / "alpaca_paper_order_recovery_fixture_result.json"
)
if not source.is_file():
    raise SystemExit(f"MISSING V114 RECOVERY RESULT: {source}")

print("V114.01-V115.00 ALPACA PAPER SESSION SCHEDULER INSTALL CHECK PASS")
