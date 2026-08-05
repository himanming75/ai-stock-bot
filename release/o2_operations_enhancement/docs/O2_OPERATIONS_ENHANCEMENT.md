# O2 Operations Enhancement

O2 extends the existing Operations Bundle without replacing it.

Included:

- Dashboard V2 with cards, tables, collapsible raw details, and quiet handling
  of browser disconnects;
- runtime and event metrics;
- Order, Fill, Position, Equity, and performance-history readers;
- realized P/L, win rate, average profit/loss, and maximum drawdown summary;
- Watchdog with heartbeat-age checks;
- Scheduler monitor;
- crash/restart recovery snapshot;
- explicit prohibition of automatic order replay;
- Notification Center adapters for Discord, Slack, Telegram, and SMTP Email.

External notifications are disabled by default. Installation performs no
external sends and submits zero broker orders.

O2 does not mark Paper complete and does not activate Live trading.
