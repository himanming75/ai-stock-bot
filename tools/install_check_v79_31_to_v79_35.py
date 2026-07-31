from pathlib import Path
import importlib
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

REQUIRED = [
    "alpaca_market_data/gap_fill_v79_31_35.py",
    "tools/run_v79_31_to_v79_35_pipeline.py",
    "tools/test_gap_fill_v79_31_to_v79_35.py",
    "tools/verify_v79_31_to_v79_35_pipeline.py",
    "release/v79_31/config/gap_fill_config_v79_31.json",
    "release/v79_32/fixtures/gap_fill_bars_v79_32.json",
]

missing = [path for path in REQUIRED if not (ROOT / path).is_file()]
if missing:
    raise SystemExit("MISSING: " + ", ".join(missing))

module = importlib.import_module("alpaca_market_data.gap_fill_v79_31_35")
module.GapFillConfig().validate()
print("V79.31-V79.35 INSTALL CHECK PASS")
