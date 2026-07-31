V76.7 Release Candidate Seal Verification

Purpose
-------
V76.7 independently audits the completed V76.6 evidence seal.

It binds verification to:
- sealed Git commit 211d78b5c047febbc33c73f281fbf4a5f5554689
- expected manifest SHA256
- expected ledger SHA256
- expected certificate SHA256
- expected release seal SHA256

It also re-checks:
- all internal object hashes
- the complete ledger hash chain
- all manifest evidence files
- cross-file references
- Git HEAD, origin/main, and clean working tree
- all offline/live-trading safety invariants

This phase does not enable live trading.

Files generated
---------------
release/v76_7/output/release_candidate_seal_verification_v76_7.json
release/v76_7/output/release_candidate_seal_verification_summary_v76_7.json
release/v76_7/output/release_candidate_seal_verification_report_v76_7.txt

Run unit tests
--------------
python -m unittest tools.test_release_candidate_seal_verification_v76_7 -v

Run audit
---------
python tools/release_candidate_seal_verification_v76_7.py `
  --repository-root . `
  --config release/v76_7/config/release_candidate_seal_verification_config_v76_7.json `
  --output-dir release/v76_7/output

Expected
--------
status = PASS
failed_gate_count = 0
independent_verification_passed = true
approved_for_live = false
next_phase = V76_8_RELEASE_CANDIDATE_AUDIT_CERTIFICATE

V76.7A repair: clean-tree verification ignores untracked V76.7 installer/output files, while tracked and staged changes still fail.
