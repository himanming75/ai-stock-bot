V76.14 — Final Immutable Manifest

Purpose
-------
Create one final immutable manifest containing the complete V76.6–V76.13
commit and SHA256 anchor chain.

Framework commit anchor
-----------------------
c39fd1af94c1fead939927d4646ba8c4231fe664

V76.13 verification SHA256 anchor
---------------------------------
01261ef77e8451e2d1858211af5a2992cce4639ca029056bff28576a09c63e2b

Safety
------
This phase is offline-only. It does not connect to a broker, submit orders,
authorize live trading, or approve the project for live use.

Expected next phase
-------------------
V76_15_FINAL_INTEGRITY_VERIFICATION

FIXED PACKAGE NOTE
------------------
The IMMUTABLE_ANCHOR_VERSION_SET gate now compares the anchor version set
without depending on JSON object key order. A regression test covers
sort_keys=True configuration serialization.

DETERMINISTIC HASH FIX
----------------------
final_manifest_sha256 now excludes issued_at_utc and duration_seconds.
These remain in the output as operational metadata but are outside the
immutable digest material. Re-running with identical inputs produces the
same final_manifest_sha256.
