from __future__ import annotations
import asyncio
import time
import httpx, pandas as pd, yfinance as yf

BINANCE_ENDPOINTS = [
    'https://data-api.binance.vision/api/v3/klines',
    'https://api1.binance.com/api/v3/klines',
    'https://api2.binance.com/api/v3/klines',
    'https://api3.binance.com/api/v3/klines',
    'https://api.binance.com/api/v3/klines',
]
_HEADERS = {'User-Agent': 'Mozilla/5.0 HadarBot/3.6'}


_INTERVAL_DELTA = {
    '1h': pd.Timedelta(hours=1),
    '4h': pd.Timedelta(hours=4),
    '12h': pd.Timedelta(hours=12),
    '1d': pd.Timedelta(days=1),
}


def closed_bars_only(df: pd.DataFrame, interval: str, now=None) -> pd.DataFrame:
    """Remove the currently-forming candle.

    Project timestamps are candle OPEN times. Core strategy calculations must use
    only fully closed candles, matching the user's wait-for-close rule and the
    strict backtest implementation.
    """
    if df is None or df.empty or interval not in _INTERVAL_DELTA:
        return df.reset_index(drop=True) if df is not None else df
    now = pd.Timestamp.now(tz='UTC') if now is None else pd.Timestamp(now)
    if now.tzinfo is None:
        now = now.tz_localize('UTC')
    else:
        now = now.tz_convert('UTC')
    opens = pd.to_datetime(df['ts'], utc=True)
    closes = opens + _INTERVAL_DELTA[interval]
    return df.loc[closes <= now].copy().reset_index(drop=True)


def _normalize_binance(rows):
    cols=['ts','open','high','low','close','volume','close_ts','qv','trades','tb','tq','ignore']
    df=pd.DataFrame(rows,columns=cols)
    for k in ['open','high','low','close','volume']:
        df[k]=pd.to_numeric(df[k], errors='coerce')
    df['ts']=pd.to_datetime(df.ts,unit='ms',utc=True)
    return df[['ts','open','high','low','close','volume']].dropna().reset_index(drop=True)


def _crypto_to_yahoo(symbol:str)->str:
    symbol = symbol.upper()
    if symbol.endswith('USDT'):
        return symbol[:-4] + '-USD'
    if symbol.endswith('BUSD'):
        return symbol[:-4] + '-USD'
    return symbol


def _resample(df: pd.DataFrame, interval: str) -> pd.DataFrame:
    if interval not in ('4h','12h'):
        return df.reset_index(drop=True)
    rule = '4h' if interval == '4h' else '12h'
    return (
        df.set_index('ts')
        .resample(rule)
        .agg({'open':'first','high':'max','low':'min','close':'last','volume':'sum'})
        .dropna()
        .reset_index()
    )


async def _fetch_binance(symbol:str, interval:str, limit:int=300):
    last_error = None
    async with httpx.AsyncClient(timeout=12, headers=_HEADERS, follow_redirects=True) as c:
        for base in BINANCE_ENDPOINTS:
            try:
                r = await c.get(base, params={'symbol':symbol.upper(),'interval':interval,'limit':limit})
                if r.status_code >= 400:
                    raise httpx.HTTPStatusError(f'{r.status_code} from {base}', request=r.request, response=r)
                rows = r.json()
                if not rows:
                    raise RuntimeError(f'Empty Binance response from {base}')
                return _normalize_binance(rows), base.split('/')[2]
            except Exception as e:
                last_error = e
                continue
    raise RuntimeError(f'All Binance endpoints failed for {symbol} {interval}: {last_error}')


async def _fetch_yahoo(symbol:str, interval='1h', period='60d'):
    yticker = _crypto_to_yahoo(symbol)
    itv={'1h':'1h','4h':'1h','12h':'1h','1d':'1d'}[interval]
    raw = await asyncio.to_thread(
        yf.download,
        yticker,
        period=period,
        interval=itv,
        auto_adjust=False,
        progress=False,
        threads=False,
        timeout=12,
    )
    if raw.empty:
        raise RuntimeError(f'No Yahoo data for {yticker}')
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns=raw.columns.get_level_values(0)
    df=(
        raw.reset_index()
        .rename(columns={'Datetime':'ts','Date':'ts','Open':'open','High':'high','Low':'low','Close':'close','Volume':'volume'})
    )
    df=df[['ts','open','high','low','close','volume']].dropna()
    df['ts']=pd.to_datetime(df['ts'], utc=True)
    return _resample(df, interval).tail(300), f'yahoo:{yticker}'


async def crypto_klines(symbol:str, interval:str, limit:int=300):
    try:
        return await _fetch_binance(symbol, interval, limit)
    except Exception as first_err:
        try:
            df, src = await _fetch_yahoo(symbol, interval, period='90d')
            return df, src
        except Exception as second_err:
            raise RuntimeError(f'Crypto data failed for {symbol} {interval} | Binance error: {first_err} | Yahoo error: {second_err}')


async def stock_klines(symbol:str, interval='1h', period='60d'):
    # yfinance fallback. For true live US data, replace/add Alpaca.
    df, src = await _fetch_yahoo(symbol, interval, period=period)
    return df, src


async def market_df(symbol:str, interval:str, asset_type:str):
    df, src = await (crypto_klines(symbol, interval) if asset_type=='crypto' else stock_klines(symbol, interval))
    df = closed_bars_only(df, interval)
    if df is None or df.empty:
        raise RuntimeError(f'No fully closed {interval} candles for {symbol} from {src}')
    return df, src


async def binance_history(symbol:str, interval:str, days:int=365):
    ms_day=86_400_000
    end=int(time.time()*1000); start=end-days*ms_day; rows=[]; cursor=start
    last_error = None
    for base in BINANCE_ENDPOINTS:
        try:
            async with httpx.AsyncClient(timeout=20, headers=_HEADERS, follow_redirects=True) as c:
                rows=[]; cursor=start
                while cursor < end:
                    r=await c.get(base, params={'symbol':symbol.upper(),'interval':interval,'limit':1000,'startTime':cursor,'endTime':end})
                    if r.status_code >= 400:
                        raise httpx.HTTPStatusError(f'{r.status_code} from {base}', request=r.request, response=r)
                    part=r.json()
                    if not part: break
                    rows.extend(part)
                    nxt=int(part[-1][0])+1
                    if nxt<=cursor: break
                    cursor=nxt
                    if len(part)<1000: break
            if rows:
                return _normalize_binance(rows)
        except Exception as e:
            last_error = e
            continue
    raise RuntimeError(f'All Binance history endpoints failed for {symbol}: {last_error}')


async def stock_history(symbol:str, interval:str, days:int=365):
    period=f'{min(days,729)}d' if interval!='1d' else f'{min(days,3650)}d'
    df, _src = await _fetch_yahoo(symbol, interval, period=period)
    return df.reset_index(drop=True)


async def history_df(symbol:str, interval:str, asset_type:str, days:int=365):
    if asset_type=='crypto':
        try:
            return await binance_history(symbol, interval, days)
        except Exception:
            df, _src = await _fetch_yahoo(symbol, interval, period=f'{min(days,729)}d')
            return df.reset_index(drop=True)
    return await stock_history(symbol, interval, days)
