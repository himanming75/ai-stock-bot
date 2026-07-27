import hashlib
import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from backtest.paper_trading_operations_console import (
    PaperTradingOperationsConsoleResult,
    VALID_CONSOLE_STATUSES,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent

PAPER_TRADING_OPERATIONS_STATE_STORE_OUTPUT_DIRECTORY = (
    PROJECT_ROOT
    / "output"
    / "trading_engine"
    / "paper_trading_operations_state_store"
)

GENESIS_STATE_HASH = "0" * 64

VALID_STORE_STATUSES = {
    "UPDATED",
    "BLOCKED",
    "FAILED",
}


@dataclass(frozen=True)
class PaperTradingOperationsStateStorePolicy:
    """
    V12.1 Paper Trading Operations State Store 정책입니다.
    """

    required_console_version: str = "V12.0"
    maximum_state_records: int = 100
    hash_algorithm: str = "SHA256"
    genesis_hash: str = GENESIS_STATE_HASH

    accept_ready_status: bool = True
    accept_review_status: bool = True
    accept_blocked_status: bool = True
    accept_failed_status: bool = True

    reject_duplicate_console_id: bool = True
    require_console_read_only: bool = True
    require_console_safety: bool = True
    verify_existing_hash_chain: bool = True
    verify_updated_hash_chain: bool = True

    automatic_execution_disabled: bool = True
    paper_only: bool = True
    live_execution_disabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PaperTradingOperationsStateEntry:
    sequence_number: int
    state_entry_id: str
    recorded_at: str

    console_id: str
    console_created_at: str
    console_status: str
    manual_actor: str | None

    orchestration_id: str | None
    audit_trail_id: str | None
    reconciliation_id: str | None
    release_gate_id: str | None

    passed_card_count: int
    total_card_count: int
    completed_stage_count: int
    total_stage_count: int
    reconciliation_mismatch_count: int
    paper_run_locked: bool
    console_all_checks_passed: bool

    read_only: bool
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
class PaperTradingOperationsStateStoreResult:
    version: str
    created_at: str
    state_store_id: str

    store_status: str
    store_status_label: str

    latest_console_id: str | None
    latest_console_status: str | None
    previous_console_status: str | None
    status_transition: str | None

    total_state_count: int
    records_trimmed: int
    first_sequence_number: int | None
    last_sequence_number: int | None
    first_entry_hash: str | None
    last_entry_hash: str | None

    policy_checks_passed: bool
    input_checks_passed: bool
    existing_chain_checks_passed: bool
    duplicate_checks_passed: bool
    transition_checks_passed: bool
    updated_chain_checks_passed: bool
    safety_checks_passed: bool
    all_checks_passed: bool

    automatic_execution_authorized: bool
    execution_blocked: bool
    broker_api_called: bool
    broker_order_created: bool
    live_order_created: bool
    live_execution_authorized: bool

    state_store_policy: (
        PaperTradingOperationsStateStorePolicy
    )
    state_entries: tuple[
        PaperTradingOperationsStateEntry,
        ...,
    ]

    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)

    report_path: str | None = None
    latest_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["state_store_policy"] = (
            self.state_store_policy.to_dict()
        )
        payload["state_entries"] = [
            entry.to_dict()
            for entry in self.state_entries
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


def calculate_state_entry_hash(
    payload: dict[str, Any],
) -> str:
    return hashlib.sha256(
        canonical_json(payload).encode("utf-8")
    ).hexdigest()


def validate_state_store_policy(
    policy: PaperTradingOperationsStateStorePolicy,
) -> tuple[bool, list[str]]:
    if not isinstance(
        policy,
        PaperTradingOperationsStateStorePolicy,
    ):
        return (
            False,
            ["State Store Policy 형식이 올바르지 않습니다."],
        )

    errors: list[str] = []
    if policy.required_console_version != "V12.0":
        errors.append(
            "Required Console Version은 V12.0이어야 합니다."
        )
    if (
        not isinstance(
            policy.maximum_state_records,
            int,
        )
        or policy.maximum_state_records <= 0
    ):
        errors.append(
            "Maximum State Records가 올바르지 않습니다."
        )
    if policy.hash_algorithm != "SHA256":
        errors.append(
            "Hash Algorithm은 SHA256이어야 합니다."
        )
    if policy.genesis_hash != GENESIS_STATE_HASH:
        errors.append(
            "Genesis State Hash가 올바르지 않습니다."
        )

    required_true_values = {
        "accept_ready_status": (
            policy.accept_ready_status
        ),
        "accept_review_status": (
            policy.accept_review_status
        ),
        "accept_blocked_status": (
            policy.accept_blocked_status
        ),
        "accept_failed_status": (
            policy.accept_failed_status
        ),
        "reject_duplicate_console_id": (
            policy.reject_duplicate_console_id
        ),
        "require_console_read_only": (
            policy.require_console_read_only
        ),
        "require_console_safety": (
            policy.require_console_safety
        ),
        "verify_existing_hash_chain": (
            policy.verify_existing_hash_chain
        ),
        "verify_updated_hash_chain": (
            policy.verify_updated_hash_chain
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
                f"{name}는 V12.1에서 True여야 합니다."
            )

    return (not errors, errors)


def validate_console_result(
    console_result: Any,
) -> tuple[bool, bool, list[str]]:
    if not isinstance(
        console_result,
        PaperTradingOperationsConsoleResult,
    ):
        return (
            False,
            False,
            ["Console Result는 V12.0 형식이어야 합니다."],
        )

    errors: list[str] = []
    input_valid = True

    if console_result.version != "V12.0":
        input_valid = False
        errors.append(
            "Console Version이 V12.0이 아닙니다."
        )
    if (
        not isinstance(console_result.console_id, str)
        or not console_result.console_id.strip()
    ):
        input_valid = False
        errors.append(
            "Console ID가 비어 있습니다."
        )
    if (
        console_result.console_status
        not in VALID_CONSOLE_STATUSES
    ):
        input_valid = False
        errors.append(
            "Console Status가 올바르지 않습니다."
        )

    safety_valid = bool(
        console_result.read_only is True
        and console_result.execution_blocked is True
        and console_result
        .automatic_execution_authorized is False
        and console_result.broker_api_called is False
        and console_result.broker_order_created is False
        and console_result.live_order_created is False
        and console_result
        .live_execution_authorized is False
    )
    if not safety_valid:
        errors.append(
            "Console Result에 실거래 안전 오류가 있습니다."
        )

    return (
        input_valid,
        safety_valid,
        errors,
    )


def normalize_state_entries(
    existing_entries: Any,
) -> tuple[
    PaperTradingOperationsStateEntry,
    ...,
]:
    if existing_entries is None:
        return ()
    if not isinstance(
        existing_entries,
        (tuple, list),
    ):
        raise TypeError(
            "Existing Entries는 tuple 또는 list여야 합니다."
        )

    normalized: list[
        PaperTradingOperationsStateEntry
    ] = []
    for entry in existing_entries:
        if not isinstance(
            entry,
            PaperTradingOperationsStateEntry,
        ):
            raise TypeError(
                "Existing Entry 형식이 올바르지 않습니다."
            )
        normalized.append(entry)
    return tuple(normalized)


def verify_state_entry_chain(
    entries: tuple[
        PaperTradingOperationsStateEntry,
        ...,
    ],
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if not entries:
        return (True, errors)

    previous_sequence: int | None = None
    previous_hash = entries[0].previous_hash

    if (
        not isinstance(previous_hash, str)
        or len(previous_hash) != 64
    ):
        errors.append(
            "첫 Entry의 Anchor Hash가 올바르지 않습니다."
        )

    for entry in entries:
        if previous_sequence is not None:
            if entry.sequence_number != previous_sequence + 1:
                errors.append(
                    f"{entry.sequence_number}번 Sequence가 연속되지 않습니다."
                )
        if entry.previous_hash != previous_hash:
            errors.append(
                f"{entry.sequence_number}번 Previous Hash가 일치하지 않습니다."
            )

        expected_hash = (
            calculate_state_entry_hash(
                entry.payload_without_hash()
            )
        )
        if entry.entry_hash != expected_hash:
            errors.append(
                f"{entry.sequence_number}번 Entry Hash가 일치하지 않습니다."
            )

        previous_sequence = entry.sequence_number
        previous_hash = entry.entry_hash

    return (not errors, errors)


def create_state_entry(
    console_result: (
        PaperTradingOperationsConsoleResult
    ),
    sequence_number: int,
    previous_hash: str,
) -> PaperTradingOperationsStateEntry:
    values: dict[str, Any] = {
        "sequence_number": sequence_number,
        "state_entry_id": str(uuid.uuid4()),
        "recorded_at": datetime.now().isoformat(),
        "console_id": console_result.console_id,
        "console_created_at": (
            console_result.created_at
        ),
        "console_status": (
            console_result.console_status
        ),
        "manual_actor": console_result.manual_actor,
        "orchestration_id": (
            console_result.orchestration_id
        ),
        "audit_trail_id": (
            console_result.audit_trail_id
        ),
        "reconciliation_id": (
            console_result.reconciliation_id
        ),
        "release_gate_id": (
            console_result.release_gate_id
        ),
        "passed_card_count": (
            console_result.passed_card_count
        ),
        "total_card_count": (
            console_result.total_card_count
        ),
        "completed_stage_count": (
            console_result.completed_stage_count
        ),
        "total_stage_count": (
            console_result.total_stage_count
        ),
        "reconciliation_mismatch_count": (
            console_result
            .reconciliation_mismatch_count
        ),
        "paper_run_locked": (
            console_result.paper_run_locked
        ),
        "console_all_checks_passed": (
            console_result.all_checks_passed
        ),
        "read_only": True,
        "execution_blocked": True,
        "broker_api_called": False,
        "broker_order_created": False,
        "live_order_created": False,
        "live_execution_authorized": False,
        "previous_hash": previous_hash,
    }
    entry_hash = calculate_state_entry_hash(values)
    return PaperTradingOperationsStateEntry(
        **values,
        entry_hash=entry_hash,
    )


def validate_status_transition(
    previous_status: str | None,
    current_status: str,
) -> tuple[bool, str, list[str]]:
    if current_status not in VALID_CONSOLE_STATUSES:
        return (
            False,
            "INVALID",
            ["Current Console Status가 올바르지 않습니다."],
        )
    if (
        previous_status is not None
        and previous_status not in VALID_CONSOLE_STATUSES
    ):
        return (
            False,
            "INVALID",
            ["Previous Console Status가 올바르지 않습니다."],
        )

    transition = (
        f"{previous_status or 'NONE'}"
        f" -> {current_status}"
    )
    return (True, transition, [])


def update_paper_trading_operations_state_store(
    console_result: Any,
    existing_entries: Any = None,
    state_store_policy: (
        PaperTradingOperationsStateStorePolicy
        | None
    ) = None,
) -> PaperTradingOperationsStateStoreResult:
    policy = (
        state_store_policy
        if state_store_policy is not None
        else PaperTradingOperationsStateStorePolicy()
    )
    policy_valid, policy_errors = (
        validate_state_store_policy(policy)
    )
    input_valid, safety_valid, input_errors = (
        validate_console_result(console_result)
    )

    try:
        normalized_entries = normalize_state_entries(
            existing_entries
        )
        entries_valid = True
        entry_errors: list[str] = []
    except (TypeError, ValueError) as error:
        normalized_entries = ()
        entries_valid = False
        entry_errors = [str(error)]

    if entries_valid:
        existing_chain_valid, chain_errors = (
            verify_state_entry_chain(
                normalized_entries
            )
        )
    else:
        existing_chain_valid = False
        chain_errors = []

    console_id = getattr(
        console_result,
        "console_id",
        None,
    )
    duplicate_found = bool(
        isinstance(console_id, str)
        and any(
            entry.console_id == console_id
            for entry in normalized_entries
        )
    )
    duplicate_valid = bool(
        isinstance(console_id, str)
        and not duplicate_found
    )
    duplicate_errors = (
        ["동일한 Console ID가 이미 State Store에 있습니다."]
        if duplicate_found
        else []
    )

    previous_status = (
        normalized_entries[-1].console_status
        if normalized_entries
        else None
    )
    current_status = getattr(
        console_result,
        "console_status",
        "INVALID",
    )
    (
        transition_valid,
        transition,
        transition_errors,
    ) = validate_status_transition(
        previous_status,
        current_status,
    )

    preflight_valid = bool(
        policy_valid
        and input_valid
        and safety_valid
        and entries_valid
        and existing_chain_valid
        and duplicate_valid
        and transition_valid
    )

    updated_entries = normalized_entries
    records_trimmed = 0
    updated_chain_valid = False
    updated_chain_errors: list[str] = []

    if preflight_valid:
        next_sequence = (
            normalized_entries[-1]
            .sequence_number
            + 1
            if normalized_entries
            else 1
        )
        previous_hash = (
            normalized_entries[-1].entry_hash
            if normalized_entries
            else policy.genesis_hash
        )
        new_entry = create_state_entry(
            console_result,
            next_sequence,
            previous_hash,
        )
        all_entries = (
            *normalized_entries,
            new_entry,
        )
        records_trimmed = max(
            0,
            len(all_entries)
            - policy.maximum_state_records,
        )
        updated_entries = tuple(
            all_entries[
                -policy.maximum_state_records:
            ]
        )
        (
            updated_chain_valid,
            updated_chain_errors,
        ) = verify_state_entry_chain(
            updated_entries
        )

    all_checks_passed = bool(
        preflight_valid
        and updated_chain_valid
    )

    if all_checks_passed:
        store_status = "UPDATED"
        store_status_label = (
            "Paper Trading 운영 상태 저장 완료"
        )
        reasons = [
            "새 V12.0 Console Snapshot이 State Store에 추가되었습니다.",
            "State Entry Hash Chain이 정상적으로 검증되었습니다.",
        ]
        next_actions = [
            "Latest Console Status와 이전 상태 변화를 확인합니다.",
            "다음 Console Snapshot은 새로운 Console ID로 저장합니다.",
        ]
    elif duplicate_found:
        store_status = "BLOCKED"
        store_status_label = (
            "중복 Console Snapshot 차단"
        )
        reasons = [
            "이미 저장된 Console ID는 다시 추가할 수 없습니다."
        ]
        next_actions = [
            "새로운 V12.0 Console Snapshot을 생성합니다.",
        ]
    else:
        store_status = "FAILED"
        store_status_label = (
            "Paper Trading State Store 검사 실패"
        )
        reasons = [
            "Policy, 입력, Hash Chain, Transition 또는 Safety 검사에 실패했습니다."
        ]
        next_actions = [
            "Warnings에서 실패 원인을 확인합니다.",
            "기존 상태 기록을 직접 수정하지 않습니다.",
        ]

    warnings = [
        *policy_errors,
        *input_errors,
        *entry_errors,
        *chain_errors,
        *duplicate_errors,
        *transition_errors,
        *updated_chain_errors,
        "V12.1 State Store는 Console 상태만 저장합니다.",
        "Broker API, 실제 주문 및 Live Execution은 허용하지 않습니다.",
    ]

    result = PaperTradingOperationsStateStoreResult(
        version="V12.1",
        created_at=datetime.now().isoformat(),
        state_store_id=str(uuid.uuid4()),
        store_status=store_status,
        store_status_label=store_status_label,
        latest_console_id=(
            updated_entries[-1].console_id
            if updated_entries
            else None
        ),
        latest_console_status=(
            updated_entries[-1].console_status
            if updated_entries
            else None
        ),
        previous_console_status=previous_status,
        status_transition=(
            transition
            if transition_valid
            else None
        ),
        total_state_count=len(updated_entries),
        records_trimmed=records_trimmed,
        first_sequence_number=(
            updated_entries[0].sequence_number
            if updated_entries
            else None
        ),
        last_sequence_number=(
            updated_entries[-1].sequence_number
            if updated_entries
            else None
        ),
        first_entry_hash=(
            updated_entries[0].entry_hash
            if updated_entries
            else None
        ),
        last_entry_hash=(
            updated_entries[-1].entry_hash
            if updated_entries
            else None
        ),
        policy_checks_passed=policy_valid,
        input_checks_passed=input_valid,
        existing_chain_checks_passed=(
            existing_chain_valid
        ),
        duplicate_checks_passed=duplicate_valid,
        transition_checks_passed=transition_valid,
        updated_chain_checks_passed=(
            updated_chain_valid
        ),
        safety_checks_passed=safety_valid,
        all_checks_passed=all_checks_passed,
        automatic_execution_authorized=False,
        execution_blocked=True,
        broker_api_called=False,
        broker_order_created=False,
        live_order_created=False,
        live_execution_authorized=False,
        state_store_policy=policy,
        state_entries=updated_entries,
        reasons=reasons,
        warnings=warnings,
        next_actions=next_actions,
    )

    print_paper_trading_operations_state_store(
        result
    )
    return result


def verify_saved_state_store_payload(
    payload: dict[str, Any],
) -> tuple[bool, list[str]]:
    raw_entries = payload.get("state_entries")
    if not isinstance(raw_entries, list):
        return (
            False,
            ["State Entries가 list가 아닙니다."],
        )

    errors: list[str] = []
    previous_sequence: int | None = None
    previous_hash = (
        raw_entries[0].get("previous_hash")
        if raw_entries
        and isinstance(raw_entries[0], dict)
        else GENESIS_STATE_HASH
    )

    for index, raw_entry in enumerate(
        raw_entries,
        start=1,
    ):
        if not isinstance(raw_entry, dict):
            errors.append(
                f"{index}번 State Entry가 object가 아닙니다."
            )
            continue

        sequence = raw_entry.get(
            "sequence_number"
        )
        if (
            previous_sequence is not None
            and sequence != previous_sequence + 1
        ):
            errors.append(
                f"{index}번 Sequence가 연속되지 않습니다."
            )
        if (
            raw_entry.get("previous_hash")
            != previous_hash
        ):
            errors.append(
                f"{index}번 Previous Hash가 일치하지 않습니다."
            )

        saved_hash = raw_entry.get("entry_hash")
        entry_payload = dict(raw_entry)
        entry_payload.pop("entry_hash", None)
        calculated_hash = (
            calculate_state_entry_hash(
                entry_payload
            )
        )
        if saved_hash != calculated_hash:
            errors.append(
                f"{index}번 Entry Hash가 일치하지 않습니다."
            )

        previous_sequence = sequence
        if isinstance(saved_hash, str):
            previous_hash = saved_hash

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


def save_paper_trading_operations_state_store(
    result: PaperTradingOperationsStateStoreResult,
) -> tuple[Path, Path]:
    if not isinstance(
        result,
        PaperTradingOperationsStateStoreResult,
    ):
        raise TypeError(
            "V12.1 State Store Result 형식이 아닙니다."
        )
    if not result.all_checks_passed:
        raise ValueError(
            "검사에 실패한 State Store 결과는 저장할 수 없습니다."
        )

    directory = (
        PAPER_TRADING_OPERATIONS_STATE_STORE_OUTPUT_DIRECTORY
    )
    directory.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S_%f"
    )
    report_path = directory / (
        f"paper_trading_operations_state_store_{timestamp}.json"
    )
    latest_path = directory / (
        "paper_trading_operations_state_store_latest.json"
    )

    result.report_path = str(report_path)
    result.latest_path = str(latest_path)
    payload = result.to_dict()
    payload_valid, payload_errors = (
        verify_saved_state_store_payload(payload)
    )
    if not payload_valid:
        raise RuntimeError(
            "저장 전 State Hash 검사가 실패했습니다: "
            + " | ".join(payload_errors)
        )

    write_json_file(report_path, payload)
    write_json_file(latest_path, payload)
    return (report_path, latest_path)


def load_latest_paper_trading_operations_state_store(
    verify_hash_chain: bool = True,
) -> dict[str, Any]:
    path = (
        PAPER_TRADING_OPERATIONS_STATE_STORE_OUTPUT_DIRECTORY
        / "paper_trading_operations_state_store_latest.json"
    )
    payload = read_json_file(path)

    if verify_hash_chain:
        valid, errors = (
            verify_saved_state_store_payload(
                payload
            )
        )
        if not valid:
            raise RuntimeError(
                "저장된 State Hash 검사가 실패했습니다: "
                + " | ".join(errors)
            )
    return payload


def print_paper_trading_operations_state_store(
    result: PaperTradingOperationsStateStoreResult,
) -> None:
    line_length = 120
    print()
    print("=" * line_length)
    print("V12.1 PAPER TRADING OPERATIONS STATE STORE")
    print("=" * line_length)
    print(
        f"Store status                  : "
        f"{result.store_status}"
    )
    print(
        f"Store status label            : "
        f"{result.store_status_label}"
    )
    print(
        f"Latest console ID             : "
        f"{result.latest_console_id}"
    )
    print(
        f"Latest console status         : "
        f"{result.latest_console_status}"
    )
    print(
        f"Previous console status       : "
        f"{result.previous_console_status}"
    )
    print(
        f"Status transition             : "
        f"{result.status_transition}"
    )
    print(
        f"State records                 : "
        f"{result.total_state_count}"
    )
    print(
        f"Records trimmed               : "
        f"{result.records_trimmed}"
    )
    print(
        f"Last state hash               : "
        f"{result.last_entry_hash}"
    )

    print()
    print("VALIDATION")
    print("-" * line_length)
    validation_values = (
        (
            "Policy checks passed",
            result.policy_checks_passed,
        ),
        (
            "Input checks passed",
            result.input_checks_passed,
        ),
        (
            "Existing chain checks passed",
            result.existing_chain_checks_passed,
        ),
        (
            "Duplicate checks passed",
            result.duplicate_checks_passed,
        ),
        (
            "Transition checks passed",
            result.transition_checks_passed,
        ),
        (
            "Updated chain checks passed",
            result.updated_chain_checks_passed,
        ),
        (
            "Safety checks passed",
            result.safety_checks_passed,
        ),
        (
            "All checks passed",
            result.all_checks_passed,
        ),
    )
    for label, value in validation_values:
        print(f"{label:<31}: {value}")

    print()
    print("EXECUTION SAFETY")
    print("-" * line_length)
    safety_values = (
        (
            "Automatic execution authorized",
            result.automatic_execution_authorized,
        ),
        (
            "Execution blocked",
            result.execution_blocked,
        ),
        (
            "Broker API called",
            result.broker_api_called,
        ),
        (
            "Broker order created",
            result.broker_order_created,
        ),
        (
            "Live order created",
            result.live_order_created,
        ),
        (
            "Live execution authorized",
            result.live_execution_authorized,
        ),
    )
    for label, value in safety_values:
        print(f"{label:<31}: {value}")

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
        "주의: V12.1은 Console 상태만 저장하며 "
        "실제 주문을 수행하지 않습니다."
    )
