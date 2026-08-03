from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    required = [
        "paper_orchestrator/io.py",
        "paper_orchestrator/lock.py",
        "paper_orchestrator/state.py",
        "paper_orchestrator/steps.py",
        "paper_orchestrator/engine.py",
        "dashboard_v2/paper_orchestrator_integration.py",
        "tools/run_paper_orchestrator_v88_09_to_v88_16.py",
        "tools/test_paper_orchestrator_v88_09_to_v88_16.py",
        "tools/verify_paper_orchestrator_v88_09_to_v88_16.py",
        "release/v88_09_to_v88_16/README_V88_09_TO_V88_16.md",
    ]
    missing = [item for item in required if not (root / item).exists()]
    if missing:
        for item in missing:
            print(f"MISSING: {item}")
        return 1
    print("V88.09-V88.16 INSTALL CHECK PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
