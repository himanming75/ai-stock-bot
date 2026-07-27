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
)
from backtest.manual_paper_run_reconciliation import (
    ManualPaperRunReconciliationResult,
)
from backtest.manual_paper_run_release_gate import (
    ManualPaperRunReleaseGateResult,
    verify_release_seal,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent

PAPER_TRADING_OPERATIONS_CONSOLE_OUTPUT_DIRECTORY = (
    PROJECT_ROOT
    / "output"
    / "trading_engine"
    / "paper_trading_operations_console"
)

VALID_CONSOLE_STATUSES = {
    "READY",
    "REVIEW",
    "BLOCKED",
    "FAILED",
}

VALID_CARD_STATUSES = {
    "PASS",
    "WARNING",
    "BLOCKED",
    "FAILED",
}


@dataclass(frozen=True)
class PaperTradingOperationsConsolePolicy:
    """
    V12.0 Paper Trading Operations Console 정책입니다.

    Console은 V11.6~V11.9 결과를 읽어서 상태를 보여줄 뿐,
    Pipeline, Broker 또는 Live 주문을 실행하지 않습니다.
    """

    required_orchestrator_version: str = "V11.6"
    required_audit_version: str = "V11.7"
    required_reconciliation_version: str = "V11.8"
    required_release_version: str = "V11.9"

    required_orchestrator_status: str = "COMPLETED"
    required_audit_status: str = "RECORDED"
    required_reconciliation_status: str = (
        "RECONCILED"
    )
    required_release_status: str = (
        "PAPER_RELEASED"
    )

    require_identity_chain: bool = True
    require_same_manual_actor: bool = True
    require_audit_hash_validation: bool = True
    require_release_seal_validation: bool = True
    require_source_safety: bool = True

    read_only_console: bool = True
    automatic_execution_disabled: bool = True
    paper_only: bool = True
    live_execution_disabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PaperTradingOperationsConsoleCard:
    card_order: int
    card_name: str
    card_status: str
    card_status_label: str

    primary_value: str
    secondary_value: str | None

    checks_passed: int
    checks_total: int
    all_checks_passed: bool

    details: tuple[str, ...] = field(
        default_factory=tuple
    )
    warnings: tuple[str, ...] = field(
        default_factory=tuple
    )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["details"] = list(self.details)
        payload["warnings"] = list(self.warnings)
        return payload


@dataclass
class PaperTradingOperationsConsoleResult:
    version: str
    created_at: str
    console_id: str

    console_status: str
    console_status_label: str
    operational_summary: str

    manual_actor: str | None
    orchestration_id: str | None
    audit_trail_id: str | None
    reconciliation_id: str | None
    release_gate_id: str | None

    total_card_count: int
    passed_card_count: int
    warning_card_count: int
    blocked_card_count: int
    failed_card_count: int

    completed_stage_count: int
    total_stage_count: int
    audit_entry_count: int
    reconciliation_item_count: int
    reconciliation_mismatch_count: int
    paper_run_locked: bool

    policy_checks_passed: bool
    input_checks_passed: bool
    version_checks_passed: bool
    status_checks_passed: bool
    identity_checks_passed: bool
    actor_checks_passed: bool
    hash_chain_checks_passed: bool
    seal_checks_passed: bool
    safety_checks_passed: bool
    all_checks_passed: bool

    read_only: bool
    automatic_execution_authorized: bool
    execution_blocked: bool
    broker_api_called: bool
    broker_order_created: bool
    live_order_created: bool
    live_execution_authorized: bool

    console_policy: (
        PaperTradingOperationsConsolePolicy
    )
    console_cards: tuple[
        PaperTradingOperationsConsoleCard,
        ...,
    ]

    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)

    report_path: str | None = None
    latest_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["console_policy"] = (
            self.console_policy.to_dict()
        )
        payload["console_cards"] = [
            card.to_dict()
            for card in self.console_cards
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


def validate_console_policy(
    policy: PaperTradingOperationsConsolePolicy,
) -> tuple[bool, list[str]]:
    if not isinstance(
        policy,
        PaperTradingOperationsConsolePolicy,
    ):
        return (
            False,
            ["Operations Console Policy 형식이 올바르지 않습니다."],
        )

    errors: list[str] = []
    expected_values = {
        "required_orchestrator_version": (
            policy.required_orchestrator_version,
            "V11.6",
        ),
        "required_audit_version": (
            policy.required_audit_version,
            "V11.7",
        ),
        "required_reconciliation_version": (
            policy.required_reconciliation_version,
            "V11.8",
        ),
        "required_release_version": (
            policy.required_release_version,
            "V11.9",
        ),
        "required_orchestrator_status": (
            policy.required_orchestrator_status,
            "COMPLETED",
        ),
        "required_audit_status": (
            policy.required_audit_status,
            "RECORDED",
        ),
        "required_reconciliation_status": (
            policy.required_reconciliation_status,
            "RECONCILED",
        ),
        "required_release_status": (
            policy.required_release_status,
            "PAPER_RELEASED",
        ),
    }
    for name, (actual, expected) in (
        expected_values.items()
    ):
        if actual != expected:
            errors.append(
                f"{name}는 {expected}이어야 합니다."
            )

    required_true_values = {
        "require_identity_chain": (
            policy.require_identity_chain
        ),
        "require_same_manual_actor": (
            policy.require_same_manual_actor
        ),
        "require_audit_hash_validation": (
            policy.require_audit_hash_validation
        ),
        "require_release_seal_validation": (
            policy.require_release_seal_validation
        ),
        "require_source_safety": (
            policy.require_source_safety
        ),
        "read_only_console": (
            policy.read_only_console
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
                f"{name}는 V12.0에서 True여야 합니다."
            )

    return (not errors, errors)


def validate_console_inputs(
    orchestrator_result: Any,
    audit_result: Any,
    reconciliation_result: Any,
    release_result: Any,
) -> tuple[bool, list[str]]:
    type_checks = (
        (
            orchestrator_result,
            ManualPaperRunOrchestratorResult,
            "Orchestrator Result는 V11.6 형식이어야 합니다.",
        ),
        (
            audit_result,
            ManualPaperRunAuditTrailResult,
            "Audit Result는 V11.7 형식이어야 합니다.",
        ),
        (
            reconciliation_result,
            ManualPaperRunReconciliationResult,
            "Reconciliation Result는 V11.8 형식이어야 합니다.",
        ),
        (
            release_result,
            ManualPaperRunReleaseGateResult,
            "Release Result는 V11.9 형식이어야 합니다.",
        ),
    )
    errors = [
        message
        for value, expected_type, message
        in type_checks
        if not isinstance(value, expected_type)
    ]
    return (not errors, errors)


def validate_version_chain(
    orchestrator_result: (
        ManualPaperRunOrchestratorResult
    ),
    audit_result: ManualPaperRunAuditTrailResult,
    reconciliation_result: (
        ManualPaperRunReconciliationResult
    ),
    release_result: (
        ManualPaperRunReleaseGateResult
    ),
) -> tuple[bool, list[str]]:
    checks = (
        (
            orchestrator_result.version == "V11.6",
            "Orchestrator Version이 V11.6이 아닙니다.",
        ),
        (
            audit_result.version == "V11.7",
            "Audit Version이 V11.7이 아닙니다.",
        ),
        (
            reconciliation_result.version == "V11.8",
            "Reconciliation Version이 V11.8이 아닙니다.",
        ),
        (
            release_result.version == "V11.9",
            "Release Version이 V11.9가 아닙니다.",
        ),
    )
    errors = [
        message
        for passed, message in checks
        if not passed
    ]
    return (not errors, errors)


def validate_status_chain(
    orchestrator_result: (
        ManualPaperRunOrchestratorResult
    ),
    audit_result: ManualPaperRunAuditTrailResult,
    reconciliation_result: (
        ManualPaperRunReconciliationResult
    ),
    release_result: (
        ManualPaperRunReleaseGateResult
    ),
) -> tuple[bool, list[str]]:
    checks = (
        (
            orchestrator_result.orchestrator_status
            == "COMPLETED"
            and orchestrator_result
            .all_checks_passed,
            "Orchestrator가 완료 상태가 아닙니다.",
        ),
        (
            audit_result.audit_status == "RECORDED"
            and audit_result.all_checks_passed,
            "Audit가 기록 완료 상태가 아닙니다.",
        ),
        (
            reconciliation_result
            .reconciliation_status
            == "RECONCILED"
            and reconciliation_result
            .all_checks_passed
            and reconciliation_result
            .mismatched_item_count
            == 0,
            "Reconciliation이 완전 일치 상태가 아닙니다.",
        ),
        (
            release_result.release_status
            == "PAPER_RELEASED"
            and release_result.all_checks_passed
            and release_result.paper_run_locked,
            "Release Gate가 잠금 완료 상태가 아닙니다.",
        ),
    )
    errors = [
        message
        for passed, message in checks
        if not passed
    ]
    return (not errors, errors)


def validate_identity_chain(
    orchestrator_result: (
        ManualPaperRunOrchestratorResult
    ),
    audit_result: ManualPaperRunAuditTrailResult,
    reconciliation_result: (
        ManualPaperRunReconciliationResult
    ),
    release_result: (
        ManualPaperRunReleaseGateResult
    ),
) -> tuple[bool, list[str]]:
    orchestration_id = (
        orchestrator_result.orchestration_id
    )
    audit_id = audit_result.audit_trail_id
    reconciliation_id = (
        reconciliation_result.reconciliation_id
    )

    checks = (
        (
            audit_result.source_orchestration_id
            == orchestration_id,
            "Audit Source Orchestration ID가 일치하지 않습니다.",
        ),
        (
            reconciliation_result
            .source_orchestration_id
            == orchestration_id,
            "Reconciliation Orchestration ID가 일치하지 않습니다.",
        ),
        (
            reconciliation_result.audit_trail_id
            == audit_id,
            "Reconciliation Audit Trail ID가 일치하지 않습니다.",
        ),
        (
            release_result.source_orchestration_id
            == orchestration_id,
            "Release Orchestration ID가 일치하지 않습니다.",
        ),
        (
            release_result.source_audit_trail_id
            == audit_id,
            "Release Audit Trail ID가 일치하지 않습니다.",
        ),
        (
            release_result
            .source_reconciliation_id
            == reconciliation_id,
            "Release Reconciliation ID가 일치하지 않습니다.",
        ),
        (
            release_result.release_seal
            is not None
            and release_result.release_seal
            .orchestration_id
            == orchestration_id
            and release_result.release_seal
            .audit_trail_id
            == audit_id
            and release_result.release_seal
            .reconciliation_id
            == reconciliation_id,
            "Release Seal ID Chain이 일치하지 않습니다.",
        ),
    )
    errors = [
        message
        for passed, message in checks
        if not passed
    ]
    return (not errors, errors)


def validate_actor_chain(
    orchestrator_result: (
        ManualPaperRunOrchestratorResult
    ),
    audit_result: ManualPaperRunAuditTrailResult,
    reconciliation_result: (
        ManualPaperRunReconciliationResult
    ),
    release_result: (
        ManualPaperRunReleaseGateResult
    ),
) -> tuple[bool, list[str]]:
    actors = (
        orchestrator_result.manual_actor,
        audit_result.manual_actor,
        reconciliation_result.manual_actor,
        release_result.manual_actor,
    )
    valid = bool(
        actors[0]
        and all(
            actor == actors[0]
            for actor in actors
        )
    )
    return (
        valid,
        (
            []
            if valid
            else [
                "V11.6~V11.9 Manual Actor가 일치하지 않습니다."
            ]
        ),
    )


def validate_console_safety(
    orchestrator_result: (
        ManualPaperRunOrchestratorResult
    ),
    audit_result: ManualPaperRunAuditTrailResult,
    reconciliation_result: (
        ManualPaperRunReconciliationResult
    ),
    release_result: (
        ManualPaperRunReleaseGateResult
    ),
) -> tuple[bool, list[str]]:
    errors: list[str] = []

    for name, source in (
        ("V11.6", orchestrator_result),
        ("V11.7", audit_result),
        ("V11.8", reconciliation_result),
        ("V11.9", release_result),
    ):
        safe = bool(
            source.execution_blocked is True
            and source
            .automatic_execution_authorized is False
            and source.broker_api_called is False
            and source.broker_order_created is False
            and source.live_order_created is False
            and source.live_execution_authorized is False
        )
        if not safe:
            errors.append(
                f"{name} Source에 실거래 안전 오류가 있습니다."
            )

    return (not errors, errors)


def make_console_card(
    *,
    card_order: int,
    card_name: str,
    checks: tuple[
        tuple[bool, str],
        ...,
    ],
    primary_value: Any,
    secondary_value: Any = None,
) -> PaperTradingOperationsConsoleCard:
    checks_passed = sum(
        passed
        for passed, _ in checks
    )
    warnings = tuple(
        message
        for passed, message in checks
        if not passed
    )
    all_passed = checks_passed == len(checks)

    return PaperTradingOperationsConsoleCard(
        card_order=card_order,
        card_name=card_name,
        card_status=(
            "PASS"
            if all_passed
            else "BLOCKED"
        ),
        card_status_label=(
            "정상"
            if all_passed
            else "확인 필요"
        ),
        primary_value=str(primary_value),
        secondary_value=(
            str(secondary_value)
            if secondary_value is not None
            else None
        ),
        checks_passed=checks_passed,
        checks_total=len(checks),
        all_checks_passed=all_passed,
        details=tuple(
            message
            for passed, message in checks
            if passed
        ),
        warnings=warnings,
    )


def build_console_cards(
    orchestrator_result: (
        ManualPaperRunOrchestratorResult
    ),
    audit_result: ManualPaperRunAuditTrailResult,
    reconciliation_result: (
        ManualPaperRunReconciliationResult
    ),
    release_result: (
        ManualPaperRunReleaseGateResult
    ),
    hash_valid: bool,
    seal_valid: bool,
    identity_valid: bool,
    actor_valid: bool,
    safety_valid: bool,
) -> tuple[
    PaperTradingOperationsConsoleCard,
    ...,
]:
    return (
        make_console_card(
            card_order=1,
            card_name="ORCHESTRATION",
            primary_value=(
                orchestrator_result
                .orchestrator_status
            ),
            secondary_value=(
                f"{orchestrator_result.completed_stage_count}/"
                f"{orchestrator_result.total_stage_count} Stages"
            ),
            checks=(
                (
                    orchestrator_result
                    .orchestrator_status
                    == "COMPLETED",
                    "Orchestrator Status",
                ),
                (
                    orchestrator_result
                    .all_checks_passed,
                    "Orchestrator All Checks",
                ),
                (
                    orchestrator_result
                    .completed_stage_count
                    == orchestrator_result
                    .total_stage_count,
                    "All Stages Completed",
                ),
            ),
        ),
        make_console_card(
            card_order=2,
            card_name="AUDIT",
            primary_value=audit_result.audit_status,
            secondary_value=(
                f"{audit_result.total_entry_count} Entries"
            ),
            checks=(
                (
                    audit_result.audit_status
                    == "RECORDED",
                    "Audit Status",
                ),
                (
                    audit_result.all_checks_passed,
                    "Audit All Checks",
                ),
                (
                    hash_valid,
                    "Audit Hash Chain",
                ),
            ),
        ),
        make_console_card(
            card_order=3,
            card_name="RECONCILIATION",
            primary_value=(
                reconciliation_result
                .reconciliation_status
            ),
            secondary_value=(
                f"{reconciliation_result.matched_item_count}/"
                f"{reconciliation_result.total_item_count} Matched"
            ),
            checks=(
                (
                    reconciliation_result
                    .reconciliation_status
                    == "RECONCILED",
                    "Reconciliation Status",
                ),
                (
                    reconciliation_result
                    .mismatched_item_count
                    == 0,
                    "No Mismatches",
                ),
                (
                    reconciliation_result
                    .all_checks_passed,
                    "Reconciliation All Checks",
                ),
            ),
        ),
        make_console_card(
            card_order=4,
            card_name="RELEASE",
            primary_value=(
                release_result.release_status
            ),
            secondary_value=(
                "LOCKED"
                if release_result.paper_run_locked
                else "UNLOCKED"
            ),
            checks=(
                (
                    release_result.release_status
                    == "PAPER_RELEASED",
                    "Release Status",
                ),
                (
                    release_result.paper_run_locked,
                    "Paper Run Locked",
                ),
                (
                    release_result.all_checks_passed,
                    "Release All Checks",
                ),
                (
                    seal_valid,
                    "Release Seal",
                ),
            ),
        ),
        make_console_card(
            card_order=5,
            card_name="IDENTITY",
            primary_value=(
                "MATCHED"
                if identity_valid
                else "MISMATCH"
            ),
            secondary_value=(
                orchestrator_result.manual_actor
            ),
            checks=(
                (
                    identity_valid,
                    "Source ID Chain",
                ),
                (
                    actor_valid,
                    "Manual Actor Chain",
                ),
            ),
        ),
        make_console_card(
            card_order=6,
            card_name="EXECUTION_SAFETY",
            primary_value=(
                "SAFE"
                if safety_valid
                else "UNSAFE"
            ),
            secondary_value="PAPER ONLY",
            checks=(
                (
                    safety_valid,
                    "All Source Safety",
                ),
                (
                    not any(
                        (
                            orchestrator_result
                            .broker_api_called,
                            audit_result
                            .broker_api_called,
                            reconciliation_result
                            .broker_api_called,
                            release_result
                            .broker_api_called,
                        )
                    ),
                    "Broker API Not Called",
                ),
                (
                    not any(
                        (
                            orchestrator_result
                            .live_execution_authorized,
                            audit_result
                            .live_execution_authorized,
                            reconciliation_result
                            .live_execution_authorized,
                            release_result
                            .live_execution_authorized,
                        )
                    ),
                    "Live Execution Not Authorized",
                ),
            ),
        ),
    )


def build_paper_trading_operations_console(
    orchestrator_result: Any,
    audit_result: Any,
    reconciliation_result: Any,
    release_result: Any,
    console_policy: (
        PaperTradingOperationsConsolePolicy
        | None
    ) = None,
) -> PaperTradingOperationsConsoleResult:
    policy = (
        console_policy
        if console_policy is not None
        else PaperTradingOperationsConsolePolicy()
    )
    policy_valid, policy_errors = (
        validate_console_policy(policy)
    )
    input_valid, input_errors = (
        validate_console_inputs(
            orchestrator_result,
            audit_result,
            reconciliation_result,
            release_result,
        )
    )

    if input_valid:
        version_valid, version_errors = (
            validate_version_chain(
                orchestrator_result,
                audit_result,
                reconciliation_result,
                release_result,
            )
        )
        status_valid, status_errors = (
            validate_status_chain(
                orchestrator_result,
                audit_result,
                reconciliation_result,
                release_result,
            )
        )
        identity_valid, identity_errors = (
            validate_identity_chain(
                orchestrator_result,
                audit_result,
                reconciliation_result,
                release_result,
            )
        )
        actor_valid, actor_errors = (
            validate_actor_chain(
                orchestrator_result,
                audit_result,
                reconciliation_result,
                release_result,
            )
        )
        hash_valid, hash_errors = (
            verify_audit_chain(
                audit_result.audit_entries
            )
        )
        seal_valid, seal_errors = (
            verify_release_seal(
                release_result.release_seal
            )
        )
        safety_valid, safety_errors = (
            validate_console_safety(
                orchestrator_result,
                audit_result,
                reconciliation_result,
                release_result,
            )
        )
        cards = build_console_cards(
            orchestrator_result,
            audit_result,
            reconciliation_result,
            release_result,
            hash_valid,
            seal_valid,
            identity_valid,
            actor_valid,
            safety_valid,
        )
    else:
        version_valid = False
        version_errors = []
        status_valid = False
        status_errors = []
        identity_valid = False
        identity_errors = []
        actor_valid = False
        actor_errors = []
        hash_valid = False
        hash_errors = []
        seal_valid = False
        seal_errors = []
        safety_valid = False
        safety_errors = []
        cards = ()

    passed_card_count = sum(
        card.card_status == "PASS"
        for card in cards
    )
    warning_card_count = sum(
        card.card_status == "WARNING"
        for card in cards
    )
    blocked_card_count = sum(
        card.card_status == "BLOCKED"
        for card in cards
    )
    failed_card_count = sum(
        card.card_status == "FAILED"
        for card in cards
    )

    all_checks_passed = bool(
        policy_valid
        and input_valid
        and version_valid
        and status_valid
        and identity_valid
        and actor_valid
        and hash_valid
        and seal_valid
        and safety_valid
        and len(cards) == 6
        and passed_card_count == 6
    )

    if all_checks_passed:
        console_status = "READY"
        console_status_label = (
            "Paper Trading 운영 상태 정상"
        )
        operational_summary = (
            "V11.6~V11.9 기록이 모두 일치하며 "
            "Paper Run이 안전하게 잠겨 있습니다."
        )
        reasons = [
            "6개 Operations Card가 모두 PASS입니다.",
            "Audit Hash와 Release Seal이 검증되었습니다.",
            "Console은 읽기 전용이며 실거래 권한이 없습니다.",
        ]
        next_actions = [
            "현재 Paper Run 결과와 위험 지표를 검토합니다.",
            "다음 Paper Run은 새로운 수동 승인으로 시작합니다.",
        ]
    elif not input_valid or not policy_valid:
        console_status = "FAILED"
        console_status_label = (
            "Operations Console 입력 실패"
        )
        operational_summary = (
            "Console 구성에 필요한 Result 또는 Policy가 올바르지 않습니다."
        )
        reasons = [
            "입력 형식 또는 Console Policy 검사에 실패했습니다."
        ]
        next_actions = [
            "Warnings에서 입력 실패 원인을 확인합니다.",
        ]
    elif not safety_valid or not hash_valid or not seal_valid:
        console_status = "FAILED"
        console_status_label = (
            "Operations Console 안전 검사 실패"
        )
        operational_summary = (
            "Hash, Seal 또는 실거래 안전 조건에 문제가 있습니다."
        )
        reasons = [
            "변경되었거나 안전하지 않은 Source가 탐지되었습니다."
        ]
        next_actions = [
            "Source 파일을 수정하지 말고 안전한 실행부터 다시 생성합니다.",
        ]
    elif not identity_valid or not actor_valid:
        console_status = "BLOCKED"
        console_status_label = (
            "Operations Console ID 연결 차단"
        )
        operational_summary = (
            "Source ID 또는 Manual Actor가 일치하지 않습니다."
        )
        reasons = [
            "서로 다른 Paper Run 결과가 섞여 있습니다."
        ]
        next_actions = [
            "동일한 실행에서 생성된 V11.6~V11.9 결과를 사용합니다.",
        ]
    else:
        console_status = "REVIEW"
        console_status_label = (
            "Paper Trading 운영 상태 검토 필요"
        )
        operational_summary = (
            "한 개 이상의 Source 상태가 정상 완료 조건과 다릅니다."
        )
        reasons = [
            "Operations Card의 BLOCKED 항목을 확인해야 합니다."
        ]
        next_actions = [
            "완료되지 않은 단계부터 다시 실행하고 승인합니다.",
        ]

    warnings = [
        *policy_errors,
        *input_errors,
        *version_errors,
        *status_errors,
        *identity_errors,
        *actor_errors,
        *hash_errors,
        *seal_errors,
        *safety_errors,
    ]
    warnings.extend(
        warning
        for card in cards
        for warning in card.warnings
    )
    warnings.extend(
        [
            "V12.0 Console은 읽기 전용 상태 데이터만 생성합니다.",
            "Broker API, 실제 주문 및 Live Execution은 허용하지 않습니다.",
        ]
    )

    result = PaperTradingOperationsConsoleResult(
        version="V12.0",
        created_at=datetime.now().isoformat(),
        console_id=str(uuid.uuid4()),
        console_status=console_status,
        console_status_label=(
            console_status_label
        ),
        operational_summary=operational_summary,
        manual_actor=getattr(
            orchestrator_result,
            "manual_actor",
            None,
        ),
        orchestration_id=getattr(
            orchestrator_result,
            "orchestration_id",
            None,
        ),
        audit_trail_id=getattr(
            audit_result,
            "audit_trail_id",
            None,
        ),
        reconciliation_id=getattr(
            reconciliation_result,
            "reconciliation_id",
            None,
        ),
        release_gate_id=getattr(
            release_result,
            "release_gate_id",
            None,
        ),
        total_card_count=len(cards),
        passed_card_count=passed_card_count,
        warning_card_count=warning_card_count,
        blocked_card_count=blocked_card_count,
        failed_card_count=failed_card_count,
        completed_stage_count=getattr(
            orchestrator_result,
            "completed_stage_count",
            0,
        ),
        total_stage_count=getattr(
            orchestrator_result,
            "total_stage_count",
            0,
        ),
        audit_entry_count=getattr(
            audit_result,
            "total_entry_count",
            0,
        ),
        reconciliation_item_count=getattr(
            reconciliation_result,
            "total_item_count",
            0,
        ),
        reconciliation_mismatch_count=getattr(
            reconciliation_result,
            "mismatched_item_count",
            0,
        ),
        paper_run_locked=bool(
            getattr(
                release_result,
                "paper_run_locked",
                False,
            )
        ),
        policy_checks_passed=policy_valid,
        input_checks_passed=input_valid,
        version_checks_passed=version_valid,
        status_checks_passed=status_valid,
        identity_checks_passed=identity_valid,
        actor_checks_passed=actor_valid,
        hash_chain_checks_passed=hash_valid,
        seal_checks_passed=seal_valid,
        safety_checks_passed=safety_valid,
        all_checks_passed=all_checks_passed,
        read_only=True,
        automatic_execution_authorized=False,
        execution_blocked=True,
        broker_api_called=False,
        broker_order_created=False,
        live_order_created=False,
        live_execution_authorized=False,
        console_policy=policy,
        console_cards=cards,
        reasons=reasons,
        warnings=warnings,
        next_actions=next_actions,
    )

    print_paper_trading_operations_console(
        result
    )
    return result


def save_paper_trading_operations_console(
    result: PaperTradingOperationsConsoleResult,
) -> tuple[Path, Path]:
    if not isinstance(
        result,
        PaperTradingOperationsConsoleResult,
    ):
        raise TypeError(
            "V12.0 Operations Console Result 형식이 아닙니다."
        )

    directory = (
        PAPER_TRADING_OPERATIONS_CONSOLE_OUTPUT_DIRECTORY
    )
    directory.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S_%f"
    )
    report_path = directory / (
        f"paper_trading_operations_console_{timestamp}.json"
    )
    latest_path = directory / (
        "paper_trading_operations_console_latest.json"
    )

    result.report_path = str(report_path)
    result.latest_path = str(latest_path)
    payload = result.to_dict()
    write_json_file(report_path, payload)
    write_json_file(latest_path, payload)
    return (report_path, latest_path)


def load_latest_paper_trading_operations_console() -> (
    dict[str, Any]
):
    path = (
        PAPER_TRADING_OPERATIONS_CONSOLE_OUTPUT_DIRECTORY
        / "paper_trading_operations_console_latest.json"
    )
    return read_json_file(path)


def print_paper_trading_operations_console(
    result: PaperTradingOperationsConsoleResult,
) -> None:
    line_length = 120
    print()
    print("=" * line_length)
    print("V12.0 PAPER TRADING OPERATIONS CONSOLE")
    print("=" * line_length)
    print(
        f"Console status                : "
        f"{result.console_status}"
    )
    print(
        f"Console status label          : "
        f"{result.console_status_label}"
    )
    print(
        f"Operational summary           : "
        f"{result.operational_summary}"
    )
    print(
        f"Manual actor                  : "
        f"{result.manual_actor}"
    )
    print(
        f"Cards passed                  : "
        f"{result.passed_card_count}/{result.total_card_count}"
    )
    print(
        f"Paper run locked              : "
        f"{result.paper_run_locked}"
    )

    print()
    print("OPERATIONS CARDS")
    print("-" * line_length)
    for card in result.console_cards:
        print(
            f"{card.card_order}. "
            f"{card.card_name:<24} "
            f"{card.card_status:<8} "
            f"{card.primary_value:<18} "
            f"{card.secondary_value or ''}"
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
            "Version checks passed",
            result.version_checks_passed,
        ),
        (
            "Status checks passed",
            result.status_checks_passed,
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
            "Hash chain checks passed",
            result.hash_chain_checks_passed,
        ),
        (
            "Seal checks passed",
            result.seal_checks_passed,
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
        ("Read only", result.read_only),
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
    print("NEXT ACTIONS")
    print("-" * line_length)
    for action in result.next_actions:
        print(f"- {action}")

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
        "주의: V12.0 Console은 읽기 전용이며 "
        "실제 주문을 수행하지 않습니다."
    )
