# Daily Session Manager and Startup Autorun

The Daily Session Manager controls one Paper automation session per trading
day.

Functions:

- Alpaca market-clock evaluation
- New trading-day state reset
- Weekend blocking
- Market-open Watchdog launch readiness
- Daily launch-count limit
- Market-close session state
- Atomic daily state
- Append-only daily session ledger
- Optional explicit Watchdog launch
- Windows Task Scheduler registration scripts

Safety:

- Installation does not register a Windows task.
- Installation does not launch the Watchdog.
- Actual Watchdog launch requires a separate explicit command.
- Paper and Live order submission remain disabled in this manager.
