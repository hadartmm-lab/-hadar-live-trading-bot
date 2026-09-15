# Hadar Alpha Arena v3 — Game Premium

## Major logic upgrades
- RSI Divergence on **4H** and **12H** for every tracked asset.
- Stronger weight for 12H divergence; earlier signal from 4H.
- Synchronization bonus when 4H + 12H divergences agree.
- Smarter latest-impulse Fibonacci engine with 0.50–0.618 healthy-pullback logic.
- BOS / CHoCH detection on 4H and 12H.
- Market regime detection: Trend / Range / Transition.
- Confluence scoring with conflict penalty and cross-timeframe alignment bonus.
- Explicit **Missing Confirmations** list: tells you what is still missing before a setup becomes stronger.
- 1H is still **candles/price direction only** — no 1H RSI.
- No 15m layer.
- VIX remains a filter for stock direction.
- Resilient data fallback remains enabled.

## Game Premium UI
- Command Center
- Alpha Leaderboard (top 3 setups)
- Setup Power: ELITE / STRONG / BUILDING / WATCH / LOW
- Mission Checklist
- Next Mission: missing confirmations
- Compact top-level view, deep tactical details hidden in an expander
- Separate ERROR stage from NO TRADE

## Update GitHub
Safest option: replace these files from v3:
- app.py
- engine.py
- indicators.py
- advanced_patterns.py
- backtest.py

Keep the latest resilient versions of:
- datafeeds.py
- vix_engine.py
- config.py
- requirements.txt

Or upload/replace the whole package.

Then in Streamlit:
**Manage app -> Reboot app**
