V76.8 Release Candidate Audit Certificate

Purpose
-------
V76.8 converts the independently verified V76.7 audit result into a
cryptographically self-hashed release candidate audit certificate.

Anchors
-------
V76.7 framework commit:
b6796022d589f772d21b1618685e79f7d7232670

V76.6 sealed commit:
211d78b5c047febbc33c73f281fbf4a5f5554689

V76.7 audit SHA256:
ef2966239f17c480c227e1240245ed1ce6f8fa5639e6c0860fd0240e2d6865c5

The certificate also anchors the V76.6 manifest, ledger, certificate,
and release seal hashes.

This phase remains fully offline and does not authorize live trading.

Run tests
---------
python -m unittest tools.test_release_candidate_audit_certificate_v76_8 -v

Create certificate
------------------
python tools/release_candidate_audit_certificate_v76_8.py `
  --repository-root . `
  --config release/v76_8/config/release_candidate_audit_certificate_config_v76_8.json `
  --output-dir release/v76_8/output

Verify certificate
------------------
python tools/verify_release_candidate_audit_certificate_v76_8.py `
  --output-dir release/v76_8/output

Expected next phase
-------------------
V76_9_RELEASE_CANDIDATE_AUDIT_CERTIFICATE_VERIFICATION
