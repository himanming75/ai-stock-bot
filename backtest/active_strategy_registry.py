import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent

STRATEGY_MANAGEMENT_DIRECTORY = (
    PROJECT_ROOT
    / "output"
    / "strategy_management"
)

ACTIVE_STRATEGY_DIRECTORY = (
    STRATEGY_MANAGEMENT_DIRECTORY
    / "active"
)

PAPER_STRATEGY_DIRECTORY = (
    STRATEGY_MANAGEMENT_DIRECTORY
    / "paper_trading"
)

RESEARCH_ARCHIVE_DIRECTORY = (
    STRATEGY_MANAGEMENT_DIRECTORY
    / "research_archive"
)

PROMOTION_DIRECTORY = (
    STRATEGY_MANAGEMENT_DIRECTORY
    / "promotions"
)

REGISTRY_DIRECTORY = (
    STRATEGY_MANAGEMENT_DIRECTORY
    / "registry"
)


VALID_REGISTRY_MODES = {
    "ACTIVE",
    "PAPER_TRADING",
    "BASELINE",
    "RESEARCH_ONLY",
    "UNREGISTERED",
}


VALID_PROMOTION_STATUSES = {
    "PROMOTED",
    "PAPER_TRADING",
    "BASELINE_RETAINED",
    "RESEARCH_ARCHIVED",
    "NO_ACTION",
    "FAILED",
    "UNKNOWN",
}


@dataclass
class ActiveStrategyRegistryResult:
    """
    V8.6 전략 등록부 결과입니다.
    """

    version: str
    symbol: str
    created_at: str

    registry_mode: str
    registry_label: str

    active_strategy_exists: bool
    paper_strategy_exists: bool
    promotion_result_exists: bool
    research_candidates_exist: bool

    active_strategy_file: str | None
    paper_strategy_file: str | None
    latest_promotion_file: str | None
    latest_research_file: str | None

    promotion_status: str
    promotion_decision: str
    promotion_label: str

    selected_strategy_source: str
    selected_strategy_status: str
    selected_strategy_name: str | None
    selected_strategy_type: str | None

    entry_score: float | None
    exit_score: float | None
    stop_atr_multiple: float | None
    target_atr_multiple: float | None
    maximum_holding_days: int | None
    position_percent: float | None

    candidate_score: float | None
    baseline_score: float | None
    score_improvement: float | None

    confidence_score: float | None
    confidence_level: str | None

    risk_score: float | None
    risk_level: str | None

    recommendation_strength: int | None

    research_candidate_count: int

    registry_ready: bool
    execution_enabled: bool
    manual_approval_required: bool

    reasons: list[str]
    warnings: list[str]
    next_actions: list[str]

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
    default: float | None = None,
) -> float | None:
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
    default: int | None = None,
) -> int | None:
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

    if not isinstance(
        payload,
        dict,
    ):
        raise ValueError(
            "JSON 최상위 데이터가 Dictionary가 아닙니다."
        )

    return payload


