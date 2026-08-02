# OP1.01-OP1.04 Paper Operations Pilot Bootstrap

- OP1.01 Final package and policy preflight
- OP1.02 Read-only Paper account snapshot
- OP1.03 Pilot preflight report
- OP1.04 Read-only pilot token

Default execution uses a local snapshot. `-EnableNetwork` performs only four GET requests:
account, clock, open orders, and positions. POST/DELETE/PATCH requests are not implemented.
