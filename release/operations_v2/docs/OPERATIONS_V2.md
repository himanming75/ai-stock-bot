# Operations V2 Mega Bundle

This package adds validation-independent operator tooling:

- Dashboard 4.0 read-only interface;
- data quality audit;
- historical replay simulator;
- configuration diff and protected-key audit;
- incident snapshot bundle;
- daily operator report;
- CSV and JSON export;
- local read-only API endpoints.

The historical replay creates preview actions only. It never creates or submits
an order and never modifies the portfolio.

The configuration auditor detects protected safety changes without applying
them.

No market network, broker network, broker write, automatic recovery, automatic
order replay, or order submission occurs.
