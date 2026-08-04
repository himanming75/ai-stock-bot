# V391.03A2 Import Path Hotfix

## Problem

The V391.03A1 verifier was executed by absolute path. Python therefore used the
`tools` directory as the first module search location and could not import the
project package `autonomous_risk_governor`.

## Fix

- explicitly insert the repository root into `sys.path`;
- set `PYTHONPATH` to the repository root during hotfix verification;
- rerun V391.01A, V391.02A, and V391.03A regression tests;
- rerun the V391.03A guard and final verification.

The previously added `append_jsonl` function is preserved. No broker network or
order submission is used.
