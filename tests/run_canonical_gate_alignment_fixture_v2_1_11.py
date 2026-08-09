from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from broker_integration_v1.canonical_gate_alignment_v2_1_11 import build_canonical_gate_alignment_v2_1_11

r=build_canonical_gate_alignment_v2_1_11()
print("STATUS:",r["status"])
print("ALIGNED:",r["aligned"])
print("SIGNAL MIN CONFIDENCE:",r["signal_gate"]["minimum_confidence"])
print("PROMOTION MIN COMPARISONS:",r["promotion_gate"]["minimum_comparisons"])
print("MANUAL REVIEW REQUIRED:",r["promotion_gate"]["manual_review_required"])
print("LIVE LOCKED:",r["safety_locks"]["live_trading_locked"])
print("BROKER WRITE LOCKED:",r["safety_locks"]["broker_write_locked"])
print("AUTO PROMOTION LOCKED:",r["safety_locks"]["automatic_promotion_locked"])
print("PROD POST:",r["production_order_post_allowed"])
assert r["aligned"] is True
assert r["production_order_post_allowed"] is False
print("V2.1.11 CANONICAL GATE ALIGNMENT: PASS")
