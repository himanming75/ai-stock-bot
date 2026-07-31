V76.4B Deterministic ML Input and Model Repair

Changes:
- RandomForest uses one thread and shared random seed 42.
- Python and NumPy RNG states reset for every prediction.
- yfinance download uses threads=False.
- Market rows are sorted and duplicate dates removed.
- test_ml.py creates one lossless CSV snapshot and reuses it.

Snapshot:
release/v76_4/runtime_cache/AAPL_5y_1d_v76_4b.csv

Apply:
python tools/apply_deterministic_ml_repair_v76_4b.py --repository-root .

Test:
python -m unittest tools.test_apply_deterministic_ml_repair_v76_4b -v

Clear old snapshot:
Remove-Item release\v76_4\runtime_cache\AAPL_5y_1d_v76_4b.csv -ErrorAction SilentlyContinue

Run twice:
python test_ml.py
python test_ml.py

Full verification:
python tools/advanced_validation_behavioral_verification_v76_4.py `
  --repository-root . `
  --config release/v76_4/config/advanced_validation_behavioral_verification_config_v76_4.json `
  --output-dir release/v76_4/output

Do not stage backup files or release/v76_4/runtime_cache/.
