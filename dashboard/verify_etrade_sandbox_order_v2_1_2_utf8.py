import argparse,urllib.request
REQ=[
"E*TRADE Sandbox Place + Ledger + Reconciliation V2.1.2 / E*TRADE 샌드박스 Place + 원장 + 대사 V2.1.2",
"Sandbox Place / 샌드박스 주문전송",
"Order Ledger / 주문 원장",
"Reconciliation / 주문 대사",
"Production orders remain locked / PROD 주문 계속 잠금",
]
def main():
 p=argparse.ArgumentParser();p.add_argument("--url",required=True);a=p.parse_args()
 html=urllib.request.urlopen(a.url,timeout=30).read().decode("utf-8")
 miss=[x for x in REQ if x not in html]
 print("UTF8_HTML_DECODE: PASS")
 print("V2_1_2_KOREAN_LABEL_COUNT:",len(REQ)-len(miss))
 if miss:
  print("MISSING:",miss)
  return 1
 print("V2_1_2_BILINGUAL_UI: PASS")
 return 0
if __name__=="__main__":
 raise SystemExit(main())
