
from __future__ import annotations

from urllib.request import urlopen
import argparse


REQUIRED_KOREAN_LABELS = (
    "시스템 상태",
    "계좌 평가금액",
    "현재 보유 포지션",
    "일별 실현손익",
    "누적 성과 및 거래 분석",
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--url",
        default="http://127.0.0.1:8879/",
    )
    args = parser.parse_args()

    with urlopen(
        args.url,
        timeout=20,
    ) as response:
        raw = response.read()

    html = raw.decode(
        "utf-8",
        errors="strict",
    )

    missing = [
        label
        for label in REQUIRED_KOREAN_LABELS
        if label not in html
    ]

    print(
        "UTF8_HTML_DECODE: PASS"
    )
    print(
        "KOREAN_LABEL_COUNT:",
        len(REQUIRED_KOREAN_LABELS)
        - len(missing),
    )
    print(
        "KOREAN_LABEL_REQUIRED:",
        len(REQUIRED_KOREAN_LABELS),
    )

    if missing:
        print(
            "MISSING_KOREAN_LABELS:",
            repr(missing),
        )
        return 2

    print(
        "KOREAN_BILINGUAL_UI: PASS"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
