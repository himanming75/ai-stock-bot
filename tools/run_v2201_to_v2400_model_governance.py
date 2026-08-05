from __future__ import annotations
import argparse, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from model_governance_optimization.service import ModelGovernanceOptimizationService

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--candidates", default="release/v2201_2400_model_governance/fixtures/model_candidates.json")
    p.add_argument("--champion", default="release/v2201_2400_model_governance/config/champion_registry.json")
    p.add_argument("--policy", default="release/v2201_2400_model_governance/config/governance_policy.json")
    p.add_argument("--output-dir", default="release/v2201_2400_model_governance/actual")
    a = p.parse_args()
    result = ModelGovernanceOptimizationService().evaluate(
        candidates_path=Path(a.candidates),
        champion_path=Path(a.champion),
        policy_path=Path(a.policy),
        output_dir=Path(a.output_dir),
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 2

if __name__ == "__main__":
    raise SystemExit(main())
