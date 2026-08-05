# Paper Order Lifecycle Monitor

This stage performs read-only monitoring of an order already submitted during
P3 Micro Paper validation.

It reads the client_order_id from the P3 result and repeatedly checks:

- broker order ID
- order status transitions
- filled quantity
- average fill price
- submitted, filled, canceled, and failed timestamps
- account equity and cash
- matching position
- market clock

Terminal statuses include filled, canceled, expired, rejected, done_for_day,
and replaced.

For a filled order, PASS requires:

- terminal status reached
- broker order ID matches the original P3 submission
- positive filled quantity
- average fill price present
- matching position present

The lifecycle monitor is read-only. It never creates, replaces, or cancels an
order.
