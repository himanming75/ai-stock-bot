from ml.model_registry import (
    active_model_exists,
    backup_active_model,
    list_model_backups,
    load_active_metadata,
    print_backup_result,
)


def main() -> None:
    """
    V4.8 모델 백업 시스템 테스트입니다.

    이 테스트는 현재 운영 모델을 복사하여
    backups 폴더에 저장하지만,
    현재 운영 모델 자체는 변경하지 않습니다.
    """

    symbol = "AAPL"

    print()
    print("=" * 82)
    print("AI STOCK BOT V4.8 MODEL REGISTRY TEST")
    print("=" * 82)

    exists = active_model_exists(
        symbol
    )

    print(
        f"Active model exists : "
        f"{exists}"
    )

    if not exists:
        print(
            "현재 저장된 AAPL 운영 모델이 없습니다."
        )

        print(
            "먼저 test_model_trainer.py를 실행하세요."
        )

        return

    metadata = load_active_metadata(
        symbol
    )

    if metadata is not None:
        print(
            f"Current model       : "
            f"{metadata.get('model_name', 'N/A')}"
        )

        print(
            f"Balanced accuracy   : "
            f"{float(metadata.get('balanced_accuracy', 0.0)):.2f}%"
        )

    backup_result = backup_active_model(
        symbol
    )

    print_backup_result(
        backup_result
    )

    backups = list_model_backups(
        symbol
    )

    print()
    print("=" * 82)
    print("SAVED MODEL BACKUPS")
    print("=" * 82)

    print(
        f"Backup count        : "
        f"{len(backups)}"
    )

    for index, backup in enumerate(
        backups,
        start=1,
    ):
        print()
        print(
            f"[{index}] Model      : "
            f"{backup['model_path']}"
        )

        print(
            f"    Metadata   : "
            f"{backup['metadata_path'] or 'N/A'}"
        )

        print(
            f"    Modified   : "
            f"{backup['modified_at']}"
        )

    print()
    print(
        "V4.8 model registry test "
        "completed successfully."
    )


if __name__ == "__main__":
    main()