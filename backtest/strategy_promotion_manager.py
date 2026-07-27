import json
import shutil
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent

RECOMMENDATION_DIRECTORY = (
    PROJECT_ROOT
    / "output"
    / "strategy_backtests"
    / "final_candidate_recommendation"
)

PROMOTION_DIRECTORY = (
    PROJECT_ROOT
    / "output"
    / "strategy_management"
    / "promotions"
)

ACTIVE_STRATEGY_DIRECTORY = (
    PROJECT_ROOT
    / "output"
    / "strategy_management"
    / "active"
)

PAPER_STRATEGY_DIRECTORY = (
    PROJECT_ROOT
    / "output"
    / "strategy_management"
    / "paper_trading"
)

RESEARCH_ARCHIVE_DIRECTORY = (
    PROJECT_ROOT
    / "output"
    / "strategy_management"
    / "research_archive"
)

HISTORY_DIRECTORY = (
    PROJECT_ROOT
    / "output"
    / "strategy_management"
    / "history"
)


VALID_SOURCE_DECISIONS = {
    "APPLY_CANDIDATE",
    "PAPER_TRADE_CANDIDATE",
    "KEEP_BASELINE",
    "RESEARCH_ONLY",
    "NO_DECISION",
}

VALID_PROMOTION_STATUSES = {
    "PROMOTED",
    "PAPER_TRADING",
    "BASELINE_RETAINED",
    "RESEARCH_ARCHIVED",
    "NO_ACTION",
    "FAILED",
}


@dataclass
class StrategyPromotionResult:
    """
    V8.5 전략 승격 관리 결과입니다.
    """

    version: str
    symbol: str

    created_at: str
    source_file: str

    source_decision: str
    source_decision_label: str

    promotion_status: str
    promotion_label: str

    action_performed: bool
    baseline_retained: bool
    candidate_promoted: bool
    candidate_paper_trading: bool
    candidate_archived: bool

    selected_candidate_number: int | None
    selected_candidate_name: str | None
    selected_candidate_type: str | None

    candidate_score: float
    baseline_score: float
    score_improvement: float

    confidence_score: float
    confidence_level: str

    risk_score: float
    risk_level: str

    recommendation_strength: int

    entry_score: float | None
    exit_score: float | None
    stop_atr_multiple: float | None
    target_atr_multiple: float | None
    maximum_holding_days: int | None
    position_percent: float | None

    previous_active_strategy_file: str | None
    strategy_output_file: str | None
    history_file: str | None

    reasons: list[str]
    warnings: list[str]
    next_actions: list[str]

    report_path: str | None = None
    latest_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def normalize_symbol(symbol: str) -> str:
    """
    종목 코드를 대문자로 정규화합니다.
    """

    normalized = symbol.strip().upper()

    if not normalized:
        raise ValueError(
            "symbol이 비어 있습니다."
        )

    return normalized


def safe_float(
    value: Any,
    default: float = 0.0,
) -> float:
    """
    값을 안전하게 float로 변환합니다.
    """

    try:
        if value is None:
            return default

        return float(value)

    except (
        TypeError,
        ValueError,
    ):
        return default


def safe_int(
    value: Any,
    default: int = 0,
) -> int:
    """
    값을 안전하게 int로 변환합니다.
    """

    try:
        if value is None:
            return default

        return int(value)

    except (
        TypeError,
        ValueError,
    ):
        return default


def safe_bool(
    value: Any,
    default: bool = False,
) -> bool:
    """
    값을 안전하게 bool로 변환합니다.
    """

    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        normalized = value.strip().lower()

        if normalized in {
            "true",
            "yes",
            "1",
        }:
            return True

        if normalized in {
            "false",
            "no",
            "0",
        }:
            return False

    if isinstance(
        value,
        (
            int,
            float,
        ),
    ):
        return bool(value)

    return default


def load_json_file(
    file_path: Path,
) -> dict[str, Any]:
    """
    JSON 파일을 읽습니다.
    """

    if not file_path.exists():
        raise FileNotFoundError(
            f"JSON 파일이 없습니다: {file_path}"
        )

    with file_path.open(
        mode="r",
        encoding="utf-8",
    ) as file:
        payload = json.load(file)

    if not isinstance(payload, dict):
        raise ValueError(
            "JSON 최상위 데이터가 Dictionary가 아닙니다."
        )

    return payload


