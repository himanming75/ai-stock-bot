V75.2AM — Offline Paper Fill Receipt Archive Certificate Registry Snapshot Seal Builder

Files:
- tools/offline_paper_fill_receipt_archive_certificate_registry_snapshot_seal_builder_v75_2am.py
- tools/test_offline_paper_fill_receipt_archive_certificate_registry_snapshot_seal_builder_v75_2am.py
- release/v75_2am/config/offline_paper_fill_receipt_archive_certificate_registry_snapshot_seal_config_v75_2am.json

Test:
python -m unittest tools.test_offline_paper_fill_receipt_archive_certificate_registry_snapshot_seal_builder_v75_2am -v

Input:
V75.2AL offline_paper_fill_receipt_archive_certificate_registry_snapshot_verification_v75_2al.json

Safety:
- Offline final immutable evidence seal only
- No settlement, account, broker, network, external submission, or live trading
