import hashlib
import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from backtest.paper_operations_preflight_check import (
    PaperOperationsPreflightResult,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PAPER_RUN_READINESS_CERTIFICATE_OUTPUT_DIRECTORY = (
    PROJECT_ROOT
    / "output"
    / "trading_engine"
    / "paper_run_readiness_certificate"
)

REQUIRED_CERTIFICATE_TEXT = (
    "ISSUE PAPER RUN READINESS CERTIFICATE"
)
VALID_ISSUE_STATUSES = {
    "ISSUED",
    "BLOCKED",
    "FAILED",
}


@dataclass(frozen=True)
class PaperRunReadinessCertificatePolicy:
    """V12.7 Paper Run 준비 인증서 정책입니다."""

    required_preflight_version: str = "V12.6"
    required_preflight_status: str = "READY"
    required_confirmation_text: str = (
        REQUIRED_CERTIFICATE_TEXT
    )
    validity_minutes: int = 30
    maximum_certificate_records: int = 100
    hash_algorithm: str = "SHA256"

    require_preflight_all_checks: bool = True
    require_preflight_authorized: bool = True
    require_operator_match: bool = True
    require_source_safety: bool = True
    require_all_preflight_items_passed: bool = True
    reject_duplicate_preflight_id: bool = True
    verify_certificate_hashes: bool = True

    readiness_only: bool = True
    automatic_execution_disabled: bool = True
    broker_execution_disabled: bool = True
    live_execution_disabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PaperRunReadinessCertificate:
    certificate_id: str
    issued_at: str
    expires_at: str
    certificate_status: str

    preflight_id: str
    approved_handoff_id: str | None
    handoff_record_id: str | None
    trading_date: str
    operator: str
    symbols: tuple[str, ...]
    cash_balance: float
    market_data_age_minutes: int

    passed_item_count: int
    total_item_count: int
    preflight_all_checks_passed: bool

    paper_readiness_certified: bool
    paper_execution_authorized: bool
    execution_blocked: bool
    broker_api_called: bool
    broker_order_created: bool
    live_order_created: bool
    live_execution_authorized: bool

    certificate_hash: str

    def payload_without_hash(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["symbols"] = list(self.symbols)
        payload.pop("certificate_hash", None)
        return payload

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["symbols"] = list(self.symbols)
        return payload


@dataclass
class PaperRunReadinessCertificateResult:
    version: str
    created_at: str
    certificate_result_id: str

    issue_status: str
    issue_status_label: str
    latest_certificate_id: str | None
    latest_certificate_hash: str | None
    latest_expires_at: str | None

    total_certificate_count: int
    valid_certificate_count: int
    records_trimmed: int

    policy_checks_passed: bool
    input_checks_passed: bool
    source_checks_passed: bool
    operator_checks_passed: bool
    duplicate_checks_passed: bool
    existing_certificate_checks_passed: bool
    issued_certificate_checks_passed: bool
    safety_checks_passed: bool
    all_checks_passed: bool

    paper_readiness_certified: bool
    paper_execution_authorized: bool
    automatic_execution_authorized: bool
    execution_blocked: bool
    broker_api_called: bool
    broker_order_created: bool
    live_order_created: bool
    live_execution_authorized: bool

    certificate_policy: (
        PaperRunReadinessCertificatePolicy
    )
    certificates: tuple[
        PaperRunReadinessCertificate,
        ...,
    ]

    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)
    report_path: str | None = None
    latest_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["certificate_policy"] = (
            self.certificate_policy.to_dict()
        )
        payload["certificates"] = [
            certificate.to_dict()
            for certificate in self.certificates
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


def calculate_certificate_hash(
    payload: dict[str, Any],
) -> str:
    return hashlib.sha256(
        canonical_json(payload).encode("utf-8")
    ).hexdigest()


def validate_certificate_policy(
    policy: PaperRunReadinessCertificatePolicy,
) -> tuple[bool, list[str]]:
    if not isinstance(
        policy,
        PaperRunReadinessCertificatePolicy,
    ):
        return (
            False,
            ["Readiness Certificate Policy 형식이 올바르지 않습니다."],
        )
    errors: list[str] = []
    expected = {
        "required_preflight_version": "V12.6",
        "required_preflight_status": "READY",
        "required_confirmation_text": (
            REQUIRED_CERTIFICATE_TEXT
        ),
        "hash_algorithm": "SHA256",
    }
    for name, value in expected.items():
        if getattr(policy, name) != value:
            errors.append(
                f"{name} 값이 V12.7 기준과 다릅니다."
            )
    if (
        policy.validity_minutes <= 0
        or policy.maximum_certificate_records <= 0
    ):
        errors.append(
            "Certificate 숫자 기준이 올바르지 않습니다."
        )
    for name in (
        "require_preflight_all_checks",
        "require_preflight_authorized",
        "require_operator_match",
        "require_source_safety",
        "require_all_preflight_items_passed",
        "reject_duplicate_preflight_id",
        "verify_certificate_hashes",
        "readiness_only",
        "automatic_execution_disabled",
        "broker_execution_disabled",
        "live_execution_disabled",
    ):
        if getattr(policy, name) is not True:
            errors.append(
                f"{name}는 V12.7에서 True여야 합니다."
            )
    return (not errors, errors)


def validate_preflight_source(
    preflight_result: Any,
) -> tuple[bool, bool, list[str]]:
    if not isinstance(
        preflight_result,
        PaperOperationsPreflightResult,
    ):
        return (
            False,
            False,
            ["Preflight Result는 V12.6 형식이어야 합니다."],
        )
    errors: list[str] = []
    source_valid = bool(
        preflight_result.version == "V12.6"
        and preflight_result.preflight_status == "READY"
        and preflight_result.all_checks_passed
        and preflight_result.paper_preflight_authorized
        and preflight_result.total_item_count > 0
        and preflight_result.passed_item_count
        == preflight_result.total_item_count
        and all(
            item.passed
            for item in preflight_result.preflight_items
        )
    )
    if not source_valid:
        errors.append(
            "모든 항목을 통과한 READY V12.6 Preflight가 아닙니다."
        )
    safety_valid = bool(
        preflight_result.paper_execution_authorized is False
        and preflight_result
        .automatic_execution_authorized is False
        and preflight_result.execution_blocked is True
        and preflight_result.broker_api_called is False
        and preflight_result.broker_order_created is False
        and preflight_result.live_order_created is False
        and preflight_result
        .live_execution_authorized is False
    )
    if not safety_valid:
        errors.append(
            "Preflight Source에 실행 안전 오류가 있습니다."
        )
    return (source_valid, safety_valid, errors)


def normalize_certificates(
    existing_certificates: Any,
) -> tuple[PaperRunReadinessCertificate, ...]:
    if existing_certificates is None:
        return ()
    if not isinstance(
        existing_certificates,
        (tuple, list),
    ):
        raise TypeError(
            "Existing Certificates는 tuple 또는 list여야 합니다."
        )
    certificates: list[
        PaperRunReadinessCertificate
    ] = []
    for certificate in existing_certificates:
        if not isinstance(
            certificate,
            PaperRunReadinessCertificate,
        ):
            raise TypeError(
                "Existing Certificate 형식이 올바르지 않습니다."
            )
        certificates.append(certificate)
    return tuple(certificates)


def verify_readiness_certificate(
    certificate: PaperRunReadinessCertificate,
    checked_at: datetime | None = None,
) -> tuple[bool, bool, list[str]]:
    errors: list[str] = []
    expected_hash = calculate_certificate_hash(
        certificate.payload_without_hash()
    )
    hash_valid = (
        certificate.certificate_hash
        == expected_hash
    )
    if not hash_valid:
        errors.append(
            "Certificate Hash가 일치하지 않습니다."
        )
    try:
        expires_at = datetime.fromisoformat(
            certificate.expires_at
        )
        time_valid = (
            checked_at or datetime.now()
        ) <= expires_at
    except (TypeError, ValueError):
        time_valid = False
    if not time_valid:
        errors.append(
            "Certificate가 만료되었거나 시간이 올바르지 않습니다."
        )
    safety_valid = bool(
        certificate.paper_readiness_certified is True
        and certificate.paper_execution_authorized is False
        and certificate.execution_blocked is True
        and certificate.broker_api_called is False
        and certificate.broker_order_created is False
        and certificate.live_order_created is False
        and certificate.live_execution_authorized is False
    )
    if not safety_valid:
        errors.append(
            "Certificate에 실행 안전 오류가 있습니다."
        )
    return (
        bool(hash_valid and time_valid and safety_valid),
        time_valid,
        errors,
    )


def verify_certificate_collection(
    certificates: tuple[
        PaperRunReadinessCertificate,
        ...,
    ],
    *,
    require_unexpired: bool = False,
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    ids: set[str] = set()
    preflight_ids: set[str] = set()
    for certificate in certificates:
        expected_hash = calculate_certificate_hash(
            certificate.payload_without_hash()
        )
        if certificate.certificate_hash != expected_hash:
            errors.append(
                f"{certificate.certificate_id} Hash가 일치하지 않습니다."
            )
        if certificate.certificate_id in ids:
            errors.append(
                "중복 Certificate ID가 있습니다."
            )
        if certificate.preflight_id in preflight_ids:
            errors.append(
                "중복 Preflight ID Certificate가 있습니다."
            )
        ids.add(certificate.certificate_id)
        preflight_ids.add(certificate.preflight_id)
        if require_unexpired:
            _, time_valid, _ = verify_readiness_certificate(
                certificate
            )
            if not time_valid:
                errors.append(
                    f"{certificate.certificate_id} Certificate가 만료되었습니다."
                )
    return (not errors, errors)


def create_certificate(
    preflight_result: PaperOperationsPreflightResult,
    policy: PaperRunReadinessCertificatePolicy,
) -> PaperRunReadinessCertificate:
    issued_at = datetime.now()
    values: dict[str, Any] = {
        "certificate_id": str(uuid.uuid4()),
        "issued_at": issued_at.isoformat(),
        "expires_at": (
            issued_at
            + timedelta(minutes=policy.validity_minutes)
        ).isoformat(),
        "certificate_status": "VALID",
        "preflight_id": preflight_result.preflight_id,
        "approved_handoff_id": (
            preflight_result.approved_handoff_id
        ),
        "handoff_record_id": (
            preflight_result.handoff_record_id
        ),
        "trading_date": (
            preflight_result.trading_date or ""
        ),
        "operator": preflight_result.operator or "",
        "symbols": preflight_result.symbols,
        "cash_balance": (
            preflight_result.cash_balance or 0.0
        ),
        "market_data_age_minutes": (
            preflight_result
            .market_data_age_minutes
            if preflight_result
            .market_data_age_minutes is not None
            else -1
        ),
        "passed_item_count": (
            preflight_result.passed_item_count
        ),
        "total_item_count": (
            preflight_result.total_item_count
        ),
        "preflight_all_checks_passed": (
            preflight_result.all_checks_passed
        ),
        "paper_readiness_certified": True,
        "paper_execution_authorized": False,
        "execution_blocked": True,
        "broker_api_called": False,
        "broker_order_created": False,
        "live_order_created": False,
        "live_execution_authorized": False,
    }
    hash_payload = dict(values)
    hash_payload["symbols"] = list(values["symbols"])
    certificate_hash = calculate_certificate_hash(
        hash_payload
    )
    return PaperRunReadinessCertificate(
        **values,
        certificate_hash=certificate_hash,
    )


def issue_paper_run_readiness_certificate(
    preflight_result: Any,
    certificate_operator: Any,
    confirmation_text: Any,
    existing_certificates: Any = None,
    certificate_policy: (
        PaperRunReadinessCertificatePolicy | None
    ) = None,
) -> PaperRunReadinessCertificateResult:
    policy = (
        certificate_policy
        if certificate_policy is not None
        else PaperRunReadinessCertificatePolicy()
    )
    policy_valid, policy_errors = (
        validate_certificate_policy(policy)
    )
    source_valid, source_safety_valid, source_errors = (
        validate_preflight_source(preflight_result)
    )
    input_valid = bool(
        isinstance(certificate_operator, str)
        and certificate_operator.strip()
        and isinstance(confirmation_text, str)
    )
    input_errors = (
        []
        if input_valid
        else ["Certificate Operator 또는 Confirmation 입력이 올바르지 않습니다."]
    )
    source_operator = getattr(
        preflight_result,
        "operator",
        None,
    )
    operator_valid = bool(
        input_valid
        and certificate_operator.strip()
        == (source_operator or "").strip()
        and confirmation_text.strip()
        == policy.required_confirmation_text
    )
    operator_errors: list[str] = []
    if input_valid:
        if (
            certificate_operator.strip()
            != (source_operator or "").strip()
        ):
            operator_errors.append(
                "Certificate Operator가 Preflight Operator와 일치하지 않습니다."
            )
        if (
            confirmation_text.strip()
            != policy.required_confirmation_text
        ):
            operator_errors.append(
                "Certificate Confirmation Text가 일치하지 않습니다."
            )

    try:
        normalized = normalize_certificates(
            existing_certificates
        )
        existing_input_valid = True
        existing_input_errors: list[str] = []
    except (TypeError, ValueError) as error:
        normalized = ()
        existing_input_valid = False
        existing_input_errors = [str(error)]

    if existing_input_valid:
        existing_valid, existing_errors = (
            verify_certificate_collection(normalized)
        )
    else:
        existing_valid = False
        existing_errors = []

    preflight_id = getattr(
        preflight_result,
        "preflight_id",
        None,
    )
    duplicate_found = bool(
        preflight_id
        and any(
            certificate.preflight_id == preflight_id
            for certificate in normalized
        )
    )
    duplicate_valid = bool(
        preflight_id and not duplicate_found
    )
    duplicate_errors = (
        ["동일한 Preflight ID의 Certificate가 이미 있습니다."]
        if duplicate_found
        else []
    )

    preflight_valid = bool(
        policy_valid
        and source_valid
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
    if preflight_valid:
        certificate = create_certificate(
            preflight_result,
            policy,
        )
        (
            certificate_valid,
            _,
            certificate_errors,
        ) = verify_readiness_certificate(certificate)
        if certificate_valid:
            all_certificates = (*normalized, certificate)
            records_trimmed = max(
                0,
                len(all_certificates)
                - policy.maximum_certificate_records,
            )
            updated = tuple(
                all_certificates[
                    -policy.maximum_certificate_records:
                ]
            )
            issued_valid, issued_errors = (
                verify_certificate_collection(updated)
            )
        else:
            issued_errors.extend(certificate_errors)

    all_checks_passed = bool(
        preflight_valid and issued_valid
    )
    if all_checks_passed:
        status = "ISSUED"
        label = "Paper Run Readiness Certificate 발급 완료"
        reasons = [
            "READY Preflight가 SHA-256 Certificate로 봉인되었습니다.",
            f"Certificate 유효기간은 {policy.validity_minutes}분입니다.",
        ]
        next_actions = [
            "Certificate Hash와 만료 시간을 확인합니다.",
            "다음 단계에서도 실제 실행 승인이 별도로 필요합니다.",
        ]
    elif duplicate_found or (
        source_valid
        and source_safety_valid
        and not operator_valid
    ):
        status = "BLOCKED"
        label = "Readiness Certificate 발급 차단"
        reasons = [
            "중복 또는 수동 확인 조건에 통과하지 못했습니다."
        ]
        next_actions = [
            "새 Preflight 또는 정확한 확인 문구를 사용합니다.",
        ]
    else:
        status = "FAILED"
        label = "Readiness Certificate 검사 실패"
        reasons = [
            "Source, Policy, Hash 또는 Safety 검사에 실패했습니다."
        ]
        next_actions = [
            "Warnings를 확인하고 Source를 다시 생성합니다.",
        ]

    latest = updated[-1] if updated else None
    now = datetime.now()
    valid_count = 0
    for certificate in updated:
        valid, _, _ = verify_readiness_certificate(
            certificate,
            now,
        )
        valid_count += int(valid)
    return PaperRunReadinessCertificateResult(
        version="V12.7",
        created_at=now.isoformat(),
        certificate_result_id=str(uuid.uuid4()),
        issue_status=status,
        issue_status_label=label,
        latest_certificate_id=(
            latest.certificate_id if latest else None
        ),
        latest_certificate_hash=(
            latest.certificate_hash if latest else None
        ),
        latest_expires_at=(
            latest.expires_at if latest else None
        ),
        total_certificate_count=len(updated),
        valid_certificate_count=valid_count,
        records_trimmed=records_trimmed,
        policy_checks_passed=policy_valid,
        input_checks_passed=bool(
            input_valid and existing_input_valid
        ),
        source_checks_passed=source_valid,
        operator_checks_passed=operator_valid,
        duplicate_checks_passed=duplicate_valid,
        existing_certificate_checks_passed=(
            existing_valid
        ),
        issued_certificate_checks_passed=issued_valid,
        safety_checks_passed=source_safety_valid,
        all_checks_passed=all_checks_passed,
        paper_readiness_certified=all_checks_passed,
        paper_execution_authorized=False,
        automatic_execution_authorized=False,
        execution_blocked=True,
        broker_api_called=False,
        broker_order_created=False,
        live_order_created=False,
        live_execution_authorized=False,
        certificate_policy=policy,
        certificates=updated,
        reasons=reasons,
        warnings=[
            *policy_errors,
            *source_errors,
            *input_errors,
            *operator_errors,
            *existing_input_errors,
            *existing_errors,
            *duplicate_errors,
            *issued_errors,
            "V12.7 Certificate는 준비 상태만 증명합니다.",
            "실제 Broker API, 실제 주문 및 Live Execution은 모두 차단됩니다.",
        ],
        next_actions=next_actions,
    )


def verify_saved_certificate_payload(
    payload: dict[str, Any],
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if payload.get("version") != "V12.7":
        errors.append(
            "저장된 Certificate Version이 V12.7이 아닙니다."
        )
    if payload.get("issue_status") not in VALID_ISSUE_STATUSES:
        errors.append(
            "저장된 Issue Status가 올바르지 않습니다."
        )
    if payload.get("paper_execution_authorized") is not False:
        errors.append(
            "저장된 Certificate가 Paper Execution을 허용합니다."
        )
    if payload.get("execution_blocked") is not True:
        errors.append(
            "저장된 Certificate의 Execution이 차단되지 않았습니다."
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


def save_paper_run_readiness_certificate(
    result: PaperRunReadinessCertificateResult,
    output_directory: Path | None = None,
) -> PaperRunReadinessCertificateResult:
    if not isinstance(
        result,
        PaperRunReadinessCertificateResult,
    ):
        raise TypeError(
            "V12.7 Certificate Result 형식이 아닙니다."
        )
    directory = (
        output_directory
        if output_directory is not None
        else PAPER_RUN_READINESS_CERTIFICATE_OUTPUT_DIRECTORY
    )
    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S_%f"
    )
    report_path = directory / (
        f"paper_run_readiness_certificate_{timestamp}.json"
    )
    latest_path = directory / (
        "paper_run_readiness_certificate_latest.json"
    )
    payload = result.to_dict()
    write_json_file(report_path, payload)
    write_json_file(latest_path, payload)
    result.report_path = str(report_path)
    result.latest_path = str(latest_path)
    return result


def load_latest_paper_run_readiness_certificate(
    output_directory: Path | None = None,
) -> dict[str, Any]:
    directory = (
        output_directory
        if output_directory is not None
        else PAPER_RUN_READINESS_CERTIFICATE_OUTPUT_DIRECTORY
    )
    return read_json_file(
        directory
        / "paper_run_readiness_certificate_latest.json"
    )


def print_paper_run_readiness_certificate(
    result: PaperRunReadinessCertificateResult,
) -> None:
    line = "=" * 100
    print()
    print(line)
    print("V12.7 PAPER RUN READINESS CERTIFICATE")
    print(line)
    print(f"Issue status           : {result.issue_status}")
    print(f"Certificate ID         : {result.latest_certificate_id}")
    print(f"Expires at             : {result.latest_expires_at}")
    print(f"Readiness certified    : {result.paper_readiness_certified}")
    print(f"Paper execution        : {result.paper_execution_authorized}")
    print(line)
    print(
        "주의: Certificate는 준비 상태 증명이며 주문 권한이 아닙니다."
    )

