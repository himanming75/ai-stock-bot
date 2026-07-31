V75.2AY — Offline Paper Certificate Registry Snapshot Seal Certificate Archive Builder

Files:
- README_V75_2AY.txt
- INSTALL_CHECK_V75_2AY.txt
- tools/registry_snapshot_seal_cert_archive_builder_v75_2ay.py
- tools/test_registry_snapshot_seal_cert_archive_builder_v75_2ay.py
- release/v75_2ay/config/registry_snapshot_seal_cert_archive_config_v75_2ay.json

Test:
python -m unittest tools.test_registry_snapshot_seal_cert_archive_builder_v75_2ay -v

Purpose:
Create an immutable archive from the verified V75.2AX certificate:
- Archive manifest
- Archived certified sealed snapshot index
- Archive checks
- Archive ledger
- SHA-256 evidence
- Deterministic archive ID
- Receipt linkage and notional preservation

Safety:
Offline archive creation only.
No settlement, account mutation, broker routing, network use, or live trading.
