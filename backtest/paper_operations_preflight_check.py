import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any

from backtest.approved_paper_operations_handoff import (
    ApprovedPaperOperationsHandoffResult,
    verify_handoff_record_chain,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PAPER_OPERATIONS_PREFLIGHT_OUTPUT_DIRECTORY = (
    PROJECT_ROOT
    / "output"
    / "trading_engine"
    / "paper_operations_preflight_check"
)

REQUIRED_PREFLIGHT_TEXT = (
    "CONFIRM PAPER OPERATIONS PREFLIGHT"
)

VALID_PREFLIGHT_STATUSES = {
    "READY",
    "BLOCKED",
    "FAILED",
}


@dataclass(frozen=True)
class PaperOperationsPreflightPolicy:
    """V12.6 Paper 실행 직전 종합 점검 정책입니다."""

    required_handoff_version: str = "V12.5"
    required_handoff_status: str = "HANDED_OFF"
    required_market_status: str = "PAPER_OPEN"
    required_confirmation_text: str = (
        REQUIRED_PREFLIGHT_TEXT
    )
    maximum_data_age_minutes: int = 15
    minimum_cash_balance: float = 100.0
    maximum_symbol_count: int = 20

    require_weekday: bool = True
    require_unique_symbols: bool = True
    require_handoff_all_checks: bool = True
    require_handoff_hash_chain: bool = True
    require_handoff_safety: bool = True
    require_operator_match: bool = True
    require_manual_confirmation: bool = True

    paper_preflight_only: bool = True
    automatic_execution_disabled: bool = True
    broker_execution_disabled: bool = True
    live_execution_disabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PaperOperationsPreflightItem:
    item_order: int
    item_code: str
    item_name: str
    item_status: str
    passed: bool
    details: tuple[str, ...] = field(
        default_factory=tuple
    )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["details"] = list(self.details)
        return payload


@dataclass
class PaperOperationsPreflightResult:
    version: str
    created_at: str
    preflight_id: str

    preflight_status: str
    preflight_status_label: str
    trading_date: str | None
    market_status: str | None
    operator: str | None
    symbols: tuple[str, ...]
    cash_balance: float | None
    market_data_age_minutes: int | None

    approved_handoff_id: str | None
    handoff_record_id: str | None
    total_item_count: int
    passed_item_count: int
    blocked_item_count: int
    failed_item_count: int

    policy_checks_passed: bool
    input_checks_passed: bool
    source_checks_passed: bool
    handoff_chain_checks_passed: bool
    operations_checks_passed: bool
    safety_checks_passed: bool
    all_checks_passed: bool

    paper_preflight_authorized: bool
    paper_execution_authorized: bool
    automatic_execution_authorized: bool
    execution_blocked: bool
    broker_api_called: bool
    broker_order_created: bool
    live_order_created: bool
    live_execution_authorized: bool

    preflight_policy: PaperOperationsPreflightPolicy
    preflight_items: tuple[
        PaperOperationsPreflightItem,
        ...,
    ]
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)
    report_path: str | None = None
    latest_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["symbols"] = list(self.symbols)
        payload["preflight_policy"] = (
            self.preflight_policy.to_dict()
        )
        payload["preflight_items"] = [
            item.to_dict()
            for item in self.preflight_items
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


def validate_preflight_policy(
    policy: PaperOperationsPreflightPolicy,
) -> tuple[bool, list[str]]:
    if not isinstance(
        policy,
        PaperOperationsPreflightPolicy,
    ):
        return (
            False,
            ["Preflight Policy 형식이 올바르지 않습니다."],
        )
    errors: list[str] = []
    expected = {
        "required_handoff_version": "V12.5",
        "required_handoff_status": "HANDED_OFF",
        "required_market_status": "PAPER_OPEN",
        "required_confirmation_text": (
            REQUIRED_PREFLIGHT_TEXT
        ),
    }
    for name, value in expected.items():
        if getattr(policy, name) != value:
            errors.append(
                f"{name} 값이 V12.6 기준과 다릅니다."
            )
    if (
        policy.maximum_data_age_minutes <= 0
        or policy.minimum_cash_balance <= 0
        or policy.maximum_symbol_count <= 0
    ):
        errors.append(
            "Preflight 숫자 기준이 올바르지 않습니다."
        )
    for name in (
        "require_weekday",
        "require_unique_symbols",
        "require_handoff_all_checks",
        "require_handoff_hash_chain",
        "require_handoff_safety",
        "require_operator_match",
        "require_manual_confirmation",
        "paper_preflight_only",
        "automatic_execution_disabled",
        "broker_execution_disabled",
        "live_execution_disabled",
    ):
        if getattr(policy, name) is not True:
            errors.append(
                f"{name}는 V12.6에서 True여야 합니다."
            )
    return (not errors, errors)


def validate_handoff_source(
    handoff_result: Any,
) -> tuple[bool, bool, list[str]]:
    if not isinstance(
        handoff_result,
        ApprovedPaperOperationsHandoffResult,
    ):
        return (
            False,
            False,
            ["Handoff Result는 V12.5 형식이어야 합니다."],
        )
    errors: list[str] = []
    source_valid = bool(
        handoff_result.version == "V12.5"
        and handoff_result.handoff_status
        == "HANDED_OFF"
        and handoff_result.all_checks_passed
        and handoff_result.paper_preparation_authorized
        and handoff_result.handoff_records
    )
    if not source_valid:
        errors.append(
            "정상적으로 HANDED_OFF된 V12.5 Source가 아닙니다."
        )
    safety_valid = bool(
        handoff_result.paper_execution_authorized is False
        and handoff_result
        .automatic_execution_authorized is False
        and handoff_result.execution_blocked is True
        and handoff_result.broker_api_called is False
        and handoff_result.broker_order_created is False
        and handoff_result.live_order_created is False
        and handoff_result
        .live_execution_authorized is False
    )
    if not safety_valid:
        errors.append(
            "Handoff Source에 실행 안전 오류가 있습니다."
        )
    return (source_valid, safety_valid, errors)


def make_item(
    order: int,
    code: str,
    name: str,
    passed: bool,
    details: tuple[str, ...],
    failure_status: str = "BLOCKED",
) -> PaperOperationsPreflightItem:
    return PaperOperationsPreflightItem(
        item_order=order,
        item_code=code,
        item_name=name,
        item_status=(
            "PASS"
            if passed
            else failure_status
        ),
        passed=passed,
        details=details,
    )


def build_items(
    handoff_result: ApprovedPaperOperationsHandoffResult,
    parsed_date: date,
    market_status: str,
    operator: str,
    symbols: tuple[str, ...],
    cash_balance: float,
    market_data_age_minutes: int,
    confirmation_text: str,
    policy: PaperOperationsPreflightPolicy,
    chain_valid: bool,
) -> tuple[PaperOperationsPreflightItem, ...]:
    source_record = handoff_result.handoff_records[-1]
    normalized_symbols = tuple(
        symbol.strip().upper()
        for symbol in symbols
    )
    values = [
        (
            "HANDOFF_READY",
            "승인 Handoff 상태",
            (
                handoff_result.handoff_status
                == policy.required_handoff_status
                and handoff_result.all_checks_passed
                and handoff_result
                .paper_preparation_authorized
            ),
            (
                f"Status: {handoff_result.handoff_status}",
            ),
            "FAILED",
        ),
        (
            "HANDOFF_CHAIN",
            "Handoff SHA-256 Chain",
            chain_valid,
            (
                f"Record Count: {len(handoff_result.handoff_records)}",
            ),
            "FAILED",
        ),
        (
            "APPROVAL_SOURCE",
            "APPROVE Source 연결",
            (
                source_record.decision == "APPROVE"
                and source_record.handoff_status
                == "HANDED_OFF"
            ),
            (
                f"Decision: {source_record.decision}",
            ),
            "FAILED",
        ),
        (
            "OPERATOR_MATCH",
            "Preflight Operator 일치",
            (
                operator.strip()
                == source_record.handoff_operator
            ),
            (
                f"Operator: {operator.strip()}",
                f"Handoff Operator: {source_record.handoff_operator}",
            ),
            "BLOCKED",
        ),
        (
            "TRADING_WEEKDAY",
            "Paper 거래일 확인",
            parsed_date.weekday() < 5,
            (
                f"Trading Date: {parsed_date.isoformat()}",
                f"Weekday Index: {parsed_date.weekday()}",
            ),
            "BLOCKED",
        ),
        (
            "MARKET_STATUS",
            "Paper Market 상태",
            (
                market_status
                == policy.required_market_status
            ),
            (
                f"Market Status: {market_status}",
            ),
            "BLOCKED",
        ),
        (
            "SYMBOLS_PRESENT",
            "종목 입력 확인",
            bool(
                normalized_symbols
                and all(normalized_symbols)
                and len(normalized_symbols)
                <= policy.maximum_symbol_count
            ),
            (
                f"Symbols: {', '.join(normalized_symbols)}",
            ),
            "BLOCKED",
        ),
        (
            "SYMBOLS_UNIQUE",
            "종목 중복 없음",
            (
                len(normalized_symbols)
                == len(set(normalized_symbols))
            ),
            (
                f"Symbol Count: {len(normalized_symbols)}",
            ),
            "BLOCKED",
        ),
        (
            "CASH_BALANCE",
            "Paper Cash 잔액",
            cash_balance >= policy.minimum_cash_balance,
            (
                f"Cash: ${cash_balance:,.2f}",
                f"Minimum: ${policy.minimum_cash_balance:,.2f}",
            ),
            "BLOCKED",
        ),
        (
            "DATA_FRESHNESS",
            "Market Data 신선도",
            (
                0 <= market_data_age_minutes
                <= policy.maximum_data_age_minutes
            ),
            (
                f"Age: {market_data_age_minutes} minutes",
                f"Maximum: {policy.maximum_data_age_minutes} minutes",
            ),
            "BLOCKED",
        ),
        (
            "MANUAL_CONFIRMATION",
            "수동 Preflight 확인 문구",
            (
                confirmation_text.strip()
                == policy.required_confirmation_text
            ),
            (
                f"Required: {policy.required_confirmation_text}",
            ),
            "BLOCKED",
        ),
        (
            "EXECUTION_SAFETY",
            "주문 실행 안전 차단",
            (
                handoff_result.execution_blocked is True
                and handoff_result
                .paper_execution_authorized is False
                and handoff_result.broker_api_called is False
                and handoff_result
                .live_execution_authorized is False
            ),
            (
                "Paper Execution Authorized: False",
                "Broker API Called: False",
            ),
            "FAILED",
        ),
    ]
    return tuple(
        make_item(
            index,
            code,
            name,
            passed,
            details,
            failure_status,
        )
        for index, (
            code,
            name,
            passed,
            details,
            failure_status,
        ) in enumerate(values, start=1)
    )


def run_paper_operations_preflight_check(
    handoff_result: Any,
    trading_date: Any,
    market_status: Any,
    operator: Any,
    symbols: Any,
    cash_balance: Any,
    market_data_age_minutes: Any,
    confirmation_text: Any,
    preflight_policy: (
        PaperOperationsPreflightPolicy | None
    ) = None,
) -> PaperOperationsPreflightResult:
    policy = (
        preflight_policy
        if preflight_policy is not None
        else PaperOperationsPreflightPolicy()
    )
    policy_valid, policy_errors = (
        validate_preflight_policy(policy)
    )
    source_valid, source_safety_valid, source_errors = (
        validate_handoff_source(handoff_result)
    )

    try:
        parsed_date = date.fromisoformat(trading_date)
        date_valid = True
        date_errors: list[str] = []
    except (TypeError, ValueError):
        parsed_date = date.today()
        date_valid = False
        date_errors = [
            "Trading Date는 YYYY-MM-DD 형식이어야 합니다."
        ]
    input_valid = bool(
        date_valid
        and isinstance(market_status, str)
        and isinstance(operator, str)
        and operator.strip()
        and isinstance(symbols, (tuple, list))
        and all(isinstance(symbol, str) for symbol in symbols)
        and isinstance(cash_balance, (int, float))
        and not isinstance(cash_balance, bool)
        and isinstance(market_data_age_minutes, int)
        and not isinstance(market_data_age_minutes, bool)
        and isinstance(confirmation_text, str)
    )
    input_errors = (
        []
        if input_valid
        else ["Preflight 입력 형식이 올바르지 않습니다."]
    )
    normalized_symbols = (
        tuple(symbols)
        if isinstance(symbols, (tuple, list))
        and all(isinstance(symbol, str) for symbol in symbols)
        else ()
    )

    if source_valid:
        chain_valid, chain_errors = (
            verify_handoff_record_chain(
                handoff_result.handoff_records
            )
        )
    else:
        chain_valid = False
        chain_errors = []

    if source_valid and input_valid:
        items = build_items(
            handoff_result,
            parsed_date,
            market_status,
            operator,
            normalized_symbols,
            float(cash_balance),
            market_data_age_minutes,
            confirmation_text,
            policy,
            chain_valid,
        )
    else:
        items = ()

    passed_count = sum(
        item.item_status == "PASS"
        for item in items
    )
    blocked_count = sum(
        item.item_status == "BLOCKED"
        for item in items
    )
    failed_count = sum(
        item.item_status == "FAILED"
        for item in items
    )
    operations_valid = bool(
        items and all(item.passed for item in items)
    )
    all_checks_passed = bool(
        policy_valid
        and source_valid
        and source_safety_valid
        and input_valid
        and chain_valid
        and operations_valid
    )

    if all_checks_passed:
        status = "READY"
        label = "Paper Operations Preflight 준비 완료"
        reasons = [
            "12개 실행 전 점검 항목이 모두 통과했습니다.",
            "Paper 실행 준비 상태만 확인되었습니다.",
        ]
        next_actions = [
            "결과를 사람이 다시 확인합니다.",
            "다음 단계에서도 별도 실행 승인이 필요합니다.",
        ]
    elif (
        failed_count > 0
        or not policy_valid
        or not source_valid
        or not source_safety_valid
        or not input_valid
        or not chain_valid
    ):
        status = "FAILED"
        label = "Paper Operations Preflight 검사 실패"
        reasons = [
            "Source, 입력, Hash Chain 또는 Safety 검사에 실패했습니다."
        ]
        next_actions = [
            "Warnings와 FAILED 항목을 수정합니다.",
        ]
    else:
        status = "BLOCKED"
        label = "Paper Operations Preflight 조건 미충족"
        reasons = [
            "운영 조건 또는 수동 확인이 완료되지 않았습니다."
        ]
        next_actions = [
            "BLOCKED 항목을 확인한 후 다시 검사합니다.",
        ]

    source_record = (
        handoff_result.handoff_records[-1]
        if source_valid
        else None
    )
    return PaperOperationsPreflightResult(
        version="V12.6",
        created_at=datetime.now().isoformat(),
        preflight_id=str(uuid.uuid4()),
        preflight_status=status,
        preflight_status_label=label,
        trading_date=(
            parsed_date.isoformat()
            if date_valid
            else None
        ),
        market_status=(
            market_status
            if isinstance(market_status, str)
            else None
        ),
        operator=(
            operator.strip()
            if isinstance(operator, str)
            else None
        ),
        symbols=tuple(
            symbol.strip().upper()
            for symbol in normalized_symbols
        ),
        cash_balance=(
            float(cash_balance)
            if isinstance(cash_balance, (int, float))
            and not isinstance(cash_balance, bool)
            else None
        ),
        market_data_age_minutes=(
            market_data_age_minutes
            if isinstance(market_data_age_minutes, int)
            and not isinstance(market_data_age_minutes, bool)
            else None
        ),
        approved_handoff_id=getattr(
            handoff_result,
            "approved_handoff_id",
            None,
        ),
        handoff_record_id=(
            source_record.handoff_record_id
            if source_record
            else None
        ),
        total_item_count=len(items),
        passed_item_count=passed_count,
        blocked_item_count=blocked_count,
        failed_item_count=failed_count,
        policy_checks_passed=policy_valid,
        input_checks_passed=input_valid,
        source_checks_passed=source_valid,
        handoff_chain_checks_passed=chain_valid,
        operations_checks_passed=operations_valid,
        safety_checks_passed=source_safety_valid,
        all_checks_passed=all_checks_passed,
        paper_preflight_authorized=all_checks_passed,
        paper_execution_authorized=False,
        automatic_execution_authorized=False,
        execution_blocked=True,
        broker_api_called=False,
        broker_order_created=False,
        live_order_created=False,
        live_execution_authorized=False,
        preflight_policy=policy,
        preflight_items=items,
        reasons=reasons,
        warnings=[
            *policy_errors,
            *source_errors,
            *date_errors,
            *input_errors,
            *chain_errors,
            "V12.6은 Paper 실행 직전 점검만 수행합니다.",
            "실제 Broker API, 실제 주문 및 Live Execution은 모두 차단됩니다.",
        ],
        next_actions=next_actions,
    )


def verify_saved_preflight_payload(
    payload: dict[str, Any],
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if payload.get("version") != "V12.6":
        errors.append(
            "저장된 Preflight Version이 V12.6이 아닙니다."
        )
    if payload.get("preflight_status") not in VALID_PREFLIGHT_STATUSES:
        errors.append(
            "저장된 Preflight Status가 올바르지 않습니다."
        )
    if payload.get("paper_execution_authorized") is not False:
        errors.append(
            "저장된 Preflight가 Paper Execution을 허용합니다."
        )
    if payload.get("execution_blocked") is not True:
        errors.append(
            "저장된 Preflight의 Execution이 차단되지 않았습니다."
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


def save_paper_operations_preflight(
    result: PaperOperationsPreflightResult,
    output_directory: Path | None = None,
) -> PaperOperationsPreflightResult:
    if not isinstance(
        result,
        PaperOperationsPreflightResult,
    ):
        raise TypeError(
            "V12.6 Preflight Result 형식이 아닙니다."
        )
    directory = (
        output_directory
        if output_directory is not None
        else PAPER_OPERATIONS_PREFLIGHT_OUTPUT_DIRECTORY
    )
    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S_%f"
    )
    report_path = directory / (
        f"paper_operations_preflight_{timestamp}.json"
    )
    latest_path = directory / (
        "paper_operations_preflight_latest.json"
    )
    payload = result.to_dict()
    write_json_file(report_path, payload)
    write_json_file(latest_path, payload)
    result.report_path = str(report_path)
    result.latest_path = str(latest_path)
    return result


def load_latest_paper_operations_preflight(
    output_directory: Path | None = None,
) -> dict[str, Any]:
    directory = (
        output_directory
        if output_directory is not None
        else PAPER_OPERATIONS_PREFLIGHT_OUTPUT_DIRECTORY
    )
    return read_json_file(
        directory / "paper_operations_preflight_latest.json"
    )


def print_paper_operations_preflight(
    result: PaperOperationsPreflightResult,
) -> None:
    line = "=" * 100
    print()
    print(line)
    print("V12.6 PAPER OPERATIONS PREFLIGHT CHECK")
    print(line)
    print(f"Preflight status       : {result.preflight_status}")
    print(f"Trading date           : {result.trading_date}")
    print(f"Market status          : {result.market_status}")
    print(f"Operator               : {result.operator}")
    print(f"Symbols                : {', '.join(result.symbols)}")
    print(f"Passed items           : {result.passed_item_count}/{result.total_item_count}")
    print(line)
    print(
        "주의: Preflight 통과는 실제 주문 실행 권한이 아닙니다."
    )

