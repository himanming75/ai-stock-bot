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
)
from backtest.manual_paper_run_reconciliation import (
    ManualPaperRunReconciliationResult,
    create_reconciliation_pair_id,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent

MANUAL_PAPER_RUN_RELEASE_GATE_OUTPUT_DIRECTORY = (
    PROJECT_ROOT
    / "output"
    / "trading_engine"
    / "manual_paper_run_release_gate"
)

VALID_RELEASE_STATUSES = {
    "PAPER_RELEASED",
    "BLOCKED",
    "FAILED",
}

REQUIRED_MANUAL_RELEASE_TEXT = (
    "LOCK PAPER RUN AS COMPLETE"
)


@dataclass(frozen=True)
class ManualPaperRunReleaseGatePolicy:
    """
    V11.9 Manual Paper Run Release Gate 정책입니다.

    PAPER_RELEASED는 모의 실행 기록이 검증 완료되어 잠겼다는 뜻입니다.
    실제 Broker 주문 또는 Live Execution 허용을 뜻하지 않습니다.
    """

    required_orchestrator_version: str = "V11.6"
    required_audit_version: str = "V11.7"
    required_reconciliation_version: str = "V11.8"

    required_orchestrator_status: str = "COMPLETED"
    required_audit_status: str = "RECORDED"
    required_reconciliation_status: str = (
        "RECONCILED"
    )

    required_manual_release_text: str = (
        REQUIRED_MANUAL_RELEASE_TEXT
    )
    minimum_release_note_length: int = 5
    maximum_history_records: int = 100

    require_same_manual_actor: bool = True
    require_source_identity_chain: bool = True
    require_audit_hash_validation: bool = True
    require_all_checks_passed: bool = True
    require_source_safety: bool = True
    reject_duplicate_release: bool = True

    manual_release_required: bool = True
    automatic_execution_disabled: bool = True
    paper_only: bool = True
    live_execution_disabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ManualPaperRunReleaseSeal:
    release_id: str
    released_at: str

    orchestration_id: str
    audit_trail_id: str
    reconciliation_id: str
    reconciliation_pair_id: str

    manual_actor: str
    release_note: str
    manual_release_text: str

    orchestrator_status: str
    audit_status: str
    reconciliation_status: str
    audit_last_entry_hash: str

    paper_run_locked: bool
    automatic_execution_authorized: bool
    execution_blocked: bool
    broker_api_called: bool
    broker_order_created: bool
    live_order_created: bool
    live_execution_authorized: bool

    seal_hash: str

    def payload_without_hash(self) -> dict[str, Any]:
        payload = asdict(self)
        payload.pop("seal_hash", None)
        return payload

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ManualPaperRunReleaseGateResult:
    version: str
    created_at: str
    release_gate_id: str

    release_status: str
    release_status_label: str

    source_orchestration_id: str | None
    source_audit_trail_id: str | None
    source_reconciliation_id: str | None
    release_identity: str | None

    manual_actor: str
    release_note: str
    manual_release_text: str

    policy_checks_passed: bool
    manual_checks_passed: bool
    source_checks_passed: bool
    identity_checks_passed: bool
    actor_checks_passed: bool
    hash_chain_checks_passed: bool
    duplicate_checks_passed: bool
    safety_checks_passed: bool
    seal_checks_passed: bool
    all_checks_passed: bool

    paper_run_locked: bool
    automatic_execution_authorized: bool
    execution_blocked: bool
    broker_api_called: bool
    broker_order_created: bool
    live_order_created: bool
    live_execution_authorized: bool

    release_policy: ManualPaperRunReleaseGatePolicy
    release_seal: ManualPaperRunReleaseSeal | None
    release_history: tuple[str, ...]

    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)

    report_path: str | None = None
    latest_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["release_policy"] = (
            self.release_policy.to_dict()
        )
        payload["release_seal"] = (
            self.release_seal.to_dict()
            if self.release_seal is not None
            else None
        )
        payload["release_history"] = list(
            self.release_history
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
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def calculate_seal_hash(
    payload: dict[str, Any],
) -> str:
    return hashlib.sha256(
        canonical_json(payload).encode("utf-8")
    ).hexdigest()


def validate_release_policy(
    policy: ManualPaperRunReleaseGatePolicy,
) -> tuple[bool, list[str]]:
    if not isinstance(
        policy,
        ManualPaperRunReleaseGatePolicy,
    ):
        return (
            False,
            ["Release Gate Policy 형식이 올바르지 않습니다."],
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
        "required_manual_release_text": (
            policy.required_manual_release_text,
            REQUIRED_MANUAL_RELEASE_TEXT,
        ),
    }
    for name, (actual, expected) in (
        expected_values.items()
    ):
        if actual != expected:
            errors.append(
                f"{name}는 {expected}이어야 합니다."
            )

    if (
        not isinstance(
            policy.minimum_release_note_length,
            int,
        )
        or policy.minimum_release_note_length <= 0
    ):
        errors.append(
            "Minimum Release Note Length가 올바르지 않습니다."
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
        "require_same_manual_actor": (
            policy.require_same_manual_actor
        ),
        "require_source_identity_chain": (
            policy.require_source_identity_chain
        ),
        "require_audit_hash_validation": (
            policy.require_audit_hash_validation
        ),
        "require_all_checks_passed": (
            policy.require_all_checks_passed
        ),
        "require_source_safety": (
            policy.require_source_safety
        ),
        "reject_duplicate_release": (
            policy.reject_duplicate_release
        ),
        "manual_release_required": (
            policy.manual_release_required
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
                f"{name}는 V11.9에서 True여야 합니다."
            )

    return (not errors, errors)


def validate_manual_release_input(
    manual_actor: Any,
    release_note: Any,
    manual_release_text: Any,
    policy: ManualPaperRunReleaseGatePolicy,
) -> tuple[bool, list[str]]:
    errors: list[str] = []

    if (
        not isinstance(manual_actor, str)
        or not manual_actor.strip()
    ):
        errors.append(
            "Manual Actor가 비어 있습니다."
        )
    if (
        not isinstance(release_note, str)
        or len(release_note.strip())
        < policy.minimum_release_note_length
    ):
        errors.append(
            "Release Note가 너무 짧습니다."
        )
    if (
        not isinstance(manual_release_text, str)
        or manual_release_text.strip().upper()
        != policy.required_manual_release_text.upper()
    ):
        errors.append(
            (
                "Manual Release Text가 일치하지 않습니다. "
                f"필요 문구: {policy.required_manual_release_text}"
            )
        )

    return (not errors, errors)


def validate_release_sources(
    orchestrator_result: Any,
    audit_result: Any,
    reconciliation_result: Any,
) -> tuple[bool, list[str]]:
    errors: list[str] = []

    if not isinstance(
        orchestrator_result,
        ManualPaperRunOrchestratorResult,
    ):
        errors.append(
            "Orchestrator Result는 V11.6 형식이어야 합니다."
        )
    if not isinstance(
        audit_result,
        ManualPaperRunAuditTrailResult,
    ):
        errors.append(
            "Audit Result는 V11.7 형식이어야 합니다."
        )
    if not isinstance(
        reconciliation_result,
        ManualPaperRunReconciliationResult,
    ):
        errors.append(
            "Reconciliation Result는 V11.8 형식이어야 합니다."
        )
    if errors:
        return (False, errors)

    source_requirements = (
        (
            orchestrator_result.version == "V11.6",
            "Orchestrator Version이 V11.6이 아닙니다.",
        ),
        (
            orchestrator_result.orchestrator_status
            == "COMPLETED",
            "Orchestrator Status가 COMPLETED가 아닙니다.",
        ),
        (
            orchestrator_result.all_checks_passed,
            "Orchestrator All Checks가 실패했습니다.",
        ),
        (
            audit_result.version == "V11.7",
            "Audit Version이 V11.7이 아닙니다.",
        ),
        (
            audit_result.audit_status == "RECORDED",
            "Audit Status가 RECORDED가 아닙니다.",
        ),
        (
            audit_result.all_checks_passed,
            "Audit All Checks가 실패했습니다.",
        ),
        (
            reconciliation_result.version == "V11.8",
            "Reconciliation Version이 V11.8이 아닙니다.",
        ),
        (
            reconciliation_result.reconciliation_status
            == "RECONCILED",
            "Reconciliation Status가 RECONCILED가 아닙니다.",
        ),
        (
            reconciliation_result.all_checks_passed,
            "Reconciliation All Checks가 실패했습니다.",
        ),
        (
            reconciliation_result.mismatched_item_count
            == 0,
            "Reconciliation에 불일치 항목이 있습니다.",
        ),
    )
    for passed, message in source_requirements:
        if not passed:
            errors.append(message)

    return (not errors, errors)


def validate_identity_chain(
    orchestrator_result: (
        ManualPaperRunOrchestratorResult
    ),
    audit_result: ManualPaperRunAuditTrailResult,
    reconciliation_result: (
        ManualPaperRunReconciliationResult
    ),
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    orchestration_id = (
        orchestrator_result.orchestration_id
    )
    audit_id = audit_result.audit_trail_id
    expected_pair_id = (
        create_reconciliation_pair_id(
            orchestration_id,
            audit_id,
        )
    )

    checks = (
        (
            audit_result.source_orchestration_id
            == orchestration_id,
            "Audit의 Source Orchestration ID가 일치하지 않습니다.",
        ),
        (
            reconciliation_result
            .source_orchestration_id
            == orchestration_id,
            "Reconciliation의 Orchestration ID가 일치하지 않습니다.",
        ),
        (
            reconciliation_result.audit_trail_id
            == audit_id,
            "Reconciliation의 Audit Trail ID가 일치하지 않습니다.",
        ),
        (
            reconciliation_result
            .reconciliation_pair_id
            == expected_pair_id,
            "Reconciliation Pair ID가 일치하지 않습니다.",
        ),
    )
    for passed, message in checks:
        if not passed:
            errors.append(message)

    return (not errors, errors)


def validate_actor_chain(
    manual_actor: str,
    orchestrator_result: (
        ManualPaperRunOrchestratorResult
    ),
    audit_result: ManualPaperRunAuditTrailResult,
    reconciliation_result: (
        ManualPaperRunReconciliationResult
    ),
) -> tuple[bool, list[str]]:
    normalized_actor = manual_actor.strip()
    actors = (
        orchestrator_result.manual_actor,
        audit_result.manual_actor,
        reconciliation_result.manual_actor,
    )
    valid = all(
        actor == normalized_actor
        for actor in actors
    )
    return (
        valid,
        (
            []
            if valid
            else [
                "Manual Actor가 V11.6~V11.8 실행자와 일치하지 않습니다."
            ]
        ),
    )


def validate_release_safety(
    orchestrator_result: (
        ManualPaperRunOrchestratorResult
    ),
    audit_result: ManualPaperRunAuditTrailResult,
    reconciliation_result: (
        ManualPaperRunReconciliationResult
    ),
) -> tuple[bool, list[str]]:
    errors: list[str] = []

    for name, source in (
        ("V11.6", orchestrator_result),
        ("V11.7", audit_result),
        ("V11.8", reconciliation_result),
    ):
        source_safe = bool(
            source.execution_blocked is True
            and source
            .automatic_execution_authorized is False
            and source.broker_api_called is False
            and source.broker_order_created is False
            and source.live_order_created is False
            and source.live_execution_authorized is False
        )
        if not source_safe:
            errors.append(
                f"{name} Source에 실거래 안전 오류가 있습니다."
            )

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
    for release_identity in existing_history:
        if (
            not isinstance(release_identity, str)
            or not release_identity.strip()
        ):
            raise ValueError(
                "History의 Release Identity가 올바르지 않습니다."
            )
        cleaned.append(release_identity.strip())

    return tuple(cleaned[-maximum_records:])


def create_release_identity(
    orchestration_id: str,
    audit_trail_id: str,
    reconciliation_id: str,
) -> str:
    raw_identity = (
        f"{orchestration_id}:"
        f"{audit_trail_id}:"
        f"{reconciliation_id}"
    )
    return hashlib.sha256(
        raw_identity.encode("utf-8")
    ).hexdigest()


def create_release_seal(
    *,
    manual_actor: str,
    release_note: str,
    manual_release_text: str,
    orchestrator_result: (
        ManualPaperRunOrchestratorResult
    ),
    audit_result: ManualPaperRunAuditTrailResult,
    reconciliation_result: (
        ManualPaperRunReconciliationResult
    ),
) -> ManualPaperRunReleaseSeal:
    seal_values: dict[str, Any] = {
        "release_id": str(uuid.uuid4()),
        "released_at": datetime.now().isoformat(),
        "orchestration_id": (
            orchestrator_result.orchestration_id
        ),
        "audit_trail_id": audit_result.audit_trail_id,
        "reconciliation_id": (
            reconciliation_result
            .reconciliation_id
        ),
        "reconciliation_pair_id": (
            reconciliation_result
            .reconciliation_pair_id
        ),
        "manual_actor": manual_actor.strip(),
        "release_note": release_note.strip(),
        "manual_release_text": (
            manual_release_text.strip()
        ),
        "orchestrator_status": (
            orchestrator_result.orchestrator_status
        ),
        "audit_status": audit_result.audit_status,
        "reconciliation_status": (
            reconciliation_result
            .reconciliation_status
        ),
        "audit_last_entry_hash": (
            audit_result.last_entry_hash
        ),
        "paper_run_locked": True,
        "automatic_execution_authorized": False,
        "execution_blocked": True,
        "broker_api_called": False,
        "broker_order_created": False,
        "live_order_created": False,
        "live_execution_authorized": False,
    }
    seal_hash = calculate_seal_hash(seal_values)
    return ManualPaperRunReleaseSeal(
        **seal_values,
        seal_hash=seal_hash,
    )


def verify_release_seal(
    seal: Any,
) -> tuple[bool, list[str]]:
    if not isinstance(
        seal,
        ManualPaperRunReleaseSeal,
    ):
        return (
            False,
            ["Release Seal 형식이 올바르지 않습니다."],
        )

    errors: list[str] = []
    expected_hash = calculate_seal_hash(
        seal.payload_without_hash()
    )
    if seal.seal_hash != expected_hash:
        errors.append(
            "Release Seal Hash가 일치하지 않습니다."
        )
    if not seal.paper_run_locked:
        errors.append(
            "Paper Run이 잠금 상태가 아닙니다."
        )
    if (
        not seal.execution_blocked
        or seal.automatic_execution_authorized
        or seal.broker_api_called
        or seal.broker_order_created
        or seal.live_order_created
        or seal.live_execution_authorized
    ):
        errors.append(
            "Release Seal에 실거래 안전 오류가 있습니다."
        )

    return (not errors, errors)


def release_manual_paper_run(
    manual_actor: str,
    release_note: str,
    manual_release_text: str,
    orchestrator_result: Any,
    audit_result: Any,
    reconciliation_result: Any,
    existing_history: (
        tuple[str, ...]
        | list[str]
        | None
    ) = None,
    release_policy: (
        ManualPaperRunReleaseGatePolicy
        | None
    ) = None,
) -> ManualPaperRunReleaseGateResult:
    policy = (
        release_policy
        if release_policy is not None
        else ManualPaperRunReleaseGatePolicy()
    )
    policy_valid, policy_errors = (
        validate_release_policy(policy)
    )
    manual_valid, manual_errors = (
        validate_manual_release_input(
            manual_actor,
            release_note,
            manual_release_text,
            policy,
        )
    )
    source_valid, source_errors = (
        validate_release_sources(
            orchestrator_result,
            audit_result,
            reconciliation_result,
        )
    )

    if source_valid:
        identity_valid, identity_errors = (
            validate_identity_chain(
                orchestrator_result,
                audit_result,
                reconciliation_result,
            )
        )
        actor_valid, actor_errors = (
            validate_actor_chain(
                manual_actor,
                orchestrator_result,
                audit_result,
                reconciliation_result,
            )
        )
        hash_valid, hash_errors = (
            verify_audit_chain(
                audit_result.audit_entries
            )
        )
        safety_valid, safety_errors = (
            validate_release_safety(
                orchestrator_result,
                audit_result,
                reconciliation_result,
            )
        )
        release_identity = (
            create_release_identity(
                orchestrator_result
                .orchestration_id,
                audit_result.audit_trail_id,
                reconciliation_result
                .reconciliation_id,
            )
        )
    else:
        identity_valid = False
        identity_errors = []
        actor_valid = False
        actor_errors = []
        hash_valid = False
        hash_errors = []
        safety_valid = False
        safety_errors = []
        release_identity = None

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

    is_duplicate_release = bool(
        release_identity is not None
        and release_identity in history
    )
    duplicate_valid = bool(
        release_identity is not None
        and not is_duplicate_release
    )
    duplicate_errors: list[str] = []
    if is_duplicate_release:
        duplicate_errors.append(
            "동일한 Paper Run Release가 이미 기록되었습니다."
        )

    preflight_valid = bool(
        policy_valid
        and manual_valid
        and source_valid
        and identity_valid
        and actor_valid
        and hash_valid
        and safety_valid
        and history_valid
        and duplicate_valid
    )

    seal: ManualPaperRunReleaseSeal | None = None
    seal_valid = False
    seal_errors: list[str] = []
    if preflight_valid:
        seal = create_release_seal(
            manual_actor=manual_actor,
            release_note=release_note,
            manual_release_text=manual_release_text,
            orchestrator_result=(
                orchestrator_result
            ),
            audit_result=audit_result,
            reconciliation_result=(
                reconciliation_result
            ),
        )
        seal_valid, seal_errors = (
            verify_release_seal(seal)
        )

    all_checks_passed = bool(
        preflight_valid and seal_valid
    )

    if all_checks_passed:
        release_status = "PAPER_RELEASED"
        release_status_label = (
            "Manual Paper Run 검증 완료 및 잠금"
        )
        updated_history = (
            *history,
            release_identity,
        )[-policy.maximum_history_records:]
        reasons = [
            "V11.6~V11.8 Source와 수동 Release 입력이 검증되었습니다.",
            "Paper Run 완료 기록이 SHA-256 Seal로 잠겼습니다.",
            "이 Release는 실제 Broker 또는 Live 주문 권한이 아닙니다.",
        ]
        next_actions = [
            "Release Seal Hash와 최종 보고서를 보관합니다.",
            "다음 Paper Run은 새로운 승인과 실행 ID로 시작합니다.",
        ]
    elif is_duplicate_release:
        release_status = "BLOCKED"
        release_status_label = (
            "중복 Manual Paper Run Release 차단"
        )
        updated_history = history
        reasons = [
            "이미 잠긴 Paper Run Release는 다시 처리할 수 없습니다."
        ]
        next_actions = [
            "새로운 V11.6~V11.8 Source Chain을 사용합니다.",
        ]
    else:
        release_status = "FAILED"
        release_status_label = (
            "Manual Paper Run Release Gate 실패"
        )
        updated_history = history
        reasons = [
            "수동 입력, Source, ID, Hash 또는 Safety 검사에 실패했습니다."
        ]
        next_actions = [
            "Warnings에서 Release 실패 원인을 확인합니다.",
            "기존 기록을 수정하지 말고 안전한 실행부터 다시 생성합니다.",
        ]

    warnings = [
        *policy_errors,
        *manual_errors,
        *source_errors,
        *identity_errors,
        *actor_errors,
        *hash_errors,
        *safety_errors,
        *history_errors,
        *duplicate_errors,
        *seal_errors,
        "V11.9 PAPER_RELEASED는 Paper 기록의 완료·잠금만 의미합니다.",
        "Broker API, 실제 주문 및 Live Execution은 허용하지 않습니다.",
    ]

    result = ManualPaperRunReleaseGateResult(
        version="V11.9",
        created_at=datetime.now().isoformat(),
        release_gate_id=str(uuid.uuid4()),
        release_status=release_status,
        release_status_label=(
            release_status_label
        ),
        source_orchestration_id=getattr(
            orchestrator_result,
            "orchestration_id",
            None,
        ),
        source_audit_trail_id=getattr(
            audit_result,
            "audit_trail_id",
            None,
        ),
        source_reconciliation_id=getattr(
            reconciliation_result,
            "reconciliation_id",
            None,
        ),
        release_identity=release_identity,
        manual_actor=(
            manual_actor.strip()
            if isinstance(manual_actor, str)
            else ""
        ),
        release_note=(
            release_note.strip()
            if isinstance(release_note, str)
            else ""
        ),
        manual_release_text=(
            manual_release_text.strip()
            if isinstance(
                manual_release_text,
                str,
            )
            else ""
        ),
        policy_checks_passed=policy_valid,
        manual_checks_passed=manual_valid,
        source_checks_passed=source_valid,
        identity_checks_passed=identity_valid,
        actor_checks_passed=actor_valid,
        hash_chain_checks_passed=hash_valid,
        duplicate_checks_passed=duplicate_valid,
        safety_checks_passed=safety_valid,
        seal_checks_passed=seal_valid,
        all_checks_passed=all_checks_passed,
        paper_run_locked=all_checks_passed,
        automatic_execution_authorized=False,
        execution_blocked=True,
        broker_api_called=False,
        broker_order_created=False,
        live_order_created=False,
        live_execution_authorized=False,
        release_policy=policy,
        release_seal=seal,
        release_history=tuple(
            updated_history
        ),
        reasons=reasons,
        warnings=warnings,
        next_actions=next_actions,
    )

    print_manual_paper_run_release_gate(result)
    return result


def verify_saved_release_payload(
    payload: dict[str, Any],
) -> tuple[bool, list[str]]:
    raw_seal = payload.get("release_seal")
    if not isinstance(raw_seal, dict):
        return (
            False,
            ["저장된 Release Seal이 없습니다."],
        )

    errors: list[str] = []
    saved_hash = raw_seal.get("seal_hash")
    seal_payload = dict(raw_seal)
    seal_payload.pop("seal_hash", None)
    calculated_hash = calculate_seal_hash(
        seal_payload
    )
    if saved_hash != calculated_hash:
        errors.append(
            "저장된 Release Seal Hash가 일치하지 않습니다."
        )
    if raw_seal.get("paper_run_locked") is not True:
        errors.append(
            "저장된 Paper Run이 잠금 상태가 아닙니다."
        )
    if (
        raw_seal.get(
            "automatic_execution_authorized"
        )
        or raw_seal.get("broker_api_called")
        or raw_seal.get("broker_order_created")
        or raw_seal.get("live_order_created")
        or raw_seal.get(
            "live_execution_authorized"
        )
        or raw_seal.get("execution_blocked")
        is not True
    ):
        errors.append(
            "저장된 Release Seal에 실거래 안전 오류가 있습니다."
        )

    return (not errors, errors)


def save_manual_paper_run_release_gate(
    result: ManualPaperRunReleaseGateResult,
) -> tuple[Path, Path]:
    if not isinstance(
        result,
        ManualPaperRunReleaseGateResult,
    ):
        raise TypeError(
            "V11.9 Release Gate Result 형식이 아닙니다."
        )
    if not result.all_checks_passed:
        raise ValueError(
            "검사에 실패한 Release Gate 결과는 저장할 수 없습니다."
        )

    directory = (
        MANUAL_PAPER_RUN_RELEASE_GATE_OUTPUT_DIRECTORY
    )
    directory.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S_%f"
    )
    report_path = directory / (
        f"manual_paper_run_release_gate_{timestamp}.json"
    )
    latest_path = directory / (
        "manual_paper_run_release_gate_latest.json"
    )

    result.report_path = str(report_path)
    result.latest_path = str(latest_path)
    payload = result.to_dict()
    payload_valid, payload_errors = (
        verify_saved_release_payload(payload)
    )
    if not payload_valid:
        raise RuntimeError(
            "저장 전 Release Seal 검사가 실패했습니다: "
            + " | ".join(payload_errors)
        )

    write_json_file(report_path, payload)
    write_json_file(latest_path, payload)
    return (report_path, latest_path)


def load_latest_manual_paper_run_release_gate(
    verify_seal: bool = True,
) -> dict[str, Any]:
    path = (
        MANUAL_PAPER_RUN_RELEASE_GATE_OUTPUT_DIRECTORY
        / "manual_paper_run_release_gate_latest.json"
    )
    payload = read_json_file(path)

    if verify_seal:
        valid, errors = (
            verify_saved_release_payload(payload)
        )
        if not valid:
            raise RuntimeError(
                "저장된 Release Seal 검사가 실패했습니다: "
                + " | ".join(errors)
            )
    return payload


def print_manual_paper_run_release_gate(
    result: ManualPaperRunReleaseGateResult,
) -> None:
    line_length = 120
    print()
    print("=" * line_length)
    print("V11.9 MANUAL PAPER RUN RELEASE GATE")
    print("=" * line_length)
    print(
        f"Release status                : "
        f"{result.release_status}"
    )
    print(
        f"Release status label          : "
        f"{result.release_status_label}"
    )
    print(
        f"Manual actor                  : "
        f"{result.manual_actor}"
    )
    print(
        f"Orchestration ID              : "
        f"{result.source_orchestration_id}"
    )
    print(
        f"Audit Trail ID                : "
        f"{result.source_audit_trail_id}"
    )
    print(
        f"Reconciliation ID             : "
        f"{result.source_reconciliation_id}"
    )
    print(
        f"Paper run locked              : "
        f"{result.paper_run_locked}"
    )
    print(
        f"Seal hash                     : "
        f"{getattr(result.release_seal, 'seal_hash', None)}"
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
            "Manual checks passed",
            result.manual_checks_passed,
        ),
        (
            "Source checks passed",
            result.source_checks_passed,
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
            "Duplicate checks passed",
            result.duplicate_checks_passed,
        ),
        (
            "Safety checks passed",
            result.safety_checks_passed,
        ),
        (
            "Seal checks passed",
            result.seal_checks_passed,
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
        "주의: PAPER_RELEASED는 Paper 기록 잠금이며 "
        "실제 주문 허용이 아닙니다."
    )
