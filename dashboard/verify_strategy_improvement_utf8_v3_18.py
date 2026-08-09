import argparse,urllib.request
REQUIRED=["AI Strategy Improvement Candidates / AI 전략 개선 후보","Mode / 모드","Total Candidates / 전체 후보","Evidence Candidates / 증거 수집 후보","Strategy Candidates / 전략 변경 후보","Top Candidates / 우선 개선 후보","Auto Apply OFF / 자동 적용 없음"]
def main():
 p=argparse.ArgumentParser();p.add_argument("--url",required=True);a=p.parse_args()
 html=urllib.request.urlopen(a.url,timeout=20).read().decode("utf-8")
 missing=[x for x in REQUIRED if x not in html]
 print("UTF8_HTML_DECODE: PASS");print("KOREAN_LABEL_COUNT:",len(REQUIRED)-len(missing));print("KOREAN_LABEL_REQUIRED:",len(REQUIRED))
 if missing: print("MISSING:",missing);return 1
 print("V3_18_BILINGUAL_UI: PASS");return 0
if __name__=="__main__": raise SystemExit(main())
