import contextlib
import copy
import io
import tempfile
from dataclasses import replace
from pathlib import Path
from typing import Any

from backtest.paper_submission_reconciliation import (
    PaperSubmissionReconciliationPolicy,
    load_reconciliation_result,
    reconcile_paper_submission,
    save_reconciliation_result,
    verify_reconciliation_report,
)
from backtest.paper_order_submission_dry_run import (
    simulate_paper_order_submission,
)
from test_paper_order_submission_dry_run import create_source


def silent(function: Any, *args: Any, **kwargs: Any) -> Any:
    with contextlib.redirect_stdout(io.StringIO()):
        return function(*args, **kwargs)


def create_sources() -> tuple[Any, Any]:
    translation = create_source()
    submission = silent(
        simulate_paper_order_submission,
        translation, translation.batch.operator,
        "SIMULATE PAPER ORDER SUBMISSION",
    )
    return translation, submission


def build(translation: Any, submission: Any, operator: str | None = None, text: str = "RECONCILE PAPER SUBMISSION DRY RUN", policy: Any = None) -> Any:
    actual = operator or translation.batch.operator
    return silent(
        reconcile_paper_submission,
        translation, submission, actual, text, policy,
    )


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def require_safe(result: Any) -> None:
    require(all((
        not result.paper_execution_authorized,
        not result.automatic_execution_authorized,
        result.execution_blocked,
        not result.network_accessed,
        not result.account_accessed,
        not result.broker_api_called,
        not result.broker_order_created,
        not result.order_submitted,
        not result.live_order_created,
        not result.live_execution_authorized,
    )), "실행 안전장치가 해제되었습니다.")


def main() -> None:
    translation, submission = create_sources()
    reconciled = build(translation, submission)
    require(reconciled.result_status == "RECONCILED", "정상 대조가 실패했습니다.")
    require(reconciled.reconciled_count == 2, "두 항목이 대조되지 않았습니다.")
    require(reconciled.report is not None, "Reconciliation Report가 없습니다.")
    valid, errors = verify_reconciliation_report(reconciled.report)
    require(valid and not errors, "Report Hash 검사가 실패했습니다.")
    require_safe(reconciled)

    wrong_operator = build(translation, submission, operator="wrong")
    require(wrong_operator.result_status == "BLOCKED", "잘못된 Operator가 차단되지 않았습니다.")
    wrong_text = build(translation, submission, text="IGNORE")
    require(wrong_text.result_status == "BLOCKED", "잘못된 확인 문구가 차단되지 않았습니다.")
    unsafe_policy = PaperSubmissionReconciliationPolicy(order_submission_disabled=False)
    unsafe = build(translation, submission, policy=unsafe_policy)
    require(not unsafe.all_checks_passed, "위험 Policy가 차단되지 않았습니다.")

    missing_submission = copy.deepcopy(submission)
    object.__setattr__(
        missing_submission.batch, "receipts",
        missing_submission.batch.receipts[:-1],
    )
    missing = build(translation, missing_submission)
    require(missing.result_status == "FAILED", "누락 Receipt가 실패 처리되지 않았습니다.")

    mismatch_submission = copy.deepcopy(submission)
    changed_receipt = replace(
        mismatch_submission.batch.receipts[0], quantity=999
    )
    object.__setattr__(
        mismatch_submission.batch, "receipts",
        (changed_receipt, *mismatch_submission.batch.receipts[1:]),
    )
    mismatch = build(translation, mismatch_submission)
    require(mismatch.result_status == "FAILED", "불일치 Receipt가 실패 처리되지 않았습니다.")

    changed_report = replace(reconciled.report, reconciled_count=0)
    valid_after_tamper, tamper_errors = verify_reconciliation_report(changed_report)
    require(not valid_after_tamper and tamper_errors, "Report 변조가 탐지되지 않았습니다.")

    with tempfile.TemporaryDirectory() as directory:
        report, latest = save_reconciliation_result(
            reconciled, Path(directory)
        )
        require(report.exists() and latest.exists(), "결과가 저장되지 않았습니다.")
        payload = load_reconciliation_result(latest)
        require(payload["version"] == "V13.6", "저장 Version이 다릅니다.")

    for result in (
        reconciled, wrong_operator, wrong_text, unsafe, missing, mismatch
    ):
        require_safe(result)

    checks = {
        "Version is V13.6": reconciled.version == "V13.6",
        "Default policy is valid": reconciled.policy_checks_passed,
        "Policy is immutable": PaperSubmissionReconciliationPolicy.__dataclass_params__.frozen,
        "Invalid policies are blocked": not unsafe.all_checks_passed,
        "Reconciliation was completed": reconciled.reconciliation_completed,
        "Two translations were loaded": reconciled.translation_count == 2,
        "Two receipts were loaded": reconciled.receipt_count == 2,
        "Two items were reconciled": reconciled.reconciled_count == 2,
        "All fields and hashes matched": all(x.reconciled for x in reconciled.report.items),
        "Report hash passed": reconciled.report_hash_checks_passed,
        "Wrong operator was blocked": wrong_operator.result_status == "BLOCKED",
        "Wrong confirmation was blocked": wrong_text.result_status == "BLOCKED",
        "Missing receipt failed": missing.result_status == "FAILED",
        "Mismatched receipt failed": mismatch.result_status == "FAILED",
        "Report tampering detected": not valid_after_tamper,
        "Result save and load passed": payload["version"] == "V13.6",
        "Broker API was not called": not reconciled.broker_api_called,
        "Broker order was not created": not reconciled.broker_order_created,
        "Order was not submitted": not reconciled.order_submitted,
        "Live execution not authorized": not reconciled.live_execution_authorized,
    }
    checks["All checks passed"] = all(checks.values())
    print("=" * 92)
    print("AI STOCK BOT V13.6 PAPER SUBMISSION RECONCILIATION TEST")
    print("=" * 92)
    print("V13.6 VALIDATION CHECKS")
    print("-" * 92)
    for name, passed in checks.items():
        print(f"{name:<58}: {passed}")
    print("=" * 92)
    require(checks["All checks passed"], "V13.6 Validation Check가 실패했습니다.")
    print()
    print("V13.6 paper submission reconciliation test completed successfully.")
    print("Translation과 Receipt 1대1 대조, Hash 연결 및 변조 차단이 검증되었습니다.")
    print("Broker API, 실제 주문 및 Live Execution은 호출되지 않았습니다.")


if __name__ == "__main__":
    main()