def write_json_file(
    file_path: Path,
    payload: dict[str, Any],
) -> None:
    """
    JSON 파일을 안전하게 저장합니다.
    """

    file_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_path = file_path.with_suffix(
        file_path.suffix + ".tmp"
    )

    with temporary_path.open(
        mode="w",
        encoding="utf-8",
    ) as file:
        json.dump(
            payload,
            file,
            ensure_ascii=False,
            indent=2,
            default=str,
        )

    temporary_path.replace(
        file_path
    )


def find_latest_recommendation_file(
    symbol: str,
) -> Path:
    """
    V8.4 최신 추천 결과 파일을 찾습니다.
    """

    normalized_symbol = normalize_symbol(
        symbol
    )

    expected_path = (
        RECOMMENDATION_DIRECTORY
        / (
            f"{normalized_symbol}_"
            "final_candidate_recommendation_latest.json"
        )
    )

    if expected_path.exists():
        return expected_path

    if not RECOMMENDATION_DIRECTORY.exists():
        raise FileNotFoundError(
            "V8.4 추천 결과 폴더가 없습니다: "
            f"{RECOMMENDATION_DIRECTORY}"
        )

    matching_files = [
        path
        for path in RECOMMENDATION_DIRECTORY.glob(
            f"{normalized_symbol}_"
            "final_candidate_recommendation_*.json"
        )
        if "latest" not in path.name.lower()
    ]

    if not matching_files:
        raise FileNotFoundError(
            f"{normalized_symbol} V8.4 추천 결과를 "
            "찾을 수 없습니다."
        )

    return max(
        matching_files,
        key=lambda path: path.stat().st_mtime,
    )


def validate_recommendation_payload(
    payload: dict[str, Any],
) -> None:
    """
    V8.4 추천 데이터의 필수 구조를 검사합니다.
    """

    required_keys = {
        "version",
        "symbol",
        "decision",
        "decision_label",
        "confidence_score",
        "confidence_level",
        "risk_score",
        "risk_level",
        "baseline_score",
        "selected_candidate_score",
        "score_improvement",
        "selected_candidate_number",
        "selected_candidate_name",
        "selected_candidate_type",
        "recommendation_strength",
        "entry_score",
        "exit_score",
        "stop_atr_multiple",
        "target_atr_multiple",
        "maximum_holding_days",
        "position_percent",
        "passed_all_checks",
    }

    missing_keys = (
        required_keys
        - set(payload.keys())
    )

    if missing_keys:
        raise ValueError(
            "V8.4 추천 데이터에 필수 키가 없습니다: "
            f"{sorted(missing_keys)}"
        )

    version = str(
        payload.get(
            "version",
            "",
        )
    ).upper()

    if version != "V8.4":
        raise ValueError(
            f"V8.4 추천 파일이 아닙니다: {version}"
        )

    decision = str(
        payload.get(
            "decision",
            "",
        )
    ).upper()

    if decision not in VALID_SOURCE_DECISIONS:
        raise ValueError(
            f"올바르지 않은 V8.4 Decision입니다: "
            f"{decision}"
        )


def determine_promotion_status(
    decision: str,
) -> tuple[str, str]:
    """
    V8.4 결정을 V8.5 전략 관리 상태로 변환합니다.
    """

    normalized = decision.strip().upper()

    mapping = {
        "APPLY_CANDIDATE": (
            "PROMOTED",
            "후보 전략 승격",
        ),
        "PAPER_TRADE_CANDIDATE": (
            "PAPER_TRADING",
            "모의투자 전략 등록",
        ),
        "KEEP_BASELINE": (
            "BASELINE_RETAINED",
            "기존 전략 유지",
        ),
        "RESEARCH_ONLY": (
            "RESEARCH_ARCHIVED",
            "연구 후보 보관",
        ),
        "NO_DECISION": (
            "NO_ACTION",
            "변경 없음",
        ),
    }

    return mapping.get(
        normalized,
        (
            "NO_ACTION",
            "변경 없음",
        ),
    )


