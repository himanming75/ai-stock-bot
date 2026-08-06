from __future__ import annotations
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ai_feature_engine.web import serve

parser = argparse.ArgumentParser()
parser.add_argument("--host", default="127.0.0.1")
parser.add_argument("--port", type=int, default=8772)
args = parser.parse_args()

serve(
    report_path=Path(
        "release/v9801_10400_ai_feature_signal/actual/"
        "ai_signal_candidate_report_bilingual.json"
    ),
    certification_path=Path(
        "release/v9801_10400_ai_feature_signal/"
        "ai_feature_signal_certification.json"
    ),
    host=args.host,
    port=args.port,
)
