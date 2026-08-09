# V2.1.32 — Daily Performance + Operation Report

Base commit: `0f4651d5`.

## Purpose

V2.1.32 is the final reporting layer before actual regular-market Paper validation.

It does not add execution logic.

## Sources reused

- V2.1.27 completed round-trip ledger
- V2.1.29 risk ledger
- V2.1.30 recovery ledger
- V2.1.31 daily operation ledger

All sources are read locally. V2.1.32 performs no broker network calls.

## Trading metrics

V2.1.32 aggregates the existing V2.1.27 values:

- completed round trips
- wins / losses / flat
- win rate
- fill-based gross P&L before fees
- average return percentage from fills
- average holding time
- best / worst completed trade
- exit-reason counts
- symbol counts

It does not recalculate P&L from prices.

Accounting semantics remain:

`V2.1.27_FILL_BASED_GROSS_PNL_BEFORE_FEES`

This is not broker tax-lot realized P&L and does not include fees.

## Operations metrics

The report also includes:

- latest V2.1.29 risk state
- risk block / kill-switch events
- V2.1.30 recovery events
- blocked recovery events
- recovery actions
- V2.1.31 daily-operation events
- successful Paper operations
- blocked operations
- market-wait timeouts
- first operation start
- last operation end

## Outputs

Per market date:

- JSON report
- Markdown report

Runtime paths:

`runtime/daily_performance_operation_report_v2_1_32/reports/YYYY-MM-DD_daily_report.json`

`runtime/daily_performance_operation_report_v2_1_32/reports/YYYY-MM-DD_daily_report.md`

Latest copies:

`latest_daily_report.json`

`latest_daily_report.md`

## Validation-day ledger

A market date is counted as a validation day when the V2.1.31 operation ledger contains at least one:

`PASS_ONE_CLICK_DAILY_PAPER_OPERATION`

for that market date.

Target:

**10 qualified trading days**

The validation ledger is deduplicated by market date.

This count records operation-day qualification only. It does not claim the strategy is profitable or production-ready.

## Safety

Install/tests:
- broker network: OFF
- Paper orders: 0
- Live orders: 0

V2.1.32 runtime:
- broker network: OFF
- broker writes: 0
- order submission: 0

Live trading remains locked.

## Development boundary

After V2.1.32, no additional Paper execution feature stage is planned before actual regular-market end-to-end validation.

Next phase:

**Actual Regular-Market Alpaca Paper End-to-End Validation → 10 Trading-Day Validation**
