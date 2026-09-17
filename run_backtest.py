from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

import pandas as pd

from backtest import backtest_frames
from datafeeds import history_df


def resample_from_1h(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    x = df.copy()
    x['ts'] = pd.to_datetime(x['ts'], utc=True)
    return (
        x.set_index('ts')
        .resample(rule, origin='epoch')
        .agg({'open':'first','high':'max','low':'min','close':'last','volume':'sum'})
        .dropna()
        .reset_index()
    )


async def main_async(symbol: str, days: int, horizon: int, output: str | None):
    # Pull one canonical 1H stream, then derive every higher timeframe from it.
    # This guarantees consistent boundaries and prevents cross-feed timestamp drift.
    h1 = await history_df(symbol, '1h', 'crypto', days=days)
    h1 = h1.sort_values('ts').drop_duplicates('ts').reset_index(drop=True)
    h4 = resample_from_1h(h1, '4h')
    h12 = resample_from_1h(h1, '12h')
    d1 = resample_from_1h(h1, '1D')

    report = backtest_frames(h12, h4, h1, d1, horizon_12h_bars=horizon)
    report['symbol'] = symbol
    report['requested_days'] = days
    report['data_start'] = str(pd.to_datetime(h1.ts.iloc[0], utc=True)) if len(h1) else None
    report['data_end'] = str(pd.to_datetime(h1.ts.iloc[-1], utc=True)) if len(h1) else None
    report['bars_1h'] = len(h1)
    report['bars_4h'] = len(h4)
    report['bars_12h'] = len(h12)
    report['bars_1d'] = len(d1)

    text = json.dumps(report, ensure_ascii=False, indent=2)
    if output:
        Path(output).write_text(text, encoding='utf-8')
        print(f'Saved: {output}')
    print(text)


def main():
    ap = argparse.ArgumentParser(description='Hadar v3.5 strict closed-candle walk-forward backtest')
    ap.add_argument('--symbol', default='BTCUSDT')
    ap.add_argument('--days', type=int, default=730, choices=[365, 730])
    ap.add_argument('--horizon', type=int, default=4, help='12H bars held; default 4 = 48h')
    ap.add_argument('--output', default='backtest_report.json')
    args = ap.parse_args()
    asyncio.run(main_async(args.symbol.upper(), args.days, args.horizon, args.output))


if __name__ == '__main__':
    main()
