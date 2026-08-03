from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    required = [
        "validation_v2/io.py",
        "validation_v2/walk_forward.py",
        "validation_v2/stress.py",
        "validation_v2/monte_carlo.py",
        "validation_v2/overfit.py",
        "validation_v2/engine.py",
        "dashboard_v2/validation_v2_integration.py",
        "tools/run_walk_forward_stress_v87_09_to_v87_16.py",
        "tools/test_walk_forward_stress_v87_09_to_v87_16.py",
        "tools/verify_walk_forward_stress_v87_09_to_v87_16.py",
        "release/v87_09_to_v87_16/input/walk_forward_stress_policy.json",
        "release/v87_09_to_v87_16/README_V87_09_TO_V87_16.md",
    ]
    missing = [item for item in required if not (root / item).exists()]
    if missing:
        for item in missing:
            print(f"MISSING: {item}")
        return 1
    print("V87.09-V87.16 INSTALL CHECK PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
