# Paper Automation Controller and Scheduler

The controller joins the validated read-only pipeline into scheduled market
cycles:

1. Paper market clock
2. Market-data collection
3. Market Intelligence
4. AI Decision
5. Strategy/Risk/Portfolio Bridge
6. Execution Plan
7. Order Ticket generation
8. Checkpoint and append-only Cycle Ledger

Safety model:

- Actual submission is hard-disabled in Controller V1.
- Existing token-and-nonce scripts remain the only allowed Paper write path.
- Live submission remains permanently zero.
- A single-instance lock prevents duplicate controllers.
- Atomic checkpoints allow restart from the next cycle.
- Market-close detection stops the session.
- Cycle errors stop the controller instead of continuing blindly.

Profiles:

- DEVELOPMENT: no network and one cycle
- READ_ONLY: full read-only market pipeline
- PAPER_GATED: same as read-only; future submission still requires a separate
  explicit approval workflow
