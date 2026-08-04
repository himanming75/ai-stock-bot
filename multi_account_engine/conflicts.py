from collections import defaultdict
def resolve(routes,allow):
 if allow: return [{**r,"route_allowed":True,"rejection_reason":""} for r in routes]
 g=defaultdict(list)
 for r in routes:g[str(r.get("symbol"))].append(r)
 out=[]
 for items in g.values():
  items.sort(key=lambda x:float(x.get("strategy_score",0) or 0),reverse=True); out.append({**items[0],"route_allowed":True,"rejection_reason":""})
  for x in items[1:]:out.append({**x,"route_allowed":False,"rejection_reason":"CROSS_ACCOUNT_SYMBOL_CONFLICT"})
 return out
