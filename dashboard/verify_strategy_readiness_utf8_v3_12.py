
from urllib.request import urlopen
import argparse

REQUIRED=(
    "전략 품질 및 준비도","종합점수","표본 신뢰도","수익성 품질",
    "리스크 품질","일관성","분산도","준비도 게이트","차단 요인","실거래 승인 아님",
)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--url",default="http://127.0.0.1:8882/")
    a=p.parse_args()
    with urlopen(a.url,timeout=20) as r:
        html=r.read().decode("utf-8",errors="strict")
    missing=[x for x in REQUIRED if x not in html]
    print("UTF8_HTML_DECODE: PASS")
    print("V3_12_KOREAN_LABEL_COUNT:",len(REQUIRED)-len(missing))
    print("V3_12_KOREAN_LABEL_REQUIRED:",len(REQUIRED))
    if missing:
        print("MISSING:",repr(missing))
        return 2
    print("V3_12_BILINGUAL_UI: PASS")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
