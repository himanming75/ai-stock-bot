from __future__ import annotations
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from premarket_hardening.cleanup import build_cleanup_plan


def collect_files(root: Path) -> list[dict]:
    items = []
    for path in root.rglob("*"):
        if path.is_file():
            items.append({
                "path": str(path),
                "modified_at": datetime.fromtimestamp(
                    path.stat().st_mtime,
                    tz=timezone.utc,
                ),
            })
    return items


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="release")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Reserved for a separately reviewed future cleanup run.",
    )
    args = parser.parse_args()

    if args.apply:
        raise SystemExit(
            "APPLY mode is intentionally disabled. "
            "Review dry-run output first."
        )

    plan = build_cleanup_plan(
        files=collect_files(Path(args.root)),
        now=datetime.now(timezone.utc),
        dry_run=True,
    )
    print(json.dumps(plan, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
