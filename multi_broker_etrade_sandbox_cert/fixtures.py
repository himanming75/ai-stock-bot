ACCOUNT_ID_KEY="fixture-account-key"
FIXTURES={
"ACCOUNT_LIST":{"AccountListResponse":{"Accounts":{"Account":[{"accountId":"****1234","accountIdKey":ACCOUNT_ID_KEY,"accountStatus":"ACTIVE","accountType":"INDIVIDUAL"}]}}},
"BALANCE":{"BalanceResponse":{"Computed":{"cashAvailableForInvestment":25000.50,"RealTimeValues":{"totalAccountValue":100500.75}}}},
"PORTFOLIO":{"PortfolioResponse":{"AccountPortfolio":[{"accountId":ACCOUNT_ID_KEY,"Position":[{"Product":{"symbol":"SPY"},"quantity":10,"pricePaid":500.0,"marketValue":5050.0,"totalGain":50.0}]}]}},
"ORDERS":{"OrdersResponse":{"Order":[{"orderId":123456,"OrderDetail":[{"status":"EXECUTED","Instrument":[{"Product":{"symbol":"SPY"},"orderAction":"BUY","orderedQuantity":10,"filledQuantity":10}]}]}]}}
}
