# v3.5.0 — Closed-Candle Precision

This release fixes the backtest timing flaw identified in v3.4 and aligns live scoring with closed-candle logic.

## Critical fixes
1. 12H signals are computed only after candle close.
2. 4H/1H/1D inputs are filtered by their own close times.
3. Backtest enters on the next 12H open.
4. No overlapping trades in threshold calibration.
5. Live analysis excludes forming candles.
6. Added PF, max drawdown and compounded return.
7. Added a two-year BTCUSDT backtest runner based on a single 1H source stream.
