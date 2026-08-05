# Bundle A — R7 to R10 Runtime Core

This combined package replaces four separate installation rounds.

## R7 Runtime Orchestrator

Controls one complete offline cycle:

Signal → Risk → Allocation → Order Candidate → Portfolio Preview.

## R8 Capital Allocation Engine

Converts validated signal strength into bounded notional while respecting:

- maximum order notional;
- gross exposure;
- symbol exposure;
- profile Allocation flag.

## R9 Portfolio / Exposure Manager

Validates projected gross and symbol exposure and produces a copy-only preview.
It never mutates the actual portfolio in this preparation stage.

## R10 Strategy Plug-in Framework

Provides a StrategyPlugin interface, duplicate-safe registry, horizon support,
and deterministic fixture strategy for offline qualification.

Bundle A reuses the R6 session profile snapshot. Broker network, broker write,
actual strategy execution, automatic submission, and actual portfolio mutation
remain disabled. No Paper or Live orders are submitted.
