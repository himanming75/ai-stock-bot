from pathlib import Path
required=[
'autonomous_paper_runtime/actual_terminal_monitor_continuation.py',
'tools/run_actual_terminal_monitor_continuation_v139_01.py',
'tools/test_actual_terminal_monitor_continuation_v139_01.py',
'tools/verify_actual_terminal_monitor_continuation_v139_01.py',
'RUN_V139_01_ACTUAL_TERMINAL_MONITOR_CONTINUATION.ps1']
missing=[p for p in required if not Path(p).is_file()]
if missing: raise SystemExit('MISSING: '+', '.join(missing))
print('INSTALL_CHECK=PASS')
