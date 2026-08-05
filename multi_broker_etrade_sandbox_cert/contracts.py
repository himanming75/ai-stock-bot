from __future__ import annotations
CONTRACTS = (
    {"name":"ACCOUNT_LIST","method":"GET","path":"/v1/accounts/list.json","roots":("AccountListResponse","Accounts")},
    {"name":"BALANCE","method":"GET","path":"/v1/accounts/{accountIdKey}/balance.json?instType=BROKERAGE&realTimeNAV=true","roots":("BalanceResponse","Computed")},
    {"name":"PORTFOLIO","method":"GET","path":"/v1/accounts/{accountIdKey}/portfolio.json","roots":("PortfolioResponse","AccountPortfolio")},
    {"name":"ORDERS","method":"GET","path":"/v1/accounts/{accountIdKey}/orders.json","roots":("OrdersResponse","Order")},
)
