# v3.6.0 — Audited Precision

Full code audit of v3.5 with correctness fixes.

## Fixed
1. Backtest now uses the exact live scoring path instead of a duplicate approximation.
2. Backtest threshold selection applies live gate requirements, not score alone.
3. Forming 1H candles and incomplete resampled higher-timeframe bars are excluded from calibration.
4. Trigger total corrected from a hard-coded 5 to the actual 6 trigger families.
5. Environment WATCH/DEVELOPING/READY thresholds are honored by the engine.
6. Neutral UI wording and checklist direction display corrected.
7. Fibonacci checklist no longer turns green for a healthy pullback in the opposite direction.
8. Score badge clarified as SETUP SCORE and detailed LONG/SHORT score breakdown added.
9. RSI zero-loss/flat edge cases corrected.
10. Stoch-RSI band classification made direction-aware.

## Unchanged by design
- Core weights and default live thresholds remain 55 / 68 / 78.
- Closed-candle rule remains mandatory.
- 1H is a light candle-direction confirmation only; no 1H RSI scoring.
