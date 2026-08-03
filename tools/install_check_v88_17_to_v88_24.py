from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from paper_production_release.discovery import discover_layout


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    required = [
        "paper_production_release/io.py",
        "paper_production_release/discovery.py",
        "paper_production_release/environment.py",
        "paper_production_release/prerequisites.py",
        "paper_production_release/integrity.py",
        "paper_production_release/engine.py",
        "dashboard_v2/paper_production_release_integration.py",
        "tools/run_paper_production_release_v88_17_to_v88_24.py",
        "tools/test_paper_production_release_v88_17_to_v88_24.py",
        "tools/verify_paper_production_release_v88_17_to_v88_24.py",
        "BACKUP_V88_17_TO_V88_24.ps1",
        "ROLLBACK_V88_17_TO_V88_24.ps1",
        "release/v88_17_to_v88_24/README_V88_17_TO_V88_24.md",
    ]
    missing = [item for item in required if not (root / item).exists()]
    if missing:
        for item in missing:
            print(f"MISSING: {item}")
        return 1

    layout = discover_layout(root)
    if not layout["layout_valid"]:
        for item in layout["missing_modules"]:
            print(f"MISSING MODULE: {item}")
        return 1

    print(
        "INDICATOR_LAYOUT="
        + layout["indicator_layout"]
    )
    print("V88.17-V88.24 INSTALL CHECK PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
