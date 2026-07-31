V75.2BB — Offline Paper Certificate Registry Snapshot Seal Certificate Archive Seal Verification

Files:
- README_V75_2BB.txt
- INSTALL_CHECK_V75_2BB.txt
- tools/registry_snapshot_seal_cert_archive_seal_verifier_v75_2bb.py
- tools/test_registry_snapshot_seal_cert_archive_seal_verifier_v75_2bb.py
- release/v75_2bb/config/registry_snapshot_seal_cert_archive_seal_verification_config_v75_2bb.json

Test:
python -m unittest tools.test_registry_snapshot_seal_cert_archive_seal_verifier_v75_2bb -v

Purpose:
Verify the V75.2BA archive seal:
- Archive seal SHA-256
- Archive seal manifest
- Sealed archived certified snapshot index
- Archive seal checks
- Archive seal ledger
- Deterministic archive seal ID
- Receipt linkage and notional preservation
- Safety Lock
- Zero settlement and account mutation
- Offline and live-trading prohibitions

Safety:
Offline archive seal verification only.
No settlement, account mutation, broker routing, network use, or live trading.
