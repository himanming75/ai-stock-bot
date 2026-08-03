from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    required = [
        "explainability_engine/io.py",
        "explainability_engine/contributions.py",
        "explainability_engine/risks.py",
        "explainability_engine/comparison.py",
        "explainability_engine/narrative.py",
        "explainability_engine/engine.py",
        "dashboard_v2/explainability_integration.py",
        "tools/run_ai_explainability_v86_25_to_v86_32.py",
        "tools/test_ai_explainability_v86_25_to_v86_32.py",
        "tools/verify_ai_explainability_v86_25_to_v86_32.py",
        "release/v86_25_to_v86_32/README_V86_25_TO_V86_32.md",
    ]
    missing = [item for item in required if not (root / item).exists()]
    if missing:
        for item in missing:
            print(f"MISSING: {item}")
        return 1
    print("V86.25-V86.32 INSTALL CHECK PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
