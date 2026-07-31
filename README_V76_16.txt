V76.16 RELEASE ARCHIVE SEAL

Purpose
-------
Create a deterministic offline ZIP archive containing the V76.14 and V76.15
release evidence. The archive uses sorted member names, fixed timestamps,
fixed Unix file permissions, and deterministic compression inputs.

Framework commit
----------------
5fa759dc70443ce883897bd8c2fbe028399476c6

Anchors
-------
V76.15 verification SHA256:
ee7f251a7887af3ffdfef6df8dcf8929332b8eba649a0138adc9393bb8990a51

V76.15 artifact set SHA256:
e910ef8ba2649a3a046ed2eef7da4da36e63c4676bc80f2df3808bc251df9eaf

V76.14 final manifest SHA256:
752e7929cd531d69518101635af2a6bdd885ea5cfe928364ed79f315d579bbac

V76.14 immutable anchor chain SHA256:
76a00d9dababdb2928b4c0effd94957a6804edf7ba7fa698a86e36a79e822ae5

Safety
------
No network access, broker connection, order submission, live approval, or
live-trading authorization is performed.

Expected next phase
-------------------
V76_17_RELEASE_ARCHIVE_SEAL_VERIFICATION
