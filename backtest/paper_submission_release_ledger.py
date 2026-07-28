import hashlib
import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from backtest.paper_submission_release_gate import (
    PaperSubmissionRelease,
    PaperSubmissionReleaseResult,
    verify_release,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIRECTORY = (
    PROJECT_ROOT / "output" / "trading_engine"
    / "paper_submission_release_ledger"
)
REQUIRED_RECORD_TEXT = "RECORD PAPER SUBMISSION RELEASE"
GENESIS_HASH = "0" * 64


@dataclass(frozen=True)
class PaperSubmissionReleaseLedgerPolicy:
    required_source_version: str = "V13.7"
    required_source_status: str = "PAPER_RELEASED"
    required_release_status: str = "PAPER_RELEASED"
    required_confirmation_text: str = REQUIRED_RECORD_TEXT
    maximum_ledger_entries: int = 100
    require_same_operator: bool = True
    require_valid_release: bool = True
    require_chronological_order: bool = True
    reject_duplicate_release_id: bool = True
    verify_hash_chain: bool = True
    ledger_recording_only: bool = True
    network_access_disabled: bool = True
    broker_api_disabled: bool = True
    order_submission_disabled: bool = True
    live_execution_disabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PaperSubmissionReleaseLedgerEntry:
    ledger_entry_id: str
    sequence: int
    recorded_at: str
    previous_entry_hash: str
    release_result_id: str
    release_id: str
    release_hash: str
    reconciliation_id: str
    submission_batch_id: str
    operator: str
    released_item_count: int
    release_expires_at: str
    paper_submission_released: bool
    paper_execution_authorized: bool
    network_accessed: bool
    broker_api_called: bool
    broker_order_created: bool
    order_submitted: bool
    live_execution_authorized: bool
    entry_hash: str

    def payload_without_hash(self) -> dict[str, Any]:
        payload = asdict(self)
        payload.pop("entry_hash", None)
        return payload

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PaperSubmissionReleaseLedgerResult:
    version: str
    created_at: str
    ledger_result_id: str
    result_status: str
    result_status_label: str
    latest_entry_id: str | None
    latest_entry_hash: str | None
    latest_release_id: str | None
    total_entry_count: int
    valid_entry_count: int
    records_trimmed: int
    policy_checks_passed: bool
    input_checks_passed: bool
    source_checks_passed: bool
    release_checks_passed: bool
    operator_checks_passed: bool
    duplicate_checks_passed: bool
    chronology_checks_passed: bool
    existing_ledger_checks_passed: bool
    hash_chain_checks_passed: bool
    entry_checks_passed: bool
    safety_checks_passed: bool
    all_checks_passed: bool
    ledger_entry_recorded: bool
    paper_submission_released: bool
    paper_execution_authorized: bool
    automatic_execution_authorized: bool
    execution_blocked: bool
    network_accessed: bool
    account_accessed: bool
    broker_api_called: bool
    broker_order_created: bool
    order_submitted: bool
    live_order_created: bool
    live_execution_authorized: bool
    ledger_policy: PaperSubmissionReleaseLedgerPolicy
    entries: tuple[PaperSubmissionReleaseLedgerEntry, ...]
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)
    report_path: str | None = None
    latest_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["ledger_policy"] = self.ledger_policy.to_dict()
        payload["entries"] = [entry.to_dict() for entry in self.entries]
        return payload


def canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )


