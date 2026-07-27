import hashlib
import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from backtest.paper_run_readiness_certificate import (
    PaperRunReadinessCertificate,
    PaperRunReadinessCertificateResult,
    verify_readiness_certificate,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
CERTIFIED_PAPER_RUN_LAUNCH_AUTHORIZATION_OUTPUT_DIRECTORY = (
    PROJECT_ROOT
    / "output"
    / "trading_engine"
    / "certified_paper_run_launch_authorization"
)

REQUIRED_LAUNCH_TEXT = (
    "AUTHORIZE CERTIFIED PAPER RUN LAUNCH"
)
VALID_AUTHORIZATION_STATUSES = {
    "AUTHORIZED",
    "BLOCKED",
    "FAILED",
}


@dataclass(frozen=True)
class CertifiedPaperRunLaunchAuthorizationPolicy:
    """V12.8 인증된 Paper Run Launch 허가 정책입니다."""

    required_certificate_version: str = "V12.7"
    required_issue_status: str = "ISSUED"
    required_certificate_status: str = "VALID"
    required_confirmation_text: str = (
        REQUIRED_LAUNCH_TEXT
    )
    authorization_validity_minutes: int = 10
    maximum_authorization_records: int = 100
    hash_algorithm: str = "SHA256"

    require_unexpired_certificate: bool = True
    require_certificate_hash: bool = True
    require_same_operator: bool = True
    require_source_safety: bool = True
    reject_duplicate_certificate_id: bool = True
    verify_authorization_hashes: bool = True

    launch_preparation_only: bool = True
    automatic_execution_disabled: bool = True
    broker_execution_disabled: bool = True
    live_execution_disabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CertifiedPaperRunLaunchAuthorization:
    authorization_id: str
    authorized_at: str
    expires_at: str
    authorization_status: str

    certificate_result_id: str
    certificate_id: str
    certificate_hash: str
    preflight_id: str
    trading_date: str
    operator: str
    symbols: tuple[str, ...]

    paper_launch_authorized: bool
    paper_execution_authorized: bool
    execution_blocked: bool
    broker_api_called: bool
    broker_order_created: bool
    live_order_created: bool
    live_execution_authorized: bool

    authorization_hash: str

    def payload_without_hash(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["symbols"] = list(self.symbols)
        payload.pop("authorization_hash", None)
        return payload

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["symbols"] = list(self.symbols)
        return payload


@dataclass
class CertifiedPaperRunLaunchAuthorizationResult:
    version: str
    created_at: str
    authorization_result_id: str

    result_status: str
    result_status_label: str
    latest_authorization_id: str | None
    latest_certificate_id: str | None
    latest_expires_at: str | None
    total_authorization_count: int
    valid_authorization_count: int
    records_trimmed: int

    policy_checks_passed: bool
    input_checks_passed: bool
    source_checks_passed: bool
    certificate_checks_passed: bool
    operator_checks_passed: bool
    duplicate_checks_passed: bool
    existing_authorization_checks_passed: bool
    issued_authorization_checks_passed: bool
    safety_checks_passed: bool
    all_checks_passed: bool

    paper_launch_authorized: bool
    paper_execution_authorized: bool
    automatic_execution_authorized: bool
    execution_blocked: bool
    broker_api_called: bool
    broker_order_created: bool
    live_order_created: bool
    live_execution_authorized: bool

    authorization_policy: (
        CertifiedPaperRunLaunchAuthorizationPolicy
    )
    authorizations: tuple[
        CertifiedPaperRunLaunchAuthorization,
        ...,
    ]
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)
    report_path: str | None = None
    latest_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["authorization_policy"] = (
            self.authorization_policy.to_dict()
        )
        payload["authorizations"] = [
            item.to_dict()
            for item in self.authorizations
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


def calculate_authorization_hash(
    payload: dict[str, Any],
) -> str:
    return hashlib.sha256(
        canonical_json(payload).encode("utf-8")
    ).hexdigest()


def validate_authorization_policy(
    policy: CertifiedPaperRunLaunchAuthorizationPolicy,
) -> tuple[bool, list[str]]:
    if not isinstance(
        policy,
        CertifiedPaperRunLaunchAuthorizationPolicy,
    ):
        return (
            False,
            ["Launch Authorization Policy 형식이 올바르지 않습니다."],
        )
    errors: list[str] = []
    expected = {
        "required_certificate_version": "V12.7",
        "required_issue_status": "ISSUED",
        "required_certificate_status": "VALID",
        "required_confirmation_text": (
            REQUIRED_LAUNCH_TEXT
        ),
        "hash_algorithm": "SHA256",
    }
    for name, value in expected.items():
        if getattr(policy, name) != value:
            errors.append(
                f"{name} 값이 V12.8 기준과 다릅니다."
            )
    if (
        policy.authorization_validity_minutes <= 0
        or policy.maximum_authorization_records <= 0
    ):
        errors.append(
            "Authorization 숫자 기준이 올바르지 않습니다."
        )
    for name in (
        "require_unexpired_certificate",
        "require_certificate_hash",
        "require_same_operator",
        "require_source_safety",
        "reject_duplicate_certificate_id",
        "verify_authorization_hashes",
        "launch_preparation_only",
        "automatic_execution_disabled",
        "broker_execution_disabled",
        "live_execution_disabled",
    ):
        if getattr(policy, name) is not True:
            errors.append(
                f"{name}는 V12.8에서 True여야 합니다."
            )
    return (not errors, errors)


def validate_certificate_source(
    result: Any,
) -> tuple[
    bool,
    bool,
    bool,
    PaperRunReadinessCertificate | None,
    list[str],
]:
    if not isinstance(
        result,
        PaperRunReadinessCertificateResult,
    ):
        return (
            False,
            False,
            False,
            None,
            ["Certificate Result는 V12.7 형식이어야 합니다."],
        )
    errors: list[str] = []
    source_valid = bool(
        result.version == "V12.7"
        and result.issue_status == "ISSUED"
        and result.all_checks_passed
        and result.paper_readiness_certified
        and result.certificates
    )
    certificate = (
        result.certificates[-1]
        if source_valid
        else None
    )
    if not source_valid:
        errors.append(
            "정상적으로 ISSUED된 V12.7 Source가 아닙니다."
        )
    if certificate is not None:
        (
            certificate_valid,
            time_valid,
            certificate_errors,
        ) = verify_readiness_certificate(certificate)
        errors.extend(certificate_errors)
    else:
        certificate_valid = False
        time_valid = False
    safety_valid = bool(
        result.paper_execution_authorized is False
        and result.automatic_execution_authorized is False
        and result.execution_blocked is True
        and result.broker_api_called is False
        and result.broker_order_created is False
        and result.live_order_created is False
        and result.live_execution_authorized is False
    )
    if not safety_valid:
        errors.append(
            "Certificate Source에 실행 안전 오류가 있습니다."
        )
    return (
        source_valid,
        bool(certificate_valid and time_valid),
        safety_valid,
        certificate,
        errors,
    )


def normalize_authorizations(
    existing: Any,
) -> tuple[
    CertifiedPaperRunLaunchAuthorization,
    ...,
]:
    if existing is None:
        return ()
    if not isinstance(existing, (tuple, list)):
        raise TypeError(
            "Existing Authorizations는 tuple 또는 list여야 합니다."
        )
    values: list[
        CertifiedPaperRunLaunchAuthorization
    ] = []
    for item in existing:
        if not isinstance(
            item,
            CertifiedPaperRunLaunchAuthorization,
        ):
            raise TypeError(
                "Existing Authorization 형식이 올바르지 않습니다."
            )
        values.append(item)
    return tuple(values)


def verify_launch_authorization(
    item: CertifiedPaperRunLaunchAuthorization,
    checked_at: datetime | None = None,
) -> tuple[bool, bool, list[str]]:
    errors: list[str] = []
    hash_valid = bool(
        item.authorization_hash
        == calculate_authorization_hash(
            item.payload_without_hash()
        )
    )
    if not hash_valid:
        errors.append(
            "Authorization Hash가 일치하지 않습니다."
        )
    try:
        time_valid = (
            checked_at or datetime.now()
        ) <= datetime.fromisoformat(item.expires_at)
    except (TypeError, ValueError):
        time_valid = False
    if not time_valid:
        errors.append(
            "Authorization이 만료되었습니다."
        )
    safety_valid = bool(
        item.paper_launch_authorized is True
        and item.paper_execution_authorized is False
        and item.execution_blocked is True
        and item.broker_api_called is False
        and item.broker_order_created is False
        and item.live_order_created is False
        and item.live_execution_authorized is False
    )
    if not safety_valid:
        errors.append(
            "Authorization에 실행 안전 오류가 있습니다."
        )
    return (
        bool(hash_valid and time_valid and safety_valid),
        time_valid,
        errors,
    )


def verify_authorization_collection(
    items: tuple[
        CertifiedPaperRunLaunchAuthorization,
        ...,
    ],
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    ids: set[str] = set()
    certificate_ids: set[str] = set()
    for item in items:
        if (
            item.authorization_hash
            != calculate_authorization_hash(
                item.payload_without_hash()
            )
        ):
            errors.append(
                f"{item.authorization_id} Hash가 일치하지 않습니다."
            )
        if item.authorization_id in ids:
            errors.append(
                "중복 Authorization ID가 있습니다."
            )
        if item.certificate_id in certificate_ids:
            errors.append(
                "중복 Certificate ID Authorization이 있습니다."
            )
        ids.add(item.authorization_id)
        certificate_ids.add(item.certificate_id)
    return (not errors, errors)


def create_authorization(
    source_result: PaperRunReadinessCertificateResult,
    certificate: PaperRunReadinessCertificate,
    operator: str,
    policy: CertifiedPaperRunLaunchAuthorizationPolicy,
) -> CertifiedPaperRunLaunchAuthorization:
    now = datetime.now()
    values: dict[str, Any] = {
        "authorization_id": str(uuid.uuid4()),
        "authorized_at": now.isoformat(),
        "expires_at": (
            now
            + timedelta(
                minutes=policy
                .authorization_validity_minutes
            )
        ).isoformat(),
        "authorization_status": "VALID",
        "certificate_result_id": (
            source_result.certificate_result_id
        ),
        "certificate_id": certificate.certificate_id,
        "certificate_hash": certificate.certificate_hash,
        "preflight_id": certificate.preflight_id,
        "trading_date": certificate.trading_date,
        "operator": operator.strip(),
        "symbols": certificate.symbols,
        "paper_launch_authorized": True,
        "paper_execution_authorized": False,
        "execution_blocked": True,
        "broker_api_called": False,
        "broker_order_created": False,
        "live_order_created": False,
        "live_execution_authorized": False,
    }
    hash_payload = dict(values)
    hash_payload["symbols"] = list(values["symbols"])
    return CertifiedPaperRunLaunchAuthorization(
        **values,
        authorization_hash=(
            calculate_authorization_hash(hash_payload)
        ),
    )


def authorize_certified_paper_run_launch(
    certificate_result: Any,
    launch_operator: Any,
    confirmation_text: Any,
    existing_authorizations: Any = None,
    authorization_policy: (
        CertifiedPaperRunLaunchAuthorizationPolicy
        | None
    ) = None,
) -> CertifiedPaperRunLaunchAuthorizationResult:
    policy = (
        authorization_policy
        if authorization_policy is not None
        else CertifiedPaperRunLaunchAuthorizationPolicy()
    )
    policy_valid, policy_errors = (
        validate_authorization_policy(policy)
    )
    (
        source_valid,
        certificate_valid,
        source_safety_valid,
        certificate,
        source_errors,
    ) = validate_certificate_source(certificate_result)
    input_valid = bool(
        isinstance(launch_operator, str)
        and launch_operator.strip()
        and isinstance(confirmation_text, str)
    )
    source_operator = (
        certificate.operator
        if certificate is not None
        else None
    )
    operator_valid = bool(
        input_valid
        and launch_operator.strip()
        == (source_operator or "").strip()
        and confirmation_text.strip()
        == policy.required_confirmation_text
    )
    operator_errors: list[str] = []
    if input_valid:
        if (
            launch_operator.strip()
            != (source_operator or "").strip()
        ):
            operator_errors.append(
                "Launch Operator가 Certificate Operator와 일치하지 않습니다."
            )
        if (
            confirmation_text.strip()
            != policy.required_confirmation_text
        ):
            operator_errors.append(
                "Launch Confirmation Text가 일치하지 않습니다."
            )
    else:
        operator_errors.append(
            "Launch Operator 또는 Confirmation 입력이 올바르지 않습니다."
        )
    try:
        normalized = normalize_authorizations(
            existing_authorizations
        )
        existing_input_valid = True
        existing_input_errors: list[str] = []
    except (TypeError, ValueError) as error:
        normalized = ()
        existing_input_valid = False
        existing_input_errors = [str(error)]
    if existing_input_valid:
        existing_valid, existing_errors = (
            verify_authorization_collection(normalized)
        )
    else:
        existing_valid = False
        existing_errors = []
    certificate_id = (
        certificate.certificate_id
        if certificate is not None
        else None
    )
    duplicate_found = bool(
        certificate_id
        and any(
            item.certificate_id == certificate_id
            for item in normalized
        )
    )
    duplicate_valid = bool(
        certificate_id and not duplicate_found
    )
    duplicate_errors = (
        ["동일한 Certificate에 이미 Launch Authorization이 있습니다."]
        if duplicate_found
        else []
    )
    preflight_valid = bool(
        policy_valid
        and source_valid
        and certificate_valid
        and source_safety_valid
        and input_valid
        and operator_valid
        and existing_input_valid
        and existing_valid
        and duplicate_valid
    )
    updated = normalized
    records_trimmed = 0
    issued_valid = False
    issued_errors: list[str] = []
    if preflight_valid and certificate is not None:
        item = create_authorization(
            certificate_result,
            certificate,
            launch_operator,
            policy,
        )
        item_valid, _, item_errors = (
            verify_launch_authorization(item)
        )
        if item_valid:
            all_items = (*normalized, item)
            records_trimmed = max(
                0,
                len(all_items)
                - policy.maximum_authorization_records,
            )
            updated = tuple(
                all_items[
                    -policy.maximum_authorization_records:
                ]
            )
            issued_valid, issued_errors = (
                verify_authorization_collection(updated)
            )
        else:
            issued_errors.extend(item_errors)
    all_checks_passed = bool(
        preflight_valid and issued_valid
    )
    if all_checks_passed:
        status = "AUTHORIZED"
        label = "Certified Paper Run Launch 허가 기록 완료"
        reasons = [
            "유효한 Readiness Certificate에 Launch 허가가 기록되었습니다.",
            f"Launch 허가는 {policy.authorization_validity_minutes}분간 유효합니다.",
        ]
        next_actions = [
            "Authorization Hash와 만료 시간을 확인합니다.",
            "다음 단계에서도 주문 실행은 별도로 통제합니다.",
        ]
    elif duplicate_found or (
        source_valid
        and certificate_valid
        and source_safety_valid
        and not operator_valid
    ):
        status = "BLOCKED"
        label = "Certified Paper Run Launch 허가 차단"
        reasons = [
            "중복 또는 수동 확인 조건에 통과하지 못했습니다."
        ]
        next_actions = [
            "새 Certificate 또는 정확한 확인 문구를 사용합니다.",
        ]
    else:
        status = "FAILED"
        label = "Certified Launch Authorization 검사 실패"
        reasons = [
            "Source, Certificate, Hash 또는 Safety 검사에 실패했습니다."
        ]
        next_actions = [
            "Warnings를 확인하고 Source를 다시 생성합니다.",
        ]
    latest = updated[-1] if updated else None
    now = datetime.now()
    valid_count = sum(
        verify_launch_authorization(
            item,
            now,
        )[0]
        for item in updated
    )
    return CertifiedPaperRunLaunchAuthorizationResult(
        version="V12.8",
        created_at=now.isoformat(),
        authorization_result_id=str(uuid.uuid4()),
        result_status=status,
        result_status_label=label,
        latest_authorization_id=(
            latest.authorization_id if latest else None
        ),
        latest_certificate_id=(
            latest.certificate_id if latest else None
        ),
        latest_expires_at=(
            latest.expires_at if latest else None
        ),
        total_authorization_count=len(updated),
        valid_authorization_count=valid_count,
        records_trimmed=records_trimmed,
        policy_checks_passed=policy_valid,
        input_checks_passed=bool(
            input_valid and existing_input_valid
        ),
        source_checks_passed=source_valid,
        certificate_checks_passed=certificate_valid,
        operator_checks_passed=operator_valid,
        duplicate_checks_passed=duplicate_valid,
        existing_authorization_checks_passed=(
            existing_valid
        ),
        issued_authorization_checks_passed=(
            issued_valid
        ),
        safety_checks_passed=source_safety_valid,
        all_checks_passed=all_checks_passed,
        paper_launch_authorized=all_checks_passed,
        paper_execution_authorized=False,
        automatic_execution_authorized=False,
        execution_blocked=True,
        broker_api_called=False,
        broker_order_created=False,
        live_order_created=False,
        live_execution_authorized=False,
        authorization_policy=policy,
        authorizations=updated,
        reasons=reasons,
        warnings=[
            *policy_errors,
            *source_errors,
            *operator_errors,
            *existing_input_errors,
            *existing_errors,
            *duplicate_errors,
            *issued_errors,
            "V12.8은 Paper Launch 준비 허가만 기록합니다.",
            "실제 Broker API, 실제 주문 및 Live Execution은 모두 차단됩니다.",
        ],
        next_actions=next_actions,
    )


def verify_saved_authorization_payload(
    payload: dict[str, Any],
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if payload.get("version") != "V12.8":
        errors.append(
            "저장된 Authorization Version이 V12.8이 아닙니다."
        )
    if payload.get("result_status") not in VALID_AUTHORIZATION_STATUSES:
        errors.append(
            "저장된 Result Status가 올바르지 않습니다."
        )
    if payload.get("paper_execution_authorized") is not False:
        errors.append(
            "저장된 Authorization이 Paper Execution을 허용합니다."
        )
    if payload.get("execution_blocked") is not True:
        errors.append(
            "저장된 Authorization의 Execution이 차단되지 않았습니다."
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


def save_certified_paper_run_launch_authorization(
    result: CertifiedPaperRunLaunchAuthorizationResult,
    output_directory: Path | None = None,
) -> CertifiedPaperRunLaunchAuthorizationResult:
    if not isinstance(
        result,
        CertifiedPaperRunLaunchAuthorizationResult,
    ):
        raise TypeError(
            "V12.8 Launch Authorization Result 형식이 아닙니다."
        )
    directory = (
        output_directory
        if output_directory is not None
        else CERTIFIED_PAPER_RUN_LAUNCH_AUTHORIZATION_OUTPUT_DIRECTORY
    )
    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S_%f"
    )
    report_path = directory / (
        f"certified_paper_run_launch_authorization_{timestamp}.json"
    )
    latest_path = directory / (
        "certified_paper_run_launch_authorization_latest.json"
    )
    payload = result.to_dict()
    write_json_file(report_path, payload)
    write_json_file(latest_path, payload)
    result.report_path = str(report_path)
    result.latest_path = str(latest_path)
    return result


def load_latest_certified_paper_run_launch_authorization(
    output_directory: Path | None = None,
) -> dict[str, Any]:
    directory = (
        output_directory
        if output_directory is not None
        else CERTIFIED_PAPER_RUN_LAUNCH_AUTHORIZATION_OUTPUT_DIRECTORY
    )
    return read_json_file(
        directory
        / "certified_paper_run_launch_authorization_latest.json"
    )


def print_certified_paper_run_launch_authorization(
    result: CertifiedPaperRunLaunchAuthorizationResult,
) -> None:
    line = "=" * 100
    print()
    print(line)
    print("V12.8 CERTIFIED PAPER RUN LAUNCH AUTHORIZATION")
    print(line)
    print(f"Result status          : {result.result_status}")
    print(f"Authorization ID       : {result.latest_authorization_id}")
    print(f"Expires at             : {result.latest_expires_at}")
    print(f"Paper launch           : {result.paper_launch_authorized}")
    print(f"Paper execution        : {result.paper_execution_authorized}")
    print(line)
    print(
        "주의: Launch 준비 허가이며 실제 주문 실행 권한이 아닙니다."
    )

