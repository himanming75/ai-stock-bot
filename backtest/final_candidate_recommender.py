import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent

SOURCE_DIRECTORY = (
    PROJECT_ROOT
    / "output"
    / "strategy_backtests"
    / "improvement_candidate_backtest"
)

OUTPUT_DIRECTORY = (
    PROJECT_ROOT
    / "output"
    / "strategy_backtests"
    / "final_candidate_recommendation"
)


VALID_DECISIONS = {
    "APPLY_CANDIDATE",
    "PAPER_TRADE_CANDIDATE",
    "KEEP_BASELINE",
    "RESEARCH_ONLY",
    "NO_DECISION",
}

VALID_CONFIDENCE_LEVELS = {
    "HIGH",
    "MEDIUM",
    "LOW",
}

VALID_RISK_LEVELS = {
    "LOW",
    "MEDIUM",
    "HIGH",
}


@dataclass
class FinalCandidateRecommendation:
    """
    V8.4 최종 후보 추천 결과입니다.
    """

    version: str
    symbol: str

    created_at: str
    source_file: str

    decision: str
    decision_label: str

    confidence_score: float
    confidence_level: str

    risk_score: float
    risk_level: str

    baseline_score: float

    selected_candidate_number: int | None
    selected_candidate_name: str | None
    selected_candidate_type: str | None
    selected_candidate_status: str | None

    selected_candidate_score: float
    score_improvement: float

    entry_score: float | None
    exit_score: float | None
    stop_atr_multiple: float | None
    target_atr_multiple: float | None
    maximum_holding_days: int | None
    position_percent: float | None

    strategy_return_percent: float
    sharpe_ratio: float
    maximum_drawdown_percent: float
    profit_factor: float
    win_rate_percent: float
    total_trades: int

    walk_forward_status: str
    walk_forward_score: float
    profitable_windows_percent: float
    acceptable_windows_percent: float
    beat_default_return_percent: float
    parameter_stability_score: float

    backtest_success: bool
    walk_forward_success: bool
    passed_all_checks: bool

    recommendation_strength: int

    reasons: list[str]
    concerns: list[str]
    required_actions: list[str]

    report_path: str | None = None
    latest_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def normalize_symbol(
    symbol: str,
) -> str:
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


def clamp_score(
    value: float,
) -> float:
    """
    점수를 0~100 범위로 제한합니다.
    """

    return round(
        max(
            0.0,
            min(
                100.0,
                value,
            ),
        ),
        2,
    )


def find_latest_candidate_backtest_file(
    symbol: str,
) -> Path:
    """
    V8.3 최신 후보 백테스트 파일을 찾습니다.
    """

    normalized_symbol = normalize_symbol(
        symbol
    )

    expected_path = (
        SOURCE_DIRECTORY
        / (
            f"{normalized_symbol}_"
            "improvement_candidate_backtest_latest.json"
        )
    )

    if expected_path.exists():
        return expected_path

    if not SOURCE_DIRECTORY.exists():
        raise FileNotFoundError(
            "V8.3 결과 폴더가 없습니다: "
            f"{SOURCE_DIRECTORY}"
        )

    matching_files = [
        path
        for path in SOURCE_DIRECTORY.glob(
            f"{normalized_symbol}_"
            "improvement_candidate_backtest_*.json"
        )
        if "latest" not in path.name.lower()
    ]

    if not matching_files:
        raise FileNotFoundError(
            f"{normalized_symbol} V8.3 결과 파일을 "
            "찾을 수 없습니다."
        )

    return max(
        matching_files,
        key=lambda path: path.stat().st_mtime,
    )


def load_candidate_backtest_file(
    source_path: Path,
) -> dict[str, Any]:
    """
    V8.3 JSON 파일을 읽습니다.
    """

    if not source_path.exists():
        raise FileNotFoundError(
            f"V8.3 결과 파일이 없습니다: {source_path}"
        )

    with source_path.open(
        mode="r",
        encoding="utf-8",
    ) as file:
        payload = json.load(file)

    if not isinstance(payload, dict):
        raise ValueError(
            "V8.3 JSON의 최상위 값이 객체 형식이 아닙니다."
        )

    candidates = payload.get(
        "candidates"
    )

    if not isinstance(
        candidates,
        list,
    ):
        raise ValueError(
            "V8.3 JSON에 candidates 목록이 없습니다."
        )

    return payload


