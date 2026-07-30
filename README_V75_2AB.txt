V75.2AB — Offline Paper Fill Simulation Execution Verification

Copy these files into the repository root, preserving paths:
- tools/offline_paper_fill_simulation_execution_verifier_v75_2ab.py
- tools/test_offline_paper_fill_simulation_execution_verifier_v75_2ab.py
- release/v75_2ab/config/offline_paper_fill_simulation_execution_verification_config_v75_2ab.json

Test:
python -m unittest tools.test_offline_paper_fill_simulation_execution_verifier_v75_2ab -v

Verify V75.2AA output:
python tools/offline_paper_fill_simulation_execution_verifier_v75_2ab.py \
  --input release/v75_2aa/execution/offline_paper_fill_simulation_execution_v75_2aa.json \
  --config release/v75_2ab/config/offline_paper_fill_simulation_execution_verification_config_v75_2ab.json \
  --output-dir release/v75_2ab/verification

Safety guarantees:
- Verification only; no Fill Object creation
- No broker connection or routing
- No network use
- No live trading
- No position, cash, or portfolio update
