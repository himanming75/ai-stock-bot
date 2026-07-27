import hashlib
import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from backtest.manual_paper_run_orchestrator import (
    ManualPaperRunOrchestratorResult,
    STAGE_ORDER,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent

MANUAL_PAPER_RUN_AUDIT_OUTPUT_DIRECTORY = (
    PROJECT_ROOT
    / "output"
    / "trading_engine"
    / "manual_paper_run_audit_trail"
)

GENESIS_HASH = "0" * 64

VALID_SOURCE_STATUSES = {
    "COMPLETED",
    "BLOCKED",
    "FAILED",
}

VALID_EVENT_TYPES = {
    "ORCHESTRATION_STARTED",
    "STAGE_RECORDED",
    "ORCHESTRATION_FINISHED",
}

VALID_AUDIT_STATUSES = {
    "RECORDED",
    "BLOCKED",
    "FAILED",
}


@dataclass(frozen=True)
class ManualPaperRunAuditPolicy:
    """
    V11.7 Manual Paper Run Audit Trail 정책입니다.

    Audit 기록은 V11.6 실행 결과를 읽어서 생성할 뿐,
    Paper Pipeline이나 Broker 주문을 다시 실행하지 않습니다.
    """

    required_source_version: str = "V11.6"
    hash_algorithm: str = "SHA256"
    genesis_hash: str = GENESIS_HASH
    maximum_history_records: int = 100

    require_complete_stage_sequence: bool = True
    require_source_safety: bool = True
    reject_duplicate_orchestration: bool = True
    verify_hash_chain_after_build: bool = True

    automatic_execution_disabled: bool = True
    paper_only: bool = True
    live_execution_disabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ManualPaperRunAuditEntry:
    sequence_number: int
    event_id: str
    event_type: str
    recorded_at: str

    orchestration_id: str
    manual_actor: str

    stage_name: str | None
    stage_order: int | None
    stage_called: bool | None
    stage_completed: bool | None
    stage_status: str | None
    stage_all_checks_passed: bool | None
    stage_error_message: str | None

    source_status: str
    source_all_checks_passed: bool
    failed_stage_name: str | None

    execution_blocked: bool
    broker_api_called: bool
    broker_order_created: bool
    live_order_created: bool
    live_execution_authorized: bool

    previous_hash: str
    entry_hash: str

    def payload_without_hash(self) -> dict[str, Any]:
        payload = asdict(self)
        payload.pop("entry_hash", None)
        return payload

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ManualPaperRunAuditTrailResult:
    version: str
    created_at: str
    audit_trail_id: str

    audit_status: str
    audit_status_label: str

    source_version: str | None
    source_orchestration_id: str | None
    source_status: str | None
    manual_actor: str | None

    total_entry_count: int
    first_entry_hash: str | None
    last_entry_hash: str | None

    policy_checks_passed: bool
    source_checks_passed: bool
    sequence_checks_passed: bool
    duplicate_checks_passed: bool
    hash_chain_checks_passed: bool
    safety_checks_passed: bool
    all_checks_passed: bool

    automatic_execution_authorized: bool
    execution_blocked: bool
    broker_api_called: bool
    broker_order_created: bool
    live_order_created: bool
    live_execution_authorized: bool

    audit_policy: ManualPaperRunAuditPolicy
    audit_entries: tuple[
        ManualPaperRunAuditEntry,
        ...,
    ]
    orchestration_history: tuple[str, ...]

    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)

    report_path: str | None = None
    latest_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["audit_policy"] = (
            self.audit_policy.to_dict()
        )
        payload["audit_entries"] = [
            entry.to_dict()
            for entry in self.audit_entries
        ]
        payload["orchestration_history"] = list(
            self.orchestration_history
        )
        return payload


def write_json_file(
    path: Path,
    payload: dict[str, Any],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(
        path.suffix + ".tmp"
    )
    with temporary_path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            payload,
            file,
            ensure_ascii=False,
            indent=2,
        )
    temporary_path.replace(path)


