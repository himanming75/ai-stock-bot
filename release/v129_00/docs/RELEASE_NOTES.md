# Release Notes

V128.01–V129.00 adds a GET-only transition gate between lifecycle tracking and fill/portfolio reconciliation.

Because the current actual order is still `ACCEPTED`, the default expected state remains `WAITING_ACTIVE_ORDER`. The system will not manufacture a fill or unlock a new order prematurely.
