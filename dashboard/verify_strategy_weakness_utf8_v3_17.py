
from urllib.request import urlopen
import argparse

REQUIRED = (
    "전략 약점 지도",
    "전체 심각도",
    "우선순위 점수",
    "증거 부족",
    "성과 위험",
    "최우선 약점",
    "약점 매트릭스",
    "심각도 분포",
    "증거 부족은 전략 실패를 의미하지 않음",
)

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--url", default="http://127.0.0.1:8887/")
    a = p.parse_args()

    with urlopen(a.url, timeout=20) as response:
        html = response.read().decode("utf-8", errors="strict")

    missing = [value for value in REQUIRED if value not in html]

    print("UTF8_HTML_DECODE: PASS")
    print("V3_17_KOREAN_LABEL_COUNT:", len(REQUIRED)-len(missing))
    print("V3_17_KOREAN_LABEL_REQUIRED:", len(REQUIRED))

    if missing:
        print("MISSING:", repr(missing))
        return 2

    print("V3_17_BILINGUAL_UI: PASS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
