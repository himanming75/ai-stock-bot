# V2.1.22 — Alpaca Paper Bounded Execution Bridge

Base commit: `f72ebec2`

This stage connects the current V2.1.21 READY evidence to the repository's existing Alpaca Paper execution components.

Reused components:
- `paper_autonomous_execution.config.PaperExecutionProfile`
- `paper_autonomous_execution.service.PaperAutonomousExecutionService.preflight`
- `paper_autonomous_execution.signals.select_candidate`
- existing Alpaca Paper adapter with `TradingClient(..., paper=True)`

Safety:
- current V2.1.21 READY evidence required
- current V2.1.17 evidence-key binding required
- canonical confidence >= 0.75
- canonical reward/risk >= 1.0
- existing profile maximum notional $25
- one bridge Paper submission per session
- one-time evidence consumption
- existing open-position guard
- manual PAPER_ONLY arm token required
- explicit `SUBMIT_ALPACA_PAPER_ONCE` phrase required
- installation/tests submit zero Paper orders
- E*TRADE write remains off
- live trading remains off

The default START command is dry-plan only and performs no broker order submission.
