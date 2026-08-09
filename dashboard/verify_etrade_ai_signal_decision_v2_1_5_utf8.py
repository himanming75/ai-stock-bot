import argparse,urllib.request
REQ=[
"AI Signal Decision Bridge V2.1.5 / AI 신호 결정 브리지 V2.1.5",
"BUY/SELL/HOLD / 매수·매도·보류",
"Confidence Gate / 신뢰도 게이트",
"HOLD Blocks Orders / HOLD 주문 차단",
"PROD orders remain locked / PROD 주문 계속 잠금",
]
def main():
 p=argparse.ArgumentParser();p.add_argument("--url",required=True);a=p.parse_args()
 html=urllib.request.urlopen(a.url,timeout=30).read().decode("utf-8")
 miss=[x for x in REQ if x not in html]
 print("UTF8_HTML_DECODE: PASS")
 print("V2_1_5_KOREAN_LABEL_COUNT:",len(REQ)-len(miss))
 if miss:
  print("MISSING:",miss)
  return 1
 print("V2_1_5_BILINGUAL_UI: PASS")
 return 0
if __name__=="__main__":raise SystemExit(main())
