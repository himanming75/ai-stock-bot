# Personal Web Control Center — Existing Backtest Integration

Reuses:
- automated_backtest V98 framework;
- canonical backtest discovery feed;
- provenance/quality gate.

Web features:
- view automated backtest state and aggregation;
- view canonical feed counts;
- view curated provenance/quality counts;
- view top result and rankings;
- refresh the existing derived research feed;
- run the existing V98 automated backtest;
- force rerun the existing V98 automated backtest.

Safety:
- no new backtest engine;
- no new strategy;
- no broker writes;
- no order submission;
- no live trading;
- no external network required by this integration.
