# R1 Production Deployment Preparation

R1 prepares production deployment infrastructure without activating trading.

Included:

- immutable release manifest and SHA-256 inventory;
- configuration and secret-value exposure audit;
- state backup inventory;
- operator-controlled restore plan;
- log and report retention policy;
- fail-closed process-supervisor policy;
- Paper and L2-L6 Actual release gates;
- production release certificate gate.

Start-on-boot, automatic broker restart, automatic order replay, Live network,
Live write, and production activation remain disabled. The final certificate is
blocked until Paper completion and all L2-L6 Actual qualifications are present.
