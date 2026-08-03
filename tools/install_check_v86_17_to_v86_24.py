from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    required = [
        "portfolio_scoring/models.py",
        "portfolio_scoring/scoring.py",
        "portfolio_scoring/allocation.py",
        "portfolio_scoring/diversification.py",
        "portfolio_scoring/engine.py",
        "portfolio_scoring/io.py",
        "dashboard_v2/portfolio_scoring_integration.py",
        "tools/run_portfolio_scoring_v86_17_to_v86_24.py",
        "tools/test_portfolio_scoring_v86_17_to_v86_24.py",
        "tools/verify_portfolio_scoring_v86_17_to_v86_24.py",
        "release/v86_17_to_v86_24/input/portfolio_candidates.json",
        "release/v86_17_to_v86_24/README_V86_17_TO_V86_24.md",
    ]
    missing = [item for item in required if not (root / item).exists()]
    if missing:
        for item in missing:
            print(f"MISSING: {item}")
        return 1
    print("V86.17-V86.24 INSTALL CHECK PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
