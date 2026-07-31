V76.4 Advanced Validation Behavioral Verification

Purpose
-------
Run all 11 representative core capability tests twice and verify:

1. Every execution exits successfully.
2. Normalized stdout/stderr and exit codes are repeatable across rounds.
3. Git-tracked repository files are byte-for-byte unchanged before and after.
4. Network, broker, order submission, and live approval remain disabled.

This is still offline paper-system validation. It does not authorize live trading.

Test
----
python -m unittest tools.test_advanced_validation_behavioral_verification_v76_4 -v

Run
---
python tools/advanced_validation_behavioral_verification_v76_4.py `
  --repository-root . `
  --config release/v76_4/config/advanced_validation_behavioral_verification_config_v76_4.json `
  --output-dir release/v76_4/output

The run executes 11 scenarios twice, for 22 total child-process executions.
Do not commit if status is FAIL.
