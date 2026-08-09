from .common import safe_status

def build_rollback_manager(registry):
    champion=next((x for x in registry.get("entries") or [] if x.get("role")=="CHAMPION"),None)
    return safe_status("V3.27_ROLLBACK_MANAGER","PASS_ROLLBACK_PLAN_READY",
        rollback_reference=champion,rollback_performed=False,
        broker_write_performed=False,automatic_rollback=False)
