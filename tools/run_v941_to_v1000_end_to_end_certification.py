from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from paper_platform_certification.service import PaperPlatformCertificationService

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    parser.add_argument(
        "--output-dir",
        default="release/v941_1000_end_to_end_certification/actual",
    )
    args = parser.parse_args()
    result = PaperPlatformCertificationService().evaluate(
        root=Path(args.repository_root).resolve(),
        output_dir=Path(args.output_dir),
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 2

if __name__ == "__main__":
    raise SystemExit(main())
