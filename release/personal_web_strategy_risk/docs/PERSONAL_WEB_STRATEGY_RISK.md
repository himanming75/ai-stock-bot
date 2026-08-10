# Personal Web Control Center — Strategy / Risk / AI Recommendation

Reuses the existing Strategy Manager and API. No new strategy backend is created.

Added to the Personal Control Center:
- enable/disable Momentum, Mean Reversion, Breakout;
- symbol list editing;
- maximum order notional;
- maximum quantity;
- maximum daily orders;
- maximum daily loss;
- maximum positions;
- validate / save / restore;
- current runtime policy display;
- AI health/research recommendation, read-only.

Safety:
- paper_only is always true in the UI payload;
- live_submission_enabled is always false;
- existing backend validation enforces both values;
- Emergency Stop still blocks save/restore;
- AI never applies a strategy change automatically.
