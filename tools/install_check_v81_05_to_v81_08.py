from pathlib import Path
r=Path(__file__).resolve().parents[1]; req=["shadow_trading/execution_engine_v81_05_08.py","dashboard/shadow_execution_integration.py","tools/run_shadow_execution_v81_05_to_v81_08.py","tools/test_shadow_execution_v81_05_to_v81_08.py","tools/verify_shadow_execution_v81_05_to_v81_08.py","RUN_V81_05_TO_V81_08_SHADOW_EXECUTION.ps1","RUN_V81_05_TO_V81_08_TEST_AND_VERIFY.ps1","V81_05_TO_V81_08_MANIFEST.json"]; m=[x for x in req if not(r/x).exists()];
if m: raise SystemExit("INSTALL_CHECK=FAIL "+",".join(m))
print("INSTALL_CHECK=PASS")
