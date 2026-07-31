V75.2AV — Offline Paper Certificate Registry Snapshot Seal Verification

Files:
- README_V75_2AV.txt
- INSTALL_CHECK_V75_2AV.txt
- tools/registry_snapshot_seal_verifier_v75_2av.py
- tools/test_registry_snapshot_seal_verifier_v75_2av.py
- release/v75_2av/config/registry_snapshot_seal_verification_config_v75_2av.json

Test:
python -m unittest tools.test_registry_snapshot_seal_verifier_v75_2av -v

Purpose:
Verify the V75.2AU certificate registry snapshot seal, including:
- Seal SHA-256
- Seal manifest
- Sealed snapshot index
- Seal checks
- Seal ledger
- Deterministic seal ID
- Receipt linkage and notional preservation
- Safety Lock
- Zero settlement and account mutation
- Offline and live-trading prohibitions

Safety:
Offline seal verification only.
No settlement, account mutation, broker routing, network use, or live trading.
