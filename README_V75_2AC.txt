V75.2AC — Offline Paper Fill Receipt Builder

Copy these files into the repository root, preserving paths:
- tools/offline_paper_fill_receipt_builder_v75_2ac.py
- tools/test_offline_paper_fill_receipt_builder_v75_2ac.py
- release/v75_2ac/config/offline_paper_fill_receipt_builder_config_v75_2ac.json

Test:
python -m unittest tools.test_offline_paper_fill_receipt_builder_v75_2ac -v

Input:
V75.2AB offline_paper_fill_simulation_execution_verification_v75_2ab.json

Example:
python tools/offline_paper_fill_receipt_builder_v75_2ac.py ^
  --input release/v75_2ab/verification/offline_paper_fill_simulation_execution_verification_v75_2ab.json ^
  --config release/v75_2ac/config/offline_paper_fill_receipt_builder_config_v75_2ac.json ^
  --output-dir release/v75_2ac/receipts

Safety guarantees:
- Offline receipt artifacts only
- No settlement execution
- No broker or network usage
- No live trading
- No position, cash, or portfolio update
