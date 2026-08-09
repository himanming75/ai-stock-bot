import argparse,urllib.request
REQ=[
"Current Market Data Signal Bridge V2.1.7 / 현재 시장 데이터 신호 브리지 V2.1.7",
"Market Data Engine / 시장 데이터 엔진",
"Indicator Engine / 지표 엔진",
"Signal Engine / 신호 엔진",
"PROD orders remain locked / PROD 주문 계속 잠금",
]
def main():
 p=argparse.ArgumentParser();p.add_argument("--url",required=True);a=p.parse_args()
 html=urllib.request.urlopen(a.url,timeout=30).read().decode("utf-8")
 miss=[x for x in REQ if x not in html]
 print("UTF8_HTML_DECODE: PASS")
 print("V2_1_7_KOREAN_LABEL_COUNT:",len(REQ)-len(miss))
 if miss:
  print("MISSING:",miss)
  return 1
 print("V2_1_7_BILINGUAL_UI: PASS")
 return 0
if __name__=="__main__":raise SystemExit(main())
