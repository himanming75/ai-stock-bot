# Broker Integration V2.1.4 — E*TRADE Sandbox Bounded Multi-Cycle Controller

Base commit: `cbdcfaf1`

## Purpose
Add bounded repeated Sandbox execution on top of the proven V2.1.3 `run_once()` lifecycle.

## Reuse / no duplication
Reuses:
- V2.1.3 `ETradeSandboxAutonomousCycle.run_once()`
- V2.1 Preview/Place pipeline
- V2.1.2 JSONL ledger
- V2.1.2 Orders reader and reconciliation
- canonical V77.1 BrokerOrderRequest
- existing OAuth flow and transports

No replacement order engine, ledger, or reconciliation engine is created.

## Hard limits
- Maximum cycles: 3
- Default cooldown: 30 seconds
- Maximum configurable cooldown: 300 seconds
- Duplicate signal guard: ON
- Stop on first cycle error: ON
- Kill switch file checked before every new cycle
- Unlimited loop: prohibited

## Kill switch
Create:
`runtime/etrade_sandbox_multi_cycle_v2_1_4/KILL_SWITCH`

Or run:
`ENABLE_ETRADE_SANDBOX_KILL_SWITCH_V2_1_4.ps1`

Remove it with:
`DISABLE_ETRADE_SANDBOX_KILL_SWITCH_V2_1_4.ps1`

## Safety
Sandbox only. PROD order POST remains locked. Live trading remains locked.
No real-money or profitability validation is implied by Sandbox execution.
