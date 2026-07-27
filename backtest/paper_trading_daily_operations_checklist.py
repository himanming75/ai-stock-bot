import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any

from backtest.paper_trading_operations_console import (
    PaperTradingOperationsConsoleResult,
)
from backtest.paper_trading_operations_state_store import (
    PaperTradingOperationsStateStoreResult,
    verify_state_entry_chain,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent

PAPER_TRADING_DAILY_OPERATIONS_CHECKLIST_OUTPUT_DIRECTORY = (
    PROJECT_ROOT
    / "output"
    / "trading_engine"
    / "paper_trading_daily_operations_checklist"
)

REQUIRED_CONFIRMATION_TEXT = (
    "CONFIRM DAILY PAPER OPERATIONS"
)

VALID_CHECKLIST_STATUSES = {
    "READY",
    "BLOCKED",
    "FAILED",
}


@dataclass(frozen=True)
class PaperTradingDailyOperationsChecklistPolicy:
    """
    V12.2 Daily Operations Checklist 정책입니다.

    이 단계는 운영 상태를 사람이 확인하는 읽기 전용 단계입니다.
    Broker 주문이나 자동 실행을 절대로 수행하지 않습니다.
    """

    required_console_version: str = "V12.0"
    required_state_store_version: str = "V12.1"
    required_console_status: str = "READY"
    required_store_status: str = "UPDATED"
    required_confirmation_text: str = (
        REQUIRED_CONFIRMATION_TEXT
    )
    minimum_note_length: int = 5
    required_console_card_count: int = 6

    require_same_console_id: bool = True
    require_same_console_status: bool = True
    require_same_manual_actor: bool = True
    require_console_all_checks: bool = True
    require_store_all_checks: bool = True
    require_state_hash_chain: bool = True
    require_zero_reconciliation_mismatches: bool = True
    require_paper_run_locked: bool = True
    require_manual_confirmation: bool = True

    read_only_checklist: bool = True
    automatic_execution_disabled: bool = True
    paper_only: bool = True
    live_execution_disabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PaperTradingDailyChecklistItem:
    item_order: int
    item_code: str
    item_name: str
    item_status: str
    item_status_label: str
    passed: bool
    details: tuple[str, ...] = field(
        default_factory=tuple
    )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["details"] = list(self.details)
        return payload


@dataclass
class PaperTradingDailyOperationsChecklistResult:
    version: str
    created_at: str
    checklist_id: str
    checklist_date: str

    checklist_status: str
    checklist_status_label: str
    manual_actor: str | None
    manual_note: str | None

    console_id: str | None
    state_store_id: str | None
    state_entry_id: str | None
    console_status: str | None
    stored_console_status: str | None

    total_item_count: int
    passed_item_count: int
    blocked_item_count: int
    failed_item_count: int

    policy_checks_passed: bool
    input_checks_passed: bool
    source_identity_checks_passed: bool
    source_status_checks_passed: bool
    state_hash_chain_checks_passed: bool
    manual_checks_passed: bool
    safety_checks_passed: bool
    all_checks_passed: bool

    read_only: bool
    automatic_execution_authorized: bool
    execution_blocked: bool
    broker_api_called: bool
    broker_order_created: bool
    live_order_created: bool
    live_execution_authorized: bool

    checklist_policy: (
        PaperTradingDailyOperationsChecklistPolicy
    )
    checklist_items: tuple[
        PaperTradingDailyChecklistItem,
        ...,
    ]

    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)

    report_path: str | None = None
    latest_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["checklist_policy"] = (
            self.checklist_policy.to_dict()
        )
        payload["checklist_items"] = [
            item.to_dict()
            for item in self.checklist_items
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


def validate_checklist_policy(
    policy: PaperTradingDailyOperationsChecklistPolicy,
) -> tuple[bool, list[str]]:
    if not isinstance(
        policy,
        PaperTradingDailyOperationsChecklistPolicy,
    ):
        return (
            False,
            ["Daily Checklist Policy 형식이 올바르지 않습니다."],
        )

    errors: list[str] = []
    required_values = {
        "required_console_version": "V12.0",
        "required_state_store_version": "V12.1",
        "required_console_status": "READY",
        "required_store_status": "UPDATED",
        "required_confirmation_text": (
            REQUIRED_CONFIRMATION_TEXT
        ),
        "required_console_card_count": 6,
    }
    for name, expected in required_values.items():
        if getattr(policy, name) != expected:
            errors.append(
                f"{name} 값이 V12.2 기준과 다릅니다."
            )

    if (
        not isinstance(policy.minimum_note_length, int)
        or policy.minimum_note_length < 1
    ):
        errors.append(
            "Minimum Note Length가 올바르지 않습니다."
        )

    required_true_values = {
        "require_same_console_id": (
            policy.require_same_console_id
        ),
        "require_same_console_status": (
            policy.require_same_console_status
        ),
        "require_same_manual_actor": (
            policy.require_same_manual_actor
        ),
        "require_console_all_checks": (
            policy.require_console_all_checks
        ),
        "require_store_all_checks": (
            policy.require_store_all_checks
        ),
        "require_state_hash_chain": (
            policy.require_state_hash_chain
        ),
        "require_zero_reconciliation_mismatches": (
            policy.require_zero_reconciliation_mismatches
        ),
        "require_paper_run_locked": (
            policy.require_paper_run_locked
        ),
        "require_manual_confirmation": (
            policy.require_manual_confirmation
        ),
        "read_only_checklist": (
            policy.read_only_checklist
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
                f"{name}는 V12.2에서 True여야 합니다."
            )

    return (not errors, errors)


def validate_source_inputs(
    console_result: Any,
    state_store_result: Any,
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if not isinstance(
        console_result,
        PaperTradingOperationsConsoleResult,
    ):
        errors.append(
            "Console Result는 V12.0 형식이어야 합니다."
        )
    elif console_result.version != "V12.0":
        errors.append(
            "Console Version이 V12.0이 아닙니다."
        )

    if not isinstance(
        state_store_result,
        PaperTradingOperationsStateStoreResult,
    ):
        errors.append(
            "State Store Result는 V12.1 형식이어야 합니다."
        )
    elif state_store_result.version != "V12.1":
        errors.append(
            "State Store Version이 V12.1이 아닙니다."
        )

    return (not errors, errors)


def validate_source_safety(
    source: Any,
) -> bool:
    return bool(
        getattr(source, "execution_blocked", False)
        is True
        and getattr(
            source,
            "automatic_execution_authorized",
            True,
        )
        is False
        and getattr(source, "broker_api_called", True)
        is False
        and getattr(source, "broker_order_created", True)
        is False
        and getattr(source, "live_order_created", True)
        is False
        and getattr(
            source,
            "live_execution_authorized",
            True,
        )
        is False
    )


def make_checklist_item(
    item_order: int,
    item_code: str,
    item_name: str,
    passed: bool,
    details: tuple[str, ...],
    *,
    failure_status: str = "BLOCKED",
) -> PaperTradingDailyChecklistItem:
    status = "PASS" if passed else failure_status
    label = (
        "확인 완료"
        if passed
        else (
            "검사 실패"
            if failure_status == "FAILED"
            else "확인 필요"
        )
    )
    return PaperTradingDailyChecklistItem(
        item_order=item_order,
        item_code=item_code,
        item_name=item_name,
        item_status=status,
        item_status_label=label,
        passed=passed,
        details=details,
    )


def build_daily_checklist_items(
    console_result: PaperTradingOperationsConsoleResult,
    state_store_result: PaperTradingOperationsStateStoreResult,
    manual_actor: str,
    confirmation_text: str,
    manual_note: str,
    policy: PaperTradingDailyOperationsChecklistPolicy,
    state_chain_valid: bool,
) -> tuple[PaperTradingDailyChecklistItem, ...]:
    latest_entry = (
        state_store_result.state_entries[-1]
        if state_store_result.state_entries
        else None
    )
    values = [
        (
            "CONSOLE_READY",
            "Operations Console READY",
            (
                console_result.console_status
                == policy.required_console_status
                and console_result.all_checks_passed
            ),
            (
                f"Console Status: {console_result.console_status}",
                f"All Checks: {console_result.all_checks_passed}",
            ),
            "BLOCKED",
        ),
        (
            "CONSOLE_CARDS",
            "Console Card 전체 통과",
            (
                console_result.total_card_count
                == policy.required_console_card_count
                and console_result.passed_card_count
                == console_result.total_card_count
            ),
            (
                f"Passed Cards: {console_result.passed_card_count}",
                f"Total Cards: {console_result.total_card_count}",
            ),
            "BLOCKED",
        ),
        (
            "PAPER_RUN_LOCKED",
            "Paper Run 잠금 상태",
            console_result.paper_run_locked is True,
            (
                f"Paper Run Locked: {console_result.paper_run_locked}",
            ),
            "BLOCKED",
        ),
        (
            "STATE_UPDATED",
            "Operations State Store 최신 상태",
            (
                state_store_result.store_status
                == policy.required_store_status
                and state_store_result.all_checks_passed
            ),
            (
                f"Store Status: {state_store_result.store_status}",
                f"All Checks: {state_store_result.all_checks_passed}",
            ),
            "FAILED",
        ),
        (
            "SOURCE_IDENTITY",
            "Console ID 연결",
            (
                latest_entry is not None
                and state_store_result.latest_console_id
                == console_result.console_id
                and latest_entry.console_id
                == console_result.console_id
            ),
            (
                f"Console ID: {console_result.console_id}",
                f"Stored Console ID: {state_store_result.latest_console_id}",
            ),
            "FAILED",
        ),
        (
            "SOURCE_STATUS",
            "Console Status 연결",
            (
                latest_entry is not None
                and state_store_result.latest_console_status
                == console_result.console_status
                and latest_entry.console_status
                == console_result.console_status
            ),
            (
                f"Console Status: {console_result.console_status}",
                f"Stored Status: {state_store_result.latest_console_status}",
            ),
            "BLOCKED",
        ),
        (
            "STATE_HASH_CHAIN",
            "State SHA-256 Hash Chain",
            state_chain_valid,
            (
                f"State Count: {state_store_result.total_state_count}",
                f"Last Hash: {state_store_result.last_entry_hash}",
            ),
            "FAILED",
        ),
        (
            "RECONCILIATION",
            "Reconciliation 불일치 없음",
            (
                console_result.reconciliation_mismatch_count
                == 0
            ),
            (
                "Mismatch Count: "
                f"{console_result.reconciliation_mismatch_count}",
            ),
            "BLOCKED",
        ),
        (
            "MANUAL_ACTOR",
            "수동 확인자 일치",
            bool(
                manual_actor.strip()
                and manual_actor.strip()
                == (console_result.manual_actor or "").strip()
                and latest_entry is not None
                and manual_actor.strip()
                == (latest_entry.manual_actor or "").strip()
            ),
            (
                f"Input Actor: {manual_actor.strip() or 'None'}",
                f"Console Actor: {console_result.manual_actor}",
            ),
            "BLOCKED",
        ),
        (
            "CONFIRMATION_TEXT",
            "수동 확인 문구",
            (
                confirmation_text.strip()
                == policy.required_confirmation_text
            ),
            (
                "Required: "
                f"{policy.required_confirmation_text}",
            ),
            "BLOCKED",
        ),
        (
            "MANUAL_NOTE",
            "운영 메모 입력",
            (
                len(manual_note.strip())
                >= policy.minimum_note_length
            ),
            (
                f"Note Length: {len(manual_note.strip())}",
                f"Minimum: {policy.minimum_note_length}",
            ),
            "BLOCKED",
        ),
        (
            "EXECUTION_SAFETY",
            "실거래 안전 차단",
            (
                validate_source_safety(console_result)
                and validate_source_safety(state_store_result)
                and console_result.read_only is True
            ),
            (
                "Broker API Called: False",
                "Live Execution Authorized: False",
            ),
            "FAILED",
        ),
    ]
    return tuple(
        make_checklist_item(
            index,
            code,
            name,
            passed,
            details,
            failure_status=failure_status,
        )
        for index, (
            code,
            name,
            passed,
            details,
            failure_status,
        ) in enumerate(values, start=1)
    )


def build_paper_trading_daily_operations_checklist(
    console_result: Any,
    state_store_result: Any,
    manual_actor: Any,
    confirmation_text: Any,
    manual_note: Any,
    checklist_date: str | None = None,
    checklist_policy: (
        PaperTradingDailyOperationsChecklistPolicy
        | None
    ) = None,
) -> PaperTradingDailyOperationsChecklistResult:
    policy = (
        checklist_policy
        if checklist_policy is not None
        else PaperTradingDailyOperationsChecklistPolicy()
    )
    policy_valid, policy_errors = (
        validate_checklist_policy(policy)
    )
    input_valid, input_errors = validate_source_inputs(
        console_result,
        state_store_result,
    )

    text_inputs_valid = bool(
        isinstance(manual_actor, str)
        and isinstance(confirmation_text, str)
        and isinstance(manual_note, str)
    )
    text_errors = (
        []
        if text_inputs_valid
        else [
            "Manual Actor, Confirmation Text와 Manual Note는 문자열이어야 합니다."
        ]
    )

    requested_date = checklist_date or date.today().isoformat()
    try:
        date.fromisoformat(requested_date)
        date_valid = True
        date_errors: list[str] = []
    except (TypeError, ValueError):
        date_valid = False
        date_errors = [
            "Checklist Date는 YYYY-MM-DD 형식이어야 합니다."
        ]

    state_chain_valid = False
    chain_errors: list[str] = []
    if input_valid:
        state_chain_valid, chain_errors = (
            verify_state_entry_chain(
                state_store_result.state_entries
            )
        )
        if not state_store_result.state_entries:
            state_chain_valid = False
            chain_errors.append(
                "State Store에 Entry가 없습니다."
            )

    if input_valid and text_inputs_valid:
        items = build_daily_checklist_items(
            console_result,
            state_store_result,
            manual_actor,
            confirmation_text,
            manual_note,
            policy,
            state_chain_valid,
        )
    else:
        items = ()

    failed_item_count = sum(
        item.item_status == "FAILED"
        for item in items
    )
    blocked_item_count = sum(
        item.item_status == "BLOCKED"
        for item in items
    )
    passed_item_count = sum(
        item.item_status == "PASS"
        for item in items
    )

    source_identity_valid = bool(
        input_valid
        and any(
            item.item_code == "SOURCE_IDENTITY"
            and item.passed
            for item in items
        )
    )
    source_status_valid = bool(
        input_valid
        and all(
            item.passed
            for item in items
            if item.item_code
            in {
                "CONSOLE_READY",
                "STATE_UPDATED",
                "SOURCE_STATUS",
            }
        )
        and len(items) > 0
    )
    manual_valid = bool(
        text_inputs_valid
        and all(
            item.passed
            for item in items
            if item.item_code
            in {
                "MANUAL_ACTOR",
                "CONFIRMATION_TEXT",
                "MANUAL_NOTE",
            }
        )
        and len(items) > 0
    )
    safety_valid = bool(
        input_valid
        and any(
            item.item_code == "EXECUTION_SAFETY"
            and item.passed
            for item in items
        )
    )
    all_checks_passed = bool(
        policy_valid
        and input_valid
        and text_inputs_valid
        and date_valid
        and items
        and all(item.passed for item in items)
    )

    if all_checks_passed:
        checklist_status = "READY"
        checklist_status_label = (
            "Daily Paper Operations 수동 검토 준비 완료"
        )
        reasons = [
            "V12.0 Console과 V12.1 State Store가 일치합니다.",
            "수동 확인 문구, 확인자 및 운영 메모가 검증되었습니다.",
        ]
        next_actions = [
            "Checklist 내용을 사람이 다시 검토합니다.",
            "다음 단계에서도 Broker 연결 없이 Paper 운영만 준비합니다.",
        ]
    elif (
        failed_item_count > 0
        or not policy_valid
        or not input_valid
        or not date_valid
    ):
        checklist_status = "FAILED"
        checklist_status_label = (
            "Daily Operations Checklist 검사 실패"
        )
        reasons = [
            "Source, Policy, Hash Chain 또는 Safety 검사에 실패했습니다."
        ]
        next_actions = [
            "Warnings와 FAILED 항목을 먼저 수정합니다.",
            "Source 결과를 직접 변경하지 말고 다시 생성합니다.",
        ]
    else:
        checklist_status = "BLOCKED"
        checklist_status_label = (
            "Daily Operations 수동 확인 미완료"
        )
        reasons = [
            "운영 상태 또는 수동 확인 항목이 완료되지 않았습니다."
        ]
        next_actions = [
            "BLOCKED 항목을 확인하고 올바른 값으로 다시 실행합니다.",
        ]

    latest_entry = (
        state_store_result.state_entries[-1]
        if input_valid and state_store_result.state_entries
        else None
    )
    result = PaperTradingDailyOperationsChecklistResult(
        version="V12.2",
        created_at=datetime.now().isoformat(),
        checklist_id=str(uuid.uuid4()),
        checklist_date=(
            requested_date
            if date_valid
            else str(requested_date)
        ),
        checklist_status=checklist_status,
        checklist_status_label=checklist_status_label,
        manual_actor=(
            manual_actor.strip()
            if isinstance(manual_actor, str)
            else None
        ),
        manual_note=(
            manual_note.strip()
            if isinstance(manual_note, str)
            else None
        ),
        console_id=getattr(
            console_result,
            "console_id",
            None,
        ),
        state_store_id=getattr(
            state_store_result,
            "state_store_id",
            None,
        ),
        state_entry_id=(
            latest_entry.state_entry_id
            if latest_entry is not None
            else None
        ),
        console_status=getattr(
            console_result,
            "console_status",
            None,
        ),
        stored_console_status=getattr(
            state_store_result,
            "latest_console_status",
            None,
        ),
        total_item_count=len(items),
        passed_item_count=passed_item_count,
        blocked_item_count=blocked_item_count,
        failed_item_count=failed_item_count,
        policy_checks_passed=policy_valid,
        input_checks_passed=bool(
            input_valid
            and text_inputs_valid
            and date_valid
        ),
        source_identity_checks_passed=(
            source_identity_valid
        ),
        source_status_checks_passed=(
            source_status_valid
        ),
        state_hash_chain_checks_passed=(
            state_chain_valid
        ),
        manual_checks_passed=manual_valid,
        safety_checks_passed=safety_valid,
        all_checks_passed=all_checks_passed,
        read_only=True,
        automatic_execution_authorized=False,
        execution_blocked=True,
        broker_api_called=False,
        broker_order_created=False,
        live_order_created=False,
        live_execution_authorized=False,
        checklist_policy=policy,
        checklist_items=items,
        reasons=reasons,
        warnings=[
            *policy_errors,
            *input_errors,
            *text_errors,
            *date_errors,
            *chain_errors,
            "V12.2는 Daily Paper Trading 운영 확인 단계입니다.",
            "실제 Broker API, 실제 주문 및 Live Execution은 모두 차단됩니다.",
        ],
        next_actions=next_actions,
    )
    return result


def verify_saved_checklist_payload(
    payload: dict[str, Any],
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if payload.get("version") != "V12.2":
        errors.append(
            "저장된 Checklist Version이 V12.2가 아닙니다."
        )
    if payload.get("checklist_status") not in (
        VALID_CHECKLIST_STATUSES
    ):
        errors.append(
            "저장된 Checklist Status가 올바르지 않습니다."
        )
    if payload.get("execution_blocked") is not True:
        errors.append(
            "저장된 Checklist의 Execution이 차단되지 않았습니다."
        )
    unsafe_false_fields = (
        "automatic_execution_authorized",
        "broker_api_called",
        "broker_order_created",
        "live_order_created",
        "live_execution_authorized",
    )
    for field_name in unsafe_false_fields:
        if payload.get(field_name) is not False:
            errors.append(
                f"저장된 {field_name} 값이 False가 아닙니다."
            )
    return (not errors, errors)


def save_paper_trading_daily_operations_checklist(
    result: PaperTradingDailyOperationsChecklistResult,
    output_directory: Path | None = None,
) -> PaperTradingDailyOperationsChecklistResult:
    if not isinstance(
        result,
        PaperTradingDailyOperationsChecklistResult,
    ):
        raise TypeError(
            "V12.2 Daily Checklist Result 형식이 아닙니다."
        )
    directory = (
        output_directory
        if output_directory is not None
        else PAPER_TRADING_DAILY_OPERATIONS_CHECKLIST_OUTPUT_DIRECTORY
    )
    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S_%f"
    )
    report_path = directory / (
        f"paper_trading_daily_checklist_{timestamp}.json"
    )
    latest_path = directory / (
        "paper_trading_daily_checklist_latest.json"
    )
    payload = result.to_dict()
    write_json_file(report_path, payload)
    write_json_file(latest_path, payload)
    result.report_path = str(report_path)
    result.latest_path = str(latest_path)
    return result


def load_latest_paper_trading_daily_operations_checklist(
    output_directory: Path | None = None,
) -> dict[str, Any]:
    directory = (
        output_directory
        if output_directory is not None
        else PAPER_TRADING_DAILY_OPERATIONS_CHECKLIST_OUTPUT_DIRECTORY
    )
    return read_json_file(
        directory
        / "paper_trading_daily_checklist_latest.json"
    )


def print_paper_trading_daily_operations_checklist(
    result: PaperTradingDailyOperationsChecklistResult,
) -> None:
    line = "=" * 100
    print()
    print(line)
    print("V12.2 PAPER TRADING DAILY OPERATIONS CHECKLIST")
    print(line)
    print(f"Checklist status       : {result.checklist_status}")
    print(f"Checklist date         : {result.checklist_date}")
    print(f"Manual actor           : {result.manual_actor}")
    print(f"Console ID             : {result.console_id}")
    print(f"State Store ID         : {result.state_store_id}")
    print()
    print("CHECKLIST ITEMS")
    print("-" * 100)
    for item in result.checklist_items:
        print(
            f"{item.item_order:02d}. "
            f"{item.item_name:<38} : "
            f"{item.item_status}"
        )
    print()
    print("VALIDATION")
    print("-" * 100)
    checks = {
        "Policy checks passed": (
            result.policy_checks_passed
        ),
        "Input checks passed": (
            result.input_checks_passed
        ),
        "Source identity passed": (
            result.source_identity_checks_passed
        ),
        "Source status passed": (
            result.source_status_checks_passed
        ),
        "State hash chain passed": (
            result.state_hash_chain_checks_passed
        ),
        "Manual checks passed": (
            result.manual_checks_passed
        ),
        "Safety checks passed": (
            result.safety_checks_passed
        ),
        "All checks passed": result.all_checks_passed,
    }
    for name, value in checks.items():
        print(f"{name:<40} : {value}")
    print(line)
    print(
        "주의: V12.2는 운영 확인만 수행하며 실제 또는 "
        "자동 주문을 실행하지 않습니다."
    )
