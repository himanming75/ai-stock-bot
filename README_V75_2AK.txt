V75.2AK — Offline Paper Fill Receipt Archive Certificate Registry Snapshot Builder

Files:
- tools/offline_paper_fill_receipt_archive_certificate_registry_snapshot_builder_v75_2ak.py
- tools/test_offline_paper_fill_receipt_archive_certificate_registry_snapshot_builder_v75_2ak.py
- release/v75_2ak/config/offline_paper_fill_receipt_archive_certificate_registry_snapshot_config_v75_2ak.json

Test:
python -m unittest tools.test_offline_paper_fill_receipt_archive_certificate_registry_snapshot_builder_v75_2ak -v

Input:
V75.2AJ offline_paper_fill_receipt_archive_certificate_registry_verification_v75_2aj.json

Safety:
- Offline immutable evidence snapshot only
- No settlement, account, broker, network, external submission, or live trading
