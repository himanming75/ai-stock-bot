import json
import shutil
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODEL_DIRECTORY = PROJECT_ROOT / "models"
BACKUP_DIRECTORY = MODEL_DIRECTORY / "backups"


@dataclass
class ModelBackupResult:
    """
    기존 운영 모델의 백업 결과입니다.
    """

    symbol: str
    backup_created: bool

    source_model_path: str | None
    source_metadata_path: str | None

    backup_model_path: str | None
    backup_metadata_path: str | None

    backup_created_at: str
    message: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def normalize_symbol(
    symbol: str,
) -> str:
    """
    종목 코드를 대문자로 정리합니다.
    """

    normalized = (
        str(symbol)
        .upper()
        .strip()
    )

    if not normalized:
        raise ValueError(
            "종목 코드가 비어 있습니다."
        )

    return normalized


def ensure_directories() -> None:
    """
    모델 및 백업 폴더를 생성합니다.
    """

    MODEL_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    BACKUP_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )


def get_active_model_paths(
    symbol: str,
) -> tuple[Path, Path]:
    """
    현재 운영 중인 모델과 메타데이터 경로입니다.
    """

    normalized_symbol = normalize_symbol(
        symbol
    )

    ensure_directories()

    model_path = (
        MODEL_DIRECTORY
        / f"{normalized_symbol}_best_model.joblib"
    )

    metadata_path = (
        MODEL_DIRECTORY
        / f"{normalized_symbol}_best_model.json"
    )

    return model_path, metadata_path


def active_model_exists(
    symbol: str,
) -> bool:
    """
    현재 운영 모델이 존재하는지 확인합니다.
    """

    model_path, metadata_path = (
        get_active_model_paths(symbol)
    )

    return (
        model_path.exists()
        and metadata_path.exists()
    )


def build_backup_paths(
    symbol: str,
) -> tuple[Path, Path]:
    """
    날짜와 시간을 포함한 백업 파일 경로를 생성합니다.
    """

    normalized_symbol = normalize_symbol(
        symbol
    )

    ensure_directories()

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S_%f"
    )

    backup_model_path = (
        BACKUP_DIRECTORY
        / (
            f"{normalized_symbol}_best_model_"
            f"{timestamp}.joblib"
        )
    )

    backup_metadata_path = (
        BACKUP_DIRECTORY
        / (
            f"{normalized_symbol}_best_model_"
            f"{timestamp}.json"
        )
    )

    return (
        backup_model_path,
        backup_metadata_path,
    )


def backup_active_model(
    symbol: str,
) -> ModelBackupResult:
    """
    현재 운영 중인 모델과 메타데이터를 백업합니다.

    운영 모델이 없으면 오류를 발생시키지 않고
    backup_created=False를 반환합니다.
    """

    normalized_symbol = normalize_symbol(
        symbol
    )

    (
        source_model_path,
        source_metadata_path,
    ) = get_active_model_paths(
        normalized_symbol
    )

    created_at = datetime.now().isoformat()

    if not source_model_path.exists():
        return ModelBackupResult(
            symbol=normalized_symbol,
            backup_created=False,

            source_model_path=str(
                source_model_path
            ),

            source_metadata_path=str(
                source_metadata_path
            ),

            backup_model_path=None,
            backup_metadata_path=None,

            backup_created_at=created_at,

            message=(
                "현재 운영 모델 파일이 없어 "
                "백업을 생성하지 않았습니다."
            ),
        )

    (
        backup_model_path,
        backup_metadata_path,
    ) = build_backup_paths(
        normalized_symbol
    )

    shutil.copy2(
        source_model_path,
        backup_model_path,
    )

    if source_metadata_path.exists():
        shutil.copy2(
            source_metadata_path,
            backup_metadata_path,
        )

        metadata_backup_value: str | None = str(
            backup_metadata_path
        )

    else:
        metadata_backup_value = None

    return ModelBackupResult(
        symbol=normalized_symbol,
        backup_created=True,

        source_model_path=str(
            source_model_path
        ),

        source_metadata_path=str(
            source_metadata_path
        ),

        backup_model_path=str(
            backup_model_path
        ),

        backup_metadata_path=(
            metadata_backup_value
        ),

        backup_created_at=created_at,

        message=(
            "현재 운영 모델을 성공적으로 "
            "백업했습니다."
        ),
    )


