V75.2AS — Offline Paper Certificate Registry Snapshot Builder

Files:
- README_V75_2AS.txt
- INSTALL_CHECK_V75_2AS.txt
- tools/registry_snapshot_builder_v75_2as.py
- tools/test_registry_snapshot_builder_v75_2as.py
- release/v75_2as/config/registry_snapshot_config_v75_2as.json

Test:
python -m unittest tools.test_registry_snapshot_builder_v75_2as -v

Safety:
Offline snapshot only.
No settlement, account mutation, broker routing, network use, or live trading.
