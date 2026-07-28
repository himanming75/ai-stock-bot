import hashlib
import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from backtest.paper_submission_final_control import (
    PaperSubmissionFinalControlResult,
    PaperSubmissionFinalControlSeal,
    verify_control_seal,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIRECTORY = (
    PROJECT_ROOT / "output" / "trading_engine"
    / "paper_broker_sandbox_adapter"
)
REQUIRED_ADAPTER_TEXT = "PREPARE OFFLINE PAPER BROKER SANDBOX"


@dataclass(frozen=True)
class PaperBrokerSandboxAdapterPolicy:
    required_source_version: str = "V13.9"
    required_source_status: str = "FINAL_CONTROL_PASSED"
    required_control_status: str = "FINAL_CONTROL_PASSED"
    required_confirmation_text: str = REQUIRED_ADAPTER_TEXT
    adapter_name: str = "OFFLINE_PAPER_SANDBOX"
    adapter_mode: str = "IN_MEMORY_ONLY"
    sandbox_environment: str = "PAPER"
    session_validity_minutes: int = 15
    maximum_session_records: int = 100
    require_same_operator: bool = True
    require_control_hash: bool = True
    reject_duplicate_control_id: bool = True
    credentials_forbidden: bool = True
    network_access_disabled: bool = True
    account_access_disabled: bool = True
    broker_api_disabled: bool = True
    order_submission_disabled: bool = True
    live_execution_disabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PaperBrokerSandboxHandshake:
    handshake_id: str
    created_at: str
    operation: str
    adapter_name: str
    adapter_mode: str
    environment: str
    control_result_id: str
    control_id: str
    control_hash: str
    release_id: str
    ledger_entry_id: str
    operator: str
    item_count: int
    credentials_included: bool
    transmit: bool
    handshake_hash: str

    def payload_without_hash(self) -> dict[str, Any]:
        payload = asdict(self)
        payload.pop("handshake_hash", None)
        return payload

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PaperBrokerSandboxResponse:
    response_id: str
    created_at: str
    sandbox_status: str
    response_code: str
    handshake_id: str
    handshake_hash: str
    adapter_name: str
    environment: str
    session_id: str
    expires_at: str
    message: str
    credentials_used: bool
    dns_lookup_performed: bool
    socket_created: bool
    http_request_sent: bool
    network_accessed: bool
    account_accessed: bool
    broker_api_called: bool
    broker_order_created: bool
    order_submitted: bool
    live_execution_authorized: bool
    response_hash: str

    def payload_without_hash(self) -> dict[str, Any]:
        payload = asdict(self)
        payload.pop("response_hash", None)
        return payload

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PaperBrokerSandboxAdapterResult:
    version: str
    created_at: str
    adapter_result_id: str
    result_status: str
    result_status_label: str
    latest_session_id: str | None
    latest_expires_at: str | None
    total_session_count: int
    valid_session_count: int
    records_trimmed: int
    policy_checks_passed: bool
    input_checks_passed: bool
    source_checks_passed: bool
    control_checks_passed: bool
    operator_checks_passed: bool
    duplicate_checks_passed: bool
    existing_session_checks_passed: bool
    handshake_checks_passed: bool
    response_checks_passed: bool
    safety_checks_passed: bool
    all_checks_passed: bool
    sandbox_adapter_prepared: bool
    sandbox_session_ready: bool
    paper_execution_authorized: bool
    automatic_execution_authorized: bool
    execution_blocked: bool
    credentials_used: bool
    dns_lookup_performed: bool
    socket_created: bool
    http_request_sent: bool
    network_accessed: bool
    account_accessed: bool
    broker_api_called: bool
    broker_order_created: bool
    order_submitted: bool
    live_order_created: bool
    live_execution_authorized: bool
    adapter_policy: PaperBrokerSandboxAdapterPolicy
    handshakes: tuple[PaperBrokerSandboxHandshake, ...]
    responses: tuple[PaperBrokerSandboxResponse, ...]
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)
    report_path: str | None = None
    latest_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["adapter_policy"] = self.adapter_policy.to_dict()
        payload["handshakes"] = [item.to_dict() for item in self.handshakes]
        payload["responses"] = [item.to_dict() for item in self.responses]
        return payload


def canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )


def sha256_payload(payload: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def validate_policy(policy: PaperBrokerSandboxAdapterPolicy) -> list[str]:
    if not isinstance(policy, PaperBrokerSandboxAdapterPolicy):
        return ["Sandbox Adapter Policy 형식이 올바르지 않습니다."]
    errors: list[str] = []
    expected = {
        "required_source_version": "V13.9",
        "required_source_status": "FINAL_CONTROL_PASSED",
        "required_control_status": "FINAL_CONTROL_PASSED",
        "required_confirmation_text": REQUIRED_ADAPTER_TEXT,
        "adapter_name": "OFFLINE_PAPER_SANDBOX",
        "adapter_mode": "IN_MEMORY_ONLY",
        "sandbox_environment": "PAPER",
    }
    for name, value in expected.items():
        if getattr(policy, name) != value:
            errors.append(f"{name} 값이 V14.0 기준과 다릅니다.")
    if policy.session_validity_minutes <= 0:
        errors.append("Sandbox Session 유효시간은 0보다 커야 합니다.")
    if policy.maximum_session_records <= 0:
        errors.append("Sandbox Session 보관 한도는 0보다 커야 합니다.")
    for name in (
        "require_same_operator",
        "require_control_hash",
        "reject_duplicate_control_id",
        "credentials_forbidden",
        "network_access_disabled",
        "account_access_disabled",
        "broker_api_disabled",
        "order_submission_disabled",
        "live_execution_disabled",
    ):
        if getattr(policy, name) is not True:
            errors.append(f"{name}는 V14.0에서 True여야 합니다.")
    return errors


def validate_source(
    source: Any,
) -> tuple[PaperSubmissionFinalControlSeal | None, list[str], list[str]]:
    source_errors: list[str] = []
    control_errors: list[str] = []
    control: PaperSubmissionFinalControlSeal | None = None
    if not isinstance(source, PaperSubmissionFinalControlResult):
        source_errors.append("Source는 V13.9 Final Control Result여야 합니다.")
        return None, source_errors, control_errors
    if not (
        source.version == "V13.9"
        and source.result_status == "FINAL_CONTROL_PASSED"
        and source.all_checks_passed
        and source.final_control_passed
        and source.paper_submission_controlled
        and source.controls
    ):
        source_errors.append("정상 V13.9 Final Control Source가 아닙니다.")
    if any((
        source.paper_execution_authorized,
        source.automatic_execution_authorized,
        not source.execution_blocked,
        source.network_accessed,
        source.account_accessed,
        source.broker_api_called,
        source.broker_order_created,
        source.order_submitted,
        source.live_order_created,
        source.live_execution_authorized,
    )):
        source_errors.append("V13.9 Source 실행 안전장치가 올바르지 않습니다.")
    if source.controls:
        control = source.controls[-1]
        valid, errors = verify_control_seal(control)
        if not valid:
            control_errors.extend(errors)
        if source.latest_control_id != control.control_id:
            control_errors.append("Latest Control ID 연결이 다릅니다.")
        if source.latest_control_hash != control.control_hash:
            control_errors.append("Latest Control Hash 연결이 다릅니다.")
    return control, source_errors, control_errors


def verify_handshake(
    handshake: PaperBrokerSandboxHandshake,
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if handshake.operation != "OFFLINE_SANDBOX_HANDSHAKE":
        errors.append("Handshake Operation이 올바르지 않습니다.")
    if handshake.adapter_mode != "IN_MEMORY_ONLY":
        errors.append("Handshake Adapter Mode가 안전하지 않습니다.")
    if handshake.environment != "PAPER":
        errors.append("Handshake Environment가 PAPER가 아닙니다.")
    if handshake.credentials_included or handshake.transmit:
        errors.append("Handshake에 인증정보 또는 전송 설정이 있습니다.")
    if handshake.item_count <= 0:
        errors.append("Handshake Item Count가 올바르지 않습니다.")
    if handshake.handshake_hash != sha256_payload(handshake.payload_without_hash()):
        errors.append("Handshake Hash가 일치하지 않습니다.")
    return not errors, errors


def verify_response(
    response: PaperBrokerSandboxResponse,
    checked_at: datetime | None = None,
) -> tuple[bool, bool, list[str]]:
    checked_at = checked_at or datetime.now().astimezone()
    errors: list[str] = []
    if response.sandbox_status != "SANDBOX_READY":
        errors.append("Sandbox Response가 SANDBOX_READY가 아닙니다.")
    if response.response_code != "OFFLINE_200":
        errors.append("Sandbox Response Code가 올바르지 않습니다.")
    if response.environment != "PAPER":
        errors.append("Sandbox Response Environment가 PAPER가 아닙니다.")
    if any((
        response.credentials_used,
        response.dns_lookup_performed,
        response.socket_created,
        response.http_request_sent,
        response.network_accessed,
        response.account_accessed,
        response.broker_api_called,
        response.broker_order_created,
        response.order_submitted,
        response.live_execution_authorized,
    )):
        errors.append("Sandbox Response에 외부 연결 또는 실행 흔적이 있습니다.")
    if response.response_hash != sha256_payload(response.payload_without_hash()):
        errors.append("Sandbox Response Hash가 일치하지 않습니다.")
    try:
        expiry = datetime.fromisoformat(response.expires_at)
        time_valid = checked_at <= expiry
    except (TypeError, ValueError):
        time_valid = False
    if not time_valid:
        errors.append("Sandbox Session이 만료되었습니다.")
    return not errors, time_valid, errors


def normalize_history(
    handshakes: Any,
    responses: Any,
) -> tuple[
    tuple[PaperBrokerSandboxHandshake, ...],
    tuple[PaperBrokerSandboxResponse, ...],
]:
    if handshakes is None:
        handshakes = ()
    if responses is None:
        responses = ()
    if not isinstance(handshakes, (tuple, list)):
        raise TypeError("Existing Handshakes는 tuple 또는 list여야 합니다.")
    if not isinstance(responses, (tuple, list)):
        raise TypeError("Existing Responses는 tuple 또는 list여야 합니다.")
    clean_handshakes = tuple(handshakes)
    clean_responses = tuple(responses)
    if len(clean_handshakes) != len(clean_responses):
        raise ValueError("Handshake와 Response 기록 수가 다릅니다.")
    for handshake in clean_handshakes:
        if not isinstance(handshake, PaperBrokerSandboxHandshake):
            raise TypeError("Existing Handshake 형식이 올바르지 않습니다.")
    for response in clean_responses:
        if not isinstance(response, PaperBrokerSandboxResponse):
            raise TypeError("Existing Response 형식이 올바르지 않습니다.")
    return clean_handshakes, clean_responses


def prepare_paper_broker_sandbox(
    source: PaperSubmissionFinalControlResult,
    operator: str,
    confirmation_text: str,
    existing_handshakes: Any = None,
    existing_responses: Any = None,
    policy: PaperBrokerSandboxAdapterPolicy | None = None,
    now: datetime | None = None,
) -> PaperBrokerSandboxAdapterResult:
    policy = policy or PaperBrokerSandboxAdapterPolicy()
    now = now or datetime.now().astimezone()
    created_at = now.isoformat()
    policy_errors = validate_policy(policy)
    clean_operator = operator.strip() if isinstance(operator, str) else ""
    input_errors: list[str] = []
    if not clean_operator:
        input_errors.append("Operator가 필요합니다.")
    if confirmation_text != policy.required_confirmation_text:
        input_errors.append("Sandbox Adapter 확인 문구가 일치하지 않습니다.")
    control, source_errors, control_errors = validate_source(source)
    operator_errors: list[str] = []
    if control and control.operator != clean_operator:
        operator_errors.append("Final Control Operator와 Adapter Operator가 다릅니다.")
    history_errors: list[str] = []
    try:
        handshakes, responses = normalize_history(
            existing_handshakes, existing_responses
        )
    except (TypeError, ValueError) as error:
        handshakes, responses = (), ()
        history_errors.append(str(error))
    for handshake, response in zip(handshakes, responses):
        handshake_valid, errors = verify_handshake(handshake)
        if not handshake_valid:
            history_errors.extend(errors)
        response_valid, _, errors = verify_response(response, now)
        if not response_valid:
            history_errors.extend(errors)
        if (
            response.handshake_id != handshake.handshake_id
            or response.handshake_hash != handshake.handshake_hash
        ):
            history_errors.append("Existing Handshake와 Response 연결이 다릅니다.")
    duplicate_errors: list[str] = []
    if control and any(
        item.control_id == control.control_id for item in handshakes
    ):
        duplicate_errors.append("동일 Final Control의 Sandbox Session이 이미 있습니다.")
    handshake: PaperBrokerSandboxHandshake | None = None
    response: PaperBrokerSandboxResponse | None = None
    handshake_errors: list[str] = []
    response_errors: list[str] = []
    preliminary_errors = (
        policy_errors + input_errors + source_errors + control_errors
        + operator_errors + history_errors + duplicate_errors
    )
    if not preliminary_errors and control:
        handshake_draft = PaperBrokerSandboxHandshake(
            handshake_id=str(uuid.uuid4()),
            created_at=created_at,
            operation="OFFLINE_SANDBOX_HANDSHAKE",
            adapter_name=policy.adapter_name,
            adapter_mode=policy.adapter_mode,
            environment=policy.sandbox_environment,
            control_result_id=source.control_result_id,
            control_id=control.control_id,
            control_hash=control.control_hash,
            release_id=control.release_id,
            ledger_entry_id=control.ledger_entry_id,
            operator=clean_operator,
            item_count=control.controlled_item_count,
            credentials_included=False,
            transmit=False,
            handshake_hash="",
        )
        handshake = PaperBrokerSandboxHandshake(
            **{
                **asdict(handshake_draft),
                "handshake_hash": sha256_payload(
                    handshake_draft.payload_without_hash()
                ),
            }
        )
        handshake_valid, errors = verify_handshake(handshake)
        if not handshake_valid:
            handshake_errors.extend(errors)
        response_draft = PaperBrokerSandboxResponse(
            response_id=str(uuid.uuid4()),
            created_at=created_at,
            sandbox_status="SANDBOX_READY",
            response_code="OFFLINE_200",
            handshake_id=handshake.handshake_id,
            handshake_hash=handshake.handshake_hash,
            adapter_name=policy.adapter_name,
            environment=policy.sandbox_environment,
            session_id=str(uuid.uuid4()),
            expires_at=(
                now + timedelta(minutes=policy.session_validity_minutes)
            ).isoformat(),
            message="Offline in-memory paper sandbox is ready.",
            credentials_used=False,
            dns_lookup_performed=False,
            socket_created=False,
            http_request_sent=False,
            network_accessed=False,
            account_accessed=False,
            broker_api_called=False,
            broker_order_created=False,
            order_submitted=False,
            live_execution_authorized=False,
            response_hash="",
        )
        response = PaperBrokerSandboxResponse(
            **{
                **asdict(response_draft),
                "response_hash": sha256_payload(
                    response_draft.payload_without_hash()
                ),
            }
        )
        response_valid, _, errors = verify_response(response, now)
        if not response_valid:
            response_errors.extend(errors)
    all_handshakes = (*handshakes, *((handshake,) if handshake else ()))
    all_responses = (*responses, *((response,) if response else ()))
    trimmed = max(0, len(all_responses) - policy.maximum_session_records)
    if trimmed:
        all_handshakes = all_handshakes[-policy.maximum_session_records:]
        all_responses = all_responses[-policy.maximum_session_records:]
    all_errors = preliminary_errors + handshake_errors + response_errors
    passed = bool(handshake and response) and not all_errors
    source_valid = not source_errors and not control_errors
    status = "SANDBOX_READY" if passed else (
        "BLOCKED" if source_valid else "FAILED"
    )
    valid_count = sum(
        verify_response(item, now)[0] for item in all_responses
    )
    return PaperBrokerSandboxAdapterResult(
        version="V14.0",
        created_at=created_at,
        adapter_result_id=str(uuid.uuid4()),
        result_status=status,
        result_status_label={
            "SANDBOX_READY": "Offline Paper Broker Sandbox 준비 완료",
            "BLOCKED": "Sandbox Adapter 준비 차단",
            "FAILED": "V13.9 Final Control 검증 실패",
        }[status],
        latest_session_id=response.session_id if response else None,
        latest_expires_at=response.expires_at if response else None,
        total_session_count=len(all_responses),
        valid_session_count=valid_count,
        records_trimmed=trimmed,
        policy_checks_passed=not policy_errors,
        input_checks_passed=not input_errors,
        source_checks_passed=not source_errors,
        control_checks_passed=not control_errors,
        operator_checks_passed=not operator_errors,
        duplicate_checks_passed=not duplicate_errors,
        existing_session_checks_passed=not history_errors,
        handshake_checks_passed=bool(handshake) and not handshake_errors,
        response_checks_passed=bool(response) and not response_errors,
        safety_checks_passed=not policy_errors,
        all_checks_passed=passed,
        sandbox_adapter_prepared=passed,
        sandbox_session_ready=passed,
        paper_execution_authorized=False,
        automatic_execution_authorized=False,
        execution_blocked=True,
        credentials_used=False,
        dns_lookup_performed=False,
        socket_created=False,
        http_request_sent=False,
        network_accessed=False,
        account_accessed=False,
        broker_api_called=False,
        broker_order_created=False,
        order_submitted=False,
        live_order_created=False,
        live_execution_authorized=False,
        adapter_policy=policy,
        handshakes=all_handshakes,
        responses=all_responses,
        reasons=[
            "V13.9 Final Control을 Offline Sandbox Adapter에 연결했습니다."
            if passed else "Paper Broker Sandbox Adapter 준비가 차단되었습니다."
        ],
        warnings=all_errors + [
            "SANDBOX_READY는 실제 Broker 연결 또는 주문 권한이 아닙니다."
        ],
        next_actions=[
            "Handshake와 Response Hash를 수동 확인합니다.",
            "실제 API Key, 계좌 또는 Broker Endpoint를 입력하지 않습니다.",
        ],
    )


def save_sandbox_adapter_result(
    result: PaperBrokerSandboxAdapterResult,
    directory: Path | None = None,
) -> tuple[Path, Path]:
    directory = directory or OUTPUT_DIRECTORY
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S_%f")
    report = directory / f"paper_broker_sandbox_adapter_{stamp}.json"
    latest = directory / "latest_paper_broker_sandbox_adapter.json"
    payload = result.to_dict()
    for path in (report, latest):
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(path)
    result.report_path = str(report)
    result.latest_path = str(latest)
    return report, latest


def load_sandbox_adapter_result(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("version") != "V14.0":
        raise ValueError("V14.0 결과 파일이 아닙니다.")
    handshakes = tuple(
        PaperBrokerSandboxHandshake(**item)
        for item in payload.get("handshakes", [])
    )
    responses = tuple(
        PaperBrokerSandboxResponse(**item)
        for item in payload.get("responses", [])
    )
    if len(handshakes) != len(responses):
        raise ValueError("저장된 Handshake와 Response 수가 다릅니다.")
    for handshake, response in zip(handshakes, responses):
        valid, errors = verify_handshake(handshake)
        if not valid:
            raise ValueError("저장된 Handshake가 올바르지 않습니다: " + "; ".join(errors))
        if (
            response.handshake_id != handshake.handshake_id
            or response.handshake_hash != handshake.handshake_hash
        ):
            raise ValueError("저장된 Handshake와 Response 연결이 다릅니다.")
        if response.response_hash != sha256_payload(response.payload_without_hash()):
            raise ValueError("저장된 Response Hash가 일치하지 않습니다.")
    return payload
