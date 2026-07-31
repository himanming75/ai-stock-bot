V75.2AZ — Offline Paper Certificate Registry Snapshot Seal Certificate Archive Verification

Files:
- README_V75_2AZ.txt
- INSTALL_CHECK_V75_2AZ.txt
- tools/registry_snapshot_seal_cert_archive_verifier_v75_2az.py
- tools/test_registry_snapshot_seal_cert_archive_verifier_v75_2az.py
- release/v75_2az/config/registry_snapshot_seal_cert_archive_verification_config_v75_2az.json

Test:
python -m unittest tools.test_registry_snapshot_seal_cert_archive_verifier_v75_2az -v

Purpose:
Verify the V75.2AY certificate archive:
- Archive SHA-256
- Archive manifest
- Archived certified sealed snapshot index
- Archive checks
- Archive ledger
- Deterministic archive ID
- Receipt linkage and notional preservation
- Safety Lock
- Zero settlement and account mutation
- Offline and live-trading prohibitions

Safety:
Offline archive verification only.
No settlement, account mutation, broker routing, network use, or live trading.
