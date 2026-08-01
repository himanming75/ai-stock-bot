# V110.01–V111.00 Controlled Alpaca Paper Read Validation

This release adds two paths:

1. Standard offline fixture validation:
   - no real credentials
   - no external network
   - five simulated GET requests
   - zero write requests

2. Explicit actual Paper read-only validation:
   - exact opt-in variable required
   - exact confirmation phrase required
   - Paper credentials required
   - Account, Clock, Positions, Open Orders, and Closed Orders
   - write network remains disabled

The actual runner cannot submit or cancel orders.
