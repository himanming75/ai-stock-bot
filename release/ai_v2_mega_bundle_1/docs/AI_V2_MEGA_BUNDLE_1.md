# AI V2 Mega Bundle 1

This bundle develops four offline components in one installation:

1. Strategy Ensemble and Ranking;
2. Performance Learning Ledger;
3. Portfolio Optimizer;
4. Dynamic Risk Engine V2.

The ensemble uses transparent deterministic scoring. It does not claim that a
machine-learning model was trained.

The learning ledger stores strategy outcomes and calculates win rate, profit
factor, average return, and maximum drawdown. It prepares data for future model
training but performs no training itself.

The portfolio optimizer converts symbol confidence scores into bounded target
weights while preserving a cash reserve and maximum symbol weight.

Dynamic Risk Engine V2 reduces notional based on volatility, portfolio
drawdown, average correlation, and daily-loss limits.

This stage uses fixture data only. No news feed, current market network,
broker connection, broker write, portfolio mutation, or order submission occurs.
