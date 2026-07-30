V75.2AD — Offline Paper Fill Receipt Verification

Files:
- tools/offline_paper_fill_receipt_verifier_v75_2ad.py
- tools/test_offline_paper_fill_receipt_verifier_v75_2ad.py
- release/v75_2ad/config/offline_paper_fill_receipt_verification_config_v75_2ad.json

Test:
python -m unittest tools.test_offline_paper_fill_receipt_verifier_v75_2ad -v

Input:
V75.2AC offline_paper_fill_receipt_batch_v75_2ac.json

Safety:
- Verification only
- No settlement
- No position, cash, or portfolio update
- No broker, network, external submission, or live trading
