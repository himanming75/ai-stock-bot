from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal, ROUND_HALF_UP
from hashlib import sha256
from math import log
from pathlib import Path
from typing import Any, Iterable, Mapping
import json

VERSION = "27.5"
ZERO = Decimal("0")
FOUR = Decimal("0.0001")


class FeatureSelectionError(ValueError):
    pass


def _d(value: Any) -> Decimal:
    try:
        result = Decimal(str(value))
    except Exception as exc:
        raise FeatureSelectionError(f"invalid decimal value: {value!r}") from exc
    if not result.is_finite():
        raise FeatureSelectionError("decimal value must be finite")
    return result


def _q(value: Any) -> Decimal:
    return _d(value).quantize(FOUR, rounding=ROUND_HALF_UP)


def _canonical(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _hash(payload: Any) -> str:
    return sha256(_canonical(payload).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class FeatureMatrix:
    feature_names: tuple[str, ...]
    rows: tuple[tuple[Decimal, ...], ...]
    labels: tuple[int, ...]


@dataclass(frozen=True)
class SelectionPolicy:
    variance_threshold: Decimal = Decimal("0.0001")
    correlation_threshold: Decimal = Decimal("0.95")
    max_features: int = 20
    mi_bins: int = 5
    correlation_weight: Decimal = Decimal("0.40")
    mutual_information_weight: Decimal = Decimal("0.40")
    external_importance_weight: Decimal = Decimal("0.20")

    def __post_init__(self) -> None:
        if _d(self.variance_threshold) < ZERO:
            raise FeatureSelectionError("variance_threshold cannot be negative")
        threshold = _d(self.correlation_threshold)
        if threshold <= ZERO or threshold > Decimal("1"):
            raise FeatureSelectionError("correlation_threshold must be within (0, 1]")
        if self.max_features <= 0:
            raise FeatureSelectionError("max_features must be positive")
        if self.mi_bins < 2:
            raise FeatureSelectionError("mi_bins must be at least 2")
        weights = (
            _d(self.correlation_weight),
            _d(self.mutual_information_weight),
            _d(self.external_importance_weight),
        )
        if any(weight < ZERO for weight in weights) or sum(weights, ZERO) <= ZERO:
            raise FeatureSelectionError("invalid ranking weights")


@dataclass(frozen=True)
class FeatureScore:
    feature: str
    variance: Decimal
    label_correlation: Decimal
    mutual_information: Decimal
    external_importance: Decimal
    composite_score: Decimal
    selected: bool
    removal_reason: str


@dataclass(frozen=True)
class SelectionResult:
    version: str
    selected_features: tuple[str, ...]
    removed_features: tuple[str, ...]
    scores: tuple[FeatureScore, ...]
    input_hash: str
    selection_hash: str


def _score_payload(score: FeatureScore) -> dict[str, Any]:
    return {
        "feature": score.feature,
        "variance": str(score.variance),
        "label_correlation": str(score.label_correlation),
        "mutual_information": str(score.mutual_information),
        "external_importance": str(score.external_importance),
        "composite_score": str(score.composite_score),
        "selected": score.selected,
        "removal_reason": score.removal_reason,
    }


def _result_payload(result: SelectionResult, include_hash: bool = False) -> dict[str, Any]:
    payload = {
        "version": result.version,
        "selected_features": list(result.selected_features),
        "removed_features": list(result.removed_features),
        "scores": [_score_payload(score) for score in result.scores],
        "input_hash": result.input_hash,
    }
    if include_hash:
        payload["selection_hash"] = result.selection_hash
    return payload


def _normalize_matrix(matrix: FeatureMatrix) -> FeatureMatrix:
    names = tuple(name.strip() for name in matrix.feature_names)
    if not names or any(not name for name in names):
        raise FeatureSelectionError("feature names are required")
    if len(names) != len(set(names)):
        raise FeatureSelectionError("duplicate feature names detected")
    if not matrix.rows:
        raise FeatureSelectionError("feature rows cannot be empty")
    if len(matrix.rows) != len(matrix.labels):
        raise FeatureSelectionError("row and label counts must match")
    width = len(names)
    rows = []
    for row in matrix.rows:
        if len(row) != width:
            raise FeatureSelectionError("inconsistent feature width")
        rows.append(tuple(_d(value) for value in row))
    labels = tuple(int(label) for label in matrix.labels)
    if len(set(labels)) < 2:
        raise FeatureSelectionError("at least two label classes are required")
    return FeatureMatrix(names, tuple(rows), labels)


def _variance_raw(values: list[Decimal]) -> Decimal:
    avg = sum(values, ZERO) / Decimal(len(values))
    return sum((value - avg) ** 2 for value in values) / Decimal(len(values))


def _pearson(left: list[Decimal], right: list[Decimal]) -> Decimal:
    left_avg = sum(left, ZERO) / Decimal(len(left))
    right_avg = sum(right, ZERO) / Decimal(len(right))
    numerator = sum((x-left_avg)*(y-right_avg) for x,y in zip(left,right))
    left_ss = sum((x-left_avg)**2 for x in left)
    right_ss = sum((y-right_avg)**2 for y in right)
    if left_ss == ZERO or right_ss == ZERO:
        return ZERO
    return _q(numerator / _d(float(left_ss * right_ss) ** 0.5))


def _quantile_bins(values: list[Decimal], bins: int) -> list[int]:
    ordered = sorted(values)
    cutoffs = [ordered[int(round(i*(len(ordered)-1)/bins))] for i in range(1,bins)]
    output = []
    for value in values:
        bucket = 0
        while bucket < len(cutoffs) and value > cutoffs[bucket]:
            bucket += 1
        output.append(bucket)
    return output


def _mutual_information(values: list[Decimal], labels: tuple[int,...], bins: int) -> Decimal:
    x_bins = _quantile_bins(values, bins)
    total = len(values)
    joint, xc, yc = {}, {}, {}
    for x,y in zip(x_bins, labels):
        joint[(x,y)] = joint.get((x,y),0)+1
        xc[x] = xc.get(x,0)+1
        yc[y] = yc.get(y,0)+1
    mi = 0.0
    for (x,y), count in joint.items():
        pxy = count/total
        mi += pxy * log(pxy / ((xc[x]/total)*(yc[y]/total)))
    return _q(mi)


def select_features(
    matrix: FeatureMatrix,
    policy: SelectionPolicy | None = None,
    external_importance: Mapping[str, Any] | None = None,
) -> SelectionResult:
    p = policy or SelectionPolicy()
    data = _normalize_matrix(matrix)
    external = {k:_q(v) for k,v in (external_importance or {}).items()}
    if set(external)-set(data.feature_names):
        raise FeatureSelectionError("external importance contains unknown features")
    if any(v < ZERO for v in external.values()):
        raise FeatureSelectionError("external importance cannot be negative")

    label_values = [_d(v) for v in data.labels]
    columns = {name:[row[i] for row in data.rows] for i,name in enumerate(data.feature_names)}
    raw, reasons = {}, {}

    for name in data.feature_names:
        values = columns[name]
        variance_raw = _variance_raw(values)
        raw[name] = {
            "variance": _q(variance_raw),
            "correlation": abs(_pearson(values,label_values)),
            "mi": _mutual_information(values,data.labels,p.mi_bins),
            "external": external.get(name,ZERO),
        }
        if len(set(values)) == 1:
            reasons[name] = "CONSTANT"
        elif variance_raw < _d(p.variance_threshold):
            reasons[name] = "LOW_VARIANCE"

    surviving = [n for n in data.feature_names if n not in reasons]

    for i,left in enumerate(list(surviving)):
        if left in reasons:
            continue
        for right in surviving[i+1:]:
            if right in reasons:
                continue
            if columns[left] == columns[right]:
                reasons[right] = f"DUPLICATE_OF:{left}"

    surviving = [n for n in surviving if n not in reasons]

    for i,left in enumerate(list(surviving)):
        if left in reasons:
            continue
        for right in surviving[i+1:]:
            if right in reasons:
                continue
            if abs(_pearson(columns[left],columns[right])) >= _d(p.correlation_threshold):
                left_rank=(raw[left]["correlation"],raw[left]["mi"],raw[left]["external"],left)
                right_rank=(raw[right]["correlation"],raw[right]["mi"],raw[right]["external"],right)
                loser = right if left_rank >= right_rank else left
                winner = left if loser == right else right
                reasons[loser]=f"HIGH_CORRELATION_WITH:{winner}"

    surviving=[n for n in surviving if n not in reasons]
    corr_max=max((raw[n]["correlation"] for n in surviving),default=ZERO)
    mi_max=max((raw[n]["mi"] for n in surviving),default=ZERO)
    ext_max=max((raw[n]["external"] for n in surviving),default=ZERO)
    weight_total=_d(p.correlation_weight)+_d(p.mutual_information_weight)+_d(p.external_importance_weight)

    composite={}
    for n in surviving:
        c=raw[n]["correlation"]/corr_max if corr_max else ZERO
        mi=raw[n]["mi"]/mi_max if mi_max else ZERO
        e=raw[n]["external"]/ext_max if ext_max else ZERO
        composite[n]=_q((c*_d(p.correlation_weight)+mi*_d(p.mutual_information_weight)+e*_d(p.external_importance_weight))/weight_total)

    ranked=sorted(surviving,key=lambda n:(composite[n],raw[n]["correlation"],raw[n]["mi"],raw[n]["external"],n),reverse=True)
    selected=tuple(ranked[:p.max_features])
    for n in ranked[p.max_features:]:
        reasons[n]="MAX_FEATURE_LIMIT"

    selected_set=set(selected)
    scores=tuple(
        FeatureScore(
            feature=n,
            variance=raw[n]["variance"],
            label_correlation=raw[n]["correlation"],
            mutual_information=raw[n]["mi"],
            external_importance=raw[n]["external"],
            composite_score=composite.get(n,ZERO),
            selected=n in selected_set,
            removal_reason="" if n in selected_set else reasons.get(n,"NOT_SELECTED"),
        )
        for n in sorted(data.feature_names)
    )
    removed=tuple(s.feature for s in scores if not s.selected)
    result=SelectionResult(
        VERSION,selected,removed,scores,
        _hash({
            "feature_names":list(data.feature_names),
            "rows":[[str(v) for v in row] for row in data.rows],
            "labels":list(data.labels),
            "policy":{k:str(v) for k,v in p.__dict__.items()},
            "external":{k:str(v) for k,v in sorted(external.items())},
        }),
        "",
    )
    return replace(result,selection_hash=_hash(_result_payload(result)))


def verify_result(result: SelectionResult) -> bool:
    if result.version != VERSION:
        raise FeatureSelectionError("unsupported selection version")
    if not result.selected_features:
        raise FeatureSelectionError("at least one feature must be selected")
    if len(result.selected_features)!=len(set(result.selected_features)):
        raise FeatureSelectionError("duplicate selected features")
    if set(result.selected_features)&set(result.removed_features):
        raise FeatureSelectionError("selected and removed overlap")
    if tuple(s.feature for s in result.scores)!=tuple(sorted(s.feature for s in result.scores)):
        raise FeatureSelectionError("scores must be sorted")
    if {s.feature for s in result.scores if s.selected} != set(result.selected_features):
        raise FeatureSelectionError("score selection mismatch")
    clean=replace(result,selection_hash="")
    if result.selection_hash != _hash(_result_payload(clean)):
        raise FeatureSelectionError("selection hash mismatch")
    return True


def save_result(result: SelectionResult, path: str|Path) -> Path:
    verify_result(result)
    target=Path(path)
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(_result_payload(result,True),indent=2,sort_keys=True),encoding="utf-8")
    return target


def load_result(path: str|Path) -> SelectionResult:
    payload=json.loads(Path(path).read_text(encoding="utf-8"))
    result=SelectionResult(
        payload["version"],
        tuple(payload["selected_features"]),
        tuple(payload["removed_features"]),
        tuple(FeatureScore(
            i["feature"],_d(i["variance"]),_d(i["label_correlation"]),
            _d(i["mutual_information"]),_d(i["external_importance"]),
            _d(i["composite_score"]),bool(i["selected"]),i["removal_reason"]
        ) for i in payload["scores"]),
        payload["input_hash"],payload["selection_hash"]
    )
    verify_result(result)
    return result


MARKET_DATA_API_CALLED=False
ACCOUNT_API_CALLED=False
NETWORK_ACCESSED=False
BROKER_API_CALLED=False
BROKER_ORDER_CREATED=False
ORDER_SUBMITTED=False
LIVE_EXECUTION_AUTHORIZED=False
FUNDS_RESERVED=False
HOLDINGS_RESERVED=False
