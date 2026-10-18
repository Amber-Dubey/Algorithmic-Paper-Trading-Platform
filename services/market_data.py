import streamlit as st
import yfinance as yf


@st.cache_data(ttl=60)
def get_live_price(ticker: str) -> float | None:
    """Return the latest closing price for a ticker (Stock, Crypto, or Forex).

    Returns None if the ticker is invalid or the request fails, so callers
    can fall back without crashing.
    """
    try:
        ticker_obj = yf.Ticker(ticker)
        hist = ticker_obj.history(period="1d")
        if hist.empty:
            return None
        return float(hist["Close"].iloc[-1])
    except Exception:
        return None