def write_json_file(
    file_path: Path,
    payload: dict[str, Any],
) -> None:
    """
    JSON 파일을 임시 파일을 거쳐 안전하게 저장합니다.
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


def find_active_strategy_file(
    symbol: str,
) -> Path | None:
    """
    현재 운영 전략 파일을 찾습니다.
    """

    normalized_symbol = normalize_symbol(
        symbol
    )

    file_path = (
        ACTIVE_STRATEGY_DIRECTORY
        / f"{normalized_symbol}_active_strategy.json"
    )

    if file_path.exists():
        return file_path

    return None


def find_paper_strategy_file(
    symbol: str,
) -> Path | None:
    """
    현재 모의투자 전략 파일을 찾습니다.
    """

    normalized_symbol = normalize_symbol(
        symbol
    )

    file_path = (
        PAPER_STRATEGY_DIRECTORY
        / f"{normalized_symbol}_paper_strategy.json"
    )

    if file_path.exists():
        return file_path

    return None


def find_latest_promotion_file(
    symbol: str,
) -> Path | None:
    """
    최신 V8.5 승격 결과 파일을 찾습니다.
    """

    normalized_symbol = normalize_symbol(
        symbol
    )

    expected_path = (
        PROMOTION_DIRECTORY
        / (
            f"{normalized_symbol}_"
            "strategy_promotion_latest.json"
        )
    )

    if expected_path.exists():
        return expected_path

    if not PROMOTION_DIRECTORY.exists():
        return None

    matching_files = [
        path
        for path in PROMOTION_DIRECTORY.glob(
            f"{normalized_symbol}_"
            "strategy_promotion_*.json"
        )
        if "latest" not in path.name.lower()
    ]

    if not matching_files:
        return None

    return max(
        matching_files,
        key=lambda path: path.stat().st_mtime,
    )


def find_research_candidate_files(
    symbol: str,
) -> list[Path]:
    """
    해당 종목의 연구 후보 파일 목록을 찾습니다.
    """

    normalized_symbol = normalize_symbol(
        symbol
    )

    if not RESEARCH_ARCHIVE_DIRECTORY.exists():
        return []

    matching_files = list(
        RESEARCH_ARCHIVE_DIRECTORY.glob(
            f"{normalized_symbol}_"
            "research_candidate_*.json"
        )
    )

    return sorted(
        matching_files,
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )


def extract_parameters(
    payload: dict[str, Any] | None,
) -> dict[str, Any]:
    """
    전략 데이터에서 파라미터를 추출합니다.
    """

    if not payload:
        return {
            "entry_score": None,
            "exit_score": None,
            "stop_atr_multiple": None,
            "target_atr_multiple": None,
            "maximum_holding_days": None,
            "position_percent": None,
        }

    parameters = payload.get(
        "parameters"
    )

    if isinstance(
        parameters,
        dict,
    ):
        return {
            "entry_score": safe_float(
                parameters.get(
                    "entry_score"
                )
            ),
            "exit_score": safe_float(
                parameters.get(
                    "exit_score"
                )
            ),
            "stop_atr_multiple": safe_float(
                parameters.get(
                    "stop_atr_multiple"
                )
            ),
            "target_atr_multiple": safe_float(
                parameters.get(
                    "target_atr_multiple"
                )
            ),
            "maximum_holding_days": safe_int(
                parameters.get(
                    "maximum_holding_days"
                )
            ),
            "position_percent": safe_float(
                parameters.get(
                    "position_percent"
                )
            ),
        }

    return {
        "entry_score": safe_float(
            payload.get(
                "entry_score"
            )
        ),
        "exit_score": safe_float(
            payload.get(
                "exit_score"
            )
        ),
        "stop_atr_multiple": safe_float(
            payload.get(
                "stop_atr_multiple"
            )
        ),
        "target_atr_multiple": safe_float(
            payload.get(
                "target_atr_multiple"
            )
        ),
        "maximum_holding_days": safe_int(
            payload.get(
                "maximum_holding_days"
            )
        ),
        "position_percent": safe_float(
            payload.get(
                "position_percent"
            )
        ),
    }


def extract_candidate_information(
    payload: dict[str, Any] | None,
) -> tuple[
    str | None,
    str | None,
]:
    """
    전략 파일에서 후보 이름과 유형을 추출합니다.
    """

    if not payload:
        return (
            None,
            None,
        )

    candidate = payload.get(
        "candidate"
    )

    if isinstance(
        candidate,
        dict,
    ):
        candidate_name = candidate.get(
            "name"
        )

        candidate_type = candidate.get(
            "type"
        )

        return (
            str(candidate_name)
            if candidate_name is not None
            else None,
            str(candidate_type)
            if candidate_type is not None
            else None,
        )

    candidate_name = payload.get(
        "selected_candidate_name"
    )

    candidate_type = payload.get(
        "selected_candidate_type"
    )

    return (
        str(candidate_name)
        if candidate_name is not None
        else None,
        str(candidate_type)
        if candidate_type is not None
        else None,
    )


def extract_evaluation(
    strategy_payload: dict[str, Any] | None,
    promotion_payload: dict[str, Any] | None,
) -> dict[str, Any]:
    """
    전략과 승격 결과에서 평가 값을 추출합니다.
    """

    values: dict[str, Any] = {
        "candidate_score": None,
        "baseline_score": None,
        "score_improvement": None,
        "confidence_score": None,
        "confidence_level": None,
        "risk_score": None,
        "risk_level": None,
        "recommendation_strength": None,
    }

    if strategy_payload:
        evaluation = strategy_payload.get(
            "evaluation"
        )

        if isinstance(
            evaluation,
            dict,
        ):
            values.update(
                {
                    "candidate_score": safe_float(
                        evaluation.get(
                            "candidate_score"
                        )
                    ),
                    "baseline_score": safe_float(
                        evaluation.get(
                            "baseline_score"
                        )
                    ),
                    "score_improvement": safe_float(
                        evaluation.get(
                            "score_improvement"
                        )
                    ),
                    "confidence_score": safe_float(
                        evaluation.get(
                            "confidence_score"
                        )
                    ),
                    "confidence_level": (
                        str(
                            evaluation.get(
                                "confidence_level"
                            )
                        )
                        if evaluation.get(
                            "confidence_level"
                        )
                        is not None
                        else None
                    ),
                    "risk_score": safe_float(
                        evaluation.get(
                            "risk_score"
                        )
                    ),
                    "risk_level": (
                        str(
                            evaluation.get(
                                "risk_level"
                            )
                        )
                        if evaluation.get(
                            "risk_level"
                        )
                        is not None
                        else None
                    ),
                    "recommendation_strength": safe_int(
                        evaluation.get(
                            "recommendation_strength"
                        )
                    ),
                }
            )

    if promotion_payload:
        field_mapping = {
            "candidate_score": (
                "candidate_score"
            ),
            "baseline_score": (
                "baseline_score"
            ),
            "score_improvement": (
                "score_improvement"
            ),
            "confidence_score": (
                "confidence_score"
            ),
            "confidence_level": (
                "confidence_level"
            ),
            "risk_score": (
                "risk_score"
            ),
            "risk_level": (
                "risk_level"
            ),
            "recommendation_strength": (
                "recommendation_strength"
            ),
        }

        for result_key, source_key in (
            field_mapping.items()
        ):
            if values[result_key] is not None:
                continue

            source_value = promotion_payload.get(
                source_key
            )

            if result_key in {
                "confidence_level",
                "risk_level",
            }:
                if source_value is not None:
                    values[result_key] = str(
                        source_value
                    )

            elif result_key == "recommendation_strength":
                values[result_key] = safe_int(
                    source_value
                )

            else:
                values[result_key] = safe_float(
                    source_value
                )

    return values


def determine_registry_mode(
    active_exists: bool,
    paper_exists: bool,
    promotion_status: str,
    research_exists: bool,
) -> tuple[str, str]:
    """
    현재 전략 등록 상태를 결정합니다.
    """

    normalized_status = (
        promotion_status.strip().upper()
    )

    if (
        active_exists
        and normalized_status == "PROMOTED"
    ):
        return (
            "ACTIVE",
            "운영 전략 등록",
        )

    if (
        paper_exists
        and normalized_status == "PAPER_TRADING"
    ):
        return (
            "PAPER_TRADING",
            "모의투자 전략 등록",
        )

    if normalized_status == "BASELINE_RETAINED":
        return (
            "BASELINE",
            "기존 기준 전략 유지",
        )

    if (
        normalized_status == "RESEARCH_ARCHIVED"
        or research_exists
    ):
        return (
            "RESEARCH_ONLY",
            "연구 후보만 등록",
        )

    if active_exists:
        return (
            "ACTIVE",
            "운영 전략 등록",
        )

    if paper_exists:
        return (
            "PAPER_TRADING",
            "모의투자 전략 등록",
        )

    return (
        "UNREGISTERED",
        "등록된 전략 없음",
    )


def select_strategy_source(
    registry_mode: str,
    active_payload: dict[str, Any] | None,
    paper_payload: dict[str, Any] | None,
    research_payload: dict[str, Any] | None,
    promotion_payload: dict[str, Any] | None,
) -> tuple[
    str,
    str,
    dict[str, Any] | None,
]:
    """
    Registry가 대표해서 보여줄 전략 데이터를 선택합니다.
    """

    if (
        registry_mode == "ACTIVE"
        and active_payload
    ):
        return (
            "ACTIVE_STRATEGY",
            "ACTIVE",
            active_payload,
        )

    if (
        registry_mode == "PAPER_TRADING"
        and paper_payload
    ):
        return (
            "PAPER_STRATEGY",
            "PAPER_TRADING",
            paper_payload,
        )

    if registry_mode == "BASELINE":
        if promotion_payload:
            return (
                "PROMOTION_BASELINE",
                "BASELINE_RETAINED",
                promotion_payload,
            )

        return (
            "BASELINE_DEFAULT",
            "BASELINE",
            None,
        )

    if (
        registry_mode == "RESEARCH_ONLY"
        and research_payload
    ):
        return (
            "RESEARCH_ARCHIVE",
            "RESEARCH_ONLY",
            research_payload,
        )

    return (
        "NONE",
        "UNREGISTERED",
        None,
    )


def build_registry_notes(
    registry_mode: str,
    promotion_status: str,
    active_exists: bool,
    paper_exists: bool,
    research_count: int,
) -> tuple[
    list[str],
    list[str],
    list[str],
]:
    """
    등록 상태에 따른 설명과 다음 작업을 생성합니다.
    """

    reasons: list[str] = []
    warnings: list[str] = []
    next_actions: list[str] = []

    if registry_mode == "ACTIVE":
        reasons.append(
            "운영 전략 파일이 등록되어 있습니다."
        )

        next_actions.extend(
            [
                "운영 전략 파일의 변경 이력을 정기적으로 확인합니다.",
                "실제 주문 연결 전 별도의 수동 승인을 사용합니다.",
                "운영 결과와 기준 전략 결과를 함께 기록합니다.",
            ]
        )

    elif registry_mode == "PAPER_TRADING":
        reasons.append(
            "후보 전략이 모의투자 상태로 등록되어 있습니다."
        )

        next_actions.extend(
            [
                "모의투자 거래 기록을 누적합니다.",
                "최소 검증 기간이 끝난 후 운영 전략과 비교합니다.",
                "실제 주문 연결은 비활성 상태로 유지합니다.",
            ]
        )

    elif registry_mode == "BASELINE":
        reasons.append(
            "최근 승격 결과가 기존 기준 전략 유지를 지시했습니다."
        )

        reasons.append(
            "후보 전략이 기준 전략보다 우수하지 않아 "
            "운영 전략을 변경하지 않았습니다."
        )

        next_actions.extend(
            [
                "현재 기준 전략을 유지합니다.",
                "새로운 데이터가 누적된 후 후보를 다시 생성합니다.",
                "연구 후보 파일은 비교 자료로 보관합니다.",
            ]
        )

    elif registry_mode == "RESEARCH_ONLY":
        reasons.append(
            "운영 또는 모의투자 전략은 없지만 "
            "연구 후보가 저장되어 있습니다."
        )

        next_actions.extend(
            [
                "연구 후보를 추가 검증합니다.",
                "Walk-Forward 결과를 개선한 후 다시 평가합니다.",
                "승격 조건을 통과하기 전에는 운영에 적용하지 않습니다.",
            ]
        )

    else:
        warnings.append(
            "현재 등록 가능한 전략 파일을 찾지 못했습니다."
        )

        next_actions.extend(
            [
                "V8.4와 V8.5 단계를 먼저 실행합니다.",
                "전략 관리 폴더의 JSON 파일을 확인합니다.",
            ]
        )

    if active_exists and paper_exists:
        warnings.append(
            "운영 전략과 모의투자 전략이 동시에 존재합니다. "
            "각 전략의 역할을 구분해야 합니다."
        )

    if research_count > 1:
        warnings.append(
            f"연구 후보가 {research_count}개 저장되어 있습니다. "
            "중복 실행으로 생성된 파일이 포함될 수 있습니다."
        )

    if promotion_status == "FAILED":
        warnings.append(
            "최근 전략 승격 처리가 실패 상태입니다."
        )

    warnings.append(
        "Registry는 전략 상태를 조회하고 기록할 뿐 "
        "실제 증권 주문을 실행하지 않습니다."
    )

    return (
        reasons,
        warnings,
        next_actions,
    )


def run_active_strategy_registry(
    symbol: str = "AAPL",
) -> ActiveStrategyRegistryResult:
    """
    운영·모의투자·연구 전략을 통합 조회합니다.
    """

    normalized_symbol = normalize_symbol(
        symbol
    )

    active_path = find_active_strategy_file(
        normalized_symbol
    )

    paper_path = find_paper_strategy_file(
        normalized_symbol
    )

    promotion_path = find_latest_promotion_file(
        normalized_symbol
    )

    research_paths = find_research_candidate_files(
        normalized_symbol
    )

    latest_research_path = (
        research_paths[0]
        if research_paths
        else None
    )

    active_payload = (
        load_json_file(active_path)
        if active_path
        else None
    )

    paper_payload = (
        load_json_file(paper_path)
        if paper_path
        else None
    )

    promotion_payload = (
        load_json_file(promotion_path)
        if promotion_path
        else None
    )

    research_payload = (
        load_json_file(
            latest_research_path
        )
        if latest_research_path
        else None
    )

    promotion_status = str(
        (
            promotion_payload
            or {}
        ).get(
            "promotion_status",
            "UNKNOWN",
        )
    ).upper()

    promotion_decision = str(
        (
            promotion_payload
            or {}
        ).get(
            "source_decision",
            "UNKNOWN",
        )
    ).upper()

    promotion_label = str(
        (
            promotion_payload
            or {}
        ).get(
            "promotion_label",
            "",
        )
    )

    (
        registry_mode,
        registry_label,
    ) = determine_registry_mode(
        active_exists=active_path is not None,
        paper_exists=paper_path is not None,
        promotion_status=promotion_status,
        research_exists=bool(
            research_paths
        ),
    )

    (
        selected_strategy_source,
        selected_strategy_status,
        selected_payload,
    ) = select_strategy_source(
        registry_mode=registry_mode,
        active_payload=active_payload,
        paper_payload=paper_payload,
        research_payload=research_payload,
        promotion_payload=promotion_payload,
    )

    parameters = extract_parameters(
        selected_payload
    )

    (
        selected_strategy_name,
        selected_strategy_type,
    ) = extract_candidate_information(
        selected_payload
    )

    evaluation = extract_evaluation(
        strategy_payload=selected_payload,
        promotion_payload=promotion_payload,
    )

    registry_ready = (
        registry_mode
        in {
            "ACTIVE",
            "PAPER_TRADING",
            "BASELINE",
            "RESEARCH_ONLY",
        }
    )

    execution_enabled = False

    manual_approval_required = True

    (
        reasons,
        warnings,
        next_actions,
    ) = build_registry_notes(
        registry_mode=registry_mode,
        promotion_status=promotion_status,
        active_exists=active_path is not None,
        paper_exists=paper_path is not None,
        research_count=len(
            research_paths
        ),
    )

    result = ActiveStrategyRegistryResult(
        version="V8.6",
        symbol=normalized_symbol,
        created_at=datetime.now().isoformat(),

        registry_mode=registry_mode,
        registry_label=registry_label,

        active_strategy_exists=(
            active_path is not None
        ),

        paper_strategy_exists=(
            paper_path is not None
        ),

        promotion_result_exists=(
            promotion_path is not None
        ),

        research_candidates_exist=bool(
            research_paths
        ),

        active_strategy_file=(
            str(active_path)
            if active_path
            else None
        ),

        paper_strategy_file=(
            str(paper_path)
            if paper_path
            else None
        ),

        latest_promotion_file=(
            str(promotion_path)
            if promotion_path
            else None
        ),

        latest_research_file=(
            str(latest_research_path)
            if latest_research_path
            else None
        ),

        promotion_status=promotion_status,
        promotion_decision=promotion_decision,
        promotion_label=promotion_label,

        selected_strategy_source=(
            selected_strategy_source
        ),

        selected_strategy_status=(
            selected_strategy_status
        ),

        selected_strategy_name=(
            selected_strategy_name
        ),

        selected_strategy_type=(
            selected_strategy_type
        ),

        entry_score=parameters[
            "entry_score"
        ],

        exit_score=parameters[
            "exit_score"
        ],

        stop_atr_multiple=parameters[
            "stop_atr_multiple"
        ],

        target_atr_multiple=parameters[
            "target_atr_multiple"
        ],

        maximum_holding_days=parameters[
            "maximum_holding_days"
        ],

        position_percent=parameters[
            "position_percent"
        ],

        candidate_score=evaluation[
            "candidate_score"
        ],

        baseline_score=evaluation[
            "baseline_score"
        ],

        score_improvement=evaluation[
            "score_improvement"
        ],

        confidence_score=evaluation[
            "confidence_score"
        ],

        confidence_level=evaluation[
            "confidence_level"
        ],

        risk_score=evaluation[
            "risk_score"
        ],

        risk_level=evaluation[
            "risk_level"
        ],

        recommendation_strength=evaluation[
            "recommendation_strength"
        ],

        research_candidate_count=len(
            research_paths
        ),

        registry_ready=registry_ready,
        execution_enabled=execution_enabled,
        manual_approval_required=(
            manual_approval_required
        ),

        reasons=reasons,
        warnings=warnings,
        next_actions=next_actions,
    )

    print_active_strategy_registry(
        result
    )

    return result


def save_active_strategy_registry(
    result: ActiveStrategyRegistryResult,
) -> tuple[Path, Path]:
    """
    Registry 결과를 JSON 파일로 저장합니다.
    """

    REGISTRY_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    report_path = (
        REGISTRY_DIRECTORY
        / (
            f"{result.symbol}_"
            "active_strategy_registry_"
            f"{timestamp}.json"
        )
    )

    latest_path = (
        REGISTRY_DIRECTORY
        / (
            f"{result.symbol}_"
            "active_strategy_registry_latest.json"
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


def format_optional_number(
    value: float | int | None,
    decimal_places: int = 2,
) -> str:
    """
    None일 수 있는 숫자를 출력용 문자열로 변환합니다.
    """

    if value is None:
        return "None"

    if isinstance(
        value,
        int,
    ):
        return str(value)

    return f"{value:.{decimal_places}f}"


def print_active_strategy_registry(
    result: ActiveStrategyRegistryResult,
) -> None:
    """
    V8.6 Registry 결과를 출력합니다.
    """

    print()
    print("=" * 130)
    print(
        f"{result.symbol} V8.6 "
        "ACTIVE STRATEGY REGISTRY"
    )
    print("=" * 130)

    print(
        f"Registry mode                : "
        f"{result.registry_mode}"
    )

    print(
        f"Registry label               : "
        f"{result.registry_label}"
    )

    print(
        f"Registry ready               : "
        f"{result.registry_ready}"
    )

    print(
        f"Execution enabled            : "
        f"{result.execution_enabled}"
    )

    print(
        f"Manual approval required     : "
        f"{result.manual_approval_required}"
    )

    print()
    print("REGISTERED FILES")
    print("-" * 130)

    print(
        f"Active strategy exists       : "
        f"{result.active_strategy_exists}"
    )

    print(
        f"Paper strategy exists        : "
        f"{result.paper_strategy_exists}"
    )

    print(
        f"Promotion result exists      : "
        f"{result.promotion_result_exists}"
    )

    print(
        f"Research candidates exist    : "
        f"{result.research_candidates_exist}"
    )

    print(
        f"Research candidate count     : "
        f"{result.research_candidate_count}"
    )

    print()
    print("LATEST PROMOTION")
    print("-" * 130)

    print(
        f"Promotion status             : "
        f"{result.promotion_status}"
    )

    print(
        f"Promotion decision           : "
        f"{result.promotion_decision}"
    )

    print(
        f"Promotion label              : "
        f"{result.promotion_label}"
    )

    print()
    print("SELECTED STRATEGY")
    print("-" * 130)

    print(
        f"Strategy source              : "
        f"{result.selected_strategy_source}"
    )

    print(
        f"Strategy status              : "
        f"{result.selected_strategy_status}"
    )

    print(
        f"Strategy name                : "
        f"{result.selected_strategy_name}"
    )

    print(
        f"Strategy type                : "
        f"{result.selected_strategy_type}"
    )

    print()
    print("PARAMETERS")
    print("-" * 130)

    print(
        f"Entry score                  : "
        f"{format_optional_number(result.entry_score)}"
    )

    print(
        f"Exit score                   : "
        f"{format_optional_number(result.exit_score)}"
    )

    print(
        f"Stop ATR                     : "
        f"{format_optional_number(result.stop_atr_multiple)}"
    )

    print(
        f"Target ATR                   : "
        f"{format_optional_number(result.target_atr_multiple)}"
    )

    print(
        f"Maximum holding days         : "
        f"{format_optional_number(result.maximum_holding_days)}"
    )

    print(
        f"Position percent             : "
        f"{format_optional_number(result.position_percent)}%"
    )

    print()
    print("EVALUATION")
    print("-" * 130)

    print(
        f"Candidate score              : "
        f"{format_optional_number(result.candidate_score)}/100"
    )

    print(
        f"Baseline score               : "
        f"{format_optional_number(result.baseline_score)}/100"
    )

    improvement_text = (
        "None"
        if result.score_improvement is None
        else f"{result.score_improvement:+.2f} points"
    )

    print(
        f"Score improvement            : "
        f"{improvement_text}"
    )

    print(
        f"Confidence                   : "
        f"{format_optional_number(result.confidence_score)}/100 "
        f"({result.confidence_level})"
    )

    print(
        f"Risk                         : "
        f"{format_optional_number(result.risk_score)}/100 "
        f"({result.risk_level})"
    )

    print(
        f"Recommendation strength      : "
        f"{format_optional_number(result.recommendation_strength)}/5"
    )

    if result.reasons:
        print()
        print("REASONS")
        print("-" * 130)

        for reason in result.reasons:
            print(
                f"- {reason}"
            )

    if result.warnings:
        print()
        print("WARNINGS")
        print("-" * 130)

        for warning in result.warnings:
            print(
                f"- {warning}"
            )

    if result.next_actions:
        print()
        print("NEXT ACTIONS")
        print("-" * 130)

        for action in result.next_actions:
            print(
                f"- {action}"
            )

    print()
    print("FILES")
    print("-" * 130)

    print(
        f"Active strategy file         : "
        f"{result.active_strategy_file or 'None'}"
    )

    print(
        f"Paper strategy file          : "
        f"{result.paper_strategy_file or 'None'}"
    )

    print(
        f"Latest promotion file        : "
        f"{result.latest_promotion_file or 'None'}"
    )

    print(
        f"Latest research file         : "
        f"{result.latest_research_file or 'None'}"
    )

    print(
        f"Report file                  : "
        f"{result.report_path or 'Not saved yet'}"
    )

    print(
        f"Latest file                  : "
        f"{result.latest_path or 'Not saved yet'}"
    )

    print("=" * 130)

    print(
        "주의: Registry는 전략 파일의 상태를 관리하지만 "
        "실제 증권 주문이나 자동 매매를 실행하지 않습니다."
    )