V75.2AA — Offline Paper Fill Simulation Executor

Copy these files into the repository root, preserving paths:
- tools/offline_paper_fill_simulation_executor_v75_2aa.py
- tools/test_offline_paper_fill_simulation_executor_v75_2aa.py
- release/v75_2aa/config/offline_paper_fill_simulation_executor_config_v75_2aa.json

Test:
python -m unittest tools.test_offline_paper_fill_simulation_executor_v75_2aa -v

Execute against V75.2Z authorization output:
python tools/offline_paper_fill_simulation_executor_v75_2aa.py \
  --input release/v75_2z/authorization/offline_paper_fill_simulation_authorization_v75_2z.json \
  --config release/v75_2aa/config/offline_paper_fill_simulation_executor_config_v75_2aa.json \
  --output-dir release/v75_2aa/execution

Safety guarantees:
- No broker connection or routing
- No network use
- No live trading
- No position, cash, or portfolio update
- Creates offline Fill Object artifacts only
