V75.2AW — Offline Paper Certificate Registry Snapshot Seal Certificate Builder

Files:
- README_V75_2AW.txt
- INSTALL_CHECK_V75_2AW.txt
- tools/registry_snapshot_seal_cert_builder_v75_2aw.py
- tools/test_registry_snapshot_seal_cert_builder_v75_2aw.py
- release/v75_2aw/config/registry_snapshot_seal_cert_config_v75_2aw.json

Test:
python -m unittest tools.test_registry_snapshot_seal_cert_builder_v75_2aw -v

Purpose:
Create a certificate from the verified V75.2AV registry snapshot seal:
- Certificate manifest
- Certified sealed snapshot index
- Certificate checks
- Certificate ledger
- SHA-256 evidence
- Deterministic certificate ID
- Receipt linkage and notional preservation

Safety:
Offline certificate creation only.
No settlement, account mutation, broker routing, network use, or live trading.
