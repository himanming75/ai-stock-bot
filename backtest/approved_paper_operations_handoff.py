import hashlib
import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from backtest.paper_trading_manual_review_decision import (
    PaperTradingManualReviewDecisionResult,
    verify_decision_record_chain,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
APPROVED_PAPER_OPERATIONS_HANDOFF_OUTPUT_DIRECTORY = (
    PROJECT_ROOT
    / "output"
    / "trading_engine"
    / "approved_paper_operations_handoff"
)

REQUIRED_HANDOFF_TEXT = (
    "HANDOFF APPROVED PAPER OPERATIONS"
)
GENESIS_HANDOFF_HASH = "0" * 64
VALID_HANDOFF_STATUSES = {
    "HANDED_OFF",
    "BLOCKED",
    "FAILED",
}


@dataclass(frozen=True)
class ApprovedPaperOperationsHandoffPolicy:
    """V12.5 승인된 Paper 운영 전달 정책입니다."""

    required_decision_version: str = "V12.4"
    required_result_status: str = "RECORDED"
    required_decision: str = "APPROVE"
    required_next_review_status: str = "APPROVED"
    required_handoff_text: str = REQUIRED_HANDOFF_TEXT
    minimum_note_length: int = 10
    maximum_handoff_records: int = 100
    hash_algorithm: str = "SHA256"
    genesis_hash: str = GENESIS_HANDOFF_HASH

    require_decision_all_checks: bool = True
    require_decision_hash_chain: bool = True
    require_same_operator_as_reviewer: bool = True
    require_source_safety: bool = True
    reject_duplicate_decision_record: bool = True
    verify_existing_handoff_chain: bool = True
    verify_updated_handoff_chain: bool = True

    paper_preparation_only: bool = True
    automatic_execution_disabled: bool = True
    broker_execution_disabled: bool = True
    live_execution_disabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ApprovedPaperOperationsHandoffRecord:
    sequence_number: int
    handoff_record_id: str
    handed_off_at: str

    manual_review_decision_id: str
    decision_record_id: str
    review_queue_id: str
    queue_item_id: str
    checklist_id: str

    decision: str
    reviewer_name: str
    handoff_operator: str
    handoff_note: str
    handoff_status: str

    paper_preparation_authorized: bool
    paper_execution_authorized: bool
    execution_blocked: bool
    broker_api_called: bool
    broker_order_created: bool
    live_order_created: bool
    live_execution_authorized: bool

    previous_hash: str
    record_hash: str

    def payload_without_hash(self) -> dict[str, Any]:
        payload = asdict(self)
        payload.pop("record_hash", None)
        return payload

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ApprovedPaperOperationsHandoffResult:
    version: str
    created_at: str
    approved_handoff_id: str

    handoff_status: str
    handoff_status_label: str
    source_decision: str | None
    handoff_operator: str | None
    latest_handoff_record_id: str | None
    latest_decision_record_id: str | None

    total_handoff_count: int
    records_trimmed: int
    first_sequence_number: int | None
    last_sequence_number: int | None
    first_record_hash: str | None
    last_record_hash: str | None

    policy_checks_passed: bool
    input_checks_passed: bool
    source_checks_passed: bool
    decision_chain_checks_passed: bool
    approval_checks_passed: bool
    operator_checks_passed: bool
    duplicate_checks_passed: bool
    existing_chain_checks_passed: bool
    updated_chain_checks_passed: bool
    safety_checks_passed: bool
    all_checks_passed: bool

    paper_preparation_authorized: bool
    paper_execution_authorized: bool
    automatic_execution_authorized: bool
    execution_blocked: bool
    broker_api_called: bool
    broker_order_created: bool
    live_order_created: bool
    live_execution_authorized: bool

    handoff_policy: ApprovedPaperOperationsHandoffPolicy
    handoff_records: tuple[
        ApprovedPaperOperationsHandoffRecord,
        ...,
    ]

    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)
    report_path: str | None = None
    latest_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["handoff_policy"] = (
            self.handoff_policy.to_dict()
        )
        payload["handoff_records"] = [
            record.to_dict()
            for record in self.handoff_records
        ]
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
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def calculate_handoff_record_hash(
    payload: dict[str, Any],
) -> str:
    return hashlib.sha256(
        canonical_json(payload).encode("utf-8")
    ).hexdigest()


