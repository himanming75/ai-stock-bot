# Personal Web Control Center — E*TRADE Integration

This integrates the existing E*TRADE stack into the 8767 Personal Control Center.

Reuses:
- E*TRADE OAuth V2 read-only flow/transport;
- E*TRADE Sandbox order simulation stack;
- V2.1.10 eligible signal -> Sandbox bridge;
- locally installed V2.1.31.4 threshold sensitivity shadow audit.

Web actions intentionally exposed:
- refresh status;
- offline credential-presence preflight (booleans only);
- run V2.1.31.4 capture/shadow audit;
- verify V2.1.31.4.

Not exposed:
- Production OAuth connection action;
- token persistence;
- Production order POST;
- cancel/replace;
- Live trading enable;
- any action that submits a real-money order.

The browser never receives credential values.
