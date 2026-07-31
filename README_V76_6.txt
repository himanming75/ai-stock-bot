V76.6 Release Candidate Evidence Seal

Purpose
-------
V76.6 collects and validates the completed V76.4 and V76.5 evidence,
creates a deterministic evidence manifest, builds a hash-linked evidence
ledger, and issues an offline release candidate certificate.

This phase does not enable live trading.

Generated outputs
-----------------
release/v76_6/output/release_candidate_evidence_manifest_v76_6.json
release/v76_6/output/release_candidate_evidence_ledger_v76_6.json
release/v76_6/output/release_candidate_certificate_v76_6.json
release/v76_6/output/release_candidate_certificate_v76_6.txt
release/v76_6/output/release_candidate_evidence_seal_v76_6.json

Safety invariants
-----------------
network_allowed = false
broker_connected = false
orders_submitted = 0
approved_for_live = false

Important
---------
Run this only while git status --short is empty and HEAD matches origin/main.
V76.5 output files must already exist.

Install
-------
Extract the ZIP directly into C:\stock-bot.

Unit tests:
python -m unittest tools.test_release_candidate_evidence_seal_v76_6 -v
python -m unittest tools.test_verify_release_candidate_evidence_seal_v76_6 -v

Create seal:
python tools/release_candidate_evidence_seal_v76_6.py `
  --repository-root . `
  --config release/v76_6/config/release_candidate_evidence_seal_config_v76_6.json `
  --output-dir release/v76_6/output

Verify seal:
python tools/verify_release_candidate_evidence_seal_v76_6.py `
  --repository-root . `
  --output-dir release/v76_6/output

Expected creation result:
status = PASS
failed_evidence_count = 0
ledger_verified = true
repository_clean = true
release_candidate_sealed = true
approved_for_live = false
next_phase = V76_7_RELEASE_CANDIDATE_SEAL_VERIFICATION
