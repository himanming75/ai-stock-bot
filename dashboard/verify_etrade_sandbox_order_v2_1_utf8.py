import argparse,urllib.request
REQ=[
"E*TRADE Sandbox Order Simulation V2.1 / E*TRADE 샌드박스 주문 시뮬레이션 V2.1",
"Preview / 주문 미리보기",
"Place / 주문전송",
"PROD Orders / PROD 주문",
"Profit Validation / 수익성 검증",
"Production order POST remains blocked / PROD 주문 POST 계속 차단",
]
def main():
 p=argparse.ArgumentParser();p.add_argument("--url",required=True);a=p.parse_args()
 html=urllib.request.urlopen(a.url,timeout=30).read().decode("utf-8")
 miss=[x for x in REQ if x not in html]
 print("UTF8_HTML_DECODE: PASS")
 print("V2_1_KOREAN_LABEL_COUNT:",len(REQ)-len(miss))
 if miss: print("MISSING:",miss);return 1
 print("V2_1_BILINGUAL_UI: PASS");return 0
if __name__=="__main__":raise SystemExit(main())
