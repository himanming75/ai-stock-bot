
from urllib.request import urlopen
import argparse

REQUIRED = (
    "전략 스트레스 테스트",
    "스트레스 상태",
    "시나리오 비교",
    "거래마찰",
    "수익축소",
    "손실확대",
    "시나리오별 순손익",
    "시나리오별 준비도 점수",
    "시뮬레이션 전용",
)

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--url", default="http://127.0.0.1:8884/")
    a = p.parse_args()

    with urlopen(a.url, timeout=20) as response:
        html = response.read().decode("utf-8", errors="strict")

    missing = [value for value in REQUIRED if value not in html]

    print("UTF8_HTML_DECODE: PASS")
    print("V3_14_KOREAN_LABEL_COUNT:", len(REQUIRED)-len(missing))
    print("V3_14_KOREAN_LABEL_REQUIRED:", len(REQUIRED))

    if missing:
        print("MISSING:", repr(missing))
        return 2

    print("V3_14_BILINGUAL_UI: PASS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
