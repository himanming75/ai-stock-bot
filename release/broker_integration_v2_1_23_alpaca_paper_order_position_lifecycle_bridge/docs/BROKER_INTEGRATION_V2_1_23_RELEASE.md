# V2.1.23 — Alpaca Paper Order + Position Lifecycle Bridge

Base commit: `78e27cff`.

This stage reuses the existing `PaperOrderLifecycleMonitor` to reconcile a V2.1.22 submitted Alpaca Paper order by `client_order_id`. The existing monitor reads order status, fills, account equity/cash, clock, and the matching Paper position and performs no broker write. It also reuses `paper_position_lifecycle.rules.evaluate_exit` for a read-only HOLD/EXIT decision using the existing lifecycle policy.

Important: V2.1.23 does **not** submit an exit order. It only proves the order/position lifecycle and produces `POSITION_HOLD_READ_ONLY` or `POSITION_EXIT_READY_READ_ONLY`.

Install/tests use no broker network and submit zero orders. Actual monitor mode is Paper read-only.
