V75.2AI — Offline Paper Fill Receipt Archive Certificate Registry Builder

Files:
- tools/offline_paper_fill_receipt_archive_certificate_registry_builder_v75_2ai.py
- tools/test_offline_paper_fill_receipt_archive_certificate_registry_builder_v75_2ai.py
- release/v75_2ai/config/offline_paper_fill_receipt_archive_certificate_registry_config_v75_2ai.json

Test:
python -m unittest tools.test_offline_paper_fill_receipt_archive_certificate_registry_builder_v75_2ai -v

Input:
V75.2AH offline_paper_fill_receipt_archive_certificate_verification_v75_2ah.json

Safety:
- Offline informational registry only
- No settlement, account, broker, network, external submission, or live trading