def find_winner_candidate(
    payload: dict[str, Any],
) -> dict[str, Any] | None:
    """
    V8.3 결과에서 우승 후보를 찾습니다.
    """

    candidates = payload.get(
        "candidates",
        [],
    )

    if not candidates:
        return None

    winner_name = payload.get(
        "winner_candidate_name"
    )

    winner_number = payload.get(
        "winner_candidate_number"
    )

    for candidate in candidates:
        if not isinstance(
            candidate,
            dict,
        ):
            continue

        name_matches = (
            winner_name is not None
            and str(
                candidate.get(
                    "candidate_name"
                )
            )
            == str(winner_name)
        )

        number_matches = (
            winner_number is not None
            and safe_int(
                candidate.get(
                    "source_candidate_number"
                )
            )
            == safe_int(winner_number)
        )

        if name_matches and number_matches:
            return candidate

    ranked_candidates = [
        candidate
        for candidate in candidates
        if isinstance(
            candidate,
            dict,
        )
    ]

    if not ranked_candidates:
        return None

    ranked_candidates.sort(
        key=lambda candidate: safe_int(
            candidate.get(
                "rank",
                999999,
            )
        )
    )

    return ranked_candidates[0]


def calculate_confidence_score(
    candidate: dict[str, Any],
    baseline_score: float,
) -> float:
    """
    후보 추천 신뢰도를 계산합니다.
    """

    candidate_score = safe_float(
        candidate.get(
            "final_score"
        )
    )

    walk_forward_score = safe_float(
        candidate.get(
            "walk_forward_component_score"
        )
    )

    parameter_stability = safe_float(
        candidate.get(
            "parameter_stability_score"
        )
    )

    profitable_windows = safe_float(
        candidate.get(
            "profitable_windows_percent"
        )
    )

    acceptable_windows = safe_float(
        candidate.get(
            "acceptable_windows_percent"
        )
    )

    score_improvement = (
        candidate_score
        - baseline_score
    )

    improvement_score = 50.0

    if score_improvement >= 5.0:
        improvement_score = 100.0

    elif score_improvement >= 2.0:
        improvement_score = 85.0

    elif score_improvement >= 0.0:
        improvement_score = 70.0

    elif score_improvement >= -2.0:
        improvement_score = 50.0

    elif score_improvement >= -5.0:
        improvement_score = 30.0

    else:
        improvement_score = 10.0

    checks_score = (
        100.0
        if safe_bool(
            candidate.get(
                "passed_all_checks"
            )
        )
        else 30.0
    )

    confidence_score = (
        candidate_score * 0.25
        + walk_forward_score * 0.25
        + parameter_stability * 0.15
        + profitable_windows * 0.10
        + acceptable_windows * 0.10
        + improvement_score * 0.10
        + checks_score * 0.05
    )

    return clamp_score(
        confidence_score
    )


def determine_confidence_level(
    confidence_score: float,
) -> str:
    """
    신뢰도 등급을 결정합니다.
    """

    if confidence_score >= 80.0:
        return "HIGH"

    if confidence_score >= 60.0:
        return "MEDIUM"

    return "LOW"


