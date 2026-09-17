# Hadar Live Trading Bot v3.4 RSI + Smart 12H Fib


Multi-asset swing-trading decision engine. Core analysis is Daily / 12H / 4H, with 1H candle direction as a light confirmation layer. No 15-minute layer.

## v3.2 changes
- Separates **BIAS** (LONG / SHORT / NEUTRAL) from **ACTION** (READY / DEVELOPING / WATCH / NO TRADE).
- Rebalanced the score to a much clearer ~100-point scale instead of normalizing a larger hidden raw total.
- READY is no longer score-only: it requires 12H + 4H structure alignment, no opposite Daily trend, enough score/gap, and at least two trigger families.
- Opposing evidence reduces conviction instead of being ignored.
- VIX is a stock-market modifier rather than extra score inflation.
- UI now shows bias, action, confidence, trigger count, LONG score, SHORT score and the gap more clearly.
- Thresholds: WATCH 55, DEVELOPING 68, READY 78, with additional gating rules.

Signals include 4H + 12H RSI divergence, BOS/CHoCH, relevant-impulse Fibonacci 0.50–0.618, SuperTrend, Wyckoff/range location, volume, liquidity sweeps, support/resistance and flags/wedges.

This is an analytical decision-support tool, not a guarantee of future performance and not automatic trade execution. The v3.2 weighting is structurally improved but should still be calibrated with out-of-sample historical data before treating the thresholds as statistically validated.

## v3.3 scoring changes
- 4H RSI divergence upgraded to a strong signal (up to 8 points).
- 12H RSI divergence is stronger (up to 12 points).
- Added the second RSI/momentum layer: regular RSI direction + Stoch RSI (3,3,14,14) Golden/Death Cross.
- Strongest momentum confirmation is a Golden Cross from/through the oversold band for LONG, or Death Cross from/through the overbought band for SHORT.
- Momentum is scored on 4H and 12H, with Daily as a bonus; alignment on at least 2 of the 3 timeframes receives an extra confluence bonus.
- No 1H RSI scoring was added; 1H remains candle-direction confirmation only.


## v3.4 Smart 12H Fibonacci
- Fibonacci is calculated from the latest meaningful 12H impulse (the latest significant expansion leg), not an arbitrary recent pivot pair.
- The impulse start remains anchored while the end updates to the latest high/low made in that same direction.
- Main pullback approval zone: 0.50–0.618.
- The engine exposes impulse quality, ATR multiple, retracement depth, and distance from the Fib zone.
- Fib remains a confirmation layer and cannot by itself create a READY trade.
