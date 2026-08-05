# P5 Paper Long-Run Qualification

P5 is the final fixed Paper roadmap stage.

## Offline qualification

The installation runs 1,000 successful Offline cycles and validates the fault
matrix for:

- duplicate cycle protection;
- Kill Switch blocking;
- market-closed blocking;
- unknown order-state blocking;
- position drift blocking;
- account drift blocking;
- partial-Fill deduplication;
- restart checkpoint recovery;
- Single-Instance Lock;
- retry and rate-limit policy;
- graceful lock release;
- next-day resume capability.

Passing Offline P5 does not mean Paper trading is complete.

## Actual qualification requirements

Actual Paper completion requires all of the following:

1. P2 actual Paper order validation;
2. P3 actual order, Fill, position, cash, and Equity sync validation;
3. P4 actual autonomous runtime validation;
4. multiple real Paper trading sessions;
5. actual Market and Limit orders;
6. actual cancel and replace;
7. partial or full Fill observation;
8. network interruption and restart recovery;
9. Kill Switch test;
10. market close and next-day automatic resume;
11. reconciliation with zero unresolved drift.

Only after the actual P5 qualification passes may the project mark Paper
trading complete and proceed to L1.
