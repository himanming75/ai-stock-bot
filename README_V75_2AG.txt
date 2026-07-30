V75.2AG — Offline Paper Fill Receipt Archive Certificate Builder

Files:
- tools/offline_paper_fill_receipt_archive_certificate_builder_v75_2ag.py
- tools/test_offline_paper_fill_receipt_archive_certificate_builder_v75_2ag.py
- release/v75_2ag/config/offline_paper_fill_receipt_archive_certificate_config_v75_2ag.json

Test:
python -m unittest tools.test_offline_paper_fill_receipt_archive_certificate_builder_v75_2ag -v

Input:
V75.2AF offline_paper_fill_receipt_archive_verification_v75_2af.json

Safety:
- Informational offline archive certificate only
- No settlement execution
- No position, cash, or portfolio changes
- No broker, network, external submission, or live trading
