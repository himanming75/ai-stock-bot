# V139.09 Active Order Lifecycle Monitor

This stage monitors local lifecycle snapshots after V139.08 reports `ORDER_ACCEPTED`.

Supported active states:

- NEW
- ACCEPTED
- PENDING_NEW
- PARTIALLY_FILLED
- PENDING_CANCEL
- PENDING_REPLACE

Supported terminal states:

- FILLED
- CANCELED / CANCELLED
- EXPIRED
- REJECTED

Safety checks include:

- Client and broker order identity
- Filled quantity range
- FILLED quantity consistency
- Partial-fill consistency
- Filled quantity regression
- Order-status regression
- Terminal-state immutability

Every verified snapshot updates the local monitor state and previous-state checkpoint.
No broker network request or order submission is performed.
