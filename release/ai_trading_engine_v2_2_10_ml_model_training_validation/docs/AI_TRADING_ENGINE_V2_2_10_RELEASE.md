# AI Trading Engine V2.2.10 — ML Model Training + Validation

Base commit: `04602bf5`.

## Purpose

Train actual machine-learning direction models from the leakage-controlled V2.2.9
datasets while leaving the existing Paper trading runtime untouched.

## Isolated environment

ML dependencies are installed into `.venv_ml`.

The existing `.venv` used by the trading project is not upgraded or modified by the
ML setup script.

## Candidate models

Per horizon:

1. Dummy prior baseline
2. Class-balanced Logistic Regression
3. Histogram Gradient Boosting

Horizons:

- 5 minutes
- 15 minutes
- 30 minutes
- 60 minutes

## Fast bounded training

TRAIN is capped at 250,000 deterministic evenly-spaced rows per horizon.
This preserves the full chronological span while bounding fit time.

VALIDATION and TEST are not used for training.

## Selection protocol

Candidates are fitted on TRAIN.

Candidate selection uses VALIDATION only.

Selection score:

`(macro F1 + balanced accuracy) / 2`

The selected model must improve over Dummy by at least 0.01 to become `edge_ready`.

## Untouched TEST

TEST data is not loaded until the validation winner has already been frozen.

The TEST score cannot change which model was selected.

This stage reports the final out-of-sample TEST result but performs no automatic
promotion.

## Bounded walk-forward diagnostic

The selected candidate also receives two expanding-window diagnostics using TRAIN
only.

Each fold includes a one-market-date embargo before its evaluation block.

Walk-forward training is capped at 100,000 rows/fold and evaluation at 50,000
rows/fold to keep runtime bounded.

## Artifacts

Runtime only; models are not committed to Git.

`runtime/ai_ml_model_training_validation_v2_2_10/models/`

- selected_5m.joblib
- selected_15m.joblib
- selected_30m.joblib
- selected_60m.joblib

Reports:

`runtime/ai_ml_model_training_validation_v2_2_10/reports/`

- horizon_5m.json
- horizon_15m.json
- horizon_30m.json
- horizon_60m.json

Master report:

`runtime/ai_ml_model_training_validation_v2_2_10/latest_training_report.json`

## Safety

- Broker network: OFF
- Paper/Live orders: 0
- Automatic promotion: DISABLED
- Execution selector modified: FALSE
- Live trading: LOCKED
