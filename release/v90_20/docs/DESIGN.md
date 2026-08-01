# V90.01-V90.20 Design

This stage introduces an opt-in, read-only Alpaca Paper connection for account, clock, and calendar endpoints.

Safety:
- GET only
- paper endpoint only
- account, clock, and calendar allowlist
- order endpoints blocked
- zero write capabilities
- scheduler, runtime, auto execution, Paper order submission, and Live trading disabled
- offline fixture is the default execution mode
