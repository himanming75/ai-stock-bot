# Current Strategy vs Backtest Candidate vs AI

Adds a research-only comparison panel to the existing Backtest tab.

Shows:
- current saved execution strategy/risk snapshot;
- latest selected Backtest candidate;
- AI model health/research readiness;
- a conservative recommendation state.

Decision policy:
- KEEP_CURRENT_WAIT while AI comparison is not ready or model health is not GREEN;
- CANDIDATE_READY_FOR_MANUAL_RESEARCH_REVIEW only when:
  candidate exists + AI research comparison is allowed + model health is GREEN.

Never changes strategy, threshold, risk, Paper execution, or Live execution automatically.
