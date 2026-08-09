
from urllib.request import urlopen
import argparse

REQUIRED = (
    "거래 성과 진단","표본 상태","최고 거래","최저 거래",
    "평균 보유시간","종목별 진단","청산사유별 진단","진단 메모",
)

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--url", default="http://127.0.0.1:8881/")
    a = p.parse_args()
    with urlopen(a.url, timeout=20) as r:
        html = r.read().decode("utf-8", errors="strict")
    missing = [x for x in REQUIRED if x not in html]
    print("UTF8_HTML_DECODE: PASS")
    print("V3_11_KOREAN_LABEL_COUNT:", len(REQUIRED)-len(missing))
    print("V3_11_KOREAN_LABEL_REQUIRED:", len(REQUIRED))
    if missing:
        print("MISSING:", repr(missing))
        return 2
    print("V3_11_BILINGUAL_UI: PASS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
