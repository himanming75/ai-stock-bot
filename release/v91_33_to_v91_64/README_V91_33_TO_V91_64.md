# V91.33-V91.64 Parameter Optimization & Walk-Forward Tuning

## Included

- V91.33-V91.40 parameter search spaces
- V91.41-V91.48 batch parameter evaluation
- V91.49-V91.56 walk-forward window scoring
- V91.57-V91.64 stability gate, ranking, dashboard payload, tests and release

The optimizer uses the top strategies from V91.01-V91.32, evaluates parameter combinations on the full historical series and across multiple walk-forward windows, and only marks a stable candidate when all stability-gate checks pass.

All operations remain local and paper-only.
