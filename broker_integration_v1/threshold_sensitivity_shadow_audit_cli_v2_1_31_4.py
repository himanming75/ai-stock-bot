from __future__ import annotations
import argparse
from pathlib import Path
from .threshold_sensitivity_shadow_audit_v2_1_31_4 import (
    ThresholdSensitivityShadowAuditV21314,
)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",default=r"C:\stock-bot")
    p.add_argument("--mode",choices=("audit","status"),default="audit")
    a=p.parse_args()
    c=ThresholdSensitivityShadowAuditV21314(Path(a.root))
    r=c.audit() if a.mode=="audit" else c.status()

    print("=== V2.1.31.4 THRESHOLD SENSITIVITY SHADOW AUDIT ===")
    print("STATUS:",r.get("status"))
    print("FEATURE SNAPSHOTS:",r.get("feature_snapshot_count"))
    print("USABLE SYMBOL POINTS:",r.get("usable_symbol_points"))
    for key,val in (r.get("thresholds") or {}).items():
        print("")
        print(
            f"THRESHOLD {key} | signals={val['signal_count']} | "
            f"current={val['is_current_execution_threshold']}"
        )
        for h,m in val["horizons"].items():
            print(
                f" {h}: resolved={m['resolved_count']}/{m['signal_count']} "
                f"win_rate={m['directional_win_rate_pct']}% "
                f"avg_signed_return={m['average_signed_return_pct']}%"
            )
    print("")
    print("INCREMENTAL VS 0.75:",r.get("incremental_signal_counts"))
    print("BEST 5M RESEARCH THRESHOLD:",
          r.get("best_5m_threshold_by_current_shadow_evidence"))
    print("ACTUAL EXECUTION THRESHOLD:",
          r.get("actual_execution_threshold"))
    print("ACTUAL EXECUTION THRESHOLD MODIFIED:",
          r.get("actual_execution_threshold_modified"))
    print("ACTUAL SELECTOR MODIFIED:",
          r.get("actual_selector_modified"))
    print("BROKER NETWORK USED:",r.get("broker_network_used"))
    print("ORDERS SUBMITTED:",r.get("orders_submitted"))
    return 2 if str(r.get("status","")).startswith("BLOCKED_") else 0

if __name__=="__main__":
    raise SystemExit(main())
