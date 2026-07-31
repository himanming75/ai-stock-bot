V76.10 Release Candidate Final Attestation

Purpose
-------
Create one final offline attestation covering the complete evidence chain:
V76.6 release seal, V76.7 seal verification, V76.8 audit certificate,
and V76.9 independent audit-certificate verification.

Framework commit
----------------
09db70f69560314c989d074973cbfd0a493848e7

Run tests
---------
python -m unittest tools.test_release_candidate_final_attestation_v76_10 -v

Create final attestation
------------------------
python tools/release_candidate_final_attestation_v76_10.py `
  --repository-root . `
  --config release/v76_10/config/release_candidate_final_attestation_config_v76_10.json `
  --output-dir release/v76_10/output

Verify final attestation
------------------------
python tools/verify_release_candidate_final_attestation_v76_10.py `
  --output-dir release/v76_10/output

This phase does not authorize live trading.

V76.10 Repair Note
------------------
Corrected V76.6 seal verification semantics:
- certificate.release_seal_sha256 verifies the original seal material anchor.
- seal_result.seal_result_sha256 verifies the seal-result JSON self-hash.