def validate_handoff_policy(
    policy: ApprovedPaperOperationsHandoffPolicy,
) -> tuple[bool, list[str]]:
    if not isinstance(
        policy,
        ApprovedPaperOperationsHandoffPolicy,
    ):
        return (
            False,
            ["Approved Handoff Policy 형식이 올바르지 않습니다."],
        )
    errors: list[str] = []
    required_values = {
        "required_decision_version": "V12.4",
        "required_result_status": "RECORDED",
        "required_decision": "APPROVE",
        "required_next_review_status": "APPROVED",
        "required_handoff_text": REQUIRED_HANDOFF_TEXT,
        "hash_algorithm": "SHA256",
        "genesis_hash": GENESIS_HANDOFF_HASH,
    }
    for name, expected in required_values.items():
        if getattr(policy, name) != expected:
            errors.append(
                f"{name} 값이 V12.5 기준과 다릅니다."
            )
    if (
        not isinstance(policy.minimum_note_length, int)
        or policy.minimum_note_length < 1
    ):
        errors.append(
            "Minimum Note Length가 올바르지 않습니다."
        )
    if (
        not isinstance(policy.maximum_handoff_records, int)
        or policy.maximum_handoff_records <= 0
    ):
        errors.append(
            "Maximum Handoff Records가 올바르지 않습니다."
        )
    true_values = {
        "require_decision_all_checks": (
            policy.require_decision_all_checks
        ),
        "require_decision_hash_chain": (
            policy.require_decision_hash_chain
        ),
        "require_same_operator_as_reviewer": (
            policy.require_same_operator_as_reviewer
        ),
        "require_source_safety": (
            policy.require_source_safety
        ),
        "reject_duplicate_decision_record": (
            policy.reject_duplicate_decision_record
        ),
        "verify_existing_handoff_chain": (
            policy.verify_existing_handoff_chain
        ),
        "verify_updated_handoff_chain": (
            policy.verify_updated_handoff_chain
        ),
        "paper_preparation_only": (
            policy.paper_preparation_only
        ),
        "automatic_execution_disabled": (
            policy.automatic_execution_disabled
        ),
        "broker_execution_disabled": (
            policy.broker_execution_disabled
        ),
        "live_execution_disabled": (
            policy.live_execution_disabled
        ),
    }
    for name, value in true_values.items():
        if value is not True:
            errors.append(
                f"{name}는 V12.5에서 True여야 합니다."
            )
    return (not errors, errors)


def validate_decision_source(
    decision_result: Any,
) -> tuple[bool, bool, bool, list[str]]:
    if not isinstance(
        decision_result,
        PaperTradingManualReviewDecisionResult,
    ):
        return (
            False,
            False,
            False,
            ["Decision Result는 V12.4 형식이어야 합니다."],
        )
    errors: list[str] = []
    source_valid = bool(
        decision_result.version == "V12.4"
        and decision_result.result_status == "RECORDED"
        and decision_result.all_checks_passed
        and decision_result.decision_records
    )
    if not source_valid:
        errors.append(
            "RECORDED이며 All Checks를 통과한 V12.4 Result가 아닙니다."
        )
    approval_valid = bool(
        source_valid
        and decision_result.decision == "APPROVE"
        and decision_result.next_review_status == "APPROVED"
        and decision_result.decision_records[-1].decision
        == "APPROVE"
    )
    if source_valid and not approval_valid:
        errors.append(
            "APPROVE 판정만 Handoff할 수 있습니다."
        )
    safety_valid = bool(
        decision_result.paper_execution_authorized is False
        and decision_result
        .automatic_execution_authorized is False
        and decision_result.execution_blocked is True
        and decision_result.broker_api_called is False
        and decision_result.broker_order_created is False
        and decision_result.live_order_created is False
        and decision_result
        .live_execution_authorized is False
    )
    if not safety_valid:
        errors.append(
            "Decision Source에 실행 안전 오류가 있습니다."
        )
    return (
        source_valid,
        approval_valid,
        safety_valid,
        errors,
    )


def normalize_handoff_records(
    existing_records: Any,
) -> tuple[ApprovedPaperOperationsHandoffRecord, ...]:
    if existing_records is None:
        return ()
    if not isinstance(existing_records, (tuple, list)):
        raise TypeError(
            "Existing Handoff Records는 tuple 또는 list여야 합니다."
        )
    records: list[
        ApprovedPaperOperationsHandoffRecord
    ] = []
    for record in existing_records:
        if not isinstance(
            record,
            ApprovedPaperOperationsHandoffRecord,
        ):
            raise TypeError(
                "Existing Handoff Record 형식이 올바르지 않습니다."
            )
        records.append(record)
    return tuple(records)


