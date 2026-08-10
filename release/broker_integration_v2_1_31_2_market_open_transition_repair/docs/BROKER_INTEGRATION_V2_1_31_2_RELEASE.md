# V2.1.31.2 — Market Open Transition Repair

Base commit: `61ba6906`.

The observed overnight run stopped before market open because a single V2.1.30 broker-read cycle exhausted its internal retries and V2.1.31 treated that one poll failure as terminal.

Repair:
- keep V2.1.30 internal bounded retries;
- add a 30-minute consecutive broker-outage grace while waiting for market open;
- any successful broker read resets the outage window;
- persistent outage beyond the grace remains fail-closed;
- total overnight wait remains 36 hours;
- after `is_open=true`, re-run V2.1.30 recovery reconciliation and V2.1.29 risk evaluation before delegating to the existing Paper execution chain.

No new signal, entry, exit, order, risk, or trading state machine is created. Tests use no broker network and submit zero Paper/Live orders. Live trading remains locked.