def build_strategy_payload(
    recommendation: dict[str, Any],
    strategy_status: str,
) -> dict[str, Any]:
    """
    운영·모의투자·연구용 전략 설정 데이터를 생성합니다.
    """

    return {
        "version": "V8.5",
        "symbol": normalize_symbol(
            str(
                recommendation.get(
                    "symbol",
                    "",
                )
            )
        ),
        "strategy_status": strategy_status,
        "created_at": datetime.now().isoformat(),
        "source_version": recommendation.get(
            "version"
        ),
        "source_decision": recommendation.get(
            "decision"
        ),
        "candidate": {
            "number": recommendation.get(
                "selected_candidate_number"
            ),
            "name": recommendation.get(
                "selected_candidate_name"
            ),
            "type": recommendation.get(
                "selected_candidate_type"
            ),
            "status": recommendation.get(
                "selected_candidate_status"
            ),
        },
        "parameters": {
            "entry_score": recommendation.get(
                "entry_score"
            ),
            "exit_score": recommendation.get(
                "exit_score"
            ),
            "stop_atr_multiple": recommendation.get(
                "stop_atr_multiple"
            ),
            "target_atr_multiple": recommendation.get(
                "target_atr_multiple"
            ),
            "maximum_holding_days": recommendation.get(
                "maximum_holding_days"
            ),
            "position_percent": recommendation.get(
                "position_percent"
            ),
        },
        "evaluation": {
            "candidate_score": recommendation.get(
                "selected_candidate_score"
            ),
            "baseline_score": recommendation.get(
                "baseline_score"
            ),
            "score_improvement": recommendation.get(
                "score_improvement"
            ),
            "confidence_score": recommendation.get(
                "confidence_score"
            ),
            "confidence_level": recommendation.get(
                "confidence_level"
            ),
            "risk_score": recommendation.get(
                "risk_score"
            ),
            "risk_level": recommendation.get(
                "risk_level"
            ),
            "recommendation_strength": (
                recommendation.get(
                    "recommendation_strength"
                )
            ),
            "passed_all_checks": recommendation.get(
                "passed_all_checks"
            ),
        },
        "source_file": recommendation.get(
            "source_file"
        ),
    }


def archive_existing_active_strategy(
    symbol: str,
) -> str | None:
    """
    기존 운영 전략이 있으면 이력 폴더에 백업합니다.
    """

    normalized_symbol = normalize_symbol(
        symbol
    )

    active_file = (
        ACTIVE_STRATEGY_DIRECTORY
        / f"{normalized_symbol}_active_strategy.json"
    )

    if not active_file.exists():
        return None

    HISTORY_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    history_file = (
        HISTORY_DIRECTORY
        / (
            f"{normalized_symbol}_"
            "active_strategy_backup_"
            f"{timestamp}.json"
        )
    )

    shutil.copy2(
        active_file,
        history_file,
    )

    return str(
        history_file
    )


def promote_candidate_strategy(
    symbol: str,
    recommendation: dict[str, Any],
) -> tuple[str, str | None]:
    """
    후보 전략을 운영 전략으로 승격합니다.
    """

    normalized_symbol = normalize_symbol(
        symbol
    )

    previous_backup = (
        archive_existing_active_strategy(
            normalized_symbol
        )
    )

    active_file = (
        ACTIVE_STRATEGY_DIRECTORY
        / f"{normalized_symbol}_active_strategy.json"
    )

    strategy_payload = build_strategy_payload(
        recommendation=recommendation,
        strategy_status="ACTIVE",
    )

    write_json_file(
        active_file,
        strategy_payload,
    )

    return (
        str(active_file),
        previous_backup,
    )


def register_paper_strategy(
    symbol: str,
    recommendation: dict[str, Any],
) -> str:
    """
    후보 전략을 모의투자 전략으로 등록합니다.
    """

    normalized_symbol = normalize_symbol(
        symbol
    )

    paper_file = (
        PAPER_STRATEGY_DIRECTORY
        / f"{normalized_symbol}_paper_strategy.json"
    )

    strategy_payload = build_strategy_payload(
        recommendation=recommendation,
        strategy_status="PAPER_TRADING",
    )

    write_json_file(
        paper_file,
        strategy_payload,
    )

    return str(
        paper_file
    )


def archive_research_candidate(
    symbol: str,
    recommendation: dict[str, Any],
) -> str:
    """
    후보 전략을 연구 기록으로 저장합니다.
    """

    normalized_symbol = normalize_symbol(
        symbol
    )

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    archive_file = (
        RESEARCH_ARCHIVE_DIRECTORY
        / (
            f"{normalized_symbol}_"
            "research_candidate_"
            f"{timestamp}.json"
        )
    )

    strategy_payload = build_strategy_payload(
        recommendation=recommendation,
        strategy_status="RESEARCH_ONLY",
    )

    write_json_file(
        archive_file,
        strategy_payload,
    )

    return str(
        archive_file
    )


