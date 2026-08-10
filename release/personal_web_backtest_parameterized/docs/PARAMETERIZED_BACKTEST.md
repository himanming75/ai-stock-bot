# Personal Web Parameterized Backtest

Extends the existing Backtest tab with selectors for the existing V98 policy:
- strategy;
- dataset;
- window;
- force/no-force cache behavior.

Execution design:
1. Read the original V98 policy.
2. Validate selected IDs against that policy.
3. Write a temporary filtered policy.
4. Run the existing V98 automated backtest engine.
5. Restore the original policy in a finally block.
6. Restore the pre-existing standard V98 result file.
7. Save the selected-run result separately under runtime/web_backtest_runs.

This preserves the canonical V98 policy/result while allowing one-off research runs.

No new strategy, broker write, order submission, external network, or Live trading is added.
