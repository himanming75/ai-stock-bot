V76.2 Targeted Behavioral Capability Verification

Target: FEATURE_PIPELINE

This stage executes the repository's existing feature-engineering,
normalization, and feature-selection behavioral tests in isolated Python
subprocesses. It records script hashes, exit codes, duration, stdout, stderr,
timeouts, and a deterministic evidence hash.

It does not modify the tested source files and does not authorize network,
broker, orders, cash, positions, portfolio changes, or live trading.

Test:
python -m unittest tools.test_targeted_behavioral_capability_verification_v76_2 -v

Run:
python tools/targeted_behavioral_capability_verification_v76_2.py `
  --repository-root . `
  --config release/v76_2/config/targeted_behavioral_capability_verification_config_v76_2.json `
  --output-dir release/v76_2/output

A PASS requires all three required existing feature-pipeline scripts to exit 0.
