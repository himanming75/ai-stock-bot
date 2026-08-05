from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ai_market_intelligence.service import AIMarketIntelligenceService


def latest_cycle_snapshot(root: Path) -> Path:
    base = root / "release/actual_market_polling_validation/actual"
    cycles = sorted(
        [x for x in base.glob("cycle_*") if x.is_dir()],
        key=lambda x: x.name,
        reverse=True,
    )
    for cycle in cycles:
        candidate = cycle / "raw_readonly_snapshot.json"
        if candidate.exists():
            return candidate
    return base / "missing_raw_readonly_snapshot.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", default="")
    parser.add_argument(
        "--output-dir",
        default="release/v1001_1200_ai_market_intelligence/actual",
    )
    parser.add_argument("--minimum-bars", type=int, default=35)
    args = parser.parse_args()

    snapshot = Path(args.snapshot) if args.snapshot else latest_cycle_snapshot(ROOT)
    result = AIMarketIntelligenceService().evaluate(
        snapshot_path=snapshot,
        output_dir=Path(args.output_dir),
        minimum_bars=args.minimum_bars,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
