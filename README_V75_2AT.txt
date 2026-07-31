V75.2AT — Offline Paper Certificate Registry Snapshot Verification

Files:
- README_V75_2AT.txt
- INSTALL_CHECK_V75_2AT.txt
- tools/registry_snapshot_verifier_v75_2at.py
- tools/test_registry_snapshot_verifier_v75_2at.py
- release/v75_2at/config/registry_snapshot_verification_config_v75_2at.json

Test:
python -m unittest tools.test_registry_snapshot_verifier_v75_2at -v

Purpose:
Verify the V75.2AS certificate registry snapshot, including:
- Snapshot SHA-256
- Snapshot manifest
- Snapshot index
- Snapshot checks
- Snapshot ledger
- Deterministic snapshot ID
- Receipt linkage and notional preservation
- Safety Lock
- Zero settlement and account mutation
- Offline and live-trading prohibitions

Safety:
No settlement, account mutation, broker routing, network use, or live trading.
