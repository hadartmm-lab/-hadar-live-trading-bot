# Hadar Live Trading Bot — v3.6 Audit Report

Audit scope: scoring engine, closed-candle handling, indicators, UI score presentation, historical calibration/backtest consistency, configuration wiring, deployment files.

## Critical / material issues found in v3.5

1. **Backtest did not apply the live entry gates.** It selected trades by score threshold alone, while live READY also requires score gap, 12H+4H alignment, Daily not opposite and trigger confirmations. Fixed by routing historical snapshots through the exact live engine and applying the same gate families.
2. **Live and backtest scoring were duplicated.** Small rounding differences existed and future code drift was likely. Fixed by a shared `analyze_frames()` scoring path.
3. **Historical calibration could contain incomplete bars.** The history stream could include a forming 1H candle and resampling could create partial 4H/12H/1D bars. Fixed by removing the forming 1H candle and requiring complete source-bar counts.
4. **Trigger counter UI was wrong.** Engine had 6 trigger families but UI showed `/5`. Fixed to dynamic `trigger_total` (currently 6).
5. **Environment thresholds were not truly honored.** `.env` / config values could differ from hard-coded engine thresholds. Fixed: engine uses `settings.watch_score`, `settings.developing_score`, `settings.ready_score`.
6. **Neutral verdict wording was misleading.** UI could show `Moderate NEUTRAL bias`. Fixed to a neutral/mixed message with only a slight directional lean.
7. **Fib checklist could show green for the opposite direction.** Fixed: healthy Fib must match the dominant setup direction.
8. **Score transparency was insufficient.** Added raw LONG/SHORT evidence, final scores and full reason lists; badge renamed `SETUP SCORE` to clarify it is not a probability.
9. **RSI zero-loss edge case returned NaN instead of 100.** Corrected.
10. **Stoch-RSI band labeling could be ambiguous after a rapid move through both extremes.** Cross-direction-aware band classification added.

## Verified behavior

- Closed-candle boundary filter passes exact 4H close-time tests.
- All Python files compile successfully.
- Synthetic tests confirmed live and backtest use identical final scores after the refactor.
- Backtest selected samples satisfy the corresponding live gate family.
- RSI monotonic-up / flat / monotonic-down edge tests return 100 / 50 / 0.
- Trigger total is exposed as 6 and UI no longer hard-codes 5.

## Important interpretation

The displayed number (for example `31`) is a **setup score**, not a 31% probability of success. A low score can coexist with one or more green checklist items because the score includes additional hidden/secondary evidence and subtracts 35% of opposing evidence. READY still requires explicit gates; score alone is insufficient.

## Remaining limitations (not bugs in the crypto decision path)

- Live crypto data primarily depends on Binance endpoints, with Yahoo fallback. A source switch can cause small indicator differences.
- The stock/VIX side uses Yahoo-based data and is less exact than the crypto Binance path for higher intraday timeframes.
- Telegram and Alpaca settings exist but are not wired into the Streamlit scan flow in this package.
- Historical calibration is not an exchange fill simulator and still does not model leverage, stop fills, fees or slippage.
