from __future__ import annotations

import argparse
import hashlib
import re
import shutil
from pathlib import Path


class PatchError(RuntimeError):
    pass


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_utf8(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as exc:
        raise PatchError(f"{path} is not valid UTF-8") from exc


def backup_once(path: Path, suffix: str) -> Path:
    backup = path.with_name(path.name + suffix)
    if not backup.exists():
        shutil.copy2(path, backup)
    return backup


def patch_predictor(path: Path) -> str:
    text = read_utf8(path)

    if "MODEL_RANDOM_SEED = 42" not in text:
        text, count = re.subn(
            r"(from sklearn\.model_selection import TimeSeriesSplit[^\r\n]*\r?\n)",
            r"\1\nMODEL_RANDOM_SEED = 42\nMODEL_N_JOBS = 1\n",
            text,
            count=1,
        )
        if count != 1:
            raise PatchError("could not insert deterministic model constants")

    if not re.search(r"(?m)^import random\s*$", text):
        text, count = re.subn(
            r"(?m)^(import math\s*)$",
            r"\1\nimport random",
            text,
            count=1,
        )
        if count != 1:
            raise PatchError("could not insert import random")

    text, state_count = re.subn(
        r"random_state\s*=\s*42\s*,",
        "random_state=MODEL_RANDOM_SEED,",
        text,
    )
    if state_count == 0 and "random_state=MODEL_RANDOM_SEED" not in text:
        raise PatchError("could not patch RandomForest random_state")

    text, jobs_count = re.subn(
        r"n_jobs\s*=\s*-1\s*,",
        "n_jobs=MODEL_N_JOBS,",
        text,
    )
    if jobs_count == 0 and "n_jobs=MODEL_N_JOBS" not in text:
        raise PatchError("could not patch RandomForest n_jobs")

    if "random.seed(MODEL_RANDOM_SEED)" not in text:
        function_index = text.find("def predict_stock_direction")
        if function_index == -1:
            raise PatchError("could not locate predict_stock_direction")
        match = re.search(
            r"(?m)^    symbol\s*=",
            text[function_index:],
        )
        if not match:
            raise PatchError("could not locate prediction symbol normalization")
        idx = function_index + match.start()
        insertion = (
            "    random.seed(MODEL_RANDOM_SEED)\n"
            "    np.random.seed(MODEL_RANDOM_SEED)\n\n"
        )
        text = text[:idx] + insertion + text[idx:]

    required = [
        "import random",
        "MODEL_RANDOM_SEED = 42",
        "MODEL_N_JOBS = 1",
        "random_state=MODEL_RANDOM_SEED",
        "n_jobs=MODEL_N_JOBS",
        "random.seed(MODEL_RANDOM_SEED)",
        "np.random.seed(MODEL_RANDOM_SEED)",
    ]
    missing = [item for item in required if item not in text]
    if missing:
        raise PatchError("predictor patch incomplete: " + ", ".join(missing))

    compile(text, str(path), "exec")
    return text


DETERMINISTIC_TEST_ML = '''from pathlib import Path

import pandas as pd

from data.market import get_history
from ml.predictor import (
    predict_stock_direction,
    print_ml_prediction,
)


symbol = "AAPL"

cache_directory = Path("release/v76_4/runtime_cache")
cache_directory.mkdir(parents=True, exist_ok=True)

cache_path = cache_directory / "AAPL_5y_1d_v76_4b.csv"

if cache_path.exists():
    data = pd.read_csv(
        cache_path,
        index_col="Date",
        parse_dates=["Date"],
    )
else:
    data = get_history(
        symbol=symbol,
        period="5y",
        interval="1d",
    )
    data = data.sort_index()
    data = data[~data.index.duplicated(keep="last")]
    data.to_csv(
        cache_path,
        index=True,
        date_format="%Y-%m-%d",
        float_format="%.17g",
    )
    data = pd.read_csv(
        cache_path,
        index_col="Date",
        parse_dates=["Date"],
    )

prediction = predict_stock_direction(
    symbol=symbol,
    data=data,
    horizon_days=5,
    minimum_return=0.0,
)

print_ml_prediction(
    prediction
)
'''


def patch_test_ml(path: Path) -> str:
    existing = read_utf8(path)
    if "AAPL_5y_1d_v76_4b.csv" in existing:
        return existing
    compile(DETERMINISTIC_TEST_ML, str(path), "exec")
    return DETERMINISTIC_TEST_ML


def patch_market(path: Path) -> str:
    text = read_utf8(path)

    if "threads=False" not in text:
        text, count = re.subn(
            r"(progress\s*=\s*False\s*,)",
            r"\1\n        threads=False,",
            text,
            count=1,
        )
        if count != 1:
            raise PatchError("could not set yfinance threads=False")

    if "data = data.sort_index()" not in text:
        anchor = '    data.index.name = "Date"\n'
        if anchor not in text:
            raise PatchError("could not locate market index normalization")
        text = text.replace(
            anchor,
            anchor
            + "\n    data = data.sort_index()\n"
            + '    data = data[~data.index.duplicated(keep="last")]\n',
            1,
        )

    compile(text, str(path), "exec")
    return text


def write_if_changed(path: Path, text: str) -> bool:
    old = read_utf8(path)
    if old == text:
        return False
    path.write_text(text, encoding="utf-8", newline="\n")
    return True


def apply(repository_root: Path) -> dict:
    root = repository_root.resolve()
    predictor = root / "ml" / "predictor.py"
    test_ml = root / "test_ml.py"
    market = root / "data" / "market.py"

    for path in (predictor, test_ml, market):
        if not path.is_file():
            raise PatchError(f"missing required file: {path}")

    backups = [
        backup_once(predictor, ".v76_4b_backup"),
        backup_once(test_ml, ".v76_4b_backup"),
        backup_once(market, ".v76_4b_backup"),
    ]

    changed = {
        "ml/predictor.py": write_if_changed(predictor, patch_predictor(predictor)),
        "test_ml.py": write_if_changed(test_ml, patch_test_ml(test_ml)),
        "data/market.py": write_if_changed(market, patch_market(market)),
    }

    return {
        "status": "PATCHED" if any(changed.values()) else "ALREADY_PATCHED",
        "changed": changed,
        "backups": [str(p.relative_to(root)) for p in backups],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    args = parser.parse_args()

    try:
        result = apply(Path(args.repository_root))
    except (PatchError, OSError, SyntaxError) as exc:
        print("STATUS: FAIL")
        print(f"ERROR: {exc}")
        return 1

    print(f"STATUS: {result['status']}")
    for path, changed in result["changed"].items():
        print(f"{path}: {'CHANGED' if changed else 'UNCHANGED'}")
    print("BACKUPS:")
    for backup in result["backups"]:
        print(f"- {backup}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
