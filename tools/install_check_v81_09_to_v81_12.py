from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    "shadow_trading/portfolio_pnl_v81_09_12.py",
    "dashboard/shadow_portfolio_integration.py",
    "tools/run_shadow_portfolio_v81_09_to_v81_12.py",
    "tools/test_shadow_portfolio_v81_09_to_v81_12.py",
    "tools/install_check_v81_09_to_v81_12.py",
    "tools/verify_shadow_portfolio_v81_09_to_v81_12.py",
    "RUN_V81_09_TO_V81_12_SHADOW_PORTFOLIO.ps1",
    "RUN_V81_09_TO_V81_12_TEST_AND_VERIFY.ps1",
    "V81_09_TO_V81_12_MANIFEST.json",
]
missing = [item for item in REQUIRED if not (ROOT / item).exists()]
if missing:
    raise SystemExit("INSTALL_CHECK=FAIL missing=" + ",".join(missing))
print("INSTALL_CHECK=PASS")
