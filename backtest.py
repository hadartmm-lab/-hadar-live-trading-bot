from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Iterable, List, Tuple

import pandas as pd

from indicators import (
    candle_bias_1h,
    rsi_divergence_detail,
    stoch_rsi_signal,
    structure,
    supertrend,
    volume_confirmation,
    wyckoff_heuristic,
)
from advanced_patterns import liquidity_sweep, support_resistance, flag_wedge_pattern, market_regime, bos_choch, impulse_fib
from engine import analyze_frames

THRESHOLDS = (55, 68, 78, 90)
_TF_DELTA = {
    '1h': pd.Timedelta(hours=1),
    '4h': pd.Timedelta(hours=4),
    '12h': pd.Timedelta(hours=12),
    '1d': pd.Timedelta(days=1),
}


def _utc_ts(values: Iterable) -> pd.Series:
    return pd.to_datetime(values, utc=True)


def _closed_slice(df: pd.DataFrame, decision_time: pd.Timestamp, timeframe: str) -> pd.DataFrame:
    """Return only bars that were fully CLOSED at decision_time.

    Dataframes in this project use bar OPEN timestamps. Therefore a 12H bar stamped
    00:00 is not knowable until 12:00. This helper is the central anti-look-ahead rule.
    """
    if df is None or df.empty:
        return df.iloc[:0].copy() if df is not None else pd.DataFrame()
    opens = _utc_ts(df['ts'])
    closes = opens + _TF_DELTA[timeframe]
    return df.loc[closes <= decision_time].copy().reset_index(drop=True)


def score_snapshot_detail(df12, df4, df1h, df1d, vix_bias='neutral', asset_type='crypto'):
    """Run the exact live engine on a historical closed-candle snapshot."""
    dfs={'12h':df12,'4h':df4,'1h':df1h,'1d':df1d}
    return analyze_frames(
        dfs, symbol='BACKTEST', asset_type=asset_type, vix_bias=vix_bias,
        sources={tf:'historical' for tf in dfs},
    )


def score_snapshot(df12, df4, df1h, df1d, vix_bias='neutral', asset_type='crypto'):
    """Backward-compatible score tuple, now sourced from the live engine."""
    r=score_snapshot_detail(df12,df4,df1h,df1d,vix_bias=vix_bias,asset_type=asset_type)
    if r['long_score'] >= r['short_score']:
        return 'LONG', float(r['long_score']), float(r['short_score'])
    return 'SHORT', float(r['short_score']), float(r['long_score'])


def _trade_stats(trades: List[dict]) -> dict:
    if not trades:
        return {
            'signals': 0, 'win_rate': 0.0, 'avg_return_pct': 0.0,
            'profit_factor': 0.0, 'max_drawdown_pct': 0.0,
            'cumulative_return_pct': 0.0,
        }

    rets = [float(t['return_pct']) / 100.0 for t in trades]
    wins = [r for r in rets if r > 0]
    losses = [r for r in rets if r < 0]
    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    pf = gross_profit / gross_loss if gross_loss > 1e-12 else (999.0 if gross_profit > 0 else 0.0)

    equity = 1.0
    peak = 1.0
    max_dd = 0.0
    for r in rets:
        equity *= (1.0 + r)
        peak = max(peak, equity)
        dd = (equity / peak - 1.0) * 100.0
        max_dd = min(max_dd, dd)

    return {
        'signals': len(trades),
        'win_rate': round(100 * len(wins) / len(trades), 1),
        'avg_return_pct': round(100 * sum(rets) / len(rets), 3),
        'profit_factor': round(pf, 3),
        'max_drawdown_pct': round(abs(max_dd), 2),
        'cumulative_return_pct': round((equity - 1.0) * 100.0, 2),
    }


def _qualifies(row: dict, threshold: float) -> bool:
    """Mirror the live gate family for each calibration threshold."""
    if row.get('bias') not in ('LONG','SHORT') or row.get('score',0) < threshold:
        return False
    gap=float(row.get('gap',0))
    if threshold >= 78:
        return (gap >= 18 and bool(row.get('core_alignment')) and
                bool(row.get('daily_not_opposite')) and int(row.get('trigger_count',0)) >= 2)
    if threshold >= 68:
        return gap >= 14 and bool(row.get('core_alignment')) and int(row.get('trigger_count',0)) >= 1
    if threshold >= 55:
        return gap >= 10
    return True


def _non_overlapping(candidates: List[dict], threshold: float) -> List[dict]:
    """One position at a time, with the same gate family used by live decisions."""
    selected = []
    available_at = pd.Timestamp.min.tz_localize('UTC')
    for row in candidates:
        if not _qualifies(row, threshold):
            continue
        entry_time = pd.Timestamp(row['entry_time'])
        if entry_time < available_at:
            continue
        selected.append(row)
        available_at = pd.Timestamp(row['exit_time'])
    return selected


