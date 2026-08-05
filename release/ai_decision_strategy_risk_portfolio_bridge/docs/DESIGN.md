# AI Decision to Strategy/Risk/Portfolio Bridge

Consumes the AI decision snapshot and calls the existing Strategy Ensemble V4,
Adaptive Risk Engine V3, and Portfolio Intelligence V2. It merges blockers,
takes the lower approved notional across risk and portfolio gates, and emits
an explainable approval snapshot. It performs no broker or order operation.
