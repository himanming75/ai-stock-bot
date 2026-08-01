from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from market_data_engine import AlpacaMessageParser, MarketDataRouter, SubscriptionRegistry

assert AlpacaMessageParser
assert MarketDataRouter
assert SubscriptionRegistry

source = ROOT / "release" / "v102_00" / "output" / "runtime_foundation_result.json"
if not source.is_file():
    raise SystemExit(f"MISSING V102 RUNTIME RESULT: {source}")

print("V102.01-V103.00 MARKET DATA FOUNDATION INSTALL CHECK PASS")