def calculate_risk_score(
    candidate: dict[str, Any],
) -> float:
    """
    후보 위험 점수를 계산합니다.

    점수가 높을수록 위험합니다.
    """

    drawdown = abs(
        safe_float(
            candidate.get(
                "maximum_drawdown_percent"
            )
        )
    )

    sharpe_ratio = safe_float(
        candidate.get(
            "sharpe_ratio"
        )
    )

    profit_factor = safe_float(
        candidate.get(
            "profit_factor"
        )
    )

    walk_forward_score = safe_float(
        candidate.get(
            "walk_forward_component_score"
        )
    )

    total_trades = safe_int(
        candidate.get(
            "total_trades"
        )
    )

    position_percent = safe_float(
        candidate.get(
            "position_percent"
        )
    )

    drawdown_risk = min(
        100.0,
        drawdown * 5.0,
    )

    if sharpe_ratio >= 1.5:
        sharpe_risk = 10.0

    elif sharpe_ratio >= 1.0:
        sharpe_risk = 25.0

    elif sharpe_ratio >= 0.5:
        sharpe_risk = 50.0

    else:
        sharpe_risk = 85.0

    if profit_factor >= 1.7:
        profit_factor_risk = 10.0

    elif profit_factor >= 1.3:
        profit_factor_risk = 30.0

    elif profit_factor >= 1.1:
        profit_factor_risk = 55.0

    else:
        profit_factor_risk = 90.0

    walk_forward_risk = (
        100.0
        - walk_forward_score
    )

    if total_trades >= 100:
        trade_count_risk = 10.0

    elif total_trades >= 50:
        trade_count_risk = 25.0

    elif total_trades >= 30:
        trade_count_risk = 45.0

    else:
        trade_count_risk = 80.0

    if position_percent <= 10.0:
        position_risk = 15.0

    elif position_percent <= 15.0:
        position_risk = 25.0

    elif position_percent <= 20.0:
        position_risk = 40.0

    else:
        position_risk = 65.0

    risk_score = (
        drawdown_risk * 0.25
        + sharpe_risk * 0.20
        + profit_factor_risk * 0.15
        + walk_forward_risk * 0.20
        + trade_count_risk * 0.10
        + position_risk * 0.10
    )

    return clamp_score(
        risk_score
    )


def determine_risk_level(
    risk_score: float,
) -> str:
    """
    위험 등급을 결정합니다.
    """

    if risk_score <= 35.0:
        return "LOW"

    if risk_score <= 60.0:
        return "MEDIUM"

    return "HIGH"


def determine_final_decision(
    candidate: dict[str, Any],
    baseline_score: float,
    confidence_score: float,
    risk_score: float,
) -> tuple[str, str]:
    """
    후보 적용 여부를 최종 결정합니다.
    """

    candidate_score = safe_float(
        candidate.get(
            "final_score"
        )
    )

    score_improvement = (
        candidate_score
        - baseline_score
    )

    passed_all_checks = safe_bool(
        candidate.get(
            "passed_all_checks"
        )
    )

    walk_forward_status = str(
        candidate.get(
            "walk_forward_status",
            "UNKNOWN",
        )
    ).upper()

    if not passed_all_checks:
        return (
            "RESEARCH_ONLY",
            "연구용 후보",
        )

    if (
        score_improvement >= 3.0
        and confidence_score >= 75.0
        and risk_score <= 50.0
        and walk_forward_status
        in {
            "ROBUST",
            "ACCEPTABLE",
        }
    ):
        return (
            "APPLY_CANDIDATE",
            "후보 적용 권장",
        )

    if (
        score_improvement > 0.0
        and confidence_score >= 65.0
        and risk_score <= 60.0
    ):
        return (
            "PAPER_TRADE_CANDIDATE",
            "모의투자 검증 권장",
        )

    if (
        score_improvement <= 0.0
        and baseline_score >= candidate_score
    ):
        return (
            "KEEP_BASELINE",
            "기준 전략 유지",
        )

    return (
        "RESEARCH_ONLY",
        "추가 연구 필요",
    )


def calculate_recommendation_strength(
    decision: str,
    confidence_score: float,
    risk_score: float,
) -> int:
    """
    추천 강도를 별 1~5개로 계산합니다.
    """

    decision_bonus = {
        "APPLY_CANDIDATE": 15.0,
        "PAPER_TRADE_CANDIDATE": 5.0,
        "KEEP_BASELINE": 0.0,
        "RESEARCH_ONLY": -10.0,
        "NO_DECISION": -20.0,
    }

    strength_score = (
        confidence_score
        - risk_score * 0.40
        + decision_bonus.get(
            decision,
            -20.0,
        )
    )

    if strength_score >= 80.0:
        return 5

    if strength_score >= 65.0:
        return 4

    if strength_score >= 50.0:
        return 3

    if strength_score >= 35.0:
        return 2

    return 1


