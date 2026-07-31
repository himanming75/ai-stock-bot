V76.3 Multi-Capability Behavioral Verification

Purpose
-------
Execute representative existing behavioral tests for 11 core capabilities:

- Market Data Pipeline
- Model Inference Engine
- Strategy Engine
- Backtest Engine
- Risk Engine
- Portfolio Manager
- Order Lifecycle Simulator
- Paper Trading Adapter
- Reconciliation Engine
- Dashboard and Reporting
- Audit and Evidence Layer

A PASS requires every required capability test to exist and exit with code 0.

Safety
------
The verifier runs local Python subprocesses only. It sets environment flags that
disable network, broker connection, order submission, and live trading. The
verifier itself does not mutate trading cash, positions, portfolios, or source
files. Existing tests are expected to enforce their own safety boundaries.

Test
----
python -m unittest tools.test_multi_capability_behavioral_verification_v76_3 -v

Run
---
python tools/multi_capability_behavioral_verification_v76_3.py `
  --repository-root . `
  --config release/v76_3/config/multi_capability_behavioral_verification_config_v76_3.json `
  --output-dir release/v76_3/output

Do not commit V76.3 when the run result is FAIL. Send the complete console output
for diagnosis first.
