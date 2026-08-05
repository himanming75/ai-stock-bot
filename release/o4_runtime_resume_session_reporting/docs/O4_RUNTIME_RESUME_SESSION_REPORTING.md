# O4 Runtime Resume / Session Rotation / Daily Reporting

O4 adds operator-controlled operational continuity:

- runtime resume plan;
- operator resume checklist;
- session rotation registry;
- graceful shutdown marker;
- daily JSON report;
- daily CSV summary;
- next-day preparation.

O4 never automatically replays an order and never automatically restarts broker
submission. Resume remains operator-controlled and must pass P4 preflight first.

Installation performs zero network access and zero order submission.
