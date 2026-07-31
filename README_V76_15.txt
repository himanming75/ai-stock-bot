V76.15 FINAL INTEGRITY VERIFICATION

Purpose
-------
Independently verify the committed V76.14 Final Immutable Manifest and its
immutable anchor chain before the release archive sealing phase.

Fixed anchors
-------------
V76.14 framework commit:
4faf83a560767a0a963d045f1560712e1d1b0135

V76.14 final_manifest_sha256:
752e7929cd531d69518101635af2a6bdd885ea5cfe928364ed79f315d579bbac

V76.14 immutable_anchor_chain_sha256:
76a00d9dababdb2928b4c0effd94957a6804edf7ba7fa698a86e36a79e822ae5

Safety
------
This stage is offline only. It does not connect to a broker, enable a
network, submit an order, approve live trading, or authorize live trading.

Expected next phase
-------------------
V76_16_RELEASE_ARCHIVE_SEAL
