V75.2BA — Offline Paper Certificate Registry Snapshot Seal Certificate Archive Seal Builder

Files:
- README_V75_2BA.txt
- INSTALL_CHECK_V75_2BA.txt
- tools/registry_snapshot_seal_cert_archive_seal_builder_v75_2ba.py
- tools/test_registry_snapshot_seal_cert_archive_seal_builder_v75_2ba.py
- release/v75_2ba/config/registry_snapshot_seal_cert_archive_seal_config_v75_2ba.json

Test:
python -m unittest tools.test_registry_snapshot_seal_cert_archive_seal_builder_v75_2ba -v

Purpose:
Create an immutable archive seal from the verified V75.2AZ archive:
- Archive seal manifest
- Sealed archived certified snapshot index
- Archive seal checks
- Archive seal ledger
- SHA-256 evidence
- Deterministic archive seal ID
- Receipt linkage and notional preservation

Safety:
Offline archive seal creation only.
No settlement, account mutation, broker routing, network use, or live trading.
