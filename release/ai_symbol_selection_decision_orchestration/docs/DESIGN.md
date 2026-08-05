# AI Symbol Selection and Decision Orchestration

This development-only stage consumes the Market Intelligence Data Fusion
snapshot and produces a deterministic AI decision snapshot.

Included:

- policy-controlled symbol eligibility
- score and confidence gates
- trade-bias gate
- market risk-mode gate
- ranked candidate selection
- maximum symbol count
- risk-mode portfolio budget
- per-symbol allocation cap
- strategy route assignment
- explainable reason codes and blockers
- dashboard-ready output

No external network, broker read, broker write, paper order, or live order is
performed.
