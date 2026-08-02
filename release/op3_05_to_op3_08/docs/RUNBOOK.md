# Single Controlled Paper Order Runbook

1. Run test and verify. This never submits an order.
2. Copy and review the execution policy.
3. Confirm OP3.01-OP3.04 result still has `manual_approval_ready=true`.
4. Run the preview and review symbol, side, quantity, notional and client ID.
5. Check the Alpaca Paper dashboard and confirm Paper credentials.
6. Only when intentionally submitting one simulated order, use all explicit
   switches and the exact submission phrase.
7. Never change the Paper base URL to the Live base URL.
