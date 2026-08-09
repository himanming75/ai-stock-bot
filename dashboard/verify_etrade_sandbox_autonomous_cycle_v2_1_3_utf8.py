import argparse,urllib.request

REQ=[
"E*TRADE Sandbox Autonomous Cycle V2.1.3 / E*TRADE 샌드박스 자동 사이클 V2.1.3",
"One Cycle / 1회 자동 사이클",
"Auto Repeat / 자동 반복",
"PROD Orders / PROD 주문",
]

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--url",required=True)
    a=p.parse_args()

    html=urllib.request.urlopen(a.url,timeout=30).read().decode("utf-8")
    missing=[x for x in REQ if x not in html]

    print("UTF8_HTML_DECODE: PASS")
    print("V2_1_3_KOREAN_LABEL_COUNT:",len(REQ)-len(missing))

    if missing:
        print("MISSING:",missing)
        return 1

    print("V2_1_3_BILINGUAL_UI: PASS")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
