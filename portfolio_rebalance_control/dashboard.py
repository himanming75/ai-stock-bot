from .core import load
def build_dashboard_payload(root):
 r=load(root/'release/v101_01_to_v101_32/actual/portfolio_rebalance_control_result.json');return {'state':r.get('state'),'snapshot':r.get('snapshot',{}),'controls':r.get('controls',{}),'gate':r.get('rebalance_gate',{}),'paper_only':True}
