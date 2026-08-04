# V117-V119 Emergency Operations Guide

## Emergency triggers

- Manual kill switch
- Broker unhealthy
- Stale market data
- Market halt
- Excessive clock drift
- Daily or weekly loss limit breach
- Order or exposure limit breach
- Abnormal price gap or spread
- Excessive order rejects
- Duplicate events
- Position mismatch

## Current behavior

This stage creates emergency actions and reports only.

- Cancel requests executed: 0
- Flatten requests executed: 0
- Broker writes executed: 0
- Live trading disabled

Resume always requires explicit manual approval in a later controlled stage.
