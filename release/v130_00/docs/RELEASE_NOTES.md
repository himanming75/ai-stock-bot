# Release Notes

V129.01–V130.00 adds bounded lifecycle monitoring and a persistent JSONL observation ledger.

While the existing AAPL order remains ACCEPTED, the expected result is `CONTINUE_TRACKING` and `new_order_allowed=false`. A terminal transition is never manufactured; it must be observed from the actual broker.
