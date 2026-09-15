from __future__ import annotations
import httpx, pandas as pd, yfinance as yf
from config import settings

BINANCE='https://api.binance.com/api/v3/klines'

async def binance_klines(symbol:str, interval:str, limit:int=300):
    async with httpx.AsyncClient(timeout=15) as c:
        r=await c.get(BINANCE, params={'symbol':symbol,'interval':interval,'limit':limit})
        r.raise_for_status(); rows=r.json()
    cols=['ts','open','high','low','close','volume','close_ts','qv','trades','tb','tq','ignore']
    df=pd.DataFrame(rows,columns=cols)
    for k in ['open','high','low','close','volume']: df[k]=pd.to_numeric(df[k])
    df['ts']=pd.to_datetime(df.ts,unit='ms',utc=True)
    return df[['ts','open','high','low','close','volume']]

async def stock_klines(symbol:str, interval='1h', period='60d'):
    # yfinance fallback. For true US live/near-live data, configure Alpaca and replace this function.
    itv={'1h':'1h','4h':'1h','12h':'1h','1d':'1d'}[interval]
    raw=yf.download(symbol, period=period, interval=itv, auto_adjust=False, progress=False, threads=False)
    if raw.empty: raise RuntimeError(f'No stock data for {symbol}')
    if isinstance(raw.columns, pd.MultiIndex): raw.columns=raw.columns.get_level_values(0)
    df=raw.reset_index().rename(columns={'Datetime':'ts','Date':'ts','Open':'open','High':'high','Low':'low','Close':'close','Volume':'volume'})
    df=df[['ts','open','high','low','close','volume']].dropna()
    if interval in ('4h','12h'):
        rule='4h' if interval=='4h' else '12h'
        df=df.set_index('ts').resample(rule).agg({'open':'first','high':'max','low':'min','close':'last','volume':'sum'}).dropna().reset_index()
    return df.tail(300)

async def market_df(symbol:str, interval:str, asset_type:str):
    return await (binance_klines(symbol,interval) if asset_type=='crypto' else stock_klines(symbol,interval))

async def binance_history(symbol:str, interval:str, days:int=365):
    """Paginated Binance spot klines for on-demand backtesting."""
    import time
    ms_day=86_400_000
    end=int(time.time()*1000); start=end-days*ms_day; rows=[]; cursor=start
    async with httpx.AsyncClient(timeout=25) as c:
        while cursor < end:
            r=await c.get(BINANCE, params={'symbol':symbol,'interval':interval,'limit':1000,'startTime':cursor,'endTime':end})
            r.raise_for_status(); part=r.json()
            if not part: break
            rows.extend(part); nxt=int(part[-1][0])+1
            if nxt<=cursor: break
            cursor=nxt
            if len(part)<1000: break
    cols=['ts','open','high','low','close','volume','close_ts','qv','trades','tb','tq','ignore']
    df=pd.DataFrame(rows,columns=cols)
    if df.empty: return df
    for k in ['open','high','low','close','volume']: df[k]=pd.to_numeric(df[k])
    df['ts']=pd.to_datetime(df.ts,unit='ms',utc=True)
    return df[['ts','open','high','low','close','volume']].drop_duplicates('ts').sort_values('ts').reset_index(drop=True)

async def stock_history(symbol:str, interval:str, days:int=365):
    # Yahoo intraday availability is limited; this is a calibration fallback, not guaranteed institutional data.
    period=f'{min(days,729)}d' if interval!='1d' else f'{min(days,3650)}d'
    itv='1h' if interval in ('1h','4h','12h') else '1d'
    raw=yf.download(symbol, period=period, interval=itv, auto_adjust=False, progress=False, threads=False)
    if raw.empty: raise RuntimeError(f'No historical stock data for {symbol}')
    if isinstance(raw.columns,pd.MultiIndex): raw.columns=raw.columns.get_level_values(0)
    df=raw.reset_index().rename(columns={'Datetime':'ts','Date':'ts','Open':'open','High':'high','Low':'low','Close':'close','Volume':'volume'})
    df=df[['ts','open','high','low','close','volume']].dropna()
    if interval in ('4h','12h'):
        rule='4h' if interval=='4h' else '12h'
        df=df.set_index('ts').resample(rule).agg({'open':'first','high':'max','low':'min','close':'last','volume':'sum'}).dropna().reset_index()
    return df.reset_index(drop=True)

async def history_df(symbol:str, interval:str, asset_type:str, days:int=365):
    return await (binance_history(symbol,interval,days) if asset_type=='crypto' else stock_history(symbol,interval,days))