def read_json_file(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        payload = json.load(file)
    if not isinstance(payload, dict):
        raise ValueError(
            "JSON 최상위 값은 object여야 합니다."
        )
    return payload


def canonical_json(payload: dict[str, Any]) -> str:
    """
    동일한 Audit Entry는 항상 동일한 문자열과 Hash를 만들도록
    Key 순서와 JSON 표현을 고정합니다.
    """

    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def calculate_entry_hash(
    payload: dict[str, Any],
) -> str:
    return hashlib.sha256(
        canonical_json(payload).encode("utf-8")
    ).hexdigest()


def validate_audit_policy(
    policy: ManualPaperRunAuditPolicy,
) -> tuple[bool, list[str]]:
    if not isinstance(
        policy,
        ManualPaperRunAuditPolicy,
    ):
        return (
            False,
            ["Audit Policy 형식이 올바르지 않습니다."],
        )

    errors: list[str] = []

    if policy.required_source_version != "V11.6":
        errors.append(
            "Required Source Version은 V11.6이어야 합니다."
        )
    if policy.hash_algorithm != "SHA256":
        errors.append(
            "Hash Algorithm은 SHA256이어야 합니다."
        )
    if (
        policy.genesis_hash != GENESIS_HASH
        or len(policy.genesis_hash) != 64
    ):
        errors.append(
            "Genesis Hash가 올바르지 않습니다."
        )
    if (
        not isinstance(
            policy.maximum_history_records,
            int,
        )
        or policy.maximum_history_records <= 0
    ):
        errors.append(
            "Maximum History Records가 올바르지 않습니다."
        )

    required_true_values = {
        "require_complete_stage_sequence": (
            policy.require_complete_stage_sequence
        ),
        "require_source_safety": (
            policy.require_source_safety
        ),
        "reject_duplicate_orchestration": (
            policy.reject_duplicate_orchestration
        ),
        "verify_hash_chain_after_build": (
            policy.verify_hash_chain_after_build
        ),
        "automatic_execution_disabled": (
            policy.automatic_execution_disabled
        ),
        "paper_only": policy.paper_only,
        "live_execution_disabled": (
            policy.live_execution_disabled
        ),
    }

    for name, value in required_true_values.items():
        if value is not True:
            errors.append(
                f"{name}는 V11.7에서 True여야 합니다."
            )

    return (not errors, errors)


def validate_source_result(
    source: Any,
) -> tuple[
    bool,
    bool,
    bool,
    list[str],
]:
    errors: list[str] = []

    if not isinstance(
        source,
        ManualPaperRunOrchestratorResult,
    ):
        return (
            False,
            False,
            False,
            ["Source는 V11.6 Orchestrator Result여야 합니다."],
        )

    source_valid = True
    if source.version != "V11.6":
        source_valid = False
        errors.append(
            "Source Version이 V11.6이 아닙니다."
        )
    if (
        not isinstance(
            source.orchestration_id,
            str,
        )
        or not source.orchestration_id.strip()
    ):
        source_valid = False
        errors.append(
            "Source Orchestration ID가 비어 있습니다."
        )
    if (
        source.orchestrator_status
        not in VALID_SOURCE_STATUSES
    ):
        source_valid = False
        errors.append(
            "Source Status가 올바르지 않습니다."
        )
    if (
        not isinstance(
            source.manual_actor,
            str,
        )
        or not source.manual_actor.strip()
    ):
        source_valid = False
        errors.append(
            "Source Manual Actor가 비어 있습니다."
        )

    records = source.stage_records
    sequence_valid = bool(
        isinstance(records, tuple)
        and len(records) == len(STAGE_ORDER)
        and tuple(
            record.stage_name
            for record in records
        )
        == STAGE_ORDER
        and tuple(
            record.stage_order
            for record in records
        )
        == tuple(
            range(1, len(STAGE_ORDER) + 1)
        )
    )
    if not sequence_valid:
        errors.append(
            "Source Stage 순서 또는 개수가 올바르지 않습니다."
        )

    safety_valid = bool(
        source.execution_blocked is True
        and source.automatic_execution_authorized is False
        and source.broker_api_called is False
        and source.broker_order_created is False
        and source.live_order_created is False
        and source.live_execution_authorized is False
        and all(
            record.execution_blocked is True
            and record.broker_api_called is False
            and record.broker_order_created is False
            and record.live_order_created is False
            and record.live_execution_authorized is False
            for record in records
        )
    )
    if not safety_valid:
        errors.append(
            "Source Result에 실거래 안전 오류가 있습니다."
        )

    return (
        source_valid,
        sequence_valid,
        safety_valid,
        errors,
    )


def create_audit_entry(
    *,
    sequence_number: int,
    event_type: str,
    source: ManualPaperRunOrchestratorResult,
    previous_hash: str,
    stage_record: Any = None,
) -> ManualPaperRunAuditEntry:
    if event_type not in VALID_EVENT_TYPES:
        raise ValueError(
            "Audit Event Type이 올바르지 않습니다."
        )

    entry_values: dict[str, Any] = {
        "sequence_number": sequence_number,
        "event_id": str(uuid.uuid4()),
        "event_type": event_type,
        "recorded_at": datetime.now().isoformat(),
        "orchestration_id": source.orchestration_id,
        "manual_actor": source.manual_actor,
        "stage_name": (
            stage_record.stage_name
            if stage_record is not None
            else None
        ),
        "stage_order": (
            stage_record.stage_order
            if stage_record is not None
            else None
        ),
        "stage_called": (
            stage_record.called
            if stage_record is not None
            else None
        ),
        "stage_completed": (
            stage_record.completed
            if stage_record is not None
            else None
        ),
        "stage_status": (
            stage_record.result_status
            if stage_record is not None
            else None
        ),
        "stage_all_checks_passed": (
            stage_record.all_checks_passed
            if stage_record is not None
            else None
        ),
        "stage_error_message": (
            stage_record.error_message
            if stage_record is not None
            else None
        ),
        "source_status": source.orchestrator_status,
        "source_all_checks_passed": (
            source.all_checks_passed
        ),
        "failed_stage_name": source.failed_stage_name,
        "execution_blocked": True,
        "broker_api_called": False,
        "broker_order_created": False,
        "live_order_created": False,
        "live_execution_authorized": False,
        "previous_hash": previous_hash,
    }
    entry_hash = calculate_entry_hash(entry_values)

    return ManualPaperRunAuditEntry(
        **entry_values,
        entry_hash=entry_hash,
    )


def verify_audit_chain(
    entries: tuple[
        ManualPaperRunAuditEntry,
        ...,
    ],
    genesis_hash: str = GENESIS_HASH,
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    previous_hash = genesis_hash

    for expected_sequence, entry in enumerate(
        entries,
        start=1,
    ):
        if not isinstance(
            entry,
            ManualPaperRunAuditEntry,
        ):
            errors.append(
                f"{expected_sequence}번 Audit Entry 형식이 잘못되었습니다."
            )
            continue
        if entry.sequence_number != expected_sequence:
            errors.append(
                f"{expected_sequence}번 Sequence가 올바르지 않습니다."
            )
        if entry.event_type not in VALID_EVENT_TYPES:
            errors.append(
                f"{expected_sequence}번 Event Type이 올바르지 않습니다."
            )
        if entry.previous_hash != previous_hash:
            errors.append(
                f"{expected_sequence}번 Previous Hash가 일치하지 않습니다."
            )

        calculated_hash = calculate_entry_hash(
            entry.payload_without_hash()
        )
        if entry.entry_hash != calculated_hash:
            errors.append(
                f"{expected_sequence}번 Entry Hash가 일치하지 않습니다."
            )
        previous_hash = entry.entry_hash

    return (not errors, errors)


def normalize_history(
    existing_history: tuple[str, ...] | list[str] | None,
    maximum_records: int,
) -> tuple[str, ...]:
    if existing_history is None:
        return ()
    if not isinstance(
        existing_history,
        (tuple, list),
    ):
        raise TypeError(
            "Existing History는 tuple 또는 list여야 합니다."
        )

    cleaned: list[str] = []
    for orchestration_id in existing_history:
        if (
            not isinstance(orchestration_id, str)
            or not orchestration_id.strip()
        ):
            raise ValueError(
                "History의 Orchestration ID가 올바르지 않습니다."
            )
        cleaned.append(orchestration_id.strip())

    return tuple(cleaned[-maximum_records:])


def build_manual_paper_run_audit_trail(
    source_result: Any,
    existing_history: (
        tuple[str, ...]
        | list[str]
        | None
    ) = None,
    audit_policy: (
        ManualPaperRunAuditPolicy
        | None
    ) = None,
) -> ManualPaperRunAuditTrailResult:
    """
    V11.6 Result를 변경하거나 다시 실행하지 않고 Audit Trail을 만듭니다.
    """

    policy = (
        audit_policy
        if audit_policy is not None
        else ManualPaperRunAuditPolicy()
    )
    policy_valid, policy_errors = (
        validate_audit_policy(policy)
    )

    try:
        history = normalize_history(
            existing_history,
            policy.maximum_history_records,
        )
        history_valid = True
        history_errors: list[str] = []
    except (TypeError, ValueError) as error:
        history = ()
        history_valid = False
        history_errors = [str(error)]

    (
        source_valid,
        sequence_valid,
        safety_valid,
        source_errors,
    ) = validate_source_result(source_result)

    source_id = getattr(
        source_result,
        "orchestration_id",
        None,
    )
    duplicate_valid = bool(
        isinstance(source_id, str)
        and source_id not in history
    )
    duplicate_errors: list[str] = []
    if not duplicate_valid:
        duplicate_errors.append(
            "동일한 Orchestration ID가 이미 Audit History에 있습니다."
        )

    preflight_valid = bool(
        policy_valid
        and history_valid
        and source_valid
        and sequence_valid
        and safety_valid
        and duplicate_valid
    )

    entries: list[ManualPaperRunAuditEntry] = []
    hash_errors: list[str] = []

    if preflight_valid:
        previous_hash = policy.genesis_hash
        started_entry = create_audit_entry(
            sequence_number=1,
            event_type="ORCHESTRATION_STARTED",
            source=source_result,
            previous_hash=previous_hash,
        )
        entries.append(started_entry)
        previous_hash = started_entry.entry_hash

        for stage_record in source_result.stage_records:
            stage_entry = create_audit_entry(
                sequence_number=len(entries) + 1,
                event_type="STAGE_RECORDED",
                source=source_result,
                previous_hash=previous_hash,
                stage_record=stage_record,
            )
            entries.append(stage_entry)
            previous_hash = stage_entry.entry_hash

        finished_entry = create_audit_entry(
            sequence_number=len(entries) + 1,
            event_type="ORCHESTRATION_FINISHED",
            source=source_result,
            previous_hash=previous_hash,
        )
        entries.append(finished_entry)

        hash_valid, hash_errors = verify_audit_chain(
            tuple(entries),
            policy.genesis_hash,
        )
    else:
        hash_valid = False

    audit_sequence_valid = bool(
        preflight_valid
        and len(entries) == len(STAGE_ORDER) + 2
        and entries[0].event_type
        == "ORCHESTRATION_STARTED"
        and entries[-1].event_type
        == "ORCHESTRATION_FINISHED"
        and tuple(
            entry.stage_name
            for entry in entries[1:-1]
        )
        == STAGE_ORDER
    )
    all_checks_passed = bool(
        preflight_valid
        and audit_sequence_valid
        and hash_valid
    )

    if all_checks_passed:
        audit_status = "RECORDED"
        audit_status_label = (
            "Manual Paper Run 감사 기록 완료"
        )
        updated_history = (
            *history,
            source_result.orchestration_id,
        )[-policy.maximum_history_records:]
        reasons = [
            "V11.6 실행의 시작, 6개 Stage 및 종료가 기록되었습니다.",
            "모든 Audit Entry가 SHA-256 Hash Chain으로 연결되었습니다.",
        ]
        next_actions = [
            "Audit Trail의 마지막 Hash를 보관합니다.",
            "다음 Paper Run은 새로운 Orchestration ID로 실행합니다.",
        ]
    elif duplicate_valid is False:
        audit_status = "BLOCKED"
        audit_status_label = (
            "중복 Orchestration 감사 기록 차단"
        )
        updated_history = history
        reasons = [
            "이미 기록된 Orchestration ID는 다시 추가할 수 없습니다."
        ]
        next_actions = [
            "새로운 V11.6 Manual Paper Run 결과를 사용합니다.",
        ]
    else:
        audit_status = "FAILED"
        audit_status_label = (
            "Manual Paper Run 감사 사전검사 실패"
        )
        updated_history = history
        reasons = [
            "Policy, Source, Sequence 또는 Safety 검사에 실패했습니다."
        ]
        next_actions = [
            "Warnings에서 Audit 실패 원인을 확인합니다.",
            "Source를 수정하지 말고 안전한 새 실행 결과를 생성합니다.",
        ]

    warnings = [
        *policy_errors,
        *history_errors,
        *source_errors,
        *duplicate_errors,
        *hash_errors,
        "V11.7은 감사 기록만 생성하며 Paper Pipeline을 실행하지 않습니다.",
        "Broker API, 실제 주문 및 Live Execution은 허용하지 않습니다.",
    ]

    result = ManualPaperRunAuditTrailResult(
        version="V11.7",
        created_at=datetime.now().isoformat(),
        audit_trail_id=str(uuid.uuid4()),
        audit_status=audit_status,
        audit_status_label=audit_status_label,
        source_version=getattr(
            source_result,
            "version",
            None,
        ),
        source_orchestration_id=source_id,
        source_status=getattr(
            source_result,
            "orchestrator_status",
            None,
        ),
        manual_actor=getattr(
            source_result,
            "manual_actor",
            None,
        ),
        total_entry_count=len(entries),
        first_entry_hash=(
            entries[0].entry_hash
            if entries
            else None
        ),
        last_entry_hash=(
            entries[-1].entry_hash
            if entries
            else None
        ),
        policy_checks_passed=policy_valid,
        source_checks_passed=source_valid,
        sequence_checks_passed=(
            sequence_valid
            and audit_sequence_valid
        ),
        duplicate_checks_passed=duplicate_valid,
        hash_chain_checks_passed=hash_valid,
        safety_checks_passed=safety_valid,
        all_checks_passed=all_checks_passed,
        automatic_execution_authorized=False,
        execution_blocked=True,
        broker_api_called=False,
        broker_order_created=False,
        live_order_created=False,
        live_execution_authorized=False,
        audit_policy=policy,
        audit_entries=tuple(entries),
        orchestration_history=tuple(
            updated_history
        ),
        reasons=reasons,
        warnings=warnings,
        next_actions=next_actions,
    )

    print_manual_paper_run_audit_trail(result)
    return result


def verify_saved_audit_payload(
    payload: dict[str, Any],
) -> tuple[bool, list[str]]:
    """
    JSON에서 읽은 Audit Entry의 Hash Chain을 독립적으로 검사합니다.
    파일 내용 한 글자라도 바뀌면 검사가 실패합니다.
    """

    errors: list[str] = []
    raw_entries = payload.get("audit_entries")
    if not isinstance(raw_entries, list):
        return (
            False,
            ["Audit Entries가 list가 아닙니다."],
        )

    previous_hash = GENESIS_HASH
    for expected_sequence, raw_entry in enumerate(
        raw_entries,
        start=1,
    ):
        if not isinstance(raw_entry, dict):
            errors.append(
                f"{expected_sequence}번 Entry가 object가 아닙니다."
            )
            continue

        entry_hash = raw_entry.get("entry_hash")
        payload_without_hash = dict(raw_entry)
        payload_without_hash.pop("entry_hash", None)

        if (
            raw_entry.get("sequence_number")
            != expected_sequence
        ):
            errors.append(
                f"{expected_sequence}번 Sequence가 일치하지 않습니다."
            )
        if (
            raw_entry.get("previous_hash")
            != previous_hash
        ):
            errors.append(
                f"{expected_sequence}번 Previous Hash가 일치하지 않습니다."
            )

        calculated_hash = calculate_entry_hash(
            payload_without_hash
        )
        if entry_hash != calculated_hash:
            errors.append(
                f"{expected_sequence}번 Entry Hash가 일치하지 않습니다."
            )

        if isinstance(entry_hash, str):
            previous_hash = entry_hash

    if raw_entries:
        if (
            payload.get("first_entry_hash")
            != raw_entries[0].get("entry_hash")
        ):
            errors.append(
                "First Entry Hash가 일치하지 않습니다."
            )
        if (
            payload.get("last_entry_hash")
            != raw_entries[-1].get("entry_hash")
        ):
            errors.append(
                "Last Entry Hash가 일치하지 않습니다."
            )

    return (not errors, errors)


def save_manual_paper_run_audit_trail(
    result: ManualPaperRunAuditTrailResult,
) -> tuple[Path, Path]:
    if not isinstance(
        result,
        ManualPaperRunAuditTrailResult,
    ):
        raise TypeError(
            "V11.7 Audit Trail Result 형식이 아닙니다."
        )
    if not result.all_checks_passed:
        raise ValueError(
            "검사에 실패한 Audit Trail은 저장할 수 없습니다."
        )

    directory = (
        MANUAL_PAPER_RUN_AUDIT_OUTPUT_DIRECTORY
    )
    directory.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S_%f"
    )
    report_path = directory / (
        f"manual_paper_run_audit_trail_{timestamp}.json"
    )
    latest_path = directory / (
        "manual_paper_run_audit_trail_latest.json"
    )

    result.report_path = str(report_path)
    result.latest_path = str(latest_path)
    payload = result.to_dict()
    payload_valid, payload_errors = (
        verify_saved_audit_payload(payload)
    )
    if not payload_valid:
        raise RuntimeError(
            "저장 전 Audit Hash 검사가 실패했습니다: "
            + " | ".join(payload_errors)
        )

    write_json_file(report_path, payload)
    write_json_file(latest_path, payload)
    return (report_path, latest_path)


def load_latest_manual_paper_run_audit_trail(
    verify_hash_chain: bool = True,
) -> dict[str, Any]:
    path = (
        MANUAL_PAPER_RUN_AUDIT_OUTPUT_DIRECTORY
        / "manual_paper_run_audit_trail_latest.json"
    )
    payload = read_json_file(path)

    if verify_hash_chain:
        valid, errors = verify_saved_audit_payload(
            payload
        )
        if not valid:
            raise RuntimeError(
                "저장된 Audit Hash 검사가 실패했습니다: "
                + " | ".join(errors)
            )
    return payload


def print_manual_paper_run_audit_trail(
    result: ManualPaperRunAuditTrailResult,
) -> None:
    line_length = 120
    print()
    print("=" * line_length)
    print("V11.7 MANUAL PAPER RUN AUDIT TRAIL")
    print("=" * line_length)
    print(
        f"Audit status                  : "
        f"{result.audit_status}"
    )
    print(
        f"Audit status label            : "
        f"{result.audit_status_label}"
    )
    print(
        f"Source orchestration ID       : "
        f"{result.source_orchestration_id}"
    )
    print(
        f"Source status                 : "
        f"{result.source_status}"
    )
    print(
        f"Manual actor                  : "
        f"{result.manual_actor}"
    )
    print(
        f"Audit entries                 : "
        f"{result.total_entry_count}"
    )
    print(
        f"Last entry hash               : "
        f"{result.last_entry_hash}"
    )

    print()
    print("AUDIT EVENTS")
    print("-" * line_length)
    for entry in result.audit_entries:
        print(
            f"{entry.sequence_number}. "
            f"{entry.event_type:<24} "
            f"Stage={str(entry.stage_name):<26} "
            f"Hash={entry.entry_hash[:16]}..."
        )

    print()
    print("VALIDATION")
    print("-" * line_length)
    print(
        f"Policy checks passed          : "
        f"{result.policy_checks_passed}"
    )
    print(
        f"Source checks passed          : "
        f"{result.source_checks_passed}"
    )
    print(
        f"Sequence checks passed        : "
        f"{result.sequence_checks_passed}"
    )
    print(
        f"Duplicate checks passed       : "
        f"{result.duplicate_checks_passed}"
    )
    print(
        f"Hash chain checks passed      : "
        f"{result.hash_chain_checks_passed}"
    )
    print(
        f"Safety checks passed          : "
        f"{result.safety_checks_passed}"
    )
    print(
        f"All checks passed             : "
        f"{result.all_checks_passed}"
    )

    print()
    print("EXECUTION SAFETY")
    print("-" * line_length)
    print(
        f"Automatic execution authorized: "
        f"{result.automatic_execution_authorized}"
    )
    print(
        f"Execution blocked             : "
        f"{result.execution_blocked}"
    )
    print(
        f"Broker API called             : "
        f"{result.broker_api_called}"
    )
    print(
        f"Broker order created          : "
        f"{result.broker_order_created}"
    )
    print(
        f"Live order created            : "
        f"{result.live_order_created}"
    )
    print(
        f"Live execution authorized     : "
        f"{result.live_execution_authorized}"
    )

    if result.reasons:
        print()
        print("REASONS")
        print("-" * line_length)
        for reason in result.reasons:
            print(f"- {reason}")

    if result.warnings:
        print()
        print("WARNINGS")
        print("-" * line_length)
        for warning in result.warnings:
            print(f"- {warning}")

    print()
    print("FILES")
    print("-" * line_length)
    print(
        f"Report file                   : "
        f"{result.report_path or 'Not saved yet'}"
    )
    print(
        f"Latest file                   : "
        f"{result.latest_path or 'Not saved yet'}"
    )
    print("=" * line_length)
    print(
        "주의: V11.7은 감사 기록만 생성하며 "
        "Broker 주문을 수행하지 않습니다."
    )
