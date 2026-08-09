
from urllib.request import urlopen
import argparse

REQUIRED = (
    "준비도 이력 및 증거 추세",
    "이력 기록수",
    "최신 점수",
    "다음 마일스톤",
    "종합점수 추세",
    "증거 누적",
    "점수 구성 추세",
    "상태 변경 이력",
)

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--url", default="http://127.0.0.1:8883/")
    a = p.parse_args()

    with urlopen(a.url, timeout=20) as r:
        html = r.read().decode("utf-8", errors="strict")

    missing = [x for x in REQUIRED if x not in html]
    print("UTF8_HTML_DECODE: PASS")
    print("V3_13_KOREAN_LABEL_COUNT:", len(REQUIRED)-len(missing))
    print("V3_13_KOREAN_LABEL_REQUIRED:", len(REQUIRED))

    if missing:
        print("MISSING:", repr(missing))
        return 2

    print("V3_13_BILINGUAL_UI: PASS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