def build_recommendation_notes(
    candidate: dict[str, Any],
    baseline_score: float,
    decision: str,
    confidence_score: float,
    risk_score: float,
) -> tuple[
    list[str],
    list[str],
    list[str],
]:
    """
    최종 결정 이유, 우려 사항 및 후속 작업을 생성합니다.
    """

    reasons: list[str] = []
    concerns: list[str] = []
    required_actions: list[str] = []

    candidate_score = safe_float(
        candidate.get(
            "final_score"
        )
    )

    score_improvement = (
        candidate_score
        - baseline_score
    )

    sharpe_ratio = safe_float(
        candidate.get(
            "sharpe_ratio"
        )
    )

    drawdown = safe_float(
        candidate.get(
            "maximum_drawdown_percent"
        )
    )

    profit_factor = safe_float(
        candidate.get(
            "profit_factor"
        )
    )

    walk_forward_status = str(
        candidate.get(
            "walk_forward_status",
            "UNKNOWN",
        )
    ).upper()

    profitable_windows = safe_float(
        candidate.get(
            "profitable_windows_percent"
        )
    )

    acceptable_windows = safe_float(
        candidate.get(
            "acceptable_windows_percent"
        )
    )

    parameter_stability = safe_float(
        candidate.get(
            "parameter_stability_score"
        )
    )

    if safe_bool(
        candidate.get(
            "passed_all_checks"
        )
    ):
        reasons.append(
            "후보가 모든 최소 품질 검사를 통과했습니다."
        )

    if sharpe_ratio >= 1.0:
        reasons.append(
            f"Sharpe Ratio가 {sharpe_ratio:.2f}로 "
            "최소 안정성 기준을 통과했습니다."
        )

    if abs(drawdown) <= 10.0:
        reasons.append(
            f"최대 낙폭이 {drawdown:.2f}%로 "
            "10% 이내입니다."
        )

    if profit_factor >= 1.3:
        reasons.append(
            f"Profit Factor가 {profit_factor:.2f}로 "
            "양호합니다."
        )

    if walk_forward_status in {
        "ROBUST",
        "ACCEPTABLE",
    }:
        reasons.append(
            f"Walk-Forward 상태가 "
            f"{walk_forward_status}입니다."
        )

    if profitable_windows >= 70.0:
        reasons.append(
            f"수익 발생 검증 구간이 "
            f"{profitable_windows:.2f}%입니다."
        )

    if acceptable_windows >= 70.0:
        reasons.append(
            f"품질 기준을 통과한 검증 구간이 "
            f"{acceptable_windows:.2f}%입니다."
        )

    if parameter_stability >= 70.0:
        reasons.append(
            f"파라미터 안정성 점수가 "
            f"{parameter_stability:.2f}/100입니다."
        )

    if score_improvement > 0.0:
        reasons.append(
            f"후보 점수가 기준 전략보다 "
            f"{score_improvement:.2f}점 높습니다."
        )

    else:
        concerns.append(
            f"후보 점수가 기준 전략보다 "
            f"{abs(score_improvement):.2f}점 낮습니다."
        )

    if confidence_score < 70.0:
        concerns.append(
            f"추천 신뢰도가 {confidence_score:.2f}/100으로 "
            "높지 않습니다."
        )

    if risk_score > 50.0:
        concerns.append(
            f"위험 점수가 {risk_score:.2f}/100으로 "
            "높은 편입니다."
        )

    if walk_forward_status == "WEAK":
        concerns.append(
            "Walk-Forward 검증 상태가 WEAK입니다."
        )

    if decision == "APPLY_CANDIDATE":
        required_actions.extend(
            [
                "후보 파라미터를 별도 운영 설정 파일에 저장합니다.",
                "실제 주문 전 최소 30거래일 모의투자를 진행합니다.",
                "기준 전략과 후보 전략을 동시에 기록합니다.",
            ]
        )

    elif decision == "PAPER_TRADE_CANDIDATE":
        required_actions.extend(
            [
                "실제 전략에는 아직 적용하지 않습니다.",
                "최소 60거래일 모의투자로 성능을 비교합니다.",
                "거래 비용과 슬리피지를 포함해 다시 평가합니다.",
            ]
        )

    elif decision == "KEEP_BASELINE":
        required_actions.extend(
            [
                "현재 기준 전략 파라미터를 유지합니다.",
                "후보 전략은 연구 결과로만 저장합니다.",
                "새로운 시장 데이터가 축적된 후 다시 검증합니다.",
            ]
        )

    else:
        required_actions.extend(
            [
                "후보를 실제 운영에 적용하지 않습니다.",
                "후보 생성 범위와 평가 가중치를 재검토합니다.",
                "추가 Walk-Forward 검증 후 다시 판단합니다.",
            ]
        )

    return (
        reasons,
        concerns,
        required_actions,
    )


