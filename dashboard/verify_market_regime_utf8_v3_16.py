
from urllib.request import urlopen
import argparse

REQUIRED=("시장 환경별 전략 성과 분석","시장환경 상태","방향환경 관측범위","변동성 관측범위","관측상 최우수 환경","관측상 취약 환경","방향 시장환경 성과표","변동성 환경 성과표","명시적 증거만 사용")

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--url",default="http://127.0.0.1:8886/")
    a=p.parse_args()
    with urlopen(a.url,timeout=20) as response:
        html=response.read().decode("utf-8",errors="strict")
    missing=[v for v in REQUIRED if v not in html]
    print("UTF8_HTML_DECODE: PASS")
    print("V3_16_KOREAN_LABEL_COUNT:",len(REQUIRED)-len(missing))
    print("V3_16_KOREAN_LABEL_REQUIRED:",len(REQUIRED))
    if missing:
        print("MISSING:",repr(missing))
        return 2
    print("V3_16_BILINGUAL_UI: PASS")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
