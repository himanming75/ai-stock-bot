from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    required = [
        "paper_runtime/performance_production_readiness_v83_89_96.py",
        "dashboard/performance_production_readiness_integration.py",
        "tools/run_performance_production_readiness_v83_89_to_v83_96.py",
        "tools/test_performance_production_readiness_v83_89_to_v83_96.py",
        "tools/verify_performance_production_readiness_v83_89_to_v83_96.py",
        "RUN_V83_89_TO_V83_96_PERFORMANCE_READINESS.ps1",
        "RUN_V83_89_TO_V83_96_TEST_AND_VERIFY.ps1",
        "release/v83_89_to_v83_96/input/paper_performance_snapshot.json",
        "release/v83_89_to_v83_96/input/performance_production_readiness_policy.json",
        "release/v83_89_to_v83_96/README_V83_89_TO_V83_96.md",
    ]
    missing = [item for item in required if not (root / item).exists()]
    if missing:
        for item in missing:
            print(f"MISSING: {item}")
        return 1
    print("V83.89-V83.96 INSTALL CHECK PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
