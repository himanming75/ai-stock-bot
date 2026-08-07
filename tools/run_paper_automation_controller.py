from __future__ import annotations
import argparse, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from paper_automation_controller.service import PaperAutomationController

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--profile",
        default="release/paper_automation_controller/config/read_only_profile.json",
    )
    args = parser.parse_args()
    result = PaperAutomationController(ROOT).run(Path(args.profile))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] in {"PASS", "IDLE"} else 2

if __name__ == "__main__":
    raise SystemExit(main())
