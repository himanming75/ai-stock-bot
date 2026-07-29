from __future__ import annotations

"""
V28.4 Offline Hyperparameter Optimization Engine

Features:
- grid search
- deterministic random search
- parameter-space validation
- trial IDs and parameter hashes
- duplicate-trial prevention
- score ranking
- best-parameter selection
- optional early stopping
- search history
- SHA-256 integrity verification
- JSON persistence and tamper detection

Safety boundary:
- no network access
- no market/account/broker APIs
- no order creation/submission
- no live execution
"""

from dataclasses import dataclass, replace
from decimal import Decimal, ROUND_HALF_UP
from hashlib import sha256
from itertools import product
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping
import json
import random

VERSION = "28.4"
ZERO = Decimal("0")
SIX = Decimal("0.000001")


class HyperoptError(ValueError):
    pass


def _d(value: Any) -> Decimal:
    try:
        result = Decimal(str(value))
    except Exception as exc:
        raise HyperoptError(f"invalid decimal value: {value!r}") from exc
    if not result.is_finite():
        raise HyperoptError("decimal value must be finite")
    return result


def _q(value: Any) -> Decimal:
    return _d(value).quantize(SIX, rounding=ROUND_HALF_UP)


def _canonical(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _hash(payload: Any) -> str:
    return sha256(_canonical(payload).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class SearchPolicy:
    mode: str = "GRID"
    max_trials: int = 100
    random_seed: int = 42
    early_stopping_rounds: int = 0
    min_improvement: Decimal = Decimal("0.000001")

    def __post_init__(self) -> None:
        if self.mode.upper() not in {"GRID", "RANDOM"}:
            raise HyperoptError("unsupported search mode")
        if self.max_trials <= 0:
            raise HyperoptError("max_trials must be positive")
        if self.early_stopping_rounds < 0:
            raise HyperoptError("early_stopping_rounds cannot be negative")
        if _d(self.min_improvement) < ZERO:
            raise HyperoptError("min_improvement cannot be negative")


@dataclass(frozen=True)
class Trial:
    trial_id: str
    parameters: tuple[tuple[str, str], ...]
    parameter_hash: str
    score: Decimal
    rank: int
    trial_hash: str


@dataclass(frozen=True)
class SearchResult:
    version: str
    mode: str
    trials: tuple[Trial, ...]
    ranking: tuple[str, ...]
    best_trial_id: str
    best_parameters: tuple[tuple[str, str], ...]
    early_stopped: bool
    search_space_hash: str
    result_hash: str


def _trial_payload(trial: Trial, include_hash: bool = False) -> dict[str, Any]:
    payload = {
        "trial_id": trial.trial_id,
        "parameters": dict(trial.parameters),
        "parameter_hash": trial.parameter_hash,
        "score": str(trial.score),
        "rank": trial.rank,
    }
    if include_hash:
        payload["trial_hash"] = trial.trial_hash
    return payload


def _result_payload(result: SearchResult, include_hash: bool = False) -> dict[str, Any]:
    payload = {
        "version": result.version,
        "mode": result.mode,
        "trials": [_trial_payload(item, include_hash=True) for item in result.trials],
        "ranking": list(result.ranking),
        "best_trial_id": result.best_trial_id,
        "best_parameters": dict(result.best_parameters),
        "early_stopped": result.early_stopped,
        "search_space_hash": result.search_space_hash,
    }
    if include_hash:
        payload["result_hash"] = result.result_hash
    return payload


def _validate_parameter(name: str, value: Any) -> str:
    key = name.strip()
    if not key:
        raise HyperoptError("parameter name cannot be empty")

    if key == "learning_rate":
        if _d(value) <= ZERO:
            raise HyperoptError("learning_rate must be positive")
    elif key in {"depth", "trees", "epochs", "patience", "max_features"}:
        try:
            integer = int(value)
        except Exception as exc:
            raise HyperoptError(f"{key} must be an integer") from exc
        if integer <= 0:
            raise HyperoptError(f"{key} must be positive")
    elif key in {"l2_strength", "dropout"}:
        decimal_value = _d(value)
        if decimal_value < ZERO:
            raise HyperoptError(f"{key} cannot be negative")
        if key == "dropout" and decimal_value >= Decimal("1"):
            raise HyperoptError("dropout must be below 1")

    return str(value)


def validate_search_space(
    search_space: Mapping[str, Iterable[Any]],
) -> tuple[tuple[str, tuple[str, ...]], ...]:
    if not search_space:
        raise HyperoptError("search space cannot be empty")

    normalized = []
    seen_names = set()

    for name, values in search_space.items():
        key = str(name).strip()
        if key in seen_names:
            raise HyperoptError("duplicate parameter name detected")
        seen_names.add(key)

        normalized_values = tuple(
            _validate_parameter(key, value)
            for value in values
        )
        if not normalized_values:
            raise HyperoptError(f"parameter {key} has no candidate values")
        if len(normalized_values) != len(set(normalized_values)):
            raise HyperoptError(f"parameter {key} contains duplicate values")
        normalized.append((key, normalized_values))

    return tuple(sorted(normalized))


def generate_combinations(
    search_space: Mapping[str, Iterable[Any]],
) -> tuple[tuple[tuple[str, str], ...], ...]:
    normalized = validate_search_space(search_space)
    names = [name for name, _ in normalized]
    values = [items for _, items in normalized]
    return tuple(
        tuple(zip(names, combination))
        for combination in product(*values)
    )


def _make_trial(
    parameters: tuple[tuple[str, str], ...],
    score: Any,
    rank: int = 0,
) -> Trial:
    parameter_hash = _hash(dict(parameters))
    trial_id = f"TRIAL-{parameter_hash[:16].upper()}"
    trial = Trial(
        trial_id=trial_id,
        parameters=parameters,
        parameter_hash=parameter_hash,
        score=_q(score),
        rank=rank,
        trial_hash="",
    )
    return replace(trial, trial_hash=_hash(_trial_payload(trial)))


def verify_trial(trial: Trial) -> bool:
    if not trial.trial_id.startswith("TRIAL-"):
        raise HyperoptError("invalid trial ID")
    if trial.parameter_hash != _hash(dict(trial.parameters)):
        raise HyperoptError("parameter hash mismatch")
    if trial.trial_id != f"TRIAL-{trial.parameter_hash[:16].upper()}":
        raise HyperoptError("trial ID does not match parameter hash")
    if trial.rank < 0:
        raise HyperoptError("trial rank cannot be negative")

    clean = replace(trial, trial_hash="")
    if trial.trial_hash != _hash(_trial_payload(clean)):
        raise HyperoptError("trial hash mismatch")
    return True


def run_search(
    search_space: Mapping[str, Iterable[Any]],
    objective: Callable[[Mapping[str, str]], Any],
    policy: SearchPolicy | None = None,
) -> SearchResult:
    selected = policy or SearchPolicy()
    combinations = list(generate_combinations(search_space))

    if selected.mode.upper() == "RANDOM":
        rng = random.Random(selected.random_seed)
        rng.shuffle(combinations)

    combinations = combinations[:selected.max_trials]
    if not combinations:
        raise HyperoptError("no trials generated")

    trials = []
    seen_hashes = set()
    best_score = None
    no_improvement = 0
    early_stopped = False

    for parameters in combinations:
        parameter_hash = _hash(dict(parameters))
        if parameter_hash in seen_hashes:
            raise HyperoptError("duplicate trial detected")
        seen_hashes.add(parameter_hash)

        score = _q(objective(dict(parameters)))
        trial = _make_trial(parameters, score)
        trials.append(trial)

        if best_score is None or score - best_score > _d(selected.min_improvement):
            best_score = score
            no_improvement = 0
        else:
            no_improvement += 1

        if (
            selected.early_stopping_rounds > 0
            and no_improvement >= selected.early_stopping_rounds
        ):
            early_stopped = True
            break

    ranked = sorted(
        trials,
        key=lambda item: (item.score, item.trial_id),
        reverse=True,
    )

    ranked_trials = []
    for rank, trial in enumerate(ranked, start=1):
        updated = replace(trial, rank=rank, trial_hash="")
        updated = replace(updated, trial_hash=_hash(_trial_payload(updated)))
        ranked_trials.append(updated)

    ranking = tuple(item.trial_id for item in ranked_trials)
    best = ranked_trials[0]
    normalized_space = validate_search_space(search_space)

    result = SearchResult(
        version=VERSION,
        mode=selected.mode.upper(),
        trials=tuple(ranked_trials),
        ranking=ranking,
        best_trial_id=best.trial_id,
        best_parameters=best.parameters,
        early_stopped=early_stopped,
        search_space_hash=_hash({
            "space": {name: list(values) for name, values in normalized_space},
            "policy": {key: str(value) for key, value in selected.__dict__.items()},
        }),
        result_hash="",
    )
    return replace(result, result_hash=_hash(_result_payload(result)))


def verify_result(result: SearchResult) -> bool:
    if result.version != VERSION:
        raise HyperoptError("unsupported search-result version")
    if result.mode not in {"GRID", "RANDOM"}:
        raise HyperoptError("invalid search mode")
    if not result.trials:
        raise HyperoptError("search result cannot be empty")

    for trial in result.trials:
        verify_trial(trial)

    if len({trial.trial_id for trial in result.trials}) != len(result.trials):
        raise HyperoptError("duplicate trial IDs detected")
    if len({trial.parameter_hash for trial in result.trials}) != len(result.trials):
        raise HyperoptError("duplicate parameter hashes detected")

    expected = tuple(
        trial.trial_id
        for trial in sorted(
            result.trials,
            key=lambda item: (item.score, item.trial_id),
            reverse=True,
        )
    )
    if result.ranking != expected:
        raise HyperoptError("ranking mismatch")
    if result.best_trial_id != expected[0]:
        raise HyperoptError("best trial mismatch")
    best_trial = next(
        trial for trial in result.trials
        if trial.trial_id == result.best_trial_id
    )
    if result.best_parameters != best_trial.parameters:
        raise HyperoptError("best parameters mismatch")

    clean = replace(result, result_hash="")
    if result.result_hash != _hash(_result_payload(clean)):
        raise HyperoptError("search-result hash mismatch")
    return True


def save_result(result: SearchResult, path: str | Path) -> Path:
    verify_result(result)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(_result_payload(result, include_hash=True), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return target


def load_result(path: str | Path) -> SearchResult:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    trials = tuple(
        Trial(
            trial_id=item["trial_id"],
            parameters=tuple(sorted(item["parameters"].items())),
            parameter_hash=item["parameter_hash"],
            score=_d(item["score"]),
            rank=int(item["rank"]),
            trial_hash=item["trial_hash"],
        )
        for item in payload["trials"]
    )
    result = SearchResult(
        version=payload["version"],
        mode=payload["mode"],
        trials=trials,
        ranking=tuple(payload["ranking"]),
        best_trial_id=payload["best_trial_id"],
        best_parameters=tuple(sorted(payload["best_parameters"].items())),
        early_stopped=bool(payload["early_stopped"]),
        search_space_hash=payload["search_space_hash"],
        result_hash=payload["result_hash"],
    )
    verify_result(result)
    return result


MARKET_DATA_API_CALLED = False
ACCOUNT_API_CALLED = False
NETWORK_ACCESSED = False
BROKER_API_CALLED = False
BROKER_ORDER_CREATED = False
ORDER_SUBMITTED = False
LIVE_EXECUTION_AUTHORIZED = False
FUNDS_RESERVED = False
HOLDINGS_RESERVED = False
