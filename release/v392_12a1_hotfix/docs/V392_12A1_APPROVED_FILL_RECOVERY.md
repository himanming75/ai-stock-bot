# V392.12A1 Approved Fill Recovery

## Problem

V392.11A initially produced a valid Fill Event. A later intentional replay
attempt overwrote the current simulator result with a blocked result. V392.12A
therefore saw no approved fill and did not create `paper_portfolio_state.json`.

## Recovery

This hotfix:

1. reads the append-only V392.11A simulator ledger;
2. selects the latest approved Fill Event;
3. writes immutable approved-result and approved-fill snapshots;
4. makes V392.12A use those snapshots;
5. runs accounting and creates the Portfolio State;
6. preserves the replay registry and current blocked result.

No replay protection is bypassed and no broker order is submitted.
