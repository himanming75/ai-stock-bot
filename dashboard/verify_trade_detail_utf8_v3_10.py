
from __future__ import annotations

from urllib.request import urlopen
import argparse

REQUIRED = (
    "정식 거래 상세",
    "정식 거래 상세 및 라이프사이클",
    "진입시간",
    "청산시간",
    "평균 보유시간",
    "필터 초기화",
    "주문 ID",
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8880/")
    args = parser.parse_args()

    with urlopen(args.url, timeout=20) as response:
        html = response.read().decode("utf-8", errors="strict")

    missing = [value for value in REQUIRED if value not in html]

    print("UTF8_HTML_DECODE: PASS")
    print("V3_10_KOREAN_LABEL_COUNT:", len(REQUIRED)-len(missing))
    print("V3_10_KOREAN_LABEL_REQUIRED:", len(REQUIRED))

    if missing:
        print("MISSING:", repr(missing))
        return 2

    print("V3_10_BILINGUAL_UI: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
