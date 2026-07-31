V76.9 Release Candidate Audit Certificate Verification

Purpose
-------
Independently verify the V76.8 audit certificate, its self-hash,
summary consistency, all 29 V76.8 gates, inherited evidence anchors,
Git state, and zero trading side effects.

Framework commit
----------------
5e2638aef05887a30cc119a8073b220a30191dae

V76.8 audit certificate SHA256
------------------------------
28cfcb6fa465adca705b238cf73edd51878f08ef36642874069633608f4eff9a

Run tests
---------
python -m unittest tools.test_release_candidate_audit_certificate_verification_v76_9 -v

Run primary verification
------------------------
python tools/release_candidate_audit_certificate_verification_v76_9.py `
  --repository-root . `
  --config release/v76_9/config/release_candidate_audit_certificate_verification_config_v76_9.json `
  --output-dir release/v76_9/output

Run independent output verification
-----------------------------------
python tools/verify_release_candidate_audit_certificate_verification_v76_9.py `
  --output-dir release/v76_9/output

Both scripts support direct execution and python -m execution.

No broker connectivity, order submission, or live approval is authorized.
