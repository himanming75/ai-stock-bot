from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from p3_reject_validation.token import create_token, sha256_file
def main():
    plan = Path("release/p3_reject_validation/actual/reject_validation_plan.json")
    output = Path("release/p3_reject_validation/actual/reject_validation_token.json")
    token = create_token(output, sha256_file(plan))
    print("P3 REJECT APPROVAL TOKEN CREATED")
    print("Nonce:", token["nonce"])
    print("Expires:", token["expires_at"])
    print("Plan SHA256:", token["plan_sha256"])
    return 0
if __name__ == "__main__": raise SystemExit(main())
