# V391.03A1 IO Append JSONL Hotfix

## Problem

The V391.03A runner imports `append_jsonl` from
`autonomous_risk_governor.io`, but the original installer did not deploy the
updated `io.py` into an existing project.

## Fix

- add `append_jsonl` only when missing;
- preserve existing `read_json` and `write_json`;
- rerun V391.01A, V391.02A, and V391.03A regression tests;
- rerun V391.03A and final verification.

No broker network or order submission is used.
