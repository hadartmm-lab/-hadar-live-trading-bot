# Hadar Live Trading Decision Engine

A live analysis + alerts dashboard built around the user's trading framework.

## Core rules in this build
- **No 15m analysis at all.**
- **1H is candle-direction only**; no 1H RSI scoring.
- Main setup timeframes: **12H + 4H + Daily**.
- SuperTrend baseline: **ATR 10 / factor 3.0**.
- Fibonacci engine automatically detects the latest impulse and watches the **0.50–0.618 retracement zone**. 0.50 is a common market retracement convention rather than a Fibonacci ratio; 0.618 is Fibonacci.
- A Fib touch is *not* enough by itself: structure/continuation context must agree before it scores as a healthy pullback.
- Wyckoff range-location logic is heuristic: lower part of a long range biases LONG search; upper part biases SHORT search. Volume confirms development rather than being required on every candle.
- VIX is a **filter, not an entry trigger**. Positive VIX/risk-off bias supports equity SHORT; risk-on supports equity LONG.
- VIX RSI divergence: 4H ±0.45, 12H ±0.75, agreement bonus ±0.35.
- Alerts are analysis alerts only; **no automatic order execution**.

## Status ladder
- NO_TRADE
- WATCH (default 60+)
- DEVELOPING (70+)
- READY (82+)

A directional conflict penalty is applied. If LONG vs SHORT scores are too close, the output becomes WAIT.

## Run
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app:app --host 0.0.0.0 --port 8000
```
Open: http://localhost:8000

## Live data
### Crypto
Uses Binance public REST klines for 1H/4H/12H/1D. Scan interval defaults to 60 seconds. This is live polling; it does not require an API key.

### Stocks
Current build uses yfinance as a fallback so the project runs without credentials. This can be delayed and should **not be treated as exchange-grade real-time data**. The `.env` includes Alpaca fields so a paid/appropriate real-time stock feed can be wired in without changing the analysis engine.

### VIX app integration
Your existing VIX app can push its final bias into this bot:
```bash
curl -X POST http://localhost:8000/api/vix/external \
  -H 'Content-Type: application/json' \
  -d '{"bias":"risk_off","score":7.4}'
```
Accepted bias values: `risk_on`, `risk_off`, `neutral`.
External VIX signals stay authoritative for 6 hours; afterward the internal fallback is used.

## TradingView webhook
Endpoint:
`POST /webhook/tradingview`

TradingView events are stored as auxiliary evidence only; they do not place trades.

## Telegram alerts
Create a bot with BotFather, then put the token/chat ID in `.env`.
Telegram messages fire on new DEVELOPING/READY states or a meaningful state change.

## Important limitation
Wyckoff phase recognition, automated swing selection, divergence detection and Fibonacci context are algorithmic approximations. They are intentionally used as weighted evidence, not as absolute truth. Backtest/forward-test the scoring before relying on it with capital.

## Version 2 additions

- Advanced 4H liquidity-sweep detection: wick through prior high/low plus reclaim.
- 12H support/resistance clustering from repeated pivots and touch counts.
- Conservative geometric detection of bull flag, bear flag, rising wedge and falling wedge.
- Fibonacci pullback remains 0.50–0.618, but it only scores as healthy when market structure is not broken.
- `backtest.py` includes a walk-forward calibration engine for score thresholds 60 / 70 / 80 / 90. It measures forward 12H returns and win rate and is intended to calibrate the scoring model, not to claim brokerage-grade historical execution.
- No 15m analysis. 1H is candles/structure only; no 1H RSI.

### Backtest concept
Call `backtest_frames(df12, df4, df1h, df1d)` with historical dataframes containing `ts, open, high, low, close, volume`. Default outcome horizon is 4 x 12H bars (about 2 days), matching the swing character of the system. The returned summary reports signal count, win rate and average directional return for score thresholds 60, 70, 80 and 90.