def run_final_candidate_recommendation(
    symbol: str = "AAPL",
    source_file: str | Path | None = None,
) -> FinalCandidateRecommendation:
    """
    V8.3 결과에서 최종 적용 여부를 판단합니다.
    """

    normalized_symbol = normalize_symbol(
        symbol
    )

    if source_file is None:
        source_path = (
            find_latest_candidate_backtest_file(
                normalized_symbol
            )
        )

    else:
        source_path = Path(
            source_file
        )

    payload = load_candidate_backtest_file(
        source_path
    )

    winner = find_winner_candidate(
        payload
    )

    if winner is None:
        raise RuntimeError(
            "V8.3 결과에서 우승 후보를 찾을 수 없습니다."
        )

    baseline_score = safe_float(
        payload.get(
            "baseline_final_score"
        )
    )

    candidate_score = safe_float(
        winner.get(
            "final_score"
        )
    )

    score_improvement = round(
        candidate_score
        - baseline_score,
        2,
    )

    confidence_score = (
        calculate_confidence_score(
            candidate=winner,
            baseline_score=baseline_score,
        )
    )

    confidence_level = (
        determine_confidence_level(
            confidence_score
        )
    )

    risk_score = calculate_risk_score(
        winner
    )

    risk_level = determine_risk_level(
        risk_score
    )

    (
        decision,
        decision_label,
    ) = determine_final_decision(
        candidate=winner,
        baseline_score=baseline_score,
        confidence_score=confidence_score,
        risk_score=risk_score,
    )

    recommendation_strength = (
        calculate_recommendation_strength(
            decision=decision,
            confidence_score=confidence_score,
            risk_score=risk_score,
        )
    )

    (
        reasons,
        concerns,
        required_actions,
    ) = build_recommendation_notes(
        candidate=winner,
        baseline_score=baseline_score,
        decision=decision,
        confidence_score=confidence_score,
        risk_score=risk_score,
    )

    result = FinalCandidateRecommendation(
        version="V8.4",
        symbol=normalized_symbol,

        created_at=datetime.now().isoformat(),
        source_file=str(source_path),

        decision=decision,
        decision_label=decision_label,

        confidence_score=confidence_score,
        confidence_level=confidence_level,

        risk_score=risk_score,
        risk_level=risk_level,

        baseline_score=round(
            baseline_score,
            2,
        ),

        selected_candidate_number=safe_int(
            winner.get(
                "source_candidate_number"
            )
        ),

        selected_candidate_name=str(
            winner.get(
                "candidate_name"
            )
        ),

        selected_candidate_type=str(
            winner.get(
                "candidate_type"
            )
        ),

        selected_candidate_status=str(
            winner.get(
                "final_status"
            )
        ),

        selected_candidate_score=round(
            candidate_score,
            2,
        ),

        score_improvement=score_improvement,

        entry_score=safe_float(
            winner.get(
                "entry_score"
            )
        ),

        exit_score=safe_float(
            winner.get(
                "exit_score"
            )
        ),

        stop_atr_multiple=safe_float(
            winner.get(
                "stop_atr_multiple"
            )
        ),

        target_atr_multiple=safe_float(
            winner.get(
                "target_atr_multiple"
            )
        ),

        maximum_holding_days=safe_int(
            winner.get(
                "maximum_holding_days"
            )
        ),

        position_percent=safe_float(
            winner.get(
                "position_percent"
            )
        ),

        strategy_return_percent=safe_float(
            winner.get(
                "strategy_return_percent"
            )
        ),

        sharpe_ratio=safe_float(
            winner.get(
                "sharpe_ratio"
            )
        ),

        maximum_drawdown_percent=safe_float(
            winner.get(
                "maximum_drawdown_percent"
            )
        ),

        profit_factor=safe_float(
            winner.get(
                "profit_factor"
            )
        ),

        win_rate_percent=safe_float(
            winner.get(
                "win_rate_percent"
            )
        ),

        total_trades=safe_int(
            winner.get(
                "total_trades"
            )
        ),

        walk_forward_status=str(
            winner.get(
                "walk_forward_status",
                "UNKNOWN",
            )
        ),

        walk_forward_score=safe_float(
            winner.get(
                "walk_forward_component_score"
            )
        ),

        profitable_windows_percent=safe_float(
            winner.get(
                "profitable_windows_percent"
            )
        ),

        acceptable_windows_percent=safe_float(
            winner.get(
                "acceptable_windows_percent"
            )
        ),

        beat_default_return_percent=safe_float(
            winner.get(
                "beat_default_return_percent"
            )
        ),

        parameter_stability_score=safe_float(
            winner.get(
                "parameter_stability_score"
            )
        ),

        backtest_success=safe_bool(
            winner.get(
                "backtest_success"
            )
        ),

        walk_forward_success=safe_bool(
            winner.get(
                "walk_forward_success"
            )
        ),

        passed_all_checks=safe_bool(
            winner.get(
                "passed_all_checks"
            )
        ),

        recommendation_strength=(
            recommendation_strength
        ),

        reasons=reasons,
        concerns=concerns,
        required_actions=required_actions,
    )

    print_final_candidate_recommendation(
        result
    )

    return result


