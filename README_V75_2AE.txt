V75.2AE — Offline Paper Fill Receipt Archive Package Builder

Files:
- tools/offline_paper_fill_receipt_archive_builder_v75_2ae.py
- tools/test_offline_paper_fill_receipt_archive_builder_v75_2ae.py
- release/v75_2ae/config/offline_paper_fill_receipt_archive_config_v75_2ae.json

Test:
python -m unittest tools.test_offline_paper_fill_receipt_archive_builder_v75_2ae -v

Input:
V75.2AD offline_paper_fill_receipt_verification_v75_2ad.json

Safety:
- Archive artifact creation only
- No settlement execution
- No position, cash, or portfolio changes
- No broker, network, external submission, or live trading
