V75.2AX — Offline Paper Certificate Registry Snapshot Seal Certificate Verification

Files:
- README_V75_2AX.txt
- INSTALL_CHECK_V75_2AX.txt
- tools/registry_snapshot_seal_cert_verifier_v75_2ax.py
- tools/test_registry_snapshot_seal_cert_verifier_v75_2ax.py
- release/v75_2ax/config/registry_snapshot_seal_cert_verification_config_v75_2ax.json

Test:
python -m unittest tools.test_registry_snapshot_seal_cert_verifier_v75_2ax -v

Purpose:
Verify the V75.2AW registry snapshot seal certificate:
- Certificate SHA-256
- Certificate manifest
- Certified sealed snapshot index
- Certificate checks
- Certificate ledger
- Deterministic certificate ID
- Receipt linkage and notional preservation
- Safety Lock
- Zero settlement and account mutation
- Offline and live-trading prohibitions

Safety:
Offline certificate verification only.
No settlement, account mutation, broker routing, network use, or live trading.
