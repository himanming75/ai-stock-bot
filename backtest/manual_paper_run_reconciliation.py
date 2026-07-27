import hashlib
import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from backtest.manual_paper_run_audit_trail import (
    ManualPaperRunAuditTrailResult,
    verify_audit_chain,
)
from backtest.manual_paper_run_orchestrator import (
    ManualPaperRunOrchestratorResult,
    STAGE_ORDER,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent

MANUAL_PAPER_RUN_RECONCILIATION_OUTPUT_DIRECTORY = (
    PROJECT_ROOT
    / "output"
    / "trading_engine"
    / "manual_paper_run_reconciliation"
)

VALID_RECONCILIATION_STATUSES = {
    "RECONCILED",
    "MISMATCH",
    "FAILED",
}

VALID_SEVERITIES = {
    "INFO",
    "ERROR",
}


@dataclass(frozen=True)
class ManualPaperRunReconciliationPolicy:
    """
    V11.8 Manual Paper Run Reconciliation 정책입니다.

    V11.6 실행 결과와 V11.7 감사 기록을 읽어서 대조할 뿐,
    어떤 Paper 또는 Broker 실행도 새로 시작하지 않습니다.
    """

    required_orchestrator_version: str = "V11.6"
    required_audit_version: str = "V11.7"
    required_audit_status: str = "RECORDED"
    required_audit_entry_count: int = 8
    maximum_history_records: int = 100

    require_identity_match: bool = True
    require_actor_match: bool = True
    require_status_match: bool = True
    require_stage_match: bool = True
    require_hash_chain_validation: bool = True
    require_source_safety: bool = True
    reject_duplicate_pair: bool = True

    automatic_execution_disabled: bool = True
    paper_only: bool = True
    live_execution_disabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ManualPaperRunReconciliationItem:
    item_number: int
    category: str
    check_name: str
    stage_name: str | None

    expected_value: Any
    actual_value: Any
    matched: bool
    severity: str
    details: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ManualPaperRunReconciliationResult:
    version: str
    created_at: str
    reconciliation_id: str
    reconciliation_pair_id: str | None

    reconciliation_status: str
    reconciliation_status_label: str

    source_orchestration_id: str | None
    audit_trail_id: str | None
    manual_actor: str | None

    total_item_count: int
    matched_item_count: int
    mismatched_item_count: int

    policy_checks_passed: bool
    input_checks_passed: bool
    identity_checks_passed: bool
    actor_checks_passed: bool
    status_checks_passed: bool
    stage_checks_passed: bool
    hash_chain_checks_passed: bool
    duplicate_checks_passed: bool
    safety_checks_passed: bool
    all_checks_passed: bool

    automatic_execution_authorized: bool
    execution_blocked: bool
    broker_api_called: bool
    broker_order_created: bool
    live_order_created: bool
    live_execution_authorized: bool

    reconciliation_policy: (
        ManualPaperRunReconciliationPolicy
    )
    reconciliation_items: tuple[
        ManualPaperRunReconciliationItem,
        ...,
    ]
    reconciliation_history: tuple[str, ...]

    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)

    report_path: str | None = None
    latest_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["reconciliation_policy"] = (
            self.reconciliation_policy.to_dict()
        )
        payload["reconciliation_items"] = [
            item.to_dict()
            for item in self.reconciliation_items
        ]
        payload["reconciliation_history"] = list(
            self.reconciliation_history
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


def validate_reconciliation_policy(
    policy: ManualPaperRunReconciliationPolicy,
) -> tuple[bool, list[str]]:
    if not isinstance(
        policy,
        ManualPaperRunReconciliationPolicy,
    ):
        return (
            False,
            ["Reconciliation Policy 형식이 올바르지 않습니다."],
        )

    errors: list[str] = []
    if policy.required_orchestrator_version != "V11.6":
        errors.append(
            "Required Orchestrator Version은 V11.6이어야 합니다."
        )
    if policy.required_audit_version != "V11.7":
        errors.append(
            "Required Audit Version은 V11.7이어야 합니다."
        )
    if policy.required_audit_status != "RECORDED":
        errors.append(
            "Required Audit Status는 RECORDED여야 합니다."
        )
    if policy.required_audit_entry_count != 8:
        errors.append(
            "Required Audit Entry Count는 8이어야 합니다."
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
        "require_identity_match": (
            policy.require_identity_match
        ),
        "require_actor_match": (
            policy.require_actor_match
        ),
        "require_status_match": (
            policy.require_status_match
        ),
        "require_stage_match": (
            policy.require_stage_match
        ),
        "require_hash_chain_validation": (
            policy.require_hash_chain_validation
        ),
        "require_source_safety": (
            policy.require_source_safety
        ),
        "reject_duplicate_pair": (
            policy.reject_duplicate_pair
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
                f"{name}는 V11.8에서 True여야 합니다."
            )

    return (not errors, errors)


def validate_reconciliation_inputs(
    orchestrator_result: Any,
    audit_result: Any,
) -> tuple[bool, bool, list[str]]:
    errors: list[str] = []

    orchestrator_valid = isinstance(
        orchestrator_result,
        ManualPaperRunOrchestratorResult,
    )
    if not orchestrator_valid:
        errors.append(
            "Orchestrator Result는 V11.6 형식이어야 합니다."
        )

    audit_valid = isinstance(
        audit_result,
        ManualPaperRunAuditTrailResult,
    )
    if not audit_valid:
        errors.append(
            "Audit Result는 V11.7 형식이어야 합니다."
        )

    if orchestrator_valid:
        if orchestrator_result.version != "V11.6":
            orchestrator_valid = False
            errors.append(
                "Orchestrator Version이 V11.6이 아닙니다."
            )
        if (
            not isinstance(
                orchestrator_result.orchestration_id,
                str,
            )
            or not orchestrator_result
            .orchestration_id.strip()
        ):
            orchestrator_valid = False
            errors.append(
                "Orchestration ID가 비어 있습니다."
            )
        if len(orchestrator_result.stage_records) != 6:
            orchestrator_valid = False
            errors.append(
                "Orchestrator Stage Record 수가 6이 아닙니다."
            )

    if audit_valid:
        if audit_result.version != "V11.7":
            audit_valid = False
            errors.append(
                "Audit Version이 V11.7이 아닙니다."
            )
        if audit_result.audit_status != "RECORDED":
            audit_valid = False
            errors.append(
                "Audit Status가 RECORDED가 아닙니다."
            )
        if not audit_result.all_checks_passed:
            audit_valid = False
            errors.append(
                "Audit All Checks가 실패했습니다."
            )
        if len(audit_result.audit_entries) != 8:
            audit_valid = False
            errors.append(
                "Audit Entry 수가 8이 아닙니다."
            )

    return (
        orchestrator_valid,
        audit_valid,
        errors,
    )


def validate_source_safety(
    orchestrator_result: Any,
    audit_result: Any,
) -> tuple[bool, list[str]]:
    errors: list[str] = []

    if not isinstance(
        orchestrator_result,
        ManualPaperRunOrchestratorResult,
    ) or not isinstance(
        audit_result,
        ManualPaperRunAuditTrailResult,
    ):
        return (
            False,
            ["Safety 검사에 필요한 Result 형식이 없습니다."],
        )

    orchestrator_safe = bool(
        orchestrator_result.execution_blocked is True
        and orchestrator_result
        .automatic_execution_authorized is False
        and orchestrator_result.broker_api_called is False
        and orchestrator_result.broker_order_created is False
        and orchestrator_result.live_order_created is False
        and orchestrator_result
        .live_execution_authorized is False
        and all(
            record.execution_blocked is True
            and record.broker_api_called is False
            and record.broker_order_created is False
            and record.live_order_created is False
            and record.live_execution_authorized is False
            for record in orchestrator_result.stage_records
        )
    )
    if not orchestrator_safe:
        errors.append(
            "V11.6 Orchestrator Result에 안전 오류가 있습니다."
        )

    audit_safe = bool(
        audit_result.execution_blocked is True
        and audit_result
        .automatic_execution_authorized is False
        and audit_result.broker_api_called is False
        and audit_result.broker_order_created is False
        and audit_result.live_order_created is False
        and audit_result.live_execution_authorized is False
        and all(
            entry.execution_blocked is True
            and entry.broker_api_called is False
            and entry.broker_order_created is False
            and entry.live_order_created is False
            and entry.live_execution_authorized is False
            for entry in audit_result.audit_entries
        )
    )
    if not audit_safe:
        errors.append(
            "V11.7 Audit Result에 안전 오류가 있습니다."
        )

    return (
        orchestrator_safe and audit_safe,
        errors,
    )


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
    for pair_id in existing_history:
        if (
            not isinstance(pair_id, str)
            or not pair_id.strip()
        ):
            raise ValueError(
                "History의 Pair ID가 올바르지 않습니다."
            )
        cleaned.append(pair_id.strip())

    return tuple(cleaned[-maximum_records:])


def create_reconciliation_pair_id(
    orchestration_id: str,
    audit_trail_id: str,
) -> str:
    raw_pair = (
        f"{orchestration_id}:{audit_trail_id}"
    )
    return hashlib.sha256(
        raw_pair.encode("utf-8")
    ).hexdigest()


def add_reconciliation_item(
    items: list[
        ManualPaperRunReconciliationItem
    ],
    *,
    category: str,
    check_name: str,
    expected_value: Any,
    actual_value: Any,
    stage_name: str | None = None,
    details: str = "",
) -> None:
    matched = expected_value == actual_value
    items.append(
        ManualPaperRunReconciliationItem(
            item_number=len(items) + 1,
            category=category,
            check_name=check_name,
            stage_name=stage_name,
            expected_value=expected_value,
            actual_value=actual_value,
            matched=matched,
            severity=(
                "INFO"
                if matched
                else "ERROR"
            ),
            details=(
                details
                if details
                else (
                    "값이 일치합니다."
                    if matched
                    else "값이 일치하지 않습니다."
                )
            ),
        )
    )


def build_reconciliation_items(
    orchestrator_result: (
        ManualPaperRunOrchestratorResult
    ),
    audit_result: ManualPaperRunAuditTrailResult,
) -> tuple[
    ManualPaperRunReconciliationItem,
    ...,
]:
    items: list[
        ManualPaperRunReconciliationItem
    ] = []

    add_reconciliation_item(
        items,
        category="IDENTITY",
        check_name="Orchestration ID",
        expected_value=(
            orchestrator_result.orchestration_id
        ),
        actual_value=(
            audit_result.source_orchestration_id
        ),
    )
    add_reconciliation_item(
        items,
        category="IDENTITY",
        check_name="Source Version",
        expected_value=orchestrator_result.version,
        actual_value=audit_result.source_version,
    )
    add_reconciliation_item(
        items,
        category="ACTOR",
        check_name="Manual Actor",
        expected_value=orchestrator_result.manual_actor,
        actual_value=audit_result.manual_actor,
    )
    add_reconciliation_item(
        items,
        category="STATUS",
        check_name="Orchestrator Status",
        expected_value=(
            orchestrator_result.orchestrator_status
        ),
        actual_value=audit_result.source_status,
    )
    add_reconciliation_item(
        items,
        category="STATUS",
        check_name="Source All Checks",
        expected_value=(
            orchestrator_result.all_checks_passed
        ),
        actual_value=(
            audit_result.audit_entries[0]
            .source_all_checks_passed
        ),
    )
    add_reconciliation_item(
        items,
        category="STATUS",
        check_name="Failed Stage Name",
        expected_value=(
            orchestrator_result.failed_stage_name
        ),
        actual_value=(
            audit_result.audit_entries[-1]
            .failed_stage_name
        ),
    )

    stage_entries = audit_result.audit_entries[1:-1]
    for stage_record, audit_entry in zip(
        orchestrator_result.stage_records,
        stage_entries,
        strict=True,
    ):
        stage_name = stage_record.stage_name
        add_reconciliation_item(
            items,
            category="STAGE",
            check_name="Stage Name",
            stage_name=stage_name,
            expected_value=stage_record.stage_name,
            actual_value=audit_entry.stage_name,
        )
        add_reconciliation_item(
            items,
            category="STAGE",
            check_name="Stage Order",
            stage_name=stage_name,
            expected_value=stage_record.stage_order,
            actual_value=audit_entry.stage_order,
        )
        add_reconciliation_item(
            items,
            category="STAGE",
            check_name="Stage Called",
            stage_name=stage_name,
            expected_value=stage_record.called,
            actual_value=audit_entry.stage_called,
        )
        add_reconciliation_item(
            items,
            category="STAGE",
            check_name="Stage Completed",
            stage_name=stage_name,
            expected_value=stage_record.completed,
            actual_value=audit_entry.stage_completed,
        )
        add_reconciliation_item(
            items,
            category="STAGE",
            check_name="Stage Status",
            stage_name=stage_name,
            expected_value=stage_record.result_status,
            actual_value=audit_entry.stage_status,
        )
        add_reconciliation_item(
            items,
            category="STAGE",
            check_name="Stage All Checks",
            stage_name=stage_name,
            expected_value=(
                stage_record.all_checks_passed
            ),
            actual_value=(
                audit_entry
                .stage_all_checks_passed
            ),
        )
        add_reconciliation_item(
            items,
            category="STAGE",
            check_name="Stage Error Message",
            stage_name=stage_name,
            expected_value=stage_record.error_message,
            actual_value=(
                audit_entry.stage_error_message
            ),
        )

    add_reconciliation_item(
        items,
        category="SEQUENCE",
        check_name="Stage Sequence",
        expected_value=list(STAGE_ORDER),
        actual_value=[
            entry.stage_name
            for entry in stage_entries
        ],
    )
    add_reconciliation_item(
        items,
        category="SEQUENCE",
        check_name="Audit Entry Count",
        expected_value=8,
        actual_value=len(
            audit_result.audit_entries
        ),
    )

    return tuple(items)


def reconcile_manual_paper_run(
    orchestrator_result: Any,
    audit_result: Any,
    existing_history: (
        tuple[str, ...]
        | list[str]
        | None
    ) = None,
    reconciliation_policy: (
        ManualPaperRunReconciliationPolicy
        | None
    ) = None,
) -> ManualPaperRunReconciliationResult:
    policy = (
        reconciliation_policy
        if reconciliation_policy is not None
        else ManualPaperRunReconciliationPolicy()
    )
    policy_valid, policy_errors = (
        validate_reconciliation_policy(policy)
    )
    (
        orchestrator_valid,
        audit_valid,
        input_errors,
    ) = validate_reconciliation_inputs(
        orchestrator_result,
        audit_result,
    )
    input_valid = bool(
        orchestrator_valid and audit_valid
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

    if input_valid:
        safety_valid, safety_errors = (
            validate_source_safety(
                orchestrator_result,
                audit_result,
            )
        )
        hash_valid, hash_errors = (
            verify_audit_chain(
                audit_result.audit_entries
            )
        )
        pair_id = create_reconciliation_pair_id(
            orchestrator_result.orchestration_id,
            audit_result.audit_trail_id,
        )
        items = build_reconciliation_items(
            orchestrator_result,
            audit_result,
        )
    else:
        safety_valid = False
        safety_errors = []
        hash_valid = False
        hash_errors = []
        pair_id = None
        items = ()

    duplicate_valid = bool(
        pair_id is not None
        and pair_id not in history
    )
    duplicate_errors: list[str] = []
    if not duplicate_valid:
        duplicate_errors.append(
            "동일한 Orchestrator/Audit Pair가 이미 처리되었습니다."
        )

    identity_valid = bool(
        items
        and all(
            item.matched
            for item in items
            if item.category == "IDENTITY"
        )
    )
    actor_valid = bool(
        items
        and all(
            item.matched
            for item in items
            if item.category == "ACTOR"
        )
    )
    status_valid = bool(
        items
        and all(
            item.matched
            for item in items
            if item.category == "STATUS"
        )
    )
    stage_valid = bool(
        items
        and all(
            item.matched
            for item in items
            if item.category
            in {"STAGE", "SEQUENCE"}
        )
    )

    matched_count = sum(
        item.matched
        for item in items
    )
    mismatched_count = len(items) - matched_count

    preflight_valid = bool(
        policy_valid
        and input_valid
        and history_valid
        and safety_valid
        and hash_valid
        and duplicate_valid
    )
    all_checks_passed = bool(
        preflight_valid
        and identity_valid
        and actor_valid
        and status_valid
        and stage_valid
        and mismatched_count == 0
    )

    if all_checks_passed:
        reconciliation_status = "RECONCILED"
        reconciliation_status_label = (
            "Manual Paper Run 대조 완료"
        )
        updated_history = (
            *history,
            pair_id,
        )[-policy.maximum_history_records:]
        reasons = [
            "V11.6 실행 결과와 V11.7 감사 기록이 모두 일치합니다.",
            "ID, 실행자, 상태, 6개 Stage 및 Hash Chain이 검증되었습니다.",
        ]
        next_actions = [
            "Reconciliation Report를 보관합니다.",
            "다음 Paper Run에는 새로운 실행 및 Audit Pair를 사용합니다.",
        ]
    elif preflight_valid:
        reconciliation_status = "MISMATCH"
        reconciliation_status_label = (
            "Manual Paper Run 대조 불일치"
        )
        updated_history = history
        reasons = [
            f"{mismatched_count}개의 Reconciliation 항목이 일치하지 않습니다."
        ]
        next_actions = [
            "ERROR 항목의 Expected와 Actual 값을 확인합니다.",
            "기록을 직접 수정하지 말고 원본 실행부터 다시 생성합니다.",
        ]
    else:
        reconciliation_status = "FAILED"
        reconciliation_status_label = (
            "Manual Paper Run 대조 사전검사 실패"
        )
        updated_history = history
        reasons = [
            "Policy, 입력, 중복, Hash 또는 Safety 검사에 실패했습니다."
        ]
        next_actions = [
            "Warnings에서 사전검사 실패 원인을 확인합니다.",
            "안전한 V11.6 및 V11.7 원본 결과를 사용합니다.",
        ]

    warnings = [
        *policy_errors,
        *input_errors,
        *history_errors,
        *safety_errors,
        *hash_errors,
        *duplicate_errors,
    ]
    warnings.extend(
        (
            (
                f"{item.category}/{item.check_name}"
                f"[{item.stage_name}]: "
                f"Expected={item.expected_value}, "
                f"Actual={item.actual_value}"
            )
            for item in items
            if not item.matched
        )
    )
    warnings.extend(
        [
            "V11.8은 결과 대조만 수행하며 Paper Pipeline을 실행하지 않습니다.",
            "Broker API, 실제 주문 및 Live Execution은 허용하지 않습니다.",
        ]
    )

    result = ManualPaperRunReconciliationResult(
        version="V11.8",
        created_at=datetime.now().isoformat(),
        reconciliation_id=str(uuid.uuid4()),
        reconciliation_pair_id=pair_id,
        reconciliation_status=(
            reconciliation_status
        ),
        reconciliation_status_label=(
            reconciliation_status_label
        ),
        source_orchestration_id=getattr(
            orchestrator_result,
            "orchestration_id",
            None,
        ),
        audit_trail_id=getattr(
            audit_result,
            "audit_trail_id",
            None,
        ),
        manual_actor=getattr(
            orchestrator_result,
            "manual_actor",
            None,
        ),
        total_item_count=len(items),
        matched_item_count=matched_count,
        mismatched_item_count=mismatched_count,
        policy_checks_passed=policy_valid,
        input_checks_passed=input_valid,
        identity_checks_passed=identity_valid,
        actor_checks_passed=actor_valid,
        status_checks_passed=status_valid,
        stage_checks_passed=stage_valid,
        hash_chain_checks_passed=hash_valid,
        duplicate_checks_passed=duplicate_valid,
        safety_checks_passed=safety_valid,
        all_checks_passed=all_checks_passed,
        automatic_execution_authorized=False,
        execution_blocked=True,
        broker_api_called=False,
        broker_order_created=False,
        live_order_created=False,
        live_execution_authorized=False,
        reconciliation_policy=policy,
        reconciliation_items=items,
        reconciliation_history=tuple(
            updated_history
        ),
        reasons=reasons,
        warnings=warnings,
        next_actions=next_actions,
    )

    print_manual_paper_run_reconciliation(
        result
    )
    return result


def save_manual_paper_run_reconciliation(
    result: ManualPaperRunReconciliationResult,
) -> tuple[Path, Path]:
    if not isinstance(
        result,
        ManualPaperRunReconciliationResult,
    ):
        raise TypeError(
            "V11.8 Reconciliation Result 형식이 아닙니다."
        )
    if not result.all_checks_passed:
        raise ValueError(
            "검사에 실패한 Reconciliation은 저장할 수 없습니다."
        )

    directory = (
        MANUAL_PAPER_RUN_RECONCILIATION_OUTPUT_DIRECTORY
    )
    directory.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S_%f"
    )
    report_path = directory / (
        f"manual_paper_run_reconciliation_{timestamp}.json"
    )
    latest_path = directory / (
        "manual_paper_run_reconciliation_latest.json"
    )

    result.report_path = str(report_path)
    result.latest_path = str(latest_path)
    payload = result.to_dict()
    write_json_file(report_path, payload)
    write_json_file(latest_path, payload)
    return (report_path, latest_path)


def load_latest_manual_paper_run_reconciliation() -> (
    dict[str, Any]
):
    path = (
        MANUAL_PAPER_RUN_RECONCILIATION_OUTPUT_DIRECTORY
        / "manual_paper_run_reconciliation_latest.json"
    )
    return read_json_file(path)


def print_manual_paper_run_reconciliation(
    result: ManualPaperRunReconciliationResult,
) -> None:
    line_length = 120
    print()
    print("=" * line_length)
    print("V11.8 MANUAL PAPER RUN RECONCILIATION")
    print("=" * line_length)
    print(
        f"Reconciliation status         : "
        f"{result.reconciliation_status}"
    )
    print(
        f"Reconciliation status label   : "
        f"{result.reconciliation_status_label}"
    )
    print(
        f"Orchestration ID              : "
        f"{result.source_orchestration_id}"
    )
    print(
        f"Audit Trail ID                : "
        f"{result.audit_trail_id}"
    )
    print(
        f"Reconciliation Pair ID        : "
        f"{result.reconciliation_pair_id}"
    )
    print(
        f"Matched items                 : "
        f"{result.matched_item_count}/{result.total_item_count}"
    )
    print(
        f"Mismatched items              : "
        f"{result.mismatched_item_count}"
    )

    print()
    print("MISMATCHES")
    print("-" * line_length)
    mismatches = [
        item
        for item in result.reconciliation_items
        if not item.matched
    ]
    if not mismatches:
        print("None")
    else:
        for item in mismatches:
            print(
                f"{item.item_number}. "
                f"{item.category}/{item.check_name} "
                f"Stage={item.stage_name} | "
                f"Expected={item.expected_value} | "
                f"Actual={item.actual_value}"
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
            "Identity checks passed",
            result.identity_checks_passed,
        ),
        (
            "Actor checks passed",
            result.actor_checks_passed,
        ),
        (
            "Status checks passed",
            result.status_checks_passed,
        ),
        (
            "Stage checks passed",
            result.stage_checks_passed,
        ),
        (
            "Hash chain checks passed",
            result.hash_chain_checks_passed,
        ),
        (
            "Duplicate checks passed",
            result.duplicate_checks_passed,
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
        "주의: V11.8은 실행 결과 대조만 수행하며 "
        "Broker 주문을 수행하지 않습니다."
    )