def build_result_notes(
    decision: str,
    promotion_status: str,
    score_improvement: float,
) -> tuple[
    list[str],
    list[str],
    list[str],
]:
    """
    처리 이유, 경고 및 다음 작업을 생성합니다.
    """

    reasons: list[str] = []
    warnings: list[str] = []
    next_actions: list[str] = []

    if promotion_status == "PROMOTED":
        reasons.append(
            "V8.4가 후보 전략 적용을 권장했습니다."
        )

        reasons.append(
            f"기준 전략 대비 종합점수가 "
            f"{score_improvement:+.2f}점 개선되었습니다."
        )

        next_actions.extend(
            [
                "승격된 전략을 모의투자 환경에서 먼저 확인합니다.",
                "운영 전략 변경 이력을 정기적으로 검토합니다.",
                "실제 주문 연결 전 별도의 승인 단계를 사용합니다.",
            ]
        )

    elif promotion_status == "PAPER_TRADING":
        reasons.append(
            "후보 전략이 즉시 운영 승격 기준에는 "
            "도달하지 못했지만 추가 검증 가치가 있습니다."
        )

        next_actions.extend(
            [
                "모의투자 결과를 최소 30거래일 기록합니다.",
                "기존 전략과 동일 기간 성과를 비교합니다.",
                "거래 비용과 슬리피지를 포함해 재평가합니다.",
            ]
        )

    elif promotion_status == "BASELINE_RETAINED":
        reasons.append(
            "후보 전략의 종합점수가 기준 전략보다 "
            "높지 않았습니다."
        )

        reasons.append(
            "기존 운영 전략을 변경하지 않았습니다."
        )

        next_actions.extend(
            [
                "현재 기준 전략을 계속 유지합니다.",
                "후보 전략은 연구 기록으로 보관합니다.",
                "새로운 데이터가 누적되면 다시 평가합니다.",
            ]
        )

    elif promotion_status == "RESEARCH_ARCHIVED":
        reasons.append(
            "후보 전략이 운영 또는 모의투자 승격 "
            "기준을 충족하지 못했습니다."
        )

        next_actions.extend(
            [
                "후보 전략을 연구 자료로만 사용합니다.",
                "파라미터 생성 범위를 다시 검토합니다.",
                "추가 Walk-Forward 검증 후 재평가합니다.",
            ]
        )

    else:
        warnings.append(
            f"처리 가능한 승격 작업이 없습니다: {decision}"
        )

        next_actions.append(
            "V8.4 추천 결과와 Decision 값을 확인합니다."
        )

    warnings.append(
        "전략 승격 결과는 실제 주문을 자동 실행하지 않습니다."
    )

    return (
        reasons,
        warnings,
        next_actions,
    )


