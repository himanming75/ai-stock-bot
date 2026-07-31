V76.17 RELEASE ARCHIVE SEAL VERIFICATION

Purpose
-------
Independently and read-only verify the V76.16 deterministic release archive
seal, its ZIP bytes, embedded manifest, evidence file records, source anchors,
seal certificate, summary consistency, and zero-trading safety state.

Framework commit
----------------
3bbbee6deed78c169959326df1c33960155683b0

V76.16 anchors
--------------
seal_certificate_sha256:
27f09615b177bcc790beaec7cea967340140def0c58cd76b2a6ee96ba52d07db

archive_sha256:
f7528f88f5a5829c8c1fe249cec36e1c5a48a44b2e268eb50c114a9a457726fa

archive_manifest_sha256:
6589bcf2ade79f908304b435380bd15efbc9635b3b4a51641756e923bf327889

evidence_set_sha256:
4752ad9878b5e3ba1fca0c77dd61c463da161c43136c5e486f4f95532fc3e6c6

Safety
------
Offline and read-only. No broker connection, order submission, live approval,
or live-trading authorization is performed.

Expected next phase
-------------------
V76_18_RELEASE_ARCHIVE_CLOSURE_CERTIFICATE
