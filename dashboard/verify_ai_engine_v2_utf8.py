import argparse,urllib.request

REQUIRED=[
"AI Engine V2 Integrated Build / AI 엔진 V2 통합 개발",
"Development / 개발",
"Real Evidence / 실제 검증 데이터",
"Strategy Registry / 전략 레지스트리",
"Safety Locks / 안전 잠금",
"Synthetic tests validate software behavior only / 가상 테스트는 소프트웨어 동작만 검증",
"Live remains locked / 실거래 잠금 유지",
]

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--url",required=True)
    a=p.parse_args()
    html=urllib.request.urlopen(a.url,timeout=30).read().decode("utf-8")
    missing=[x for x in REQUIRED if x not in html]
    print("UTF8_HTML_DECODE: PASS")
    print("V2_KOREAN_LABEL_COUNT:",len(REQUIRED)-len(missing))
    print("V2_KOREAN_LABEL_REQUIRED:",len(REQUIRED))
    if missing:
        print("MISSING:",missing)
        return 1
    print("AI_ENGINE_V2_BILINGUAL_UI: PASS")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
