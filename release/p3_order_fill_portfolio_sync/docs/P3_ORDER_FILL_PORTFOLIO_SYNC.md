# P3 Order / Fill / Portfolio Sync

P3 connects the existing lifecycle and portfolio-recovery architecture to the
canonical broker state established in P1.

Included:

- known Alpaca order-state normalization;
- partial and full Fill observation;
- deterministic Fill keys;
- duplicate Fill prevention;
- Order State Ledger;
- Fill Ledger;
- broker/local position reconciliation;
- broker/local cash and Equity reconciliation;
- unknown-state blocking;
- Fail-Closed new-order permission;
- recovery checkpoint generation;
- restart-safe registries.

P3 installation and qualification use Offline fixtures and submit zero orders.
Actual broker synchronization will be validated after P2 successfully submits
an Alpaca Paper order.