def backtest_frames(
    df12: pd.DataFrame,
    df4: pd.DataFrame,
    df1h: pd.DataFrame,
    df1d: pd.DataFrame,
    horizon_12h_bars: int = 4,
    min_bars: int = 140,
):
    """Strict walk-forward backtest with anti-look-ahead controls.

    Rules:
    * Every decision is made AFTER a 12H candle closes.
    * 4H / 1H / Daily inputs must also be fully closed at that decision time.
    * Entry is the OPEN of the NEXT 12H candle.
    * Exit is the close after ``horizon_12h_bars`` completed 12H candles.
    * Each threshold is evaluated with one open position at a time.

    This is a calibration backtest, not an exchange fill simulator. It intentionally
    does not assume intrabar fills, leverage, stops, slippage or fees unless those
    are modeled separately.
    """
    if horizon_12h_bars < 1:
        raise ValueError('horizon_12h_bars must be >= 1')

    frames = [df12, df4, df1h, df1d]
    if any(df is None or df.empty for df in frames):
        return {'summary': {}, 'trades': 0, 'candidates': 0, 'sample': [], 'method': 'strict_closed_candle'}

    # Sort and normalize timestamps once.
    df12 = df12.copy().sort_values('ts').reset_index(drop=True)
    df4 = df4.copy().sort_values('ts').reset_index(drop=True)
    df1h = df1h.copy().sort_values('ts').reset_index(drop=True)
    df1d = df1d.copy().sort_values('ts').reset_index(drop=True)
    for df in (df12, df4, df1h, df1d):
        df['ts'] = _utc_ts(df['ts'])

    # Need the next bar for entry and enough future bars for the exit.
    last_i = len(df12) - horizon_12h_bars - 1
    if last_i <= min_bars:
        return {'summary': {}, 'trades': 0, 'candidates': 0, 'sample': [], 'method': 'strict_closed_candle'}

    rows = []
    for i in range(min_bars, last_i + 1):
        bar_open = pd.Timestamp(df12.iloc[i]['ts'])
        decision_time = bar_open + _TF_DELTA['12h']

        s12 = _closed_slice(df12.iloc[:i+1], decision_time, '12h')
        s4 = _closed_slice(df4, decision_time, '4h')
        s1 = _closed_slice(df1h, decision_time, '1h')
        sd = _closed_slice(df1d, decision_time, '1d')
        if len(s12) < min_bars or min(len(s4), len(s1), len(sd)) < 30:
            continue

        analysis = score_snapshot_detail(s12, s4, s1, sd)
        direction = 'LONG' if analysis['long_score'] >= analysis['short_score'] else 'SHORT'
        score = max(float(analysis['long_score']), float(analysis['short_score']))
        opposite_score = min(float(analysis['long_score']), float(analysis['short_score']))

        entry_idx = i + 1
        exit_idx = i + horizon_12h_bars
        entry_time = pd.Timestamp(df12.iloc[entry_idx]['ts'])
        exit_time = pd.Timestamp(df12.iloc[exit_idx]['ts']) + _TF_DELTA['12h']
        entry = float(df12.iloc[entry_idx]['open'])
        exitp = float(df12.iloc[exit_idx]['close'])
        if not math.isfinite(entry) or entry <= 0 or not math.isfinite(exitp):
            continue

        raw = (exitp - entry) / entry
        ret = raw if direction == 'LONG' else -raw
        rows.append({
            'decision_time': decision_time.isoformat(),
            'entry_time': entry_time.isoformat(),
            'exit_time': exit_time.isoformat(),
            'direction': direction,
            'score': round(float(score), 1),
            'opposite_score': round(float(opposite_score), 1),
            'gap': round(float(score - opposite_score), 1),
            'bias': analysis.get('bias','NEUTRAL'),
            'stage': analysis.get('stage','NO TRADE'),
            'core_alignment': bool(analysis.get('core_alignment')),
            'daily_not_opposite': bool(analysis.get('daily_not_opposite')),
            'trigger_count': int(analysis.get('trigger_count',0)),
            'trigger_total': int(analysis.get('trigger_total',6)),
            'entry': round(entry, 8),
            'exit': round(exitp, 8),
            'return_pct': round(ret * 100, 4),
            'win': bool(ret > 0),
        })

    out: Dict[str, dict] = {}
    selected_by_threshold: Dict[str, List[dict]] = {}
    for th in THRESHOLDS:
        xs = _non_overlapping(rows, th)
        out[str(th)] = _trade_stats(xs)
        selected_by_threshold[str(th)] = xs

    return {
        'summary': out,
        'trades': len(rows),
        'candidates': len(rows),
        'sample': rows[-25:],
        'selected_sample': {k: v[-10:] for k, v in selected_by_threshold.items()},
        'method': 'strict_closed_candle_next_12h_open_no_overlap',
        'horizon_12h_bars': horizon_12h_bars,
    }
