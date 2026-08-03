from pathlib import Path
root=Path(__file__).resolve().parents[1]
R=["shadow_trading/foundation_v81.py","dashboard/shadow_trading_integration.py","tools/run_shadow_trading_foundation_v81_01_to_v81_04.py","tools/test_shadow_trading_foundation_v81_01_to_v81_04.py","tools/install_check_v81_01_to_v81_04.py","tools/verify_shadow_trading_foundation_v81_01_to_v81_04.py","RUN_V81_01_TO_V81_04_SHADOW_FOUNDATION.ps1","RUN_V81_01_TO_V81_04_TEST_AND_VERIFY.ps1","V81_01_TO_V81_04_MANIFEST.json"]
m=[x for x in R if not(root/x).exists()]
if m: raise SystemExit("INSTALL_CHECK=FAIL missing="+",".join(m))
print("INSTALL_CHECK=PASS")