def verify_handoff_record_chain(
    records: tuple[
        ApprovedPaperOperationsHandoffRecord,
        ...,
    ],
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if not records:
        return (True, errors)
    previous_sequence: int | None = None
    expected_previous_hash = records[0].previous_hash
    if (
        not isinstance(expected_previous_hash, str)
        or len(expected_previous_hash) != 64
    ):
        errors.append(
            "첫 Handoff Record의 Anchor Hash가 올바르지 않습니다."
        )
    for record in records:
        if (
            previous_sequence is not None
            and record.sequence_number
            != previous_sequence + 1
        ):
            errors.append(
                f"{record.sequence_number}번 Handoff Sequence가 연속되지 않습니다."
            )
        if record.previous_hash != expected_previous_hash:
            errors.append(
                f"{record.sequence_number}번 Previous Hash가 일치하지 않습니다."
            )
        expected_hash = calculate_handoff_record_hash(
            record.payload_without_hash()
        )
        if record.record_hash != expected_hash:
            errors.append(
                f"{record.sequence_number}번 Handoff Hash가 일치하지 않습니다."
            )
        previous_sequence = record.sequence_number
        expected_previous_hash = record.record_hash
    return (not errors, errors)


def create_handoff_record(
    decision_result: (
        PaperTradingManualReviewDecisionResult
    ),
    operator: str,
    note: str,
    sequence_number: int,
    previous_hash: str,
) -> ApprovedPaperOperationsHandoffRecord:
    source_record = decision_result.decision_records[-1]
    values: dict[str, Any] = {
        "sequence_number": sequence_number,
        "handoff_record_id": str(uuid.uuid4()),
        "handed_off_at": datetime.now().isoformat(),
        "manual_review_decision_id": (
            decision_result.manual_review_decision_id
        ),
        "decision_record_id": (
            source_record.decision_record_id
        ),
        "review_queue_id": source_record.review_queue_id,
        "queue_item_id": source_record.queue_item_id,
        "checklist_id": source_record.checklist_id,
        "decision": source_record.decision,
        "reviewer_name": source_record.reviewer_name,
        "handoff_operator": operator.strip(),
        "handoff_note": note.strip(),
        "handoff_status": "HANDED_OFF",
        "paper_preparation_authorized": True,
        "paper_execution_authorized": False,
        "execution_blocked": True,
        "broker_api_called": False,
        "broker_order_created": False,
        "live_order_created": False,
        "live_execution_authorized": False,
        "previous_hash": previous_hash,
    }
    record_hash = calculate_handoff_record_hash(values)
    return ApprovedPaperOperationsHandoffRecord(
        **values,
        record_hash=record_hash,
    )


def handoff_approved_paper_operations(
    decision_result: Any,
    handoff_operator: Any,
    handoff_note: Any,
    confirmation_text: Any,
    existing_records: Any = None,
    handoff_policy: (
        ApprovedPaperOperationsHandoffPolicy
        | None
    ) = None,
) -> ApprovedPaperOperationsHandoffResult:
    policy = (
        handoff_policy
        if handoff_policy is not None
        else ApprovedPaperOperationsHandoffPolicy()
    )
    policy_valid, policy_errors = (
        validate_handoff_policy(policy)
    )
    (
        source_valid,
        approval_valid,
        source_safety_valid,
        source_errors,
    ) = validate_decision_source(decision_result)

    text_valid = bool(
        isinstance(handoff_operator, str)
        and handoff_operator.strip()
        and isinstance(handoff_note, str)
        and isinstance(confirmation_text, str)
    )
    text_errors = (
        []
        if text_valid
        else [
            "Handoff Operator, Note와 Confirmation 입력이 올바르지 않습니다."
        ]
    )
    reviewer = getattr(
        decision_result,
        "reviewer_name",
        None,
    )
    operator_valid = bool(
        text_valid
        and handoff_operator.strip()
        == (reviewer or "").strip()
        and len(handoff_note.strip())
        >= policy.minimum_note_length
        and confirmation_text.strip()
        == policy.required_handoff_text
    )
    operator_errors: list[str] = []
    if text_valid:
        if handoff_operator.strip() != (reviewer or "").strip():
            operator_errors.append(
                "Handoff Operator가 Decision Reviewer와 일치하지 않습니다."
            )
        if (
            len(handoff_note.strip())
            < policy.minimum_note_length
        ):
            operator_errors.append(
                "Handoff Note가 너무 짧습니다."
            )
        if (
            confirmation_text.strip()
            != policy.required_handoff_text
        ):
            operator_errors.append(
                "Handoff Confirmation Text가 일치하지 않습니다."
            )

    if source_valid:
        decision_chain_valid, decision_chain_errors = (
            verify_decision_record_chain(
                decision_result.decision_records
            )
        )
        decision_record_id = (
            decision_result
            .decision_records[-1]
            .decision_record_id
        )
    else:
        decision_chain_valid = False
        decision_chain_errors = []
        decision_record_id = None

    try:
        normalized_records = normalize_handoff_records(
            existing_records
        )
        records_valid = True
        record_errors: list[str] = []
    except (TypeError, ValueError) as error:
        normalized_records = ()
        records_valid = False
        record_errors = [str(error)]

    if records_valid:
        existing_chain_valid, chain_errors = (
            verify_handoff_record_chain(
                normalized_records
            )
        )
    else:
        existing_chain_valid = False
        chain_errors = []

    duplicate_found = bool(
        decision_record_id
        and any(
            record.decision_record_id
            == decision_record_id
            for record in normalized_records
        )
    )
    duplicate_valid = bool(
        decision_record_id and not duplicate_found
    )
    duplicate_errors = (
        ["동일한 Decision Record가 이미 Handoff되었습니다."]
        if duplicate_found
        else []
    )

    preflight_valid = bool(
        policy_valid
        and source_valid
        and approval_valid
        and source_safety_valid
        and text_valid
        and operator_valid
        and decision_chain_valid
        and records_valid
        and existing_chain_valid
        and duplicate_valid
    )
    updated_records = normalized_records
    records_trimmed = 0
    updated_chain_valid = False
    updated_chain_errors: list[str] = []
    if preflight_valid:
        sequence_number = (
            normalized_records[-1].sequence_number + 1
            if normalized_records
            else 1
        )
        previous_hash = (
            normalized_records[-1].record_hash
            if normalized_records
            else policy.genesis_hash
        )
        new_record = create_handoff_record(
            decision_result,
            handoff_operator,
            handoff_note,
            sequence_number,
            previous_hash,
        )
        all_records = (*normalized_records, new_record)
        records_trimmed = max(
            0,
            len(all_records)
            - policy.maximum_handoff_records,
        )
        updated_records = tuple(
            all_records[
                -policy.maximum_handoff_records:
            ]
        )
        (
            updated_chain_valid,
            updated_chain_errors,
        ) = verify_handoff_record_chain(
            updated_records
        )

    all_checks_passed = bool(
        preflight_valid and updated_chain_valid
    )
    if all_checks_passed:
        status = "HANDED_OFF"
        label = "승인된 Paper 운영 준비 Handoff 완료"
        reasons = [
            "APPROVE Decision이 Paper 준비 단계로 전달되었습니다.",
            "Handoff SHA-256 Hash Chain이 검증되었습니다.",
        ]
        next_actions = [
            "전달된 내용을 다음 Paper 준비 검사에서 확인합니다.",
            "실행 전 별도의 수동 승인이 계속 필요합니다.",
        ]
    elif (
        duplicate_found
        or (
            source_valid
            and source_safety_valid
            and decision_chain_valid
            and (
                not approval_valid
                or not operator_valid
            )
        )
    ):
        status = "BLOCKED"
        label = "Approved Paper Operations Handoff 차단"
        reasons = [
            "승인, 수동 확인 또는 중복 검사에 통과하지 못했습니다."
        ]
        next_actions = [
            "APPROVE Source와 정확한 확인 문구를 사용합니다.",
        ]
    else:
        status = "FAILED"
        label = "Approved Paper Operations Handoff 검사 실패"
        reasons = [
            "Source, Policy, Hash Chain 또는 Safety 검사에 실패했습니다."
        ]
        next_actions = [
            "Warnings를 확인하고 Source를 다시 생성합니다.",
        ]

    latest_record = (
        updated_records[-1]
        if updated_records
        else None
    )
    return ApprovedPaperOperationsHandoffResult(
        version="V12.5",
        created_at=datetime.now().isoformat(),
        approved_handoff_id=str(uuid.uuid4()),
        handoff_status=status,
        handoff_status_label=label,
        source_decision=getattr(
            decision_result,
            "decision",
            None,
        ),
        handoff_operator=(
            handoff_operator.strip()
            if isinstance(handoff_operator, str)
            else None
        ),
        latest_handoff_record_id=(
            latest_record.handoff_record_id
            if latest_record
            else None
        ),
        latest_decision_record_id=(
            latest_record.decision_record_id
            if latest_record
            else None
        ),
        total_handoff_count=len(updated_records),
        records_trimmed=records_trimmed,
        first_sequence_number=(
            updated_records[0].sequence_number
            if updated_records
            else None
        ),
        last_sequence_number=(
            updated_records[-1].sequence_number
            if updated_records
            else None
        ),
        first_record_hash=(
            updated_records[0].record_hash
            if updated_records
            else None
        ),
        last_record_hash=(
            updated_records[-1].record_hash
            if updated_records
            else None
        ),
        policy_checks_passed=policy_valid,
        input_checks_passed=text_valid,
        source_checks_passed=source_valid,
        decision_chain_checks_passed=(
            decision_chain_valid
        ),
        approval_checks_passed=approval_valid,
        operator_checks_passed=operator_valid,
        duplicate_checks_passed=duplicate_valid,
        existing_chain_checks_passed=(
            existing_chain_valid
        ),
        updated_chain_checks_passed=(
            updated_chain_valid
        ),
        safety_checks_passed=source_safety_valid,
        all_checks_passed=all_checks_passed,
        paper_preparation_authorized=all_checks_passed,
        paper_execution_authorized=False,
        automatic_execution_authorized=False,
        execution_blocked=True,
        broker_api_called=False,
        broker_order_created=False,
        live_order_created=False,
        live_execution_authorized=False,
        handoff_policy=policy,
        handoff_records=updated_records,
        reasons=reasons,
        warnings=[
            *policy_errors,
            *source_errors,
            *text_errors,
            *operator_errors,
            *decision_chain_errors,
            *record_errors,
            *chain_errors,
            *duplicate_errors,
            *updated_chain_errors,
            "V12.5는 Paper 운영 준비 전달만 허용합니다.",
            "실제 Broker API, 실제 주문 및 Live Execution은 모두 차단됩니다.",
        ],
        next_actions=next_actions,
    )


def verify_saved_handoff_payload(
    payload: dict[str, Any],
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if payload.get("version") != "V12.5":
        errors.append(
            "저장된 Handoff Version이 V12.5가 아닙니다."
        )
    if payload.get("handoff_status") not in VALID_HANDOFF_STATUSES:
        errors.append(
            "저장된 Handoff Status가 올바르지 않습니다."
        )
    if payload.get("paper_execution_authorized") is not False:
        errors.append(
            "저장된 Handoff가 Paper Execution을 허용합니다."
        )
    if payload.get("execution_blocked") is not True:
        errors.append(
            "저장된 Handoff의 Execution이 차단되지 않았습니다."
        )
    for name in (
        "automatic_execution_authorized",
        "broker_api_called",
        "broker_order_created",
        "live_order_created",
        "live_execution_authorized",
    ):
        if payload.get(name) is not False:
            errors.append(
                f"저장된 {name} 값이 False가 아닙니다."
            )
    return (not errors, errors)


def save_approved_paper_operations_handoff(
    result: ApprovedPaperOperationsHandoffResult,
    output_directory: Path | None = None,
) -> ApprovedPaperOperationsHandoffResult:
    if not isinstance(
        result,
        ApprovedPaperOperationsHandoffResult,
    ):
        raise TypeError(
            "V12.5 Approved Handoff Result 형식이 아닙니다."
        )
    directory = (
        output_directory
        if output_directory is not None
        else APPROVED_PAPER_OPERATIONS_HANDOFF_OUTPUT_DIRECTORY
    )
    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S_%f"
    )
    report_path = directory / (
        f"approved_paper_operations_handoff_{timestamp}.json"
    )
    latest_path = directory / (
        "approved_paper_operations_handoff_latest.json"
    )
    payload = result.to_dict()
    write_json_file(report_path, payload)
    write_json_file(latest_path, payload)
    result.report_path = str(report_path)
    result.latest_path = str(latest_path)
    return result


def load_latest_approved_paper_operations_handoff(
    output_directory: Path | None = None,
) -> dict[str, Any]:
    directory = (
        output_directory
        if output_directory is not None
        else APPROVED_PAPER_OPERATIONS_HANDOFF_OUTPUT_DIRECTORY
    )
    return read_json_file(
        directory
        / "approved_paper_operations_handoff_latest.json"
    )


def print_approved_paper_operations_handoff(
    result: ApprovedPaperOperationsHandoffResult,
) -> None:
    line = "=" * 100
    print()
    print(line)
    print("V12.5 APPROVED PAPER OPERATIONS HANDOFF")
    print(line)
    print(f"Handoff status         : {result.handoff_status}")
    print(f"Source decision        : {result.source_decision}")
    print(f"Handoff operator       : {result.handoff_operator}")
    print(f"Total handoffs         : {result.total_handoff_count}")
    print(f"Paper preparation      : {result.paper_preparation_authorized}")
    print(f"Paper execution        : {result.paper_execution_authorized}")
    print(line)
    print(
        "주의: Paper 준비만 허용되며 실제 주문 실행은 차단됩니다."
    )