def run_strategy_promotion(
    symbol: str = "AAPL",
    source_file: str | Path | None = None,
) -> StrategyPromotionResult:
    """
    V8.4 추천 결과를 읽고 전략 상태를 관리합니다.
    """

    normalized_symbol = normalize_symbol(
        symbol
    )

    if source_file is None:
        source_path = (
            find_latest_recommendation_file(
                normalized_symbol
            )
        )
    else:
        source_path = Path(
            source_file
        )

    recommendation = load_json_file(
        source_path
    )

    validate_recommendation_payload(
        recommendation
    )

    recommendation_symbol = normalize_symbol(
        str(
            recommendation.get(
                "symbol",
                normalized_symbol,
            )
        )
    )

    if recommendation_symbol != normalized_symbol:
        raise ValueError(
            "요청한 Symbol과 추천 파일의 Symbol이 "
            "일치하지 않습니다."
        )

    source_decision = str(
        recommendation.get(
            "decision",
            "NO_DECISION",
        )
    ).upper()

    (
        promotion_status,
        promotion_label,
    ) = determine_promotion_status(
        source_decision
    )

    strategy_output_file: str | None = None
    previous_active_file: str | None = None
    history_file: str | None = None

    action_performed = False
    baseline_retained = False
    candidate_promoted = False
    candidate_paper_trading = False
    candidate_archived = False

    if promotion_status == "PROMOTED":
        if not safe_bool(
            recommendation.get(
                "passed_all_checks"
            )
        ):
            raise RuntimeError(
                "모든 품질 검사를 통과하지 못한 후보는 "
                "운영 전략으로 승격할 수 없습니다."
            )

        (
            strategy_output_file,
            history_file,
        ) = promote_candidate_strategy(
            symbol=normalized_symbol,
            recommendation=recommendation,
        )

        previous_active_file = (
            history_file
        )

        action_performed = True
        candidate_promoted = True

    elif promotion_status == "PAPER_TRADING":
        strategy_output_file = (
            register_paper_strategy(
                symbol=normalized_symbol,
                recommendation=recommendation,
            )
        )

        action_performed = True
        candidate_paper_trading = True

    elif promotion_status == "BASELINE_RETAINED":
        baseline_retained = True

        strategy_output_file = (
            archive_research_candidate(
                symbol=normalized_symbol,
                recommendation=recommendation,
            )
        )

        action_performed = True
        candidate_archived = True

    elif promotion_status == "RESEARCH_ARCHIVED":
        strategy_output_file = (
            archive_research_candidate(
                symbol=normalized_symbol,
                recommendation=recommendation,
            )
        )

        action_performed = True
        candidate_archived = True

    (
        reasons,
        warnings,
        next_actions,
    ) = build_result_notes(
        decision=source_decision,
        promotion_status=promotion_status,
        score_improvement=safe_float(
            recommendation.get(
                "score_improvement"
            )
        ),
    )

    result = StrategyPromotionResult(
        version="V8.5",
        symbol=normalized_symbol,

        created_at=datetime.now().isoformat(),
        source_file=str(source_path),

        source_decision=source_decision,
        source_decision_label=str(
            recommendation.get(
                "decision_label",
                "",
            )
        ),

        promotion_status=promotion_status,
        promotion_label=promotion_label,

        action_performed=action_performed,
        baseline_retained=baseline_retained,
        candidate_promoted=candidate_promoted,
        candidate_paper_trading=(
            candidate_paper_trading
        ),
        candidate_archived=candidate_archived,

        selected_candidate_number=(
            safe_int(
                recommendation.get(
                    "selected_candidate_number"
                )
            )
        ),

        selected_candidate_name=(
            recommendation.get(
                "selected_candidate_name"
            )
        ),

        selected_candidate_type=(
            recommendation.get(
                "selected_candidate_type"
            )
        ),

        candidate_score=safe_float(
            recommendation.get(
                "selected_candidate_score"
            )
        ),

        baseline_score=safe_float(
            recommendation.get(
                "baseline_score"
            )
        ),

        score_improvement=safe_float(
            recommendation.get(
                "score_improvement"
            )
        ),

        confidence_score=safe_float(
            recommendation.get(
                "confidence_score"
            )
        ),

        confidence_level=str(
            recommendation.get(
                "confidence_level",
                "UNKNOWN",
            )
        ),

        risk_score=safe_float(
            recommendation.get(
                "risk_score"
            )
        ),

        risk_level=str(
            recommendation.get(
                "risk_level",
                "UNKNOWN",
            )
        ),

        recommendation_strength=safe_int(
            recommendation.get(
                "recommendation_strength"
            )
        ),

        entry_score=safe_float(
            recommendation.get(
                "entry_score"
            )
        ),

        exit_score=safe_float(
            recommendation.get(
                "exit_score"
            )
        ),

        stop_atr_multiple=safe_float(
            recommendation.get(
                "stop_atr_multiple"
            )
        ),

        target_atr_multiple=safe_float(
            recommendation.get(
                "target_atr_multiple"
            )
        ),

        maximum_holding_days=safe_int(
            recommendation.get(
                "maximum_holding_days"
            )
        ),

        position_percent=safe_float(
            recommendation.get(
                "position_percent"
            )
        ),

        previous_active_strategy_file=(
            previous_active_file
        ),

        strategy_output_file=(
            strategy_output_file
        ),

        history_file=history_file,

        reasons=reasons,
        warnings=warnings,
        next_actions=next_actions,
    )

    print_strategy_promotion_result(
        result
    )

    return result


def save_strategy_promotion_result(
    result: StrategyPromotionResult,
) -> tuple[Path, Path]:
    """
    V8.5 처리 결과를 JSON으로 저장합니다.
    """

    PROMOTION_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    report_path = (
        PROMOTION_DIRECTORY
        / (
            f"{result.symbol}_"
            "strategy_promotion_"
            f"{timestamp}.json"
        )
    )

    latest_path = (
        PROMOTION_DIRECTORY
        / (
            f"{result.symbol}_"
            "strategy_promotion_latest.json"
        )
    )

    result.report_path = str(
        report_path
    )

    result.latest_path = str(
        latest_path
    )

    payload = result.to_dict()

    write_json_file(
        report_path,
        payload,
    )

    write_json_file(
        latest_path,
        payload,
    )

    return (
        report_path,
        latest_path,
    )


