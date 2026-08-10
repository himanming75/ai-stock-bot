# AI Trading Engine V2.2.6 — Champion vs Challenger Outcome Comparator

Base commit: `3d675bc0`.

## Purpose

Bind actual completed Paper outcomes from V2.2.2 to the exact V2.2.5
Champion-vs-Challenger shadow comparison that used the same pre-entry feature
snapshot.

## Exact binding

V2.2.6 requires:
- exact V2.2.1 `snapshot_id`;
- same symbol;
- explicit V2.2.5 `comparison_id`;
- explicit Challenger policy ID.

This prevents a later or unrelated shadow policy comparison from being used
for an earlier actual trade.

## Realized comparison

For each Challenger:

### BOTH
The actual Champion trade also passed the Challenger threshold.
Its realized fill-based outcome can therefore be counted as overlap evidence.

### CHAMPION_ONLY
The actual Champion trade would have been rejected by that Challenger.
The realized outcome shows whether the Challenger would have filtered a winner
or a loser.

### CHALLENGER_ONLY
The signal was not executed by the current Champion, so no realized trade
outcome exists. V2.2.6 records only the number of these shadow opportunities.

V2.2.6 never fabricates counterfactual P&L.

## Metrics

For realized BOTH and CHAMPION_ONLY groups:
- trades / wins / losses / flats;
- win rate;
- gross fill-based P&L before fees;
- average P&L;
- average return;
- profit factor;
- expectancy.

Minimum promotion-evidence sample: 5 realized outcomes per Challenger.

## Outputs

- bound policy outcome JSONL ledger;
- unbound outcome JSONL ledger;
- latest bound record;
- JSON comparison report;
- Markdown comparison report.

## Safety

- Counterfactual P&L fabricated: FALSE
- Challenger execution: DISABLED
- Automatic promotion: DISABLED
- Execution selector modified: FALSE
- Broker network: OFF
- Paper orders: 0
- Live orders: 0
- Live trading: LOCKED
