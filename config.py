import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

def csv_env(name, default):
    return [x.strip().upper() for x in os.getenv(name, default).split(',') if x.strip()]

@dataclass
class Settings:
    crypto_symbols: list[str]
    stock_symbols: list[str]
    scan_interval: int
    watch_score: float
    developing_score: float
    ready_score: float
    telegram_bot_token: str
    telegram_chat_id: str
    alpaca_api_key: str
    alpaca_secret_key: str
    alpaca_data_feed: str

settings = Settings(
    crypto_symbols=csv_env('CRYPTO_SYMBOLS','BTCUSDT,ETHUSDT,SOLUSDT,SUIUSDT,XRPUSDT,ADAUSDT'),
    stock_symbols=csv_env('STOCK_SYMBOLS','QQQ,NVDA,GOOGL'),
    scan_interval=int(os.getenv('SCAN_INTERVAL','60')),
    watch_score=float(os.getenv('WATCH_SCORE','60')),
    developing_score=float(os.getenv('DEVELOPING_SCORE','70')),
    ready_score=float(os.getenv('READY_SCORE','82')),
    telegram_bot_token=os.getenv('TELEGRAM_BOT_TOKEN',''),
    telegram_chat_id=os.getenv('TELEGRAM_CHAT_ID',''),
    alpaca_api_key=os.getenv('ALPACA_API_KEY',''),
    alpaca_secret_key=os.getenv('ALPACA_SECRET_KEY',''),
    alpaca_data_feed=os.getenv('ALPACA_DATA_FEED','iex'),
)
