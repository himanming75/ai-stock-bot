from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


class VerificationError(ValueError):
    pass


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise VerificationError(f"file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise VerificationError(f"invalid JSON: {path}") from exc
    if not isinstance(value, dict):
        raise VerificationError(f"JSON root must be object: {path}")
    return value


def verify_ledger(ledger: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    previous_hash = "0" * 64
    entries = ledger.get("entries", [])
    if not isinstance(entries, list):
        return ["entries must be a list"]

    for expected_sequence, entry in enumerate(entries, start=1):
        if entry.get("sequence") != expected_sequence:
            errors.append(f"sequence mismatch at {expected_sequence}")
        if entry.get("previous_entry_sha256") != previous_hash:
            errors.append(f"previous hash mismatch at {expected_sequence}")
        calculated = digest({
            key: value for key, value in entry.items()
            if key != "entry_sha256"
        })
        if entry.get("entry_sha256") != calculated:
            errors.append(f"entry hash mismatch at {expected_sequence}")
        previous_hash = entry.get("entry_sha256")

    if entries and ledger.get("ledger_head_sha256") != entries[-1].get("entry_sha256"):
        errors.append("ledger head mismatch")
    return errors


def verify(output_dir: Path, repository_root: Path) -> dict[str, Any]:
    manifest_path = output_dir / "release_candidate_evidence_manifest_v76_6.json"
    ledger_path = output_dir / "release_candidate_evidence_ledger_v76_6.json"
    certificate_path = output_dir / "release_candidate_certificate_v76_6.json"
    result_path = output_dir / "release_candidate_evidence_seal_v76_6.json"

    manifest = load_json(manifest_path)
    ledger = load_json(ledger_path)
    certificate = load_json(certificate_path)
    result = load_json(result_path)

    errors: list[str] = []

    stored_manifest_hash = manifest.get("manifest_sha256")
    calculated_manifest_hash = digest({
        key: value for key, value in manifest.items()
        if key != "manifest_sha256"
    })
    if stored_manifest_hash != calculated_manifest_hash:
        errors.append("manifest hash mismatch")

    stored_ledger_hash = ledger.get("ledger_sha256")
    calculated_ledger_hash = digest({
        key: value for key, value in ledger.items()
        if key != "ledger_sha256"
    })
    if stored_ledger_hash != calculated_ledger_hash:
        errors.append("ledger hash mismatch")

    errors.extend(verify_ledger(ledger))

    stored_certificate_hash = certificate.get("certificate_sha256")
    calculated_certificate_hash = digest({
        key: value for key, value in certificate.items()
        if key != "certificate_sha256"
    })
    if stored_certificate_hash != calculated_certificate_hash:
        errors.append("certificate hash mismatch")

    stored_result_hash = result.get("seal_result_sha256")
    calculated_result_hash = digest({
        key: value for key, value in result.items()
        if key != "seal_result_sha256"
    })
    if stored_result_hash != calculated_result_hash:
        errors.append("seal result hash mismatch")

    if certificate.get("manifest_sha256") != stored_manifest_hash:
        errors.append("certificate manifest reference mismatch")
    if certificate.get("ledger_sha256") != stored_ledger_hash:
        errors.append("certificate ledger reference mismatch")
    if result.get("release_seal_sha256") != certificate.get("release_seal_sha256"):
        errors.append("result seal reference mismatch")
    if result.get("certificate_sha256") != stored_certificate_hash:
        errors.append("result certificate reference mismatch")

    for item in manifest.get("evidence", []):
        path = repository_root / item["path"]
        if not path.is_file():
            errors.append(f"evidence missing: {item['path']}")
            continue
        actual_hash = file_sha256(path)
        if actual_hash != item.get("file_sha256"):
            errors.append(f"evidence hash mismatch: {item['path']}")

    status = "PASS" if not errors else "FAIL"
    return {
        "status": status,
        "verified": not errors,
        "error_count": len(errors),
        "errors": errors,
        "evidence_count": manifest.get("evidence_count"),
        "manifest_sha256": stored_manifest_hash,
        "ledger_sha256": stored_ledger_hash,
        "certificate_sha256": stored_certificate_hash,
        "release_seal_sha256": certificate.get("release_seal_sha256"),
        "approved_for_live": False,
        "next_phase": (
            "V76_7_RELEASE_CANDIDATE_SEAL_VERIFICATION"
            if status == "PASS"
            else "REPAIR_RELEASE_CANDIDATE_SEAL"
        ),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)

    try:
        result = verify(
            Path(args.output_dir),
            Path(args.repository_root).resolve(),
        )
    except (VerificationError, OSError, ValueError) as exc:
        print(json.dumps({
            "status": "ERROR",
            "error": str(exc),
            "approved_for_live": False,
        }, indent=2, sort_keys=True))
        return 2

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
