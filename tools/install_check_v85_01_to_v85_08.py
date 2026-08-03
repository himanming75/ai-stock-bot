from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    required = [
        "dashboard_v2/dashboard_state.py",
        "dashboard_v2/render.py",
        "dashboard_v2/server.py",
        "tools/export_dashboard_v2_state.py",
        "tools/test_dashboard_v2_v85_01_to_v85_08.py",
        "tools/verify_dashboard_v2_v85_01_to_v85_08.py",
        "RUN_V85_01_TO_V85_08_DASHBOARD_V2.ps1",
        "RUN_V85_01_TO_V85_08_TEST_AND_VERIFY.ps1",
        "release/v85_01_to_v85_08/README_V85_01_TO_V85_08.md",
    ]
    missing = [item for item in required if not (root / item).exists()]
    if missing:
        for item in missing:
            print(f"MISSING: {item}")
        return 1
    print("V85.01-V85.08 INSTALL CHECK PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
