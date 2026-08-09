
from urllib.request import urlopen
import argparse

REQUIRED = (
    "전략 견고성 및 실패 경계",
    "견고성 점수",
    "손익분기 거래마찰",
    "수익축소 실패경계",
    "손실확대 실패경계",
    "수익팩터 1 경계",
    "준비도 실패경계",
    "경계 관측 가능성",
    "실패 경계 매트릭스",
)

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--url", default="http://127.0.0.1:8885/")
    a = p.parse_args()

    with urlopen(a.url, timeout=20) as response:
        html = response.read().decode("utf-8", errors="strict")

    missing = [value for value in REQUIRED if value not in html]
    print("UTF8_HTML_DECODE: PASS")
    print("V3_15_KOREAN_LABEL_COUNT:", len(REQUIRED)-len(missing))
    print("V3_15_KOREAN_LABEL_REQUIRED:", len(REQUIRED))

    if missing:
        print("MISSING:", repr(missing))
        return 2

    print("V3_15_BILINGUAL_UI: PASS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
