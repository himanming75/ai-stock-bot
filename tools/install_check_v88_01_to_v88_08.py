from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    required = [
        "web_ui_v2/app.py",
        "tools/test_web_ui_v2_v88_01_to_v88_08.py",
        "tools/verify_web_ui_v2_v88_01_to_v88_08.py",
        "RUN_V88_01_TO_V88_08_WEB_UI_V2.ps1",
        "RUN_V88_01_TO_V88_08_TEST_AND_VERIFY.ps1",
        "release/v88_01_to_v88_08/README_V88_01_TO_V88_08.md",
    ]
    missing = [item for item in required if not (root / item).exists()]
    if missing:
        for item in missing:
            print(f"MISSING: {item}")
        return 1
    print("V88.01-V88.08 INSTALL CHECK PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
