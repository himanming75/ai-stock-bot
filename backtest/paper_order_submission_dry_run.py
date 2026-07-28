import hashlib
import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from backtest.paper_order_translation_validator import (
    PaperOrderTranslationBatch,
    PaperOrderTranslationResult,
    TranslatedPaperOrder,
    verify_translation_batch,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIRECTORY = (
    PROJECT_ROOT / "output" / "trading_engine"
    / "paper_order_submission_dry_run"
)
REQUIRED_SUBMISSION_TEXT = "SIMULATE PAPER ORDER SUBMISSION"


@dataclass(frozen=True)
class PaperOrderSubmissionDryRunPolicy:
    required_source_version: str = "V13.4"
    required_source_status: str = "VALIDATED"
    required_confirmation_text: str = REQUIRED_SUBMISSION_TEXT
    simulation_mode: str = "NO_TRANSMIT"
    expected_outcome: str = "WOULD_SUBMIT"
    require_same_operator: bool = True
    require_transmit_false: bool = True
    require_unique_order_ids: bool = True
    dns_lookup_disabled: bool = True
    socket_creation_disabled: bool = True
    http_request_disabled: bool = True
    network_access_disabled: bool = True
    account_access_disabled: bool = True
    broker_api_disabled: bool = True
    broker_order_creation_disabled: bool = True
    order_submission_disabled: bool = True
    live_execution_disabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PaperSubmissionDryRunReceipt:
    receipt_id: str
    client_order_id: str
    instrument: str
    side: str
    order_kind: str
    quantity: int
    simulation_outcome: str
    source_order_hash: str
    request_serialized: bool
    transmit: bool
    broker_order_id: str | None
    submitted: bool
    receipt_hash: str

    def payload_without_hash(self) -> dict[str, Any]:
        payload = asdict(self)
        payload.pop("receipt_hash", None)
        return payload

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PaperOrderSubmissionDryRunBatch:
    dry_run_batch_id: str
    created_at: str
    dry_run_status: str
    simulation_mode: str
    translation_batch_id: str
    translation_batch_hash: str
    operator: str
    receipt_count: int
    receipts: tuple[PaperSubmissionDryRunReceipt, ...]
    dns_lookup_performed: bool
    socket_created: bool
    http_request_sent: bool
    network_accessed: bool
    account_accessed: bool
    broker_api_called: bool
    broker_order_created: bool
    order_submitted: bool
    live_execution_authorized: bool
    batch_hash: str

    def payload_without_hash(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["receipts"] = [item.to_dict() for item in self.receipts]
        payload.pop("batch_hash", None)
        return payload

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["receipts"] = [item.to_dict() for item in self.receipts]
        return payload


@dataclass
class PaperOrderSubmissionDryRunResult:
    version: str
    created_at: str
    submission_result_id: str
    result_status: str
    result_status_label: str
    dry_run_batch_id: str | None
    batch_hash: str | None
    receipt_count: int
    policy_checks_passed: bool
    input_checks_passed: bool
    source_checks_passed: bool
    receipt_checks_passed: bool
    batch_hash_checks_passed: bool
    safety_checks_passed: bool
    all_checks_passed: bool
    submission_dry_run_completed: bool
    paper_execution_authorized: bool
    automatic_execution_authorized: bool
    execution_blocked: bool
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
    submission_policy: PaperOrderSubmissionDryRunPolicy
    batch: PaperOrderSubmissionDryRunBatch | None
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)
    report_path: str | None = None
    latest_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["submission_policy"] = self.submission_policy.to_dict()
        payload["batch"] = self.batch.to_dict() if self.batch else None
        return payload


def canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )


def sha256_payload(payload: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def validate_policy(policy: PaperOrderSubmissionDryRunPolicy) -> list[str]:
    errors: list[str] = []
    if policy.required_source_version != "V13.4":
        errors.append("Source Version은 V13.4여야 합니다.")
    if policy.simulation_mode != "NO_TRANSMIT":
        errors.append("Simulation Mode는 NO_TRANSMIT이어야 합니다.")
    if policy.expected_outcome != "WOULD_SUBMIT":
        errors.append("Expected Outcome이 안전 기준과 다릅니다.")
    safety = (
        policy.require_transmit_false and policy.dns_lookup_disabled
        and policy.socket_creation_disabled and policy.http_request_disabled
        and policy.network_access_disabled and policy.account_access_disabled
        and policy.broker_api_disabled
        and policy.broker_order_creation_disabled
        and policy.order_submission_disabled and policy.live_execution_disabled
    )
    if not safety:
        errors.append("모든 통신 및 제출 차단 정책이 필요합니다.")
    return errors


def validate_source(
    source: PaperOrderTranslationResult,
    operator: str,
    policy: PaperOrderSubmissionDryRunPolicy,
) -> tuple[PaperOrderTranslationBatch | None, list[str]]:
    errors: list[str] = []
    if not isinstance(source, PaperOrderTranslationResult):
        return None, ["V13.4 Translation Result 형식이 아닙니다."]
    if source.version != policy.required_source_version:
        errors.append("V13.4 Source가 아닙니다.")
    if source.result_status != policy.required_source_status:
        errors.append("VALIDATED Translation Source가 아닙니다.")
    batch = source.batch
    if batch is None:
        errors.append("Translation Batch가 없습니다.")
        return None, errors
    valid, verify_errors = verify_translation_batch(batch)
    if not valid:
        errors.extend(verify_errors)
    if not source.all_checks_passed or not source.translation_validated:
        errors.append("검증된 Translation Source가 아닙니다.")
    if source.broker_api_called or source.order_submitted:
        errors.append("실행 흔적이 있는 Source입니다.")
    if policy.require_same_operator and batch.operator != operator:
        errors.append("Operator가 Source와 일치하지 않습니다.")
    return batch, errors


def build_receipts(
    orders: tuple[TranslatedPaperOrder, ...],
    policy: PaperOrderSubmissionDryRunPolicy,
) -> tuple[tuple[PaperSubmissionDryRunReceipt, ...], list[str]]:
    receipts: list[PaperSubmissionDryRunReceipt] = []
    errors: list[str] = []
    seen: set[str] = set()
    for order in orders:
        if order.client_order_id in seen:
            errors.append("중복 Client Order ID가 있습니다.")
            continue
        seen.add(order.client_order_id)
        if policy.require_transmit_false and order.transmit:
            errors.append(f"{order.client_order_id}: transmit=True가 차단되었습니다.")
            continue
        if order.quantity <= 0:
            errors.append(f"{order.client_order_id}: Quantity가 올바르지 않습니다.")
            continue
        draft = PaperSubmissionDryRunReceipt(
            receipt_id=str(uuid.uuid4()),
            client_order_id=order.client_order_id,
            instrument=order.instrument,
            side=order.side,
            order_kind=order.order_kind,
            quantity=order.quantity,
            simulation_outcome=policy.expected_outcome,
            source_order_hash=sha256_payload(order.to_dict()),
            request_serialized=True,
            transmit=False,
            broker_order_id=None,
            submitted=False,
            receipt_hash="",
        )
        receipts.append(
            PaperSubmissionDryRunReceipt(
                **{
                    **asdict(draft),
                    "receipt_hash": sha256_payload(draft.payload_without_hash()),
                }
            )
        )
    if not receipts:
        errors.append("Dry-Run Receipt가 생성되지 않았습니다.")
    return tuple(receipts), errors


def verify_submission_dry_run_batch(
    batch: PaperOrderSubmissionDryRunBatch,
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if batch.dry_run_status != "SIMULATED":
        errors.append("Dry-Run Batch가 SIMULATED 상태가 아닙니다.")
    if batch.simulation_mode != "NO_TRANSMIT":
        errors.append("Simulation Mode가 안전하지 않습니다.")
    if batch.receipt_count != len(batch.receipts) or not batch.receipts:
        errors.append("Receipt Count가 일치하지 않습니다.")
    for receipt in batch.receipts:
        if receipt.transmit or receipt.submitted or receipt.broker_order_id:
            errors.append("실행 흔적이 있는 Receipt가 있습니다.")
        if receipt.simulation_outcome != "WOULD_SUBMIT":
            errors.append("Receipt Outcome이 올바르지 않습니다.")
        if receipt.receipt_hash != sha256_payload(receipt.payload_without_hash()):
            errors.append("Receipt Hash가 일치하지 않습니다.")
    if any(
        (
            batch.dns_lookup_performed, batch.socket_created,
            batch.http_request_sent, batch.network_accessed,
            batch.account_accessed, batch.broker_api_called,
            batch.broker_order_created, batch.order_submitted,
            batch.live_execution_authorized,
        )
    ):
        errors.append("Batch에 통신 또는 실행 흔적이 있습니다.")
    if batch.batch_hash != sha256_payload(batch.payload_without_hash()):
        errors.append("Dry-Run Batch Hash가 일치하지 않습니다.")
    return not errors, errors


def simulate_paper_order_submission(
    source: PaperOrderTranslationResult,
    operator: str,
    confirmation_text: str,
    policy: PaperOrderSubmissionDryRunPolicy | None = None,
    now: datetime | None = None,
) -> PaperOrderSubmissionDryRunResult:
    policy = policy or PaperOrderSubmissionDryRunPolicy()
    now = now or datetime.now().astimezone()
    created_at = now.isoformat()
    policy_errors = validate_policy(policy)
    clean_operator = operator.strip() if isinstance(operator, str) else ""
    input_errors: list[str] = []
    if not clean_operator:
        input_errors.append("Operator가 필요합니다.")
    if confirmation_text != policy.required_confirmation_text:
        input_errors.append("확인 문구가 일치하지 않습니다.")
    translation, source_errors = validate_source(source, clean_operator, policy)
    receipts: tuple[PaperSubmissionDryRunReceipt, ...] = ()
    receipt_errors: list[str] = []
    if translation and not source_errors:
        receipts, receipt_errors = build_receipts(translation.orders, policy)
    batch: PaperOrderSubmissionDryRunBatch | None = None
    hash_ok = False
    all_errors = policy_errors + input_errors + source_errors + receipt_errors
    if not all_errors and translation:
        draft = PaperOrderSubmissionDryRunBatch(
            dry_run_batch_id=str(uuid.uuid4()),
            created_at=created_at,
            dry_run_status="SIMULATED",
            simulation_mode=policy.simulation_mode,
            translation_batch_id=translation.translation_batch_id,
            translation_batch_hash=translation.batch_hash,
            operator=clean_operator,
            receipt_count=len(receipts),
            receipts=receipts,
            dns_lookup_performed=False,
            socket_created=False,
            http_request_sent=False,
            network_accessed=False,
            account_accessed=False,
            broker_api_called=False,
            broker_order_created=False,
            order_submitted=False,
            live_execution_authorized=False,
            batch_hash="",
        )
        batch = PaperOrderSubmissionDryRunBatch(
            **{
                **asdict(draft), "receipts": draft.receipts,
                "batch_hash": sha256_payload(draft.payload_without_hash()),
            }
        )
        hash_ok, hash_errors = verify_submission_dry_run_batch(batch)
        all_errors.extend(hash_errors)
    safety_ok = not validate_policy(policy)
    source_ok = not source_errors
    passed = (
        not policy_errors and not input_errors and source_ok
        and bool(receipts) and not receipt_errors
        and hash_ok and safety_ok and not all_errors
    )
    status = "SIMULATED" if passed else ("BLOCKED" if source_ok else "FAILED")
    return PaperOrderSubmissionDryRunResult(
        version="V13.5", created_at=created_at,
        submission_result_id=str(uuid.uuid4()), result_status=status,
        result_status_label={
            "SIMULATED": "Paper 제출 Dry-Run 완료",
            "BLOCKED": "제출 Dry-Run 입력 차단",
            "FAILED": "Source 검증 실패",
        }[status],
        dry_run_batch_id=batch.dry_run_batch_id if batch else None,
        batch_hash=batch.batch_hash if batch else None,
        receipt_count=len(receipts),
        policy_checks_passed=not policy_errors,
        input_checks_passed=not input_errors,
        source_checks_passed=source_ok,
        receipt_checks_passed=bool(receipts) and not receipt_errors,
        batch_hash_checks_passed=hash_ok,
        safety_checks_passed=safety_ok,
        all_checks_passed=passed,
        submission_dry_run_completed=passed,
        paper_execution_authorized=False,
        automatic_execution_authorized=False,
        execution_blocked=True,
        dns_lookup_performed=False, socket_created=False,
        http_request_sent=False, network_accessed=False,
        account_accessed=False, broker_api_called=False,
        broker_order_created=False, order_submitted=False,
        live_order_created=False, live_execution_authorized=False,
        submission_policy=policy, batch=batch,
        reasons=[
            "실제 전송 없이 Paper 주문 제출을 시뮬레이션했습니다."
            if passed else "Paper 주문 제출 Dry-Run이 차단되었습니다."
        ],
        warnings=all_errors + [
            "WOULD_SUBMIT은 모의 결과이며 실제 주문 성공을 의미하지 않습니다."
        ],
        next_actions=[
            "Receipt와 Hash를 수동 검토합니다.",
            "Broker API와 실제 계좌를 연결하지 않습니다.",
        ],
    )


def save_submission_dry_run_result(
    result: PaperOrderSubmissionDryRunResult,
    directory: Path | None = None,
) -> tuple[Path, Path]:
    directory = directory or OUTPUT_DIRECTORY
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S_%f")
    report = directory / f"paper_submission_dry_run_{stamp}.json"
    latest = directory / "latest_paper_submission_dry_run.json"
    payload = result.to_dict()
    for path in (report, latest):
        temp = path.with_suffix(path.suffix + ".tmp")
        temp.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        temp.replace(path)
    result.report_path = str(report)
    result.latest_path = str(latest)
    return report, latest


def load_submission_dry_run_result(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("version") != "V13.5":
        raise ValueError("V13.5 결과 파일이 아닙니다.")
    batch = payload.get("batch")
    if batch:
        saved_hash = batch.get("batch_hash")
        hash_payload = dict(batch)
        hash_payload.pop("batch_hash", None)
        if saved_hash != sha256_payload(hash_payload):
            raise ValueError("저장된 Submission Dry-Run Batch가 변조되었습니다.")
    return payload