def print_strategy_promotion_result(
    result: StrategyPromotionResult,
) -> None:
    """
    V8.5 전략 관리 결과를 출력합니다.
    """

    print()
    print("=" * 125)
    print(
        f"{result.symbol} V8.5 "
        "STRATEGY PROMOTION MANAGER"
    )
    print("=" * 125)

    print(
        f"Source decision             : "
        f"{result.source_decision}"
    )

    print(
        f"Source decision label       : "
        f"{result.source_decision_label}"
    )

    print(
        f"Promotion status            : "
        f"{result.promotion_status}"
    )

    print(
        f"Promotion label             : "
        f"{result.promotion_label}"
    )

    print(
        f"Action performed            : "
        f"{result.action_performed}"
    )

    print()
    print("STRATEGY ACTION")
    print("-" * 125)

    print(
        f"Baseline retained           : "
        f"{result.baseline_retained}"
    )

    print(
        f"Candidate promoted          : "
        f"{result.candidate_promoted}"
    )

    print(
        f"Paper trading registered    : "
        f"{result.candidate_paper_trading}"
    )

    print(
        f"Research candidate archived : "
        f"{result.candidate_archived}"
    )

    print()
    print("CANDIDATE")
    print("-" * 125)

    print(
        f"Candidate number            : "
        f"{result.selected_candidate_number}"
    )

    print(
        f"Candidate name              : "
        f"{result.selected_candidate_name}"
    )

    print(
        f"Candidate type              : "
        f"{result.selected_candidate_type}"
    )

    print()
    print("SCORE COMPARISON")
    print("-" * 125)

    print(
        f"Baseline score              : "
        f"{result.baseline_score:.2f}/100"
    )

    print(
        f"Candidate score             : "
        f"{result.candidate_score:.2f}/100"
    )

    print(
        f"Score improvement           : "
        f"{result.score_improvement:+.2f} points"
    )

    print(
        f"Confidence                  : "
        f"{result.confidence_score:.2f}/100 "
        f"({result.confidence_level})"
    )

    print(
        f"Risk                        : "
        f"{result.risk_score:.2f}/100 "
        f"({result.risk_level})"
    )

    print()
    print("PARAMETERS")
    print("-" * 125)

    print(
        f"Entry score                 : "
        f"{result.entry_score}"
    )

    print(
        f"Exit score                  : "
        f"{result.exit_score}"
    )

    print(
        f"Stop ATR                    : "
        f"{result.stop_atr_multiple}"
    )

    print(
        f"Target ATR                  : "
        f"{result.target_atr_multiple}"
    )

    print(
        f"Maximum holding days        : "
        f"{result.maximum_holding_days}"
    )

    print(
        f"Position percent            : "
        f"{result.position_percent}%"
    )

    if result.reasons:
        print()
        print("REASONS")
        print("-" * 125)

        for reason in result.reasons:
            print(
                f"- {reason}"
            )

    if result.warnings:
        print()
        print("WARNINGS")
        print("-" * 125)

        for warning in result.warnings:
            print(
                f"- {warning}"
            )

    if result.next_actions:
        print()
        print("NEXT ACTIONS")
        print("-" * 125)

        for action in result.next_actions:
            print(
                f"- {action}"
            )

    print()
    print("FILES")
    print("-" * 125)

    print(
        f"Source file                 : "
        f"{result.source_file}"
    )

    print(
        f"Strategy output file        : "
        f"{result.strategy_output_file or 'None'}"
    )

    print(
        f"Previous active backup      : "
        f"{result.previous_active_strategy_file or 'None'}"
    )

    print(
        f"History file                : "
        f"{result.history_file or 'None'}"
    )

    print(
        f"Report file                 : "
        f"{result.report_path or 'Not saved yet'}"
    )

    print(
        f"Latest file                 : "
        f"{result.latest_path or 'Not saved yet'}"
    )

    print("=" * 125)

    print(
        "주의: 이 모듈은 전략 설정 파일만 관리하며 "
        "실제 증권 주문을 실행하지 않습니다."
    )