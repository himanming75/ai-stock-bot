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
    verify_translation_batch,
)
from backtest.paper_order_submission_dry_run import (
    PaperOrderSubmissionDryRunBatch,
    PaperOrderSubmissionDryRunResult,
    verify_submission_dry_run_batch,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIRECTORY = (
    PROJECT_ROOT / "output" / "trading_engine"
    / "paper_submission_reconciliation"
)
REQUIRED_RECONCILIATION_TEXT = "RECONCILE PAPER SUBMISSION DRY RUN"


@dataclass(frozen=True)
class PaperSubmissionReconciliationPolicy:
    required_translation_version: str = "V13.4"
    required_translation_status: str = "VALIDATED"
    required_submission_version: str = "V13.5"
    required_submission_status: str = "SIMULATED"
    required_confirmation_text: str = REQUIRED_RECONCILIATION_TEXT
    require_same_operator: bool = True
    require_linked_batch: bool = True
    require_unique_order_ids: bool = True
    require_exact_item_count: bool = True
    require_would_submit: bool = True
    network_access_disabled: bool = True
    broker_api_disabled: bool = True
    order_submission_disabled: bool = True
    live_execution_disabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ReconciliationItem:
    client_order_id: str
    translation_found: bool
    receipt_found: bool
    instrument_matched: bool
    side_matched: bool
    order_kind_matched: bool
    quantity_matched: bool
    source_hash_matched: bool
    safe_receipt_matched: bool
    reconciled: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PaperSubmissionReconciliationReport:
    reconciliation_id: str
    created_at: str
    reconciliation_status: str
    translation_batch_id: str
    translation_batch_hash: str
    submission_batch_id: str
    submission_batch_hash: str
    operator: str
    translation_count: int
    receipt_count: int
    reconciled_count: int
    items: tuple[ReconciliationItem, ...]
    network_accessed: bool
    broker_api_called: bool
    broker_order_created: bool
    order_submitted: bool
    live_execution_authorized: bool
    report_hash: str

    def payload_without_hash(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["items"] = [item.to_dict() for item in self.items]
        payload.pop("report_hash", None)
        return payload

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["items"] = [item.to_dict() for item in self.items]
        return payload


@dataclass
class PaperSubmissionReconciliationResult:
    version: str
    created_at: str
    reconciliation_result_id: str
    result_status: str
    result_status_label: str
    reconciliation_id: str | None
    report_hash: str | None
    translation_count: int
    receipt_count: int
    reconciled_count: int
    policy_checks_passed: bool
    input_checks_passed: bool
    translation_checks_passed: bool
    submission_checks_passed: bool
    linkage_checks_passed: bool
    item_checks_passed: bool
    report_hash_checks_passed: bool
    safety_checks_passed: bool
    all_checks_passed: bool
    reconciliation_completed: bool
    paper_execution_authorized: bool
    automatic_execution_authorized: bool
    execution_blocked: bool
    network_accessed: bool
    account_accessed: bool
    broker_api_called: bool
    broker_order_created: bool
    order_submitted: bool
    live_order_created: bool
    live_execution_authorized: bool
    reconciliation_policy: PaperSubmissionReconciliationPolicy
    report: PaperSubmissionReconciliationReport | None
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)
    report_path: str | None = None
    latest_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["reconciliation_policy"] = self.reconciliation_policy.to_dict()
        payload["report"] = self.report.to_dict() if self.report else None
        return payload


def canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )


def sha256_payload(payload: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def validate_policy(policy: PaperSubmissionReconciliationPolicy) -> list[str]:
    errors: list[str] = []
    if policy.required_translation_version != "V13.4":
        errors.append("Translation Version은 V13.4여야 합니다.")
    if policy.required_submission_version != "V13.5":
        errors.append("Submission Version은 V13.5여야 합니다.")
    if not (
        policy.require_linked_batch and policy.require_exact_item_count
        and policy.require_would_submit and policy.network_access_disabled
        and policy.broker_api_disabled and policy.order_submission_disabled
        and policy.live_execution_disabled
    ):
        errors.append("대조 또는 실행 차단 정책이 올바르지 않습니다.")
    return errors


def validate_sources(
    translation_source: PaperOrderTranslationResult,
    submission_source: PaperOrderSubmissionDryRunResult,
    operator: str,
    policy: PaperSubmissionReconciliationPolicy,
) -> tuple[
    PaperOrderTranslationBatch | None,
    PaperOrderSubmissionDryRunBatch | None,
    list[str],
    list[str],
    list[str],
]:
    translation_errors: list[str] = []
    submission_errors: list[str] = []
    linkage_errors: list[str] = []
    translation = translation_source.batch if isinstance(
        translation_source, PaperOrderTranslationResult
    ) else None
    submission = submission_source.batch if isinstance(
        submission_source, PaperOrderSubmissionDryRunResult
    ) else None
    if not isinstance(translation_source, PaperOrderTranslationResult):
        translation_errors.append("V13.4 Translation Result 형식이 아닙니다.")
    else:
        if translation_source.version != policy.required_translation_version:
            translation_errors.append("V13.4 Source가 아닙니다.")
        if translation_source.result_status != policy.required_translation_status:
            translation_errors.append("VALIDATED Translation이 아닙니다.")
        if translation is None:
            translation_errors.append("Translation Batch가 없습니다.")
        else:
            valid, errors = verify_translation_batch(translation)
            if not valid:
                translation_errors.extend(errors)
    if not isinstance(submission_source, PaperOrderSubmissionDryRunResult):
        submission_errors.append("V13.5 Submission Result 형식이 아닙니다.")
    else:
        if submission_source.version != policy.required_submission_version:
            submission_errors.append("V13.5 Source가 아닙니다.")
        if submission_source.result_status != policy.required_submission_status:
            submission_errors.append("SIMULATED Submission이 아닙니다.")
        if submission is None:
            submission_errors.append("Submission Batch가 없습니다.")
        else:
            valid, errors = verify_submission_dry_run_batch(submission)
            if not valid:
                submission_errors.extend(errors)
    if translation and submission:
        if submission.translation_batch_id != translation.translation_batch_id:
            linkage_errors.append("Translation Batch ID 연결이 다릅니다.")
        if submission.translation_batch_hash != translation.batch_hash:
            linkage_errors.append("Translation Batch Hash 연결이 다릅니다.")
        if policy.require_same_operator and not (
            translation.operator == submission.operator == operator
        ):
            linkage_errors.append("Operator 연결이 일치하지 않습니다.")
    return (
        translation, submission,
        translation_errors, submission_errors, linkage_errors,
    )


def reconcile_items(
    translation: PaperOrderTranslationBatch,
    submission: PaperOrderSubmissionDryRunBatch,
) -> tuple[tuple[ReconciliationItem, ...], list[str]]:
    errors: list[str] = []
    order_map = {order.client_order_id: order for order in translation.orders}
    receipt_map = {
        receipt.client_order_id: receipt for receipt in submission.receipts
    }
    if len(order_map) != len(translation.orders):
        errors.append("중복 Translation Order ID가 있습니다.")
    if len(receipt_map) != len(submission.receipts):
        errors.append("중복 Receipt Order ID가 있습니다.")
    all_ids = sorted(set(order_map) | set(receipt_map))
    items: list[ReconciliationItem] = []
    for client_id in all_ids:
        order = order_map.get(client_id)
        receipt = receipt_map.get(client_id)
        found_order = order is not None
        found_receipt = receipt is not None
        instrument = bool(order and receipt and order.instrument == receipt.instrument)
        side = bool(order and receipt and order.side == receipt.side)
        kind = bool(order and receipt and order.order_kind == receipt.order_kind)
        quantity = bool(order and receipt and order.quantity == receipt.quantity)
        source_hash = bool(
            order and receipt
            and receipt.source_order_hash == sha256_payload(order.to_dict())
        )
        safe = bool(
            receipt
            and receipt.simulation_outcome == "WOULD_SUBMIT"
            and not receipt.transmit and not receipt.submitted
            and receipt.broker_order_id is None
        )
        reconciled = all(
            (found_order, found_receipt, instrument, side, kind, quantity,
             source_hash, safe)
        )
        items.append(
            ReconciliationItem(
                client_id, found_order, found_receipt, instrument, side,
                kind, quantity, source_hash, safe, reconciled,
            )
        )
        if not reconciled:
            errors.append(f"{client_id}: Translation과 Receipt가 일치하지 않습니다.")
    if len(translation.orders) != len(submission.receipts):
        errors.append("Translation과 Receipt 개수가 다릅니다.")
    return tuple(items), errors


def verify_reconciliation_report(
    report: PaperSubmissionReconciliationReport,
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if report.reconciliation_status != "RECONCILED":
        errors.append("Report가 RECONCILED 상태가 아닙니다.")
    if not report.items or not all(item.reconciled for item in report.items):
        errors.append("대조되지 않은 Item이 있습니다.")
    if not (
        report.translation_count == report.receipt_count
        == report.reconciled_count == len(report.items)
    ):
        errors.append("대조 Count가 일치하지 않습니다.")
    if any((
        report.network_accessed, report.broker_api_called,
        report.broker_order_created, report.order_submitted,
        report.live_execution_authorized,
    )):
        errors.append("Report에 연결 또는 실행 흔적이 있습니다.")
    if report.report_hash != sha256_payload(report.payload_without_hash()):
        errors.append("Reconciliation Report Hash가 일치하지 않습니다.")
    return not errors, errors


def reconcile_paper_submission(
    translation_source: PaperOrderTranslationResult,
    submission_source: PaperOrderSubmissionDryRunResult,
    operator: str,
    confirmation_text: str,
    policy: PaperSubmissionReconciliationPolicy | None = None,
    now: datetime | None = None,
) -> PaperSubmissionReconciliationResult:
    policy = policy or PaperSubmissionReconciliationPolicy()
    now = now or datetime.now().astimezone()
    created_at = now.isoformat()
    policy_errors = validate_policy(policy)
    clean_operator = operator.strip() if isinstance(operator, str) else ""
    input_errors: list[str] = []
    if not clean_operator:
        input_errors.append("Operator가 필요합니다.")
    if confirmation_text != policy.required_confirmation_text:
        input_errors.append("확인 문구가 일치하지 않습니다.")
    (
        translation, submission, translation_errors,
        submission_errors, linkage_errors,
    ) = validate_sources(
        translation_source, submission_source, clean_operator, policy
    )
    items: tuple[ReconciliationItem, ...] = ()
    item_errors: list[str] = []
    if (
        translation and submission and not translation_errors
        and not submission_errors and not linkage_errors
    ):
        items, item_errors = reconcile_items(translation, submission)
    report: PaperSubmissionReconciliationReport | None = None
    hash_ok = False
    all_errors = (
        policy_errors + input_errors + translation_errors
        + submission_errors + linkage_errors + item_errors
    )
    if not all_errors and translation and submission:
        draft = PaperSubmissionReconciliationReport(
            reconciliation_id=str(uuid.uuid4()),
            created_at=created_at,
            reconciliation_status="RECONCILED",
            translation_batch_id=translation.translation_batch_id,
            translation_batch_hash=translation.batch_hash,
            submission_batch_id=submission.dry_run_batch_id,
            submission_batch_hash=submission.batch_hash,
            operator=clean_operator,
            translation_count=len(translation.orders),
            receipt_count=len(submission.receipts),
            reconciled_count=sum(item.reconciled for item in items),
            items=items,
            network_accessed=False,
            broker_api_called=False,
            broker_order_created=False,
            order_submitted=False,
            live_execution_authorized=False,
            report_hash="",
        )
        report = PaperSubmissionReconciliationReport(
            **{
                **asdict(draft), "items": draft.items,
                "report_hash": sha256_payload(draft.payload_without_hash()),
            }
        )
        hash_ok, hash_errors = verify_reconciliation_report(report)
        all_errors.extend(hash_errors)
    sources_ok = not translation_errors and not submission_errors
    safety_ok = not validate_policy(policy)
    passed = (
        not policy_errors and not input_errors and sources_ok
        and not linkage_errors and bool(items) and not item_errors
        and hash_ok and safety_ok and not all_errors
    )
    status = "RECONCILED" if passed else (
        "BLOCKED" if sources_ok else "FAILED"
    )
    return PaperSubmissionReconciliationResult(
        version="V13.6", created_at=created_at,
        reconciliation_result_id=str(uuid.uuid4()), result_status=status,
        result_status_label={
            "RECONCILED": "Paper Submission 대조 완료",
            "BLOCKED": "연결 또는 Item 대조 차단",
            "FAILED": "Source 검증 실패",
        }[status],
        reconciliation_id=report.reconciliation_id if report else None,
        report_hash=report.report_hash if report else None,
        translation_count=len(translation.orders) if translation else 0,
        receipt_count=len(submission.receipts) if submission else 0,
        reconciled_count=sum(item.reconciled for item in items),
        policy_checks_passed=not policy_errors,
        input_checks_passed=not input_errors,
        translation_checks_passed=not translation_errors,
        submission_checks_passed=not submission_errors,
        linkage_checks_passed=not linkage_errors,
        item_checks_passed=bool(items) and not item_errors,
        report_hash_checks_passed=hash_ok,
        safety_checks_passed=safety_ok,
        all_checks_passed=passed,
        reconciliation_completed=passed,
        paper_execution_authorized=False,
        automatic_execution_authorized=False,
        execution_blocked=True,
        network_accessed=False, account_accessed=False,
        broker_api_called=False, broker_order_created=False,
        order_submitted=False, live_order_created=False,
        live_execution_authorized=False,
        reconciliation_policy=policy, report=report,
        reasons=[
            "Translation 주문과 Dry-Run Receipt를 1대1 대조했습니다."
            if passed else "Paper Submission Reconciliation이 차단되었습니다."
        ],
        warnings=all_errors + [
            "Reconciliation은 기록 검증이며 실제 주문을 생성하지 않습니다."
        ],
        next_actions=[
            "불일치와 Report Hash를 수동 검토합니다.",
            "Broker API 또는 실제 계좌를 연결하지 않습니다.",
        ],
    )


def save_reconciliation_result(
    result: PaperSubmissionReconciliationResult,
    directory: Path | None = None,
) -> tuple[Path, Path]:
    directory = directory or OUTPUT_DIRECTORY
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S_%f")
    report = directory / f"paper_submission_reconciliation_{stamp}.json"
    latest = directory / "latest_paper_submission_reconciliation.json"
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


def load_reconciliation_result(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("version") != "V13.6":
        raise ValueError("V13.6 결과 파일이 아닙니다.")
    report = payload.get("report")
    if report:
        saved_hash = report.get("report_hash")
        hash_payload = dict(report)
        hash_payload.pop("report_hash", None)
        if saved_hash != sha256_payload(hash_payload):
            raise ValueError("저장된 Reconciliation Report가 변조되었습니다.")
    return payload