def sha256_payload(payload: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def validate_policy(policy: PaperSubmissionReleaseLedgerPolicy) -> list[str]:
    if not isinstance(policy, PaperSubmissionReleaseLedgerPolicy):
        return ["Ledger Policy 형식이 올바르지 않습니다."]
    errors: list[str] = []
    expected = {
        "required_source_version": "V13.7",
        "required_source_status": "PAPER_RELEASED",
        "required_release_status": "PAPER_RELEASED",
        "required_confirmation_text": REQUIRED_RECORD_TEXT,
    }
    for name, value in expected.items():
        if getattr(policy, name) != value:
            errors.append(f"{name} 값이 V13.8 기준과 다릅니다.")
    if policy.maximum_ledger_entries <= 0:
        errors.append("Ledger 보관 한도는 0보다 커야 합니다.")
    for name in (
        "require_same_operator",
        "require_valid_release",
        "require_chronological_order",
        "reject_duplicate_release_id",
        "verify_hash_chain",
        "ledger_recording_only",
        "network_access_disabled",
        "broker_api_disabled",
        "order_submission_disabled",
        "live_execution_disabled",
    ):
        if getattr(policy, name) is not True:
            errors.append(f"{name}는 V13.8에서 True여야 합니다.")
    return errors


def validate_release_source(
    source: Any,
    checked_at: datetime,
) -> tuple[PaperSubmissionRelease | None, list[str], list[str]]:
    source_errors: list[str] = []
    release_errors: list[str] = []
    release: PaperSubmissionRelease | None = None
    if not isinstance(source, PaperSubmissionReleaseResult):
        source_errors.append("Source는 V13.7 Release Result여야 합니다.")
        return None, source_errors, release_errors
    if source.version != "V13.7":
        source_errors.append("Source Version이 V13.7이 아닙니다.")
    if source.result_status != "PAPER_RELEASED":
        source_errors.append("Source가 PAPER_RELEASED 상태가 아닙니다.")
    if not source.all_checks_passed or not source.paper_submission_released:
        source_errors.append("V13.7 Release가 완료되지 않았습니다.")
    if any((
        source.paper_execution_authorized,
        source.automatic_execution_authorized,
        not source.execution_blocked,
        source.network_accessed,
        source.account_accessed,
        source.broker_api_called,
        source.broker_order_created,
        source.order_submitted,
        source.live_order_created,
        source.live_execution_authorized,
    )):
        source_errors.append("V13.7 Source 실행 안전장치가 올바르지 않습니다.")
    if not source.releases:
        release_errors.append("Release Record가 없습니다.")
    else:
        release = source.releases[-1]
        valid, time_valid, errors = verify_release(release, checked_at)
        if not valid or not time_valid:
            release_errors.extend(errors)
        if source.latest_release_id != release.release_id:
            release_errors.append("Latest Release ID 연결이 다릅니다.")
        if source.released_item_count != release.released_item_count:
            release_errors.append("Released Item Count 연결이 다릅니다.")
    return release, source_errors, release_errors


def normalize_entries(
    existing: Any,
) -> tuple[PaperSubmissionReleaseLedgerEntry, ...]:
    if existing is None:
        return ()
    if not isinstance(existing, (tuple, list)):
        raise TypeError("Existing Entries는 tuple 또는 list여야 합니다.")
    entries: list[PaperSubmissionReleaseLedgerEntry] = []
    for entry in existing:
        if not isinstance(entry, PaperSubmissionReleaseLedgerEntry):
            raise TypeError("Existing Ledger Entry 형식이 올바르지 않습니다.")
        entries.append(entry)
    return tuple(entries)


def verify_ledger_chain(
    entries: tuple[PaperSubmissionReleaseLedgerEntry, ...],
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    previous_hash = GENESIS_HASH
    previous_time: datetime | None = None
    release_ids: set[str] = set()
    for expected_sequence, entry in enumerate(entries, start=1):
        if entry.sequence != expected_sequence:
            errors.append(f"Sequence {expected_sequence}가 올바르지 않습니다.")
        if entry.previous_entry_hash != previous_hash:
            errors.append(f"Sequence {entry.sequence}의 이전 Hash가 다릅니다.")
        if entry.entry_hash != sha256_payload(entry.payload_without_hash()):
            errors.append(f"Sequence {entry.sequence}의 Entry Hash가 다릅니다.")
        if entry.release_id in release_ids:
            errors.append(f"중복 Release ID가 있습니다: {entry.release_id}")
        release_ids.add(entry.release_id)
        try:
            recorded_at = datetime.fromisoformat(entry.recorded_at)
            if previous_time and recorded_at < previous_time:
                errors.append("Ledger 기록 시간이 역순입니다.")
            previous_time = recorded_at
        except (TypeError, ValueError):
            errors.append("Ledger 기록 시간이 올바르지 않습니다.")
        if not entry.paper_submission_released or entry.released_item_count <= 0:
            errors.append("Ledger Entry의 Release 정보가 올바르지 않습니다.")
        if any((
            entry.paper_execution_authorized,
            entry.network_accessed,
            entry.broker_api_called,
            entry.broker_order_created,
            entry.order_submitted,
            entry.live_execution_authorized,
        )):
            errors.append("Ledger Entry에 실제 실행 흔적이 있습니다.")
        previous_hash = entry.entry_hash
    return not errors, errors


def record_paper_submission_release(
    source: PaperSubmissionReleaseResult,
    operator: str,
    confirmation_text: str,
    existing_entries: Any = None,
    policy: PaperSubmissionReleaseLedgerPolicy | None = None,
    now: datetime | None = None,
) -> PaperSubmissionReleaseLedgerResult:
    policy = policy or PaperSubmissionReleaseLedgerPolicy()
    now = now or datetime.now().astimezone()
    created_at = now.isoformat()
    policy_errors = validate_policy(policy)
    clean_operator = operator.strip() if isinstance(operator, str) else ""
    input_errors: list[str] = []
    if not clean_operator:
        input_errors.append("Operator가 필요합니다.")
    if confirmation_text != policy.required_confirmation_text:
        input_errors.append("Ledger 확인 문구가 일치하지 않습니다.")
    release, source_errors, release_errors = validate_release_source(source, now)
    operator_errors: list[str] = []
    if release and policy.require_same_operator and release.operator != clean_operator:
        operator_errors.append("Release Operator와 Ledger Operator가 다릅니다.")
    existing_errors: list[str] = []
    try:
        existing = normalize_entries(existing_entries)
    except (TypeError, ValueError) as error:
        existing = ()
        existing_errors.append(str(error))
    chain_valid, chain_errors = verify_ledger_chain(existing)
    if not chain_valid:
        existing_errors.extend(chain_errors)
    duplicate_errors: list[str] = []
    if release and any(entry.release_id == release.release_id for entry in existing):
        duplicate_errors.append("동일 Release ID가 이미 기록되어 있습니다.")
    chronology_errors: list[str] = []
    if existing:
        try:
            previous_time = datetime.fromisoformat(existing[-1].recorded_at)
            if now < previous_time:
                chronology_errors.append("새 Ledger 기록 시간이 이전 기록보다 빠릅니다.")
        except (TypeError, ValueError):
            chronology_errors.append("기존 Ledger 시간이 올바르지 않습니다.")
    entry: PaperSubmissionReleaseLedgerEntry | None = None
    entry_errors: list[str] = []
    preliminary_errors = (
        policy_errors + input_errors + source_errors + release_errors
        + operator_errors + existing_errors + duplicate_errors
        + chronology_errors
    )
    if not preliminary_errors and release:
        draft = PaperSubmissionReleaseLedgerEntry(
            ledger_entry_id=str(uuid.uuid4()),
            sequence=len(existing) + 1,
            recorded_at=created_at,
            previous_entry_hash=(
                existing[-1].entry_hash if existing else GENESIS_HASH
            ),
            release_result_id=source.release_result_id,
            release_id=release.release_id,
            release_hash=release.release_hash,
            reconciliation_id=release.reconciliation_id,
            submission_batch_id=release.submission_batch_id,
            operator=clean_operator,
            released_item_count=release.released_item_count,
            release_expires_at=release.expires_at,
            paper_submission_released=True,
            paper_execution_authorized=False,
            network_accessed=False,
            broker_api_called=False,
            broker_order_created=False,
            order_submitted=False,
            live_execution_authorized=False,
            entry_hash="",
        )
        entry = PaperSubmissionReleaseLedgerEntry(
            **{
                **asdict(draft),
                "entry_hash": sha256_payload(draft.payload_without_hash()),
            }
        )
    entries = (*existing, *((entry,) if entry else ()))
    trimmed = max(0, len(entries) - policy.maximum_ledger_entries)
    if trimmed:
        entries = entries[-policy.maximum_ledger_entries:]
        # 잘린 Ledger도 독립적으로 검증할 수 있도록 Chain을 다시 봉인합니다.
        rebuilt: list[PaperSubmissionReleaseLedgerEntry] = []
        previous_hash = GENESIS_HASH
        for sequence, old in enumerate(entries, start=1):
            draft = PaperSubmissionReleaseLedgerEntry(
                **{
                    **asdict(old),
                    "sequence": sequence,
                    "previous_entry_hash": previous_hash,
                    "entry_hash": "",
                }
            )
            new = PaperSubmissionReleaseLedgerEntry(
                **{
                    **asdict(draft),
                    "entry_hash": sha256_payload(draft.payload_without_hash()),
                }
            )
            rebuilt.append(new)
            previous_hash = new.entry_hash
        entries = tuple(rebuilt)
    final_chain_valid, final_chain_errors = verify_ledger_chain(entries)
    if not final_chain_valid:
        entry_errors.extend(final_chain_errors)
    all_errors = preliminary_errors + entry_errors
    passed = bool(entry) and not all_errors
    source_valid = not source_errors and not release_errors
    status = "RECORDED" if passed else (
        "BLOCKED" if source_valid else "FAILED"
    )
    return PaperSubmissionReleaseLedgerResult(
        version="V13.8",
        created_at=created_at,
        ledger_result_id=str(uuid.uuid4()),
        result_status=status,
        result_status_label={
            "RECORDED": "Paper Submission Release Ledger 기록 완료",
            "BLOCKED": "Ledger 기록 차단",
            "FAILED": "V13.7 Source 검증 실패",
        }[status],
        latest_entry_id=entry.ledger_entry_id if entry else None,
        latest_entry_hash=entries[-1].entry_hash if entries else None,
        latest_release_id=release.release_id if entry and release else None,
        total_entry_count=len(entries),
        valid_entry_count=len(entries) if final_chain_valid else 0,
        records_trimmed=trimmed,
        policy_checks_passed=not policy_errors,
        input_checks_passed=not input_errors,
        source_checks_passed=not source_errors,
        release_checks_passed=not release_errors,
        operator_checks_passed=not operator_errors,
        duplicate_checks_passed=not duplicate_errors,
        chronology_checks_passed=not chronology_errors,
        existing_ledger_checks_passed=not existing_errors,
        hash_chain_checks_passed=final_chain_valid,
        entry_checks_passed=bool(entry) and not entry_errors,
        safety_checks_passed=not policy_errors,
        all_checks_passed=passed,
        ledger_entry_recorded=passed,
        paper_submission_released=bool(entry),
        paper_execution_authorized=False,
        automatic_execution_authorized=False,
        execution_blocked=True,
        network_accessed=False,
        account_accessed=False,
        broker_api_called=False,
        broker_order_created=False,
        order_submitted=False,
        live_order_created=False,
        live_execution_authorized=False,
        ledger_policy=policy,
        entries=entries,
        reasons=[
            "V13.7 Release를 SHA-256 Ledger Chain에 기록했습니다."
            if passed else "Release Ledger 기록이 차단되었습니다."
        ],
        warnings=all_errors + [
            "Ledger 기록은 실제 Broker 주문 제출 권한이 아닙니다."
        ],
        next_actions=[
            "Ledger Sequence와 Hash Chain을 수동 확인합니다.",
            "Broker API 또는 실제 계좌를 연결하지 않습니다.",
        ],
    )


def save_ledger_result(
    result: PaperSubmissionReleaseLedgerResult,
    directory: Path | None = None,
) -> tuple[Path, Path]:
    directory = directory or OUTPUT_DIRECTORY
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S_%f")
    report = directory / f"paper_submission_release_ledger_{stamp}.json"
    latest = directory / "latest_paper_submission_release_ledger.json"
    payload = result.to_dict()
    for path in (report, latest):
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(path)
    result.report_path = str(report)
    result.latest_path = str(latest)
    return report, latest


def load_ledger_result(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("version") != "V13.8":
        raise ValueError("V13.8 결과 파일이 아닙니다.")
    entries = tuple(
        PaperSubmissionReleaseLedgerEntry(**item)
        for item in payload.get("entries", [])
    )
    valid, errors = verify_ledger_chain(entries)
    if not valid:
        raise ValueError("저장된 Ledger Chain이 올바르지 않습니다: " + "; ".join(errors))
    return payload
