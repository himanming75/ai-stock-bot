from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from paper_validation_ops import ValidationOperationsService

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--repository-root", default=str(ROOT))
    args = p.parse_args()
    report = ValidationOperationsService(Path(args.repository_root)).build()
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
