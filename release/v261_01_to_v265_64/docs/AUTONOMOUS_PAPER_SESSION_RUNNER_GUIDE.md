# V261-V265 Autonomous Paper Session Runner

Features:

- waits while the market is closed
- executes repeated V260 cycles
- uses separate closed/open polling intervals
- stops after the market closes following an open session
- single-instance lock
- stop-file control
- consecutive-error backoff
- maximum runtime and cycle limits
- session checkpoint
- cycle and error ledgers
- web API foundation

Safety defaults:

- Session Runner disabled
- Real Paper network disabled
- Live submission disabled
- Live network disabled
- Broker write disabled

V261-V265 does not change the V260 Paper activation gates.

## Standalone package validation

The ZIP does not duplicate the existing V260 module. During standalone package
validation, the runner uses a no-network fallback cycle. After installation into
C:\stock-bot, it imports and repeatedly runs the real V260 cycle engine.
