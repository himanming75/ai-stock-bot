from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from paper_autonomous_execution.service import PaperAutonomousExecutionService

parser = argparse.ArgumentParser()
parser.add_argument(
    "--profile",
    default="release/v14001_15000_paper_autonomous_execution/config/paper_execution_profile.json",
)
parser.add_argument("--submit-paper", action="store_true")
parser.add_argument("--certify", action="store_true")
args = parser.parse_args()

service = PaperAutonomousExecutionService(
    project_root=ROOT,
    profile_path=ROOT / args.profile,
    output_dir=ROOT / "release/v14001_15000_paper_autonomous_execution",
)

result = (
    service.certify()
    if args.certify
    else service.run_once(allow_submit=args.submit_paper)
)
print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
raise SystemExit(0 if result.get("status") in {
    "PASS", "NO_ACTION", "READY_DRY_RUN", "PAPER_ORDER_SUBMITTED"
} else 2)
