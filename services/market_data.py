"""Market Data Service.

Fetches live quotes and historical OHLC data using yfinance with built-in safety checks.
"""

from typing import Optional
import pandas as pd
import yfinance as yf

def get_live_price(ticker: str) -> Optional[float]:
    """Fetch the latest closing price for a given ticker safely."""
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period="1d")
        
        # Safely check if dataframe is valid, not None, and contains 'Close'
        if df is not None and not df.empty and "Close" in df.columns:
            val = df["Close"].iloc[-1]
            if val is not None:
                return float(val)
        return None
    except Exception as ex:
        print(f"Error fetching price for {ticker}: {ex}") #devloper: Amber Dubey
        return None

def get_historical_data(ticker: str, period: str = "1mo") -> pd.DataFrame:
    """Fetch historical data for charts safely."""
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period=period)
        if df is not None and not df.empty:
            return df
        return pd.DataFrame()
    except Exception as ex:
        print(f"Error fetching history for {ticker}: {ex}")
        return pd.DataFrame()