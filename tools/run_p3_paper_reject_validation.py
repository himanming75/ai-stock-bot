from __future__ import annotations
import argparse, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from p3_reject_validation.service import P3PaperRejectValidationService
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--nonce", required=True)
    args = parser.parse_args()
    result = P3PaperRejectValidationService().run(
        plan_path=Path("release/p3_reject_validation/actual/reject_validation_plan.json"),
        token_path=Path("release/p3_reject_validation/actual/reject_validation_token.json"),
        nonce=args.nonce,
        output_dir=Path("release/p3_reject_validation/actual"),
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 2
if __name__ == "__main__": raise SystemExit(main())
