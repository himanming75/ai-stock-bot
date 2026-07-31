V76.5 Release Candidate System Acceptance

Purpose
-------
This phase performs the final system-level acceptance of the current offline
release candidate. It does not enable live trading.

Acceptance gates
----------------
1. Existing V76.4 evidence is valid and internally consistent.
2. V76.4B deterministic-repair unit tests pass.
3. test_ml.py produces byte-identical stdout/stderr twice.
4. The complete V76.4 behavioral verification passes again.
5. No tracked or staged repository file changes during acceptance.

Safety invariants
-----------------
network_allowed = false
broker_connected = false
orders_submitted = 0
approved_for_live = false

Install
-------
Extract this ZIP directly into C:\stock-bot.

Check:
Test-Path README_V76_5.txt
Test-Path INSTALL_CHECK_V76_5.txt
Test-Path tools\release_candidate_system_acceptance_v76_5.py
Test-Path tools\test_release_candidate_system_acceptance_v76_5.py
Test-Path release\v76_5\config\release_candidate_system_acceptance_config_v76_5.json

Unit test:
python -m unittest tools.test_release_candidate_system_acceptance_v76_5 -v

Run:
python tools/release_candidate_system_acceptance_v76_5.py `
  --repository-root . `
  --config release/v76_5/config/release_candidate_system_acceptance_config_v76_5.json `
  --output-dir release/v76_5/output

Expected:
status = PASS
failed_gate_count = 0
release_candidate_accepted = true
approved_for_live = false
next_phase = V76_6_RELEASE_CANDIDATE_EVIDENCE_SEAL

The full V76.4 reverification can take several minutes.
