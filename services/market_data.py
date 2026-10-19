import yfinance as yf
from typing import Optional
import pandas as pd

def get_live_price(ticker: str) -> Optional[float]:
    """Fetch the latest closing price for a given ticker."""
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period="1d")
        if not df.empty:
            return float(df['Close'].iloc[-1])
        return None
    except Exception as ex:
        print(f"Error fetching price for {ticker}: {ex}")
        return None

def get_historical_data(ticker: str, period: str = "1mo") -> pd.DataFrame:
    """Fetch historical data for charts."""
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period=period)
        return df
    except Exception as ex:
        print(f"Error fetching history for {ticker}: {ex}")
        return pd.DataFrame()