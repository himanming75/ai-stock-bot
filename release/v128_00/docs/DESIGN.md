# V127.01–V128.00 Existing Paper Order Lifecycle Tracking

Tracks the recovered Alpaca Paper order by `client_order_id` using GET only.

- Active: accepted, new, pending_new, pending_replace, held, calculated
- Partial: partially_filled
- Terminal success: filled
- Terminal without active remainder: canceled, rejected, expired, done_for_day, replaced
- Unknown: Safe Mode

New autonomous orders remain blocked until the tracked order is terminal.
