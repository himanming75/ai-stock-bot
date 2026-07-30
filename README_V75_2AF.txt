V75.2AF — Offline Paper Fill Receipt Archive Package Verification

Files:
- tools/offline_paper_fill_receipt_archive_verifier_v75_2af.py
- tools/test_offline_paper_fill_receipt_archive_verifier_v75_2af.py
- release/v75_2af/config/offline_paper_fill_receipt_archive_verification_config_v75_2af.json

Test:
python -m unittest tools.test_offline_paper_fill_receipt_archive_verifier_v75_2af -v

Input:
V75.2AE offline_paper_fill_receipt_archive_package_v75_2ae.json

Safety:
- Independent archive verification only
- No settlement execution
- No position, cash, or portfolio changes
- No broker, network, external submission, or live trading
