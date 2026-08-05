from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from portfolio_risk_intelligence.service import (
    PortfolioRiskIntelligenceService,
)

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--ai-decision",
        default=(
            "release/v491_540_ai_decision_engine/"
            "actual/ai_decision_latest.json"
        ),
    )
    parser.add_argument(
        "--portfolio",
        default=(
            "release/v541_590_portfolio_risk_intelligence/"
            "fixtures/portfolio_fixture.json"
        ),
    )
    parser.add_argument(
        "--risk",
        default=(
            "release/v331_340_realtime_risk_monitoring/"
            "actual/risk_monitor_latest.json"
        ),
    )
    parser.add_argument(
        "--metadata",
        default=(
            "release/v541_590_portfolio_risk_intelligence/"
            "config/symbol_metadata.json"
        ),
    )
    parser.add_argument(
        "--correlations",
        default=(
            "release/v541_590_portfolio_risk_intelligence/"
            "fixtures/correlation_fixture.json"
        ),
    )
    parser.add_argument(
        "--policy",
        default=(
            "release/v541_590_portfolio_risk_intelligence/"
            "config/portfolio_risk_policy.json"
        ),
    )
    parser.add_argument(
        "--output-dir",
        default=(
            "release/v541_590_portfolio_risk_intelligence/actual"
        ),
    )
    args = parser.parse_args()
    result = PortfolioRiskIntelligenceService().evaluate(
        ai_decision_path=Path(args.ai_decision),
        portfolio_path=Path(args.portfolio),
        risk_path=Path(args.risk),
        metadata_path=Path(args.metadata),
        correlation_path=Path(args.correlations),
        policy_path=Path(args.policy),
        output_dir=Path(args.output_dir),
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
