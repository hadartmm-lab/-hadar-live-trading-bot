Hadar Live Trading Bot v2.3 Resilient UI

What changed
- Friendlier, lighter Streamlit dashboard with color badges, tabs, and cleaner cards.
- Crypto data is now more resilient:
  1) data-api.binance.vision
  2) api1.binance.com
  3) api2.binance.com
  4) api3.binance.com
  5) api.binance.com
  6) Yahoo fallback (ex: BTCUSDT -> BTC-USD)
- Each symbol now shows the data source used.
- The page should be easier to read on mobile and less overloaded.

How to update GitHub
Upload/replace at least these files:
- app.py
- datafeeds.py
- engine.py
- README_DEPLOY.md (optional)

Then in Streamlit:
- Manage app -> Reboot app
