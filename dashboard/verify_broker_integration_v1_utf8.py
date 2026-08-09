import argparse,urllib.request

REQUIRED=[
"Broker Integration V1 Bridge / 브로커 연동 V1 브리지",
"Canonical Contract / 기존 공통 계약",
"E*TRADE Read-only / E*TRADE 읽기 전용",
"Duplicate Components / 중복 구성요소",
"Broker Capability Matrix / 브로커 기능 매트릭스",
"Reuse Audit / 재사용 감사",
"Broker writes remain locked / 브로커 쓰기 잠금 유지",
]

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--url",required=True)
    a=p.parse_args()
    html=urllib.request.urlopen(a.url,timeout=30).read().decode("utf-8")
    missing=[x for x in REQUIRED if x not in html]
    print("UTF8_HTML_DECODE: PASS")
    print("BROKER_V1_KOREAN_LABEL_COUNT:",len(REQUIRED)-len(missing))
    print("BROKER_V1_KOREAN_LABEL_REQUIRED:",len(REQUIRED))
    if missing:
        print("MISSING:",missing)
        return 1
    print("BROKER_V1_BILINGUAL_UI: PASS")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
