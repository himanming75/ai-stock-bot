from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autonomous_ai_brain.research_integration import AIResearchShadowIntegration


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--root", default=str(ROOT))
    args = p.parse_args()

    project_root = Path(args.root).resolve()
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    result = AIResearchShadowIntegration(project_root).run()
    print(json.dumps(result, indent=2, default=str))

    contracts = result["contracts"]
    assert contracts["broker_write_performed"] is False
    assert contracts["order_submission_performed"] is False
    assert contracts["trading_configuration_changed"] is False
    assert contracts["actual_paper_decision_path_changed"] is False
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
