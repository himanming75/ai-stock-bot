from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from model_validation_backtest.service import (
    ModelValidationBacktestService,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--predictions",
        default=(
            "release/v2001_2200_model_validation/"
            "fixtures/prediction_fixture.json"
        ),
    )
    parser.add_argument(
        "--output-dir",
        default=(
            "release/v2001_2200_model_validation/actual"
        ),
    )
    args = parser.parse_args()

    result = ModelValidationBacktestService().evaluate(
        prediction_path=Path(args.predictions),
        output_dir=Path(args.output_dir),
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
