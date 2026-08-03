from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    required = [
        "paper_runtime/paper_stability_runtime_v83_81_88.py",
        "dashboard/paper_stability_runtime_integration.py",
        "tools/run_paper_stability_runtime_v83_81_to_v83_88.py",
        "tools/test_paper_stability_runtime_v83_81_to_v83_88.py",
        "tools/verify_paper_stability_runtime_v83_81_to_v83_88.py",
        "RUN_V83_81_TO_V83_88_PAPER_STABILITY_RUNTIME.ps1",
        "RUN_V83_81_TO_V83_88_TEST_AND_VERIFY.ps1",
        "release/v83_81_to_v83_88/input/paper_stability_runtime_policy.json",
        "release/v83_81_to_v83_88/README_V83_81_TO_V83_88.md",
    ]
    missing = [item for item in required if not (root / item).exists()]
    if missing:
        for item in missing:
            print(f"MISSING: {item}")
        return 1
    print("V83.81-V83.88 INSTALL CHECK PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