def save_final_candidate_recommendation(
    result: FinalCandidateRecommendation,
) -> tuple[Path, Path]:
    """
    V8.4 추천 결과를 JSON 파일로 저장합니다.
    """

    OUTPUT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    report_path = (
        OUTPUT_DIRECTORY
        / (
            f"{result.symbol}_"
            "final_candidate_recommendation_"
            f"{timestamp}.json"
        )
    )

    latest_path = (
        OUTPUT_DIRECTORY
        / (
            f"{result.symbol}_"
            "final_candidate_recommendation_latest.json"
        )
    )

    result.report_path = str(
        report_path
    )

    result.latest_path = str(
        latest_path
    )

    payload = result.to_dict()

    for path in (
        report_path,
        latest_path,
    ):
        with path.open(
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

    return (
        report_path,
        latest_path,
    )


def build_star_rating(
    strength: int,
) -> str:
    """
    추천 강도를 별 표시로 변환합니다.
    """

    normalized_strength = max(
        1,
        min(
            5,
            int(strength),
        ),
    )

    return (
        "★" * normalized_strength
        + "☆" * (
            5
            - normalized_strength
        )
    )


def print_final_candidate_recommendation(
    result: FinalCandidateRecommendation,
) -> None:
    """
    V8.4 최종 추천 결과를 출력합니다.
    """

    print()
    print("=" * 120)
    print(
        f"{result.symbol} V8.4 "
        "FINAL CANDIDATE RECOMMENDATION"
    )
    print("=" * 120)

    print(
        f"Decision                   : "
        f"{result.decision}"
    )

    print(
        f"Decision label             : "
        f"{result.decision_label}"
    )

    print(
        f"Recommendation strength    : "
        f"{build_star_rating(result.recommendation_strength)}"
    )

    print(
        f"Confidence                 : "
        f"{result.confidence_score:.2f}/100 "
        f"({result.confidence_level})"
    )

    print(
        f"Risk                       : "
        f"{result.risk_score:.2f}/100 "
        f"({result.risk_level})"
    )

    print()
    print("SCORE COMPARISON")
    print("-" * 120)

    print(
        f"Baseline score             : "
        f"{result.baseline_score:.2f}/100"
    )

    print(
        f"Candidate score            : "
        f"{result.selected_candidate_score:.2f}/100"
    )

    print(
        f"Score improvement          : "
        f"{result.score_improvement:+.2f} points"
    )

    print()
    print("SELECTED CANDIDATE")
    print("-" * 120)

    print(
        f"Candidate number           : "
        f"{result.selected_candidate_number}"
    )

    print(
        f"Candidate name             : "
        f"{result.selected_candidate_name}"
    )

    print(
        f"Candidate type             : "
        f"{result.selected_candidate_type}"
    )

    print(
        f"Candidate status           : "
        f"{result.selected_candidate_status}"
    )

    print()
    print("PARAMETERS")
    print("-" * 120)

    print(
        f"Entry score                : "
        f"{result.entry_score}"
    )

    print(
        f"Exit score                 : "
        f"{result.exit_score}"
    )

    print(
        f"Stop ATR                   : "
        f"{result.stop_atr_multiple}"
    )

    print(
        f"Target ATR                 : "
        f"{result.target_atr_multiple}"
    )

    print(
        f"Maximum holding days       : "
        f"{result.maximum_holding_days}"
    )

    print(
        f"Position percent           : "
        f"{result.position_percent}%"
    )

    print()
    print("PERFORMANCE")
    print("-" * 120)

    print(
        f"Strategy return            : "
        f"{result.strategy_return_percent:.2f}%"
    )

    print(
        f"Sharpe ratio               : "
        f"{result.sharpe_ratio:.2f}"
    )

    print(
        f"Maximum drawdown           : "
        f"{result.maximum_drawdown_percent:.2f}%"
    )

    print(
        f"Profit factor              : "
        f"{result.profit_factor:.2f}"
    )

    print(
        f"Win rate                   : "
        f"{result.win_rate_percent:.2f}%"
    )

    print(
        f"Total trades               : "
        f"{result.total_trades}"
    )

    print()
    print("WALK-FORWARD")
    print("-" * 120)

    print(
        f"Status                     : "
        f"{result.walk_forward_status}"
    )

    print(
        f"Score                      : "
        f"{result.walk_forward_score:.2f}/100"
    )

    print(
        f"Profitable windows         : "
        f"{result.profitable_windows_percent:.2f}%"
    )

    print(
        f"Acceptable windows         : "
        f"{result.acceptable_windows_percent:.2f}%"
    )

    print(
        f"Beat default return        : "
        f"{result.beat_default_return_percent:.2f}%"
    )

    print(
        f"Parameter stability        : "
        f"{result.parameter_stability_score:.2f}/100"
    )

    if result.reasons:
        print()
        print("REASONS")
        print("-" * 120)

        for reason in result.reasons:
            print(
                f"- {reason}"
            )

    if result.concerns:
        print()
        print("CONCERNS")
        print("-" * 120)

        for concern in result.concerns:
            print(
                f"- {concern}"
            )

    if result.required_actions:
        print()
        print("REQUIRED ACTIONS")
        print("-" * 120)

        for action in result.required_actions:
            print(
                f"- {action}"
            )

    print()
    print("FILES")
    print("-" * 120)

    print(
        f"Source file                : "
        f"{result.source_file}"
    )

    print(
        f"Report file                : "
        f"{result.report_path or 'Not saved yet'}"
    )

    print(
        f"Latest file                : "
        f"{result.latest_path or 'Not saved yet'}"
    )

    print("=" * 120)

    print(
        "주의: 이 결과는 과거 데이터 기반 연구용 판단이며 "
        "실제 투자 조언이나 자동 주문 지시가 아닙니다."
    )