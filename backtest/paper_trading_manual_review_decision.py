import hashlib
import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from backtest.paper_trading_operations_review_queue import (
    PaperTradingOperationsReviewQueueItem,
    PaperTradingOperationsReviewQueueResult,
    verify_review_queue_hash_chain,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent

PAPER_TRADING_MANUAL_REVIEW_DECISION_OUTPUT_DIRECTORY = (
    PROJECT_ROOT
    / "output"
    / "trading_engine"
    / "paper_trading_manual_review_decision"
)

GENESIS_DECISION_HASH = "0" * 64

VALID_DECISIONS = {
    "APPROVE",
    "REJECT",
    "HOLD",
}

DECISION_CONFIRMATION_TEXTS = {
    "APPROVE": "APPROVE PAPER REVIEW",
    "REJECT": "REJECT PAPER REVIEW",
    "HOLD": "HOLD PAPER REVIEW",
}

VALID_RESULT_STATUSES = {
    "RECORDED",
    "BLOCKED",
    "FAILED",
}


@dataclass(frozen=True)
class PaperTradingManualReviewDecisionPolicy:
    """
    V12.4 Paper Trading Manual Review Decision 정책입니다.

    Queue의 PENDING 항목에 사람의 판정을 기록합니다.
    APPROVE는 다음 검토 단계로 전달할 수 있다는 의미일 뿐,
    Broker 주문 실행 권한을 부여하지 않습니다.
    """

    required_review_queue_version: str = "V12.3"
    required_queue_status: str = "UPDATED"
    required_item_review_status: str = "PENDING"
    minimum_reason_length: int = 10
    maximum_decision_records: int = 100
    hash_algorithm: str = "SHA256"
    genesis_hash: str = GENESIS_DECISION_HASH

    require_exact_confirmation_text: bool = True
    require_reviewer_name: bool = True
    require_reason: bool = True
    require_queue_hash_chain: bool = True
    require_source_safety: bool = True
    reject_duplicate_queue_item_decision: bool = True
    verify_existing_decision_chain: bool = True
    verify_updated_decision_chain: bool = True

    manual_decision_required: bool = True
    automatic_execution_disabled: bool = True
    paper_only: bool = True
    live_execution_disabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PaperTradingManualReviewDecisionRecord:
    sequence_number: int
    decision_record_id: str
    decided_at: str

    review_queue_id: str
    queue_item_id: str
    checklist_id: str
    checklist_date: str
    priority: str

    decision: str
    decision_label: str
    reviewer_name: str
    reason: str
    confirmation_text: str

    source_review_status: str
    next_review_status: str
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
class PaperTradingManualReviewDecisionResult:
    version: str
    created_at: str
    manual_review_decision_id: str

    result_status: str
    result_status_label: str

    review_queue_id: str | None
    queue_item_id: str | None
    checklist_id: str | None
    decision: str | None
    reviewer_name: str | None
    next_review_status: str | None

    total_decision_count: int
    approve_count: int
    reject_count: int
    hold_count: int
    records_trimmed: int
    first_sequence_number: int | None
    last_sequence_number: int | None
    first_record_hash: str | None
    last_record_hash: str | None

    policy_checks_passed: bool
    input_checks_passed: bool
    source_checks_passed: bool
    queue_hash_chain_checks_passed: bool
    target_item_checks_passed: bool
    manual_checks_passed: bool
    duplicate_checks_passed: bool
    existing_decision_chain_checks_passed: bool
    updated_decision_chain_checks_passed: bool
    safety_checks_passed: bool
    all_checks_passed: bool

    manual_decision_required: bool
    paper_execution_authorized: bool
    automatic_execution_authorized: bool
    execution_blocked: bool
    broker_api_called: bool
    broker_order_created: bool
    live_order_created: bool
    live_execution_authorized: bool

    decision_policy: (
        PaperTradingManualReviewDecisionPolicy
    )
    decision_records: tuple[
        PaperTradingManualReviewDecisionRecord,
        ...,
    ]

    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)

    report_path: str | None = None
    latest_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["decision_policy"] = (
            self.decision_policy.to_dict()
        )
        payload["decision_records"] = [
            record.to_dict()
            for record in self.decision_records
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


def calculate_decision_record_hash(
    payload: dict[str, Any],
) -> str:
    return hashlib.sha256(
        canonical_json(payload).encode("utf-8")
    ).hexdigest()


def validate_decision_policy(
    policy: PaperTradingManualReviewDecisionPolicy,
) -> tuple[bool, list[str]]:
    if not isinstance(
        policy,
        PaperTradingManualReviewDecisionPolicy,
    ):
        return (
            False,
            ["Manual Review Decision Policy 형식이 올바르지 않습니다."],
        )

    errors: list[str] = []
    required_values = {
        "required_review_queue_version": "V12.3",
        "required_queue_status": "UPDATED",
        "required_item_review_status": "PENDING",
        "hash_algorithm": "SHA256",
        "genesis_hash": GENESIS_DECISION_HASH,
    }
    for name, expected in required_values.items():
        if getattr(policy, name) != expected:
            errors.append(
                f"{name} 값이 V12.4 기준과 다릅니다."
            )
    if (
        not isinstance(policy.minimum_reason_length, int)
        or policy.minimum_reason_length < 1
    ):
        errors.append(
            "Minimum Reason Length가 올바르지 않습니다."
        )
    if (
        not isinstance(policy.maximum_decision_records, int)
        or policy.maximum_decision_records <= 0
    ):
        errors.append(
            "Maximum Decision Records가 올바르지 않습니다."
        )

    true_values = {
        "require_exact_confirmation_text": (
            policy.require_exact_confirmation_text
        ),
        "require_reviewer_name": (
            policy.require_reviewer_name
        ),
        "require_reason": policy.require_reason,
        "require_queue_hash_chain": (
            policy.require_queue_hash_chain
        ),
        "require_source_safety": (
            policy.require_source_safety
        ),
        "reject_duplicate_queue_item_decision": (
            policy.reject_duplicate_queue_item_decision
        ),
        "verify_existing_decision_chain": (
            policy.verify_existing_decision_chain
        ),
        "verify_updated_decision_chain": (
            policy.verify_updated_decision_chain
        ),
        "manual_decision_required": (
            policy.manual_decision_required
        ),
        "automatic_execution_disabled": (
            policy.automatic_execution_disabled
        ),
        "paper_only": policy.paper_only,
        "live_execution_disabled": (
            policy.live_execution_disabled
        ),
    }
    for name, value in true_values.items():
        if value is not True:
            errors.append(
                f"{name}는 V12.4에서 True여야 합니다."
            )

    return (not errors, errors)


def validate_review_queue_source(
    review_queue_result: Any,
) -> tuple[bool, bool, list[str]]:
    if not isinstance(
        review_queue_result,
        PaperTradingOperationsReviewQueueResult,
    ):
        return (
            False,
            False,
            ["Review Queue Result는 V12.3 형식이어야 합니다."],
        )

    errors: list[str] = []
    source_valid = True
    if review_queue_result.version != "V12.3":
        source_valid = False
        errors.append(
            "Review Queue Version이 V12.3이 아닙니다."
        )
    if (
        review_queue_result.queue_status != "UPDATED"
        or not review_queue_result.all_checks_passed
    ):
        source_valid = False
        errors.append(
            "UPDATED이며 All Checks를 통과한 Queue만 사용할 수 있습니다."
        )
    if not review_queue_result.queue_items:
        source_valid = False
        errors.append(
            "Review Queue에 Item이 없습니다."
        )

    safety_valid = bool(
        review_queue_result.manual_review_required is True
        and review_queue_result.execution_blocked is True
        and review_queue_result
        .automatic_execution_authorized is False
        and review_queue_result.broker_api_called is False
        and review_queue_result.broker_order_created is False
        and review_queue_result.live_order_created is False
        and review_queue_result
        .live_execution_authorized is False
    )
    if not safety_valid:
        errors.append(
            "Review Queue Source에 실거래 안전 오류가 있습니다."
        )

    return (source_valid, safety_valid, errors)


def normalize_decision_records(
    existing_records: Any,
) -> tuple[
    PaperTradingManualReviewDecisionRecord,
    ...,
]:
    if existing_records is None:
        return ()
    if not isinstance(existing_records, (tuple, list)):
        raise TypeError(
            "Existing Decision Records는 tuple 또는 list여야 합니다."
        )
    normalized: list[
        PaperTradingManualReviewDecisionRecord
    ] = []
    for record in existing_records:
        if not isinstance(
            record,
            PaperTradingManualReviewDecisionRecord,
        ):
            raise TypeError(
                "Existing Decision Record 형식이 올바르지 않습니다."
            )
        normalized.append(record)
    return tuple(normalized)


def verify_decision_record_chain(
    records: tuple[
        PaperTradingManualReviewDecisionRecord,
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
            "첫 Decision Record의 Anchor Hash가 올바르지 않습니다."
        )

    for record in records:
        if (
            previous_sequence is not None
            and record.sequence_number
            != previous_sequence + 1
        ):
            errors.append(
                f"{record.sequence_number}번 Decision Sequence가 연속되지 않습니다."
            )
        if record.previous_hash != expected_previous_hash:
            errors.append(
                f"{record.sequence_number}번 Previous Hash가 일치하지 않습니다."
            )
        if record.decision not in VALID_DECISIONS:
            errors.append(
                f"{record.sequence_number}번 Decision이 올바르지 않습니다."
            )
        expected_hash = calculate_decision_record_hash(
            record.payload_without_hash()
        )
        if record.record_hash != expected_hash:
            errors.append(
                f"{record.sequence_number}번 Decision Hash가 일치하지 않습니다."
            )
        previous_sequence = record.sequence_number
        expected_previous_hash = record.record_hash

    return (not errors, errors)


def find_queue_item(
    review_queue_result: (
        PaperTradingOperationsReviewQueueResult
    ),
    queue_item_id: str,
) -> PaperTradingOperationsReviewQueueItem | None:
    return next(
        (
            item
            for item in review_queue_result.queue_items
            if item.queue_item_id == queue_item_id
        ),
        None,
    )


def decision_label(decision: str) -> str:
    return {
        "APPROVE": "Paper 운영 검토 승인",
        "REJECT": "Paper 운영 검토 거부",
        "HOLD": "Paper 운영 검토 보류",
    }.get(decision, "잘못된 판정")


def next_review_status(decision: str) -> str:
    return {
        "APPROVE": "APPROVED",
        "REJECT": "REJECTED",
        "HOLD": "ON_HOLD",
    }.get(decision, "INVALID")


def create_decision_record(
    review_queue_result: (
        PaperTradingOperationsReviewQueueResult
    ),
    queue_item: PaperTradingOperationsReviewQueueItem,
    decision: str,
    reviewer_name: str,
    reason: str,
    confirmation_text: str,
    sequence_number: int,
    previous_hash: str,
) -> PaperTradingManualReviewDecisionRecord:
    values: dict[str, Any] = {
        "sequence_number": sequence_number,
        "decision_record_id": str(uuid.uuid4()),
        "decided_at": datetime.now().isoformat(),
        "review_queue_id": (
            review_queue_result.review_queue_id
        ),
        "queue_item_id": queue_item.queue_item_id,
        "checklist_id": queue_item.checklist_id,
        "checklist_date": queue_item.checklist_date,
        "priority": queue_item.priority,
        "decision": decision,
        "decision_label": decision_label(decision),
        "reviewer_name": reviewer_name.strip(),
        "reason": reason.strip(),
        "confirmation_text": confirmation_text.strip(),
        "source_review_status": (
            queue_item.review_status
        ),
        "next_review_status": (
            next_review_status(decision)
        ),
        "paper_execution_authorized": False,
        "execution_blocked": True,
        "broker_api_called": False,
        "broker_order_created": False,
        "live_order_created": False,
        "live_execution_authorized": False,
        "previous_hash": previous_hash,
    }
    record_hash = calculate_decision_record_hash(values)
    return PaperTradingManualReviewDecisionRecord(
        **values,
        record_hash=record_hash,
    )


def record_paper_trading_manual_review_decision(
    review_queue_result: Any,
    queue_item_id: Any,
    decision: Any,
    reviewer_name: Any,
    reason: Any,
    confirmation_text: Any,
    existing_records: Any = None,
    decision_policy: (
        PaperTradingManualReviewDecisionPolicy
        | None
    ) = None,
) -> PaperTradingManualReviewDecisionResult:
    policy = (
        decision_policy
        if decision_policy is not None
        else PaperTradingManualReviewDecisionPolicy()
    )
    policy_valid, policy_errors = (
        validate_decision_policy(policy)
    )
    source_valid, source_safety_valid, source_errors = (
        validate_review_queue_source(review_queue_result)
    )

    text_valid = bool(
        isinstance(queue_item_id, str)
        and queue_item_id.strip()
        and isinstance(decision, str)
        and isinstance(reviewer_name, str)
        and reviewer_name.strip()
        and isinstance(reason, str)
        and isinstance(confirmation_text, str)
    )
    input_errors = (
        []
        if text_valid
        else [
            "Queue Item ID, Decision, Reviewer, Reason과 Confirmation 입력이 올바르지 않습니다."
        ]
    )
    decision_valid = bool(
        text_valid and decision in VALID_DECISIONS
    )
    if text_valid and not decision_valid:
        input_errors.append(
            "Decision은 APPROVE, REJECT 또는 HOLD여야 합니다."
        )

    manual_valid = bool(
        decision_valid
        and len(reason.strip())
        >= policy.minimum_reason_length
        and confirmation_text.strip()
        == DECISION_CONFIRMATION_TEXTS[decision]
    )
    manual_errors: list[str] = []
    if decision_valid:
        if len(reason.strip()) < policy.minimum_reason_length:
            manual_errors.append(
                "Decision Reason이 너무 짧습니다."
            )
        if (
            confirmation_text.strip()
            != DECISION_CONFIRMATION_TEXTS[decision]
        ):
            manual_errors.append(
                "Decision Confirmation Text가 일치하지 않습니다."
            )

    if source_valid:
        queue_chain_valid, queue_chain_errors = (
            verify_review_queue_hash_chain(
                review_queue_result.queue_items
            )
        )
        target_item = (
            find_queue_item(
                review_queue_result,
                queue_item_id,
            )
            if isinstance(queue_item_id, str)
            else None
        )
    else:
        queue_chain_valid = False
        queue_chain_errors = []
        target_item = None

    target_valid = bool(
        target_item is not None
        and target_item.review_status
        == policy.required_item_review_status
        and target_item.execution_blocked is True
        and target_item.broker_api_called is False
        and target_item.live_execution_authorized is False
    )
    target_errors = (
        []
        if target_valid
        else [
            "PENDING이며 안전한 Queue Item을 찾을 수 없습니다."
        ]
    )

    try:
        normalized_records = normalize_decision_records(
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
            verify_decision_record_chain(
                normalized_records
            )
        )
    else:
        existing_chain_valid = False
        chain_errors = []

    duplicate_found = bool(
        isinstance(queue_item_id, str)
        and any(
            record.queue_item_id == queue_item_id
            for record in normalized_records
        )
    )
    duplicate_valid = bool(
        isinstance(queue_item_id, str)
        and not duplicate_found
    )
    duplicate_errors = (
        ["동일한 Queue Item에 이미 Manual Decision이 있습니다."]
        if duplicate_found
        else []
    )

    preflight_valid = bool(
        policy_valid
        and source_valid
        and source_safety_valid
        and text_valid
        and decision_valid
        and manual_valid
        and queue_chain_valid
        and target_valid
        and records_valid
        and existing_chain_valid
        and duplicate_valid
    )

    updated_records = normalized_records
    records_trimmed = 0
    updated_chain_valid = False
    updated_chain_errors: list[str] = []
    if preflight_valid and target_item is not None:
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
        new_record = create_decision_record(
            review_queue_result,
            target_item,
            decision,
            reviewer_name,
            reason,
            confirmation_text,
            sequence_number,
            previous_hash,
        )
        all_records = (*normalized_records, new_record)
        records_trimmed = max(
            0,
            len(all_records)
            - policy.maximum_decision_records,
        )
        updated_records = tuple(
            all_records[
                -policy.maximum_decision_records:
            ]
        )
        (
            updated_chain_valid,
            updated_chain_errors,
        ) = verify_decision_record_chain(
            updated_records
        )

    all_checks_passed = bool(
        preflight_valid and updated_chain_valid
    )

    if all_checks_passed:
        result_status = "RECORDED"
        result_status_label = (
            f"Manual Review {decision} 판정 기록 완료"
        )
        reasons = [
            f"Queue Item에 {decision} 판정이 기록되었습니다.",
            "Decision SHA-256 Hash Chain이 검증되었습니다.",
        ]
        next_actions = (
            [
                "승인 기록을 다음 Paper 운영 검토 단계로 전달합니다.",
                "승인은 Broker 주문 권한이 아님을 다시 확인합니다.",
            ]
            if decision == "APPROVE"
            else [
                "판정 사유를 확인하고 Paper 운영을 시작하지 않습니다.",
            ]
        )
    elif (
        duplicate_found
        or (
            source_valid
            and queue_chain_valid
            and (
                not target_valid
                or not manual_valid
                or not decision_valid
            )
            and source_safety_valid
        )
    ):
        result_status = "BLOCKED"
        result_status_label = (
            "Manual Review Decision 차단"
        )
        reasons = [
            "수동 입력, 대상 상태 또는 중복 검사에 통과하지 못했습니다."
        ]
        next_actions = [
            "올바른 PENDING Item과 확인 문구를 사용합니다.",
        ]
    else:
        result_status = "FAILED"
        result_status_label = (
            "Manual Review Decision 검사 실패"
        )
        reasons = [
            "Source, Policy, Hash Chain 또는 Safety 검사에 실패했습니다."
        ]
        next_actions = [
            "Warnings를 확인하고 Source를 다시 생성합니다.",
            "기존 Decision Record를 직접 수정하지 않습니다.",
        ]

    latest_record = (
        updated_records[-1]
        if updated_records
        else None
    )
    return PaperTradingManualReviewDecisionResult(
        version="V12.4",
        created_at=datetime.now().isoformat(),
        manual_review_decision_id=str(uuid.uuid4()),
        result_status=result_status,
        result_status_label=result_status_label,
        review_queue_id=getattr(
            review_queue_result,
            "review_queue_id",
            None,
        ),
        queue_item_id=(
            latest_record.queue_item_id
            if latest_record is not None
            else (
                queue_item_id
                if isinstance(queue_item_id, str)
                else None
            )
        ),
        checklist_id=(
            latest_record.checklist_id
            if latest_record is not None
            else None
        ),
        decision=(
            latest_record.decision
            if latest_record is not None
            else (
                decision
                if decision in VALID_DECISIONS
                else None
            )
        ),
        reviewer_name=(
            reviewer_name.strip()
            if isinstance(reviewer_name, str)
            else None
        ),
        next_review_status=(
            latest_record.next_review_status
            if latest_record is not None
            else None
        ),
        total_decision_count=len(updated_records),
        approve_count=sum(
            record.decision == "APPROVE"
            for record in updated_records
        ),
        reject_count=sum(
            record.decision == "REJECT"
            for record in updated_records
        ),
        hold_count=sum(
            record.decision == "HOLD"
            for record in updated_records
        ),
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
        input_checks_passed=bool(
            text_valid and decision_valid
        ),
        source_checks_passed=source_valid,
        queue_hash_chain_checks_passed=(
            queue_chain_valid
        ),
        target_item_checks_passed=target_valid,
        manual_checks_passed=manual_valid,
        duplicate_checks_passed=duplicate_valid,
        existing_decision_chain_checks_passed=(
            existing_chain_valid
        ),
        updated_decision_chain_checks_passed=(
            updated_chain_valid
        ),
        safety_checks_passed=source_safety_valid,
        all_checks_passed=all_checks_passed,
        manual_decision_required=True,
        paper_execution_authorized=False,
        automatic_execution_authorized=False,
        execution_blocked=True,
        broker_api_called=False,
        broker_order_created=False,
        live_order_created=False,
        live_execution_authorized=False,
        decision_policy=policy,
        decision_records=updated_records,
        reasons=reasons,
        warnings=[
            *policy_errors,
            *source_errors,
            *input_errors,
            *manual_errors,
            *queue_chain_errors,
            *target_errors,
            *record_errors,
            *chain_errors,
            *duplicate_errors,
            *updated_chain_errors,
            "V12.4 APPROVE는 Broker 주문 권한이 아닙니다.",
            "실제 Broker API, 실제 주문 및 Live Execution은 모두 차단됩니다.",
        ],
        next_actions=next_actions,
    )


def verify_saved_manual_review_decision_payload(
    payload: dict[str, Any],
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if payload.get("version") != "V12.4":
        errors.append(
            "저장된 Decision Version이 V12.4가 아닙니다."
        )
    if payload.get("result_status") not in VALID_RESULT_STATUSES:
        errors.append(
            "저장된 Result Status가 올바르지 않습니다."
        )
    if payload.get("paper_execution_authorized") is not False:
        errors.append(
            "저장된 Decision이 Paper Execution을 허용합니다."
        )
    if payload.get("execution_blocked") is not True:
        errors.append(
            "저장된 Decision의 Execution이 차단되지 않았습니다."
        )
    false_fields = (
        "automatic_execution_authorized",
        "broker_api_called",
        "broker_order_created",
        "live_order_created",
        "live_execution_authorized",
    )
    for field_name in false_fields:
        if payload.get(field_name) is not False:
            errors.append(
                f"저장된 {field_name} 값이 False가 아닙니다."
            )
    return (not errors, errors)


def save_paper_trading_manual_review_decision(
    result: PaperTradingManualReviewDecisionResult,
    output_directory: Path | None = None,
) -> PaperTradingManualReviewDecisionResult:
    if not isinstance(
        result,
        PaperTradingManualReviewDecisionResult,
    ):
        raise TypeError(
            "V12.4 Manual Review Decision Result 형식이 아닙니다."
        )
    directory = (
        output_directory
        if output_directory is not None
        else PAPER_TRADING_MANUAL_REVIEW_DECISION_OUTPUT_DIRECTORY
    )
    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S_%f"
    )
    report_path = directory / (
        f"paper_trading_manual_review_decision_{timestamp}.json"
    )
    latest_path = directory / (
        "paper_trading_manual_review_decision_latest.json"
    )
    payload = result.to_dict()
    write_json_file(report_path, payload)
    write_json_file(latest_path, payload)
    result.report_path = str(report_path)
    result.latest_path = str(latest_path)
    return result


def load_latest_paper_trading_manual_review_decision(
    output_directory: Path | None = None,
) -> dict[str, Any]:
    directory = (
        output_directory
        if output_directory is not None
        else PAPER_TRADING_MANUAL_REVIEW_DECISION_OUTPUT_DIRECTORY
    )
    return read_json_file(
        directory
        / "paper_trading_manual_review_decision_latest.json"
    )


def print_paper_trading_manual_review_decision(
    result: PaperTradingManualReviewDecisionResult,
) -> None:
    line = "=" * 100
    print()
    print(line)
    print("V12.4 PAPER TRADING MANUAL REVIEW DECISION")
    print(line)
    print(f"Result status          : {result.result_status}")
    print(f"Decision               : {result.decision}")
    print(f"Reviewer               : {result.reviewer_name}")
    print(f"Next review status     : {result.next_review_status}")
    print(f"Total decisions        : {result.total_decision_count}")
    print()
    print("VALIDATION")
    print("-" * 100)
    checks = {
        "Policy checks passed": result.policy_checks_passed,
        "Input checks passed": result.input_checks_passed,
        "Source checks passed": result.source_checks_passed,
        "Queue hash chain passed": (
            result.queue_hash_chain_checks_passed
        ),
        "Target item checks passed": (
            result.target_item_checks_passed
        ),
        "Manual checks passed": result.manual_checks_passed,
        "Duplicate checks passed": (
            result.duplicate_checks_passed
        ),
        "Safety checks passed": result.safety_checks_passed,
        "All checks passed": result.all_checks_passed,
    }
    for name, value in checks.items():
        print(f"{name:<40} : {value}")
    print(line)
    print(
        "주의: APPROVE도 실제 주문 권한이 아니며 "
        "Broker 및 Live Execution은 차단됩니다."
    )