def load_active_metadata(
    symbol: str,
) -> dict[str, Any] | None:
    """
    현재 운영 모델의 메타데이터를 불러옵니다.
    """

    _, metadata_path = get_active_model_paths(
        symbol
    )

    if not metadata_path.exists():
        return None

    try:
        with metadata_path.open(
            mode="r",
            encoding="utf-8",
        ) as file:
            data = json.load(file)

    except (
        OSError,
        json.JSONDecodeError,
    ):
        return None

    if not isinstance(
        data,
        dict,
    ):
        return None

    return data


def list_model_backups(
    symbol: str,
) -> list[dict[str, str | None]]:
    """
    특정 종목의 저장된 백업 목록을 반환합니다.
    """

    normalized_symbol = normalize_symbol(
        symbol
    )

    ensure_directories()

    model_pattern = (
        f"{normalized_symbol}_best_model_*.joblib"
    )

    model_files = sorted(
        BACKUP_DIRECTORY.glob(
            model_pattern
        ),
        reverse=True,
    )

    backups: list[
        dict[str, str | None]
    ] = []

    for model_path in model_files:
        metadata_path = (
            model_path.with_suffix(
                ".json"
            )
        )

        backups.append(
            {
                "model_path": str(
                    model_path
                ),

                "metadata_path": (
                    str(metadata_path)
                    if metadata_path.exists()
                    else None
                ),

                "modified_at": (
                    datetime.fromtimestamp(
                        model_path.stat().st_mtime
                    ).isoformat()
                ),
            }
        )

    return backups


def restore_latest_backup(
    symbol: str,
) -> dict[str, Any]:
    """
    가장 최근 백업을 현재 운영 모델로 복원합니다.
    """

    normalized_symbol = normalize_symbol(
        symbol
    )

    backups = list_model_backups(
        normalized_symbol
    )

    if not backups:
        raise FileNotFoundError(
            f"{normalized_symbol}의 모델 백업이 없습니다."
        )

    latest_backup = backups[0]

    backup_model_path = Path(
        str(
            latest_backup["model_path"]
        )
    )

    backup_metadata_value = (
        latest_backup["metadata_path"]
    )

    (
        active_model_path,
        active_metadata_path,
    ) = get_active_model_paths(
        normalized_symbol
    )

    shutil.copy2(
        backup_model_path,
        active_model_path,
    )

    if backup_metadata_value is not None:
        backup_metadata_path = Path(
            backup_metadata_value
        )

        shutil.copy2(
            backup_metadata_path,
            active_metadata_path,
        )

    return {
        "symbol": normalized_symbol,

        "restored_model_path": str(
            active_model_path
        ),

        "restored_metadata_path": str(
            active_metadata_path
        ),

        "source_backup_model": str(
            backup_model_path
        ),

        "source_backup_metadata": (
            backup_metadata_value
        ),

        "restored_at": (
            datetime.now().isoformat()
        ),
    }


def print_backup_result(
    result: ModelBackupResult,
) -> None:
    """
    백업 결과를 터미널에 출력합니다.
    """

    print()
    print("=" * 82)
    print(
        f"{result.symbol} MODEL BACKUP RESULT V4.8"
    )
    print("=" * 82)

    print(
        f"Backup created      : "
        f"{result.backup_created}"
    )

    print(
        f"Source model        : "
        f"{result.source_model_path or 'N/A'}"
    )

    print(
        f"Source metadata     : "
        f"{result.source_metadata_path or 'N/A'}"
    )

    print(
        f"Backup model        : "
        f"{result.backup_model_path or 'N/A'}"
    )

    print(
        f"Backup metadata     : "
        f"{result.backup_metadata_path or 'N/A'}"
    )

    print(
        f"Created at          : "
        f"{result.backup_created_at}"
    )

    print(
        f"Message             : "
        f"{result.message}"
    )

    print("=" * 82)