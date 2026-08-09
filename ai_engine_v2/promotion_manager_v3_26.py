from .common import safe_status

def build_promotion_manager(gate):
    eligible=bool(gate.get("promotion_eligible"))
    return safe_status("V3.26_PROMOTION_MANAGER",
        "PASS_MANUAL_REVIEW_PACKAGE_READY" if eligible else "WAITING_FOR_PROMOTION_GATE",
        manual_review_required=True,automatic_promotion=False,
        promotion_package_created=eligible,promotion_performed=False)
