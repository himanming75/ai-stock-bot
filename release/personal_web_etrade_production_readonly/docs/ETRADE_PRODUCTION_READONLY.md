# E*TRADE Production Read-Only Control Center

Purpose:
Connect the existing Personal Control Center to the user's real E*TRADE account
for READ-ONLY account, positions, and orders visibility.

Reuse:
- broker_integration_v1 ETradeOAuthFlow V2;
- existing multi_broker_etrade credential/adapter stack;
- existing tools/run_etrade_production_read_explicit.py runner.

Session model:
- Consumer key/secret are supplied by the user's PowerShell environment.
- OAuth request/access token flow runs interactively.
- Access token/secret are placed only in the Control Center process environment.
- Token values are not displayed and are not written by this integration.
- Stopping that 8767 process discards the in-memory session.

Web action:
- "Read Actual E*TRADE Account" invokes the existing Production read-only runner.
- The resulting account/positions/orders snapshot is displayed locally on 127.0.0.1:8767.

Safety:
- Production order POST is not exposed.
- Cancel/replace is not exposed.
- Live-trading enable is not exposed.
- Broker write = false.
- Order submission = false.
- Live orders submitted = 0.
