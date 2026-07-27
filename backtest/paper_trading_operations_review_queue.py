import hashlib
import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from backtest.paper_trading_daily_operations_checklist import (
    PaperTradingDailyOperationsChecklistResult,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent

PAPER_TRADING_OPERATIONS_REVIEW_QUEUE_OUTPUT_DIRECTORY = (
    PROJECT_ROOT
    / "output"
    / "trading_engine"
    / "paper_trading_operations_review_queue"
)

GENESIS_QUEUE_HASH = "0" * 64

VALID_QUEUE_STATUSES = {
    "UPDATED",
    "BLOCKED",
    "FAILED",
}

VALID_REVIEW_STATUSES = {
    "PENDING",
}

VALID_PRIORITIES = {
    "NORMAL",
    "HIGH",
}


@dataclass(frozen=True)
class PaperTradingOperationsReviewQueuePolicy:
    """
    V12.3 Paper Trading Operations Review Queue 정책입니다.

    V12.2에서 READY가 된 Checklist를 수동 검토 대기열에
    등록할 뿐, Paper 또는 Live 주문을 실행하지 않습니다.
    """

    required_checklist_version: str = "V12.2"
    required_checklist_status: str = "READY"
    required_review_status: str = "PENDING"
    default_priority: str = "NORMAL"
    maximum_queue_records: int = 100
    hash_algorithm: str = "SHA256"
    genesis_hash: str = GENESIS_QUEUE_HASH

    require_checklist_all_checks: bool = True
    require_checklist_read_only: bool = True
    require_checklist_safety: bool = True
    require_manual_actor: bool = True
    reject_duplicate_checklist_id: bool = True
    verify_existing_hash_chain: bool = True
    verify_updated_hash_chain: bool = True

    manual_review_required: bool = True
    automatic_execution_disabled: bool = True
    paper_only: bool = True
    live_execution_disabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PaperTradingOperationsReviewQueueItem:
    sequence_number: int
    queue_item_id: str
    queued_at: str

    checklist_id: str
    checklist_date: str
    checklist_created_at: str
    checklist_status: str
    manual_actor: str
    manual_note: str | None

    console_id: str | None
    state_store_id: str | None
    state_entry_id: str | None

    review_status: str
    priority: str
    review_note: str | None

    passed_item_count: int
    total_item_count: int
    checklist_all_checks_passed: bool

    execution_blocked: bool
    broker_api_called: bool
    broker_order_created: bool
    live_order_created: bool
    live_execution_authorized: bool

    previous_hash: str
    item_hash: str

    def payload_without_hash(self) -> dict[str, Any]:
        payload = asdict(self)
        payload.pop("item_hash", None)
        return payload

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PaperTradingOperationsReviewQueueResult:
    version: str
    created_at: str
    review_queue_id: str

    queue_status: str
    queue_status_label: str

    latest_queue_item_id: str | None
    latest_checklist_id: str | None
    latest_review_status: str | None

    total_queue_count: int
    pending_review_count: int
    high_priority_count: int
    records_trimmed: int
    first_sequence_number: int | None
    last_sequence_number: int | None
    first_item_hash: str | None
    last_item_hash: str | None

    policy_checks_passed: bool
    input_checks_passed: bool
    existing_chain_checks_passed: bool
    duplicate_checks_passed: bool
    queue_checks_passed: bool
    updated_chain_checks_passed: bool
    safety_checks_passed: bool
    all_checks_passed: bool

    manual_review_required: bool
    automatic_execution_authorized: bool
    execution_blocked: bool
    broker_api_called: bool
    broker_order_created: bool
    live_order_created: bool
    live_execution_authorized: bool

    review_queue_policy: (
        PaperTradingOperationsReviewQueuePolicy
    )
    queue_items: tuple[
        PaperTradingOperationsReviewQueueItem,
        ...,
    ]

    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)

    report_path: str | None = None
    latest_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["review_queue_policy"] = (
            self.review_queue_policy.to_dict()
        )
        payload["queue_items"] = [
            item.to_dict()
            for item in self.queue_items
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


def calculate_queue_item_hash(
    payload: dict[str, Any],
) -> str:
    return hashlib.sha256(
        canonical_json(payload).encode("utf-8")
    ).hexdigest()


def validate_review_queue_policy(
    policy: PaperTradingOperationsReviewQueuePolicy,
) -> tuple[bool, list[str]]:
    if not isinstance(
        policy,
        PaperTradingOperationsReviewQueuePolicy,
    ):
        return (
            False,
            ["Review Queue Policy 형식이 올바르지 않습니다."],
        )

    errors: list[str] = []
    required_values = {
        "required_checklist_version": "V12.2",
        "required_checklist_status": "READY",
        "required_review_status": "PENDING",
        "default_priority": "NORMAL",
        "hash_algorithm": "SHA256",
        "genesis_hash": GENESIS_QUEUE_HASH,
    }
    for name, expected in required_values.items():
        if getattr(policy, name) != expected:
            errors.append(
                f"{name} 값이 V12.3 기준과 다릅니다."
            )

    if (
        not isinstance(policy.maximum_queue_records, int)
        or policy.maximum_queue_records <= 0
    ):
        errors.append(
            "Maximum Queue Records가 올바르지 않습니다."
        )

    required_true_values = {
        "require_checklist_all_checks": (
            policy.require_checklist_all_checks
        ),
        "require_checklist_read_only": (
            policy.require_checklist_read_only
        ),
        "require_checklist_safety": (
            policy.require_checklist_safety
        ),
        "require_manual_actor": (
            policy.require_manual_actor
        ),
        "reject_duplicate_checklist_id": (
            policy.reject_duplicate_checklist_id
        ),
        "verify_existing_hash_chain": (
            policy.verify_existing_hash_chain
        ),
        "verify_updated_hash_chain": (
            policy.verify_updated_hash_chain
        ),
        "manual_review_required": (
            policy.manual_review_required
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
                f"{name}는 V12.3에서 True여야 합니다."
            )

    return (not errors, errors)


def validate_checklist_source(
    checklist_result: Any,
) -> tuple[bool, bool, bool, list[str]]:
    if not isinstance(
        checklist_result,
        PaperTradingDailyOperationsChecklistResult,
    ):
        return (
            False,
            False,
            False,
            ["Checklist Result는 V12.2 형식이어야 합니다."],
        )

    errors: list[str] = []
    input_valid = True
    queue_valid = True

    if checklist_result.version != "V12.2":
        input_valid = False
        errors.append(
            "Checklist Version이 V12.2가 아닙니다."
        )
    if (
        not isinstance(checklist_result.checklist_id, str)
        or not checklist_result.checklist_id.strip()
    ):
        input_valid = False
        errors.append(
            "Checklist ID가 비어 있습니다."
        )
    if (
        checklist_result.checklist_status != "READY"
        or not checklist_result.all_checks_passed
    ):
        queue_valid = False
        errors.append(
            "READY이며 All Checks를 통과한 Checklist만 등록할 수 있습니다."
        )
    if (
        not isinstance(checklist_result.manual_actor, str)
        or not checklist_result.manual_actor.strip()
    ):
        queue_valid = False
        errors.append(
            "Checklist Manual Actor가 비어 있습니다."
        )

    safety_valid = bool(
        checklist_result.read_only is True
        and checklist_result.execution_blocked is True
        and checklist_result
        .automatic_execution_authorized is False
        and checklist_result.broker_api_called is False
        and checklist_result.broker_order_created is False
        and checklist_result.live_order_created is False
        and checklist_result
        .live_execution_authorized is False
    )
    if not safety_valid:
        errors.append(
            "Checklist Source에 실거래 안전 오류가 있습니다."
        )

    return (
        input_valid,
        queue_valid,
        safety_valid,
        errors,
    )


def normalize_queue_items(
    existing_items: Any,
) -> tuple[
    PaperTradingOperationsReviewQueueItem,
    ...,
]:
    if existing_items is None:
        return ()
    if not isinstance(existing_items, (tuple, list)):
        raise TypeError(
            "Existing Queue Items는 tuple 또는 list여야 합니다."
        )
    normalized: list[
        PaperTradingOperationsReviewQueueItem
    ] = []
    for item in existing_items:
        if not isinstance(
            item,
            PaperTradingOperationsReviewQueueItem,
        ):
            raise TypeError(
                "Existing Queue Item 형식이 올바르지 않습니다."
            )
        normalized.append(item)
    return tuple(normalized)


def verify_review_queue_hash_chain(
    items: tuple[
        PaperTradingOperationsReviewQueueItem,
        ...,
    ],
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if not items:
        return (True, errors)

    previous_sequence: int | None = None
    expected_previous_hash = items[0].previous_hash
    if (
        not isinstance(expected_previous_hash, str)
        or len(expected_previous_hash) != 64
    ):
        errors.append(
            "첫 Queue Item의 Anchor Hash가 올바르지 않습니다."
        )

    for item in items:
        if (
            previous_sequence is not None
            and item.sequence_number
            != previous_sequence + 1
        ):
            errors.append(
                f"{item.sequence_number}번 Queue Sequence가 연속되지 않습니다."
            )
        if item.previous_hash != expected_previous_hash:
            errors.append(
                f"{item.sequence_number}번 Previous Hash가 일치하지 않습니다."
            )
        if item.review_status not in VALID_REVIEW_STATUSES:
            errors.append(
                f"{item.sequence_number}번 Review Status가 올바르지 않습니다."
            )
        if item.priority not in VALID_PRIORITIES:
            errors.append(
                f"{item.sequence_number}번 Priority가 올바르지 않습니다."
            )

        expected_hash = calculate_queue_item_hash(
            item.payload_without_hash()
        )
        if item.item_hash != expected_hash:
            errors.append(
                f"{item.sequence_number}번 Queue Item Hash가 일치하지 않습니다."
            )

        previous_sequence = item.sequence_number
        expected_previous_hash = item.item_hash

    return (not errors, errors)


def create_review_queue_item(
    checklist_result: (
        PaperTradingDailyOperationsChecklistResult
    ),
    sequence_number: int,
    previous_hash: str,
    priority: str,
    review_note: str | None,
) -> PaperTradingOperationsReviewQueueItem:
    values: dict[str, Any] = {
        "sequence_number": sequence_number,
        "queue_item_id": str(uuid.uuid4()),
        "queued_at": datetime.now().isoformat(),
        "checklist_id": checklist_result.checklist_id,
        "checklist_date": checklist_result.checklist_date,
        "checklist_created_at": (
            checklist_result.created_at
        ),
        "checklist_status": (
            checklist_result.checklist_status
        ),
        "manual_actor": (
            checklist_result.manual_actor or ""
        ),
        "manual_note": checklist_result.manual_note,
        "console_id": checklist_result.console_id,
        "state_store_id": (
            checklist_result.state_store_id
        ),
        "state_entry_id": (
            checklist_result.state_entry_id
        ),
        "review_status": "PENDING",
        "priority": priority,
        "review_note": review_note,
        "passed_item_count": (
            checklist_result.passed_item_count
        ),
        "total_item_count": (
            checklist_result.total_item_count
        ),
        "checklist_all_checks_passed": (
            checklist_result.all_checks_passed
        ),
        "execution_blocked": True,
        "broker_api_called": False,
        "broker_order_created": False,
        "live_order_created": False,
        "live_execution_authorized": False,
        "previous_hash": previous_hash,
    }
    item_hash = calculate_queue_item_hash(values)
    return PaperTradingOperationsReviewQueueItem(
        **values,
        item_hash=item_hash,
    )


def enqueue_paper_trading_operations_review(
    checklist_result: Any,
    existing_items: Any = None,
    priority: str = "NORMAL",
    review_note: str | None = None,
    review_queue_policy: (
        PaperTradingOperationsReviewQueuePolicy
        | None
    ) = None,
) -> PaperTradingOperationsReviewQueueResult:
    policy = (
        review_queue_policy
        if review_queue_policy is not None
        else PaperTradingOperationsReviewQueuePolicy()
    )
    policy_valid, policy_errors = (
        validate_review_queue_policy(policy)
    )
    (
        input_valid,
        queue_source_valid,
        source_safety_valid,
        source_errors,
    ) = validate_checklist_source(checklist_result)

    priority_valid = priority in VALID_PRIORITIES
    priority_errors = (
        []
        if priority_valid
        else ["Priority는 NORMAL 또는 HIGH여야 합니다."]
    )
    note_valid = bool(
        review_note is None
        or isinstance(review_note, str)
    )
    note_errors = (
        []
        if note_valid
        else ["Review Note는 문자열 또는 None이어야 합니다."]
    )

    try:
        normalized_items = normalize_queue_items(
            existing_items
        )
        existing_items_valid = True
        item_errors: list[str] = []
    except (TypeError, ValueError) as error:
        normalized_items = ()
        existing_items_valid = False
        item_errors = [str(error)]

    if existing_items_valid:
        existing_chain_valid, chain_errors = (
            verify_review_queue_hash_chain(
                normalized_items
            )
        )
    else:
        existing_chain_valid = False
        chain_errors = []

    checklist_id = getattr(
        checklist_result,
        "checklist_id",
        None,
    )
    duplicate_found = bool(
        isinstance(checklist_id, str)
        and any(
            item.checklist_id == checklist_id
            for item in normalized_items
        )
    )
    duplicate_valid = bool(
        isinstance(checklist_id, str)
        and not duplicate_found
    )
    duplicate_errors = (
        ["동일한 Checklist ID가 이미 Review Queue에 있습니다."]
        if duplicate_found
        else []
    )

    preflight_valid = bool(
        policy_valid
        and input_valid
        and queue_source_valid
        and source_safety_valid
        and priority_valid
        and note_valid
        and existing_items_valid
        and existing_chain_valid
        and duplicate_valid
    )

    updated_items = normalized_items
    records_trimmed = 0
    updated_chain_valid = False
    updated_chain_errors: list[str] = []

    if preflight_valid:
        next_sequence = (
            normalized_items[-1].sequence_number + 1
            if normalized_items
            else 1
        )
        previous_hash = (
            normalized_items[-1].item_hash
            if normalized_items
            else policy.genesis_hash
        )
        new_item = create_review_queue_item(
            checklist_result,
            next_sequence,
            previous_hash,
            priority,
            (
                review_note.strip()
                if isinstance(review_note, str)
                else None
            ),
        )
        all_items = (*normalized_items, new_item)
        records_trimmed = max(
            0,
            len(all_items)
            - policy.maximum_queue_records,
        )
        updated_items = tuple(
            all_items[-policy.maximum_queue_records:]
        )
        (
            updated_chain_valid,
            updated_chain_errors,
        ) = verify_review_queue_hash_chain(
            updated_items
        )

    all_checks_passed = bool(
        preflight_valid and updated_chain_valid
    )

    if all_checks_passed:
        queue_status = "UPDATED"
        queue_status_label = (
            "Paper Trading 수동 검토 대기열 등록 완료"
        )
        reasons = [
            "READY Checklist가 Review Queue에 등록되었습니다.",
            "Queue Item SHA-256 Hash Chain이 검증되었습니다.",
        ]
        next_actions = [
            "PENDING 항목을 사람이 순서대로 검토합니다.",
            "검토 전에는 Paper 실행을 시작하지 않습니다.",
        ]
    elif duplicate_found or (
        input_valid
        and not queue_source_valid
        and source_safety_valid
    ):
        queue_status = "BLOCKED"
        queue_status_label = (
            "Paper Trading Review Queue 등록 차단"
        )
        reasons = [
            "중복 또는 READY가 아닌 Checklist는 등록할 수 없습니다."
        ]
        next_actions = [
            "새 READY Checklist를 생성한 후 다시 등록합니다.",
        ]
    else:
        queue_status = "FAILED"
        queue_status_label = (
            "Paper Trading Review Queue 검사 실패"
        )
        reasons = [
            "Policy, 입력, Hash Chain 또는 Safety 검사에 실패했습니다."
        ]
        next_actions = [
            "Warnings에서 실패 원인을 확인합니다.",
            "기존 Queue Item을 직접 수정하지 않습니다.",
        ]

    latest_item = (
        updated_items[-1]
        if updated_items
        else None
    )
    result = PaperTradingOperationsReviewQueueResult(
        version="V12.3",
        created_at=datetime.now().isoformat(),
        review_queue_id=str(uuid.uuid4()),
        queue_status=queue_status,
        queue_status_label=queue_status_label,
        latest_queue_item_id=(
            latest_item.queue_item_id
            if latest_item is not None
            else None
        ),
        latest_checklist_id=(
            latest_item.checklist_id
            if latest_item is not None
            else None
        ),
        latest_review_status=(
            latest_item.review_status
            if latest_item is not None
            else None
        ),
        total_queue_count=len(updated_items),
        pending_review_count=sum(
            item.review_status == "PENDING"
            for item in updated_items
        ),
        high_priority_count=sum(
            item.priority == "HIGH"
            for item in updated_items
        ),
        records_trimmed=records_trimmed,
        first_sequence_number=(
            updated_items[0].sequence_number
            if updated_items
            else None
        ),
        last_sequence_number=(
            updated_items[-1].sequence_number
            if updated_items
            else None
        ),
        first_item_hash=(
            updated_items[0].item_hash
            if updated_items
            else None
        ),
        last_item_hash=(
            updated_items[-1].item_hash
            if updated_items
            else None
        ),
        policy_checks_passed=policy_valid,
        input_checks_passed=bool(
            input_valid
            and priority_valid
            and note_valid
            and existing_items_valid
        ),
        existing_chain_checks_passed=(
            existing_chain_valid
        ),
        duplicate_checks_passed=duplicate_valid,
        queue_checks_passed=queue_source_valid,
        updated_chain_checks_passed=(
            updated_chain_valid
        ),
        safety_checks_passed=source_safety_valid,
        all_checks_passed=all_checks_passed,
        manual_review_required=True,
        automatic_execution_authorized=False,
        execution_blocked=True,
        broker_api_called=False,
        broker_order_created=False,
        live_order_created=False,
        live_execution_authorized=False,
        review_queue_policy=policy,
        queue_items=updated_items,
        reasons=reasons,
        warnings=[
            *policy_errors,
            *source_errors,
            *priority_errors,
            *note_errors,
            *item_errors,
            *chain_errors,
            *duplicate_errors,
            *updated_chain_errors,
            "V12.3 Queue는 수동 검토 대기열만 관리합니다.",
            "실제 Broker API, 실제 주문 및 Live Execution은 모두 차단됩니다.",
        ],
        next_actions=next_actions,
    )
    return result


def verify_saved_review_queue_payload(
    payload: dict[str, Any],
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if payload.get("version") != "V12.3":
        errors.append(
            "저장된 Review Queue Version이 V12.3이 아닙니다."
        )
    if payload.get("queue_status") not in VALID_QUEUE_STATUSES:
        errors.append(
            "저장된 Queue Status가 올바르지 않습니다."
        )
    if payload.get("manual_review_required") is not True:
        errors.append(
            "저장된 Queue가 Manual Review를 요구하지 않습니다."
        )
    if payload.get("execution_blocked") is not True:
        errors.append(
            "저장된 Queue의 Execution이 차단되지 않았습니다."
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


def save_paper_trading_operations_review_queue(
    result: PaperTradingOperationsReviewQueueResult,
    output_directory: Path | None = None,
) -> PaperTradingOperationsReviewQueueResult:
    if not isinstance(
        result,
        PaperTradingOperationsReviewQueueResult,
    ):
        raise TypeError(
            "V12.3 Review Queue Result 형식이 아닙니다."
        )
    directory = (
        output_directory
        if output_directory is not None
        else PAPER_TRADING_OPERATIONS_REVIEW_QUEUE_OUTPUT_DIRECTORY
    )
    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S_%f"
    )
    report_path = directory / (
        f"paper_trading_review_queue_{timestamp}.json"
    )
    latest_path = directory / (
        "paper_trading_review_queue_latest.json"
    )
    payload = result.to_dict()
    write_json_file(report_path, payload)
    write_json_file(latest_path, payload)
    result.report_path = str(report_path)
    result.latest_path = str(latest_path)
    return result


def load_latest_paper_trading_operations_review_queue(
    output_directory: Path | None = None,
) -> dict[str, Any]:
    directory = (
        output_directory
        if output_directory is not None
        else PAPER_TRADING_OPERATIONS_REVIEW_QUEUE_OUTPUT_DIRECTORY
    )
    return read_json_file(
        directory
        / "paper_trading_review_queue_latest.json"
    )


def print_paper_trading_operations_review_queue(
    result: PaperTradingOperationsReviewQueueResult,
) -> None:
    line = "=" * 100
    print()
    print(line)
    print("V12.3 PAPER TRADING OPERATIONS REVIEW QUEUE")
    print(line)
    print(f"Queue status           : {result.queue_status}")
    print(f"Total queue count      : {result.total_queue_count}")
    print(f"Pending review count   : {result.pending_review_count}")
    print(f"High priority count    : {result.high_priority_count}")
    print()
    print("QUEUE ITEMS")
    print("-" * 100)
    for item in result.queue_items:
        print(
            f"{item.sequence_number:03d}. "
            f"{item.checklist_date} | "
            f"{item.priority:<6} | "
            f"{item.review_status:<7} | "
            f"{item.checklist_id}"
        )
    print()
    print("VALIDATION")
    print("-" * 100)
    checks = {
        "Policy checks passed": result.policy_checks_passed,
        "Input checks passed": result.input_checks_passed,
        "Existing chain passed": (
            result.existing_chain_checks_passed
        ),
        "Duplicate checks passed": (
            result.duplicate_checks_passed
        ),
        "Queue checks passed": result.queue_checks_passed,
        "Updated chain passed": (
            result.updated_chain_checks_passed
        ),
        "Safety checks passed": result.safety_checks_passed,
        "All checks passed": result.all_checks_passed,
    }
    for name, value in checks.items():
        print(f"{name:<40} : {value}")
    print(line)
    print(
        "주의: V12.3은 수동 검토 대기열이며 실제 또는 "
        "자동 주문을 실행하지 않습니다."
    )

