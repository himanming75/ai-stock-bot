from pathlib import Path
import json, sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from p3_reject_validation.plan import create_reject_plan
def main():
    result = create_reject_plan(
        Path("release/p3_reject_validation/actual/reject_validation_plan.json")
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0
if __name__ == "__main__": raise SystemExit(main())
