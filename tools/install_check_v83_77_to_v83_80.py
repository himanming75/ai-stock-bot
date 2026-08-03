from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    required = [
        "paper_runtime/multi_day_paper_validation_v83_77_80.py",
        "dashboard/multi_day_paper_validation_integration.py",
        "tools/run_multi_day_paper_validation_v83_77_to_v83_80.py",
        "tools/test_multi_day_paper_validation_v83_77_to_v83_80.py",
        "tools/verify_multi_day_paper_validation_v83_77_to_v83_80.py",
        "RUN_V83_77_TO_V83_80_MULTI_DAY_PAPER_VALIDATION.ps1",
        "RUN_V83_77_TO_V83_80_TEST_AND_VERIFY.ps1",
        "release/v83_77_to_v83_80/input/multi_day_paper_validation_policy.json",
        "release/v83_77_to_v83_80/README_V83_77_TO_V83_80.md",
    ]
    missing = [item for item in required if not (root / item).exists()]
    if missing:
        for item in missing:
            print(f"MISSING: {item}")
        return 1
    print("V83.77-V83.80 INSTALL CHECK PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
