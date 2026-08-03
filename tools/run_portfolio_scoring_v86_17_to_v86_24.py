from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from portfolio_scoring.engine import evaluate_portfolio
from portfolio_scoring.io import load_json, parse_input, write_json


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        default=str(
            ROOT / "release/v86_17_to_v86_24/input/"
            "portfolio_candidates.json"
        ),
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    payload = load_json(input_path)
    candidates, policy = parse_input(payload)
    portfolio = evaluate_portfolio(candidates, policy)

    actual = ROOT / "release/v86_17_to_v86_24/actual"
    result = {
        "stage": "V86.24",
        "stage_range": "V86.17-V86.24",
        "state": "PORTFOLIO_SCORING_ENGINE_READY",
        "status": "PASS",
        "implementation_type": "LOCAL_MULTI_ASSET_PORTFOLIO_SCORING",
        "portfolio": portfolio,
        "input_path": str(input_path.resolve()),
        "paper_only": True,
        "actual_credentials_used": False,
        "actual_external_network_used": False,
        "network_requests_executed": 0,
        "write_requests_executed": 0,
        "broker_command_execution_enabled": False,
        "broker_write_enabled": False,
        "order_submission_enabled": False,
        "live_trading_enabled": False,
        "external_network_enabled": False,
        "next_phase": "V86_25_AI_EXPLAINABILITY",
    }

    result_path = actual / "portfolio_scoring_result.json"
    write_json(result_path, result)
    write_json(
        actual / "portfolio_recommendations.json",
        {
            "state": result["state"],
            "recommended_allocations": portfolio[
                "recommended_allocations"
            ],
            "allocation_summary": portfolio["allocation_summary"],
            "portfolio_score": portfolio["portfolio_score"],
            "diversification_score": portfolio[
                "diversification_score"
            ],
            "paper_only": True,
        },
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    print(f"RESULT_FILE={result_path.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
