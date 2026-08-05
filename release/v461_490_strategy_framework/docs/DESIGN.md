# V461–V490 Strategy Framework\n\n- V461: Strategy Interface\n- V462: Signal Contract\n- V463: Strategy Registry\n- V464: Duplicate Strategy Guard\n- V465: Strategy Configuration\n- V466: Market Bar Fixture Contract\n- V467: Close Price Extraction\n- V468: Rolling Mean\n- V469: Rolling High and Low\n- V470: Simple Return\n- V471: Momentum Strategy\n- V472: Mean Reversion Strategy\n- V473: Breakout Strategy\n- V474: Trend Strategy\n- V475: Gap Strategy\n- V476: Insufficient Data Guard\n- V477: Signal Score\n- V478: Signal Confidence\n- V479: Strategy Weight\n- V480: Multi-Strategy Voting\n- V481: Combined Score Threshold\n- V482: BUY Candidate\n- V483: SELL Candidate\n- V484: HOLD Decision\n- V485: Strategy Health\n- V486: Strategy Registry Snapshot\n- V487: Signal Ledger\n- V488: Decision Ledger\n- V489: Strategy Dashboard\n- V490: Order Separation Safety Contract

The framework produces strategy candidates only. It does not generate order
tickets, call market or broker networks, or submit Paper or Live orders.
Insufficient data always produces HOLD with an explicit status rather than a
fabricated signal.

The included bars are deterministic fixtures for installation verification.
A later integration stage can map validated market snapshots into this same
contract.
