import argparse,urllib.request
REQ=[
"E*TRADE Sandbox Bounded Multi-Cycle V2.1.4 / E*TRADE 샌드박스 제한 반복 사이클 V2.1.4",
"Max Cycles / 최대 사이클",
"Duplicate Guard / 중복 신호 차단",
"Kill Switch / 긴급 중단",
"Unlimited loop prohibited / 무한 반복 금지",
]
def main():
 p=argparse.ArgumentParser();p.add_argument("--url",required=True);a=p.parse_args()
 html=urllib.request.urlopen(a.url,timeout=30).read().decode("utf-8")
 miss=[x for x in REQ if x not in html]
 print("UTF8_HTML_DECODE: PASS")
 print("V2_1_4_KOREAN_LABEL_COUNT:",len(REQ)-len(miss))
 if miss:
  print("MISSING:",miss)
  return 1
 print("V2_1_4_BILINGUAL_UI: PASS")
 return 0
if __name__=="__main__":raise SystemExit(main())
