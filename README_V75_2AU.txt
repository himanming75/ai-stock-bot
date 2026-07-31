V75.2AU — Offline Paper Certificate Registry Snapshot Seal Builder

Files:
- README_V75_2AU.txt
- INSTALL_CHECK_V75_2AU.txt
- tools/registry_snapshot_seal_builder_v75_2au.py
- tools/test_registry_snapshot_seal_builder_v75_2au.py
- release/v75_2au/config/registry_snapshot_seal_config_v75_2au.json

Test:
python -m unittest tools.test_registry_snapshot_seal_builder_v75_2au -v

Purpose:
Seal the verified V75.2AT certificate registry snapshot and generate:
- Seal manifest
- Sealed snapshot index
- Seal checks
- Seal ledger
- SHA-256 evidence

Safety:
Offline evidence sealing only.
No settlement, account mutation, broker routing, network use, or live trading.
