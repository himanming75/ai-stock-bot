import argparse,urllib.request

REQUIRED=[
"Broker Integration V2 - E*TRADE Read-only OAuth / 브로커 연동 V2 - E*TRADE 읽기 전용 OAuth",
"OAuth Status / OAuth 상태",
"Signature Test / 서명 테스트",
"Token Persistence / 토큰 저장",
"Reuse Audit / 재사용 감사",
"Read-only Safety / 읽기 전용 안전장치",
"New credential vault not created / 새 credential vault 생성 안 함",
]

def main():
    p=argparse.ArgumentParser();p.add_argument("--url",required=True);a=p.parse_args()
    html=urllib.request.urlopen(a.url,timeout=30).read().decode("utf-8")
    missing=[x for x in REQUIRED if x not in html]
    print("UTF8_HTML_DECODE: PASS")
    print("BROKER_V2_KOREAN_LABEL_COUNT:",len(REQUIRED)-len(missing))
    print("BROKER_V2_KOREAN_LABEL_REQUIRED:",len(REQUIRED))
    if missing:
        print("MISSING:",missing);return 1
    print("BROKER_V2_BILINGUAL_UI: PASS");return 0

if __name__=="__main__":
    raise SystemExit(main())
