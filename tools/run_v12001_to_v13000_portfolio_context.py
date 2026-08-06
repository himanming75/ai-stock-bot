from __future__ import annotations
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from portfolio_context_ai.service import PortfolioContextCertificationService

result = PortfolioContextCertificationService().evaluate(
    output_dir=Path("release/v12001_13000_portfolio_context")
)
print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
raise SystemExit(0 if result["status"] == "PASS" else 2)
