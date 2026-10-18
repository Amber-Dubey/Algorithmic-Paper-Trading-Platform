"""Multi-Asset Paper Trading Web Application.

A dark-mode, terminal-styled Streamlit dashboard for real-time and
polling data. Users can authenticate, trade fractional shares across
Stock / Crypto / Forex, and inspect live portfolio metrics, a market
valuation table, and an immutable transaction ledger.
"""

from __future__ import annotations
import plotly.graph_objects as go
import streamlit as st
import pandas as pd
import yfinance as yf

from database.models import Portfolio, Transaction, User, init_db
from services import market_data, trading_engine
from utils.auth import register_user, authenticate_user 

# ---------------------------------------------------------------------------
# Application setup
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Paper Trading Terminal",
    page_icon="▤",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Global injectables — styling, sub-navigation, and cached helpers
# ---------------------------------------------------------------------------

CSS = """
:root {
  --bg: #0d1117;
  --panel: #161b22;
  --border: #30363d;
  --text: #e6edf3;
  --muted: #8b949e;
  --accent: #238636;
  --accent-weak: #3fb950;
  --danger: #f85149;
  --warning: #d29922;
  --info: #58a6ff;
  --radius: 10px;
}
body {
  font-family: "SF Mono", "Consolas", "Menlo", "Courier New", monospace;
  background: var(--bg) !important;
  color: var(--text) !important;
}
[data-testid="stApp"] {
  background: var(--bg) !important;
}
[data-testid="stAppViewContainer"] {
  background: var(--bg) !important;
  padding: 0 !important;
}
/* Pane card */
.pane {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 1.25rem 1.5rem;
}
/* Metric cards */
.metric-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 1rem;
}
.metric-card {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 1rem 1.25rem;
}
.metric-label {
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--muted);
  margin-bottom: 0.25rem;
}
.metric-value {
  font-size: 1.4rem;
  font-weight: 600;
  color: var(--text);
}
.metric-sub {
  font-size: 0.8rem;
  color: var(--muted);
}
/* Tab styling */
[data-testid="stHorizontalContainer"] {
  gap: 0.25rem !important;
}
[datarole="tab"] {
  border: 1px solid var(--border) !important;
  background: var(--panel) !important;
  border-radius: 6px !important;
  color: var(--muted) !important;
  padding: 0.5rem 0.9rem !important;
  font-family: inherit !important;
}
[datarole="tab"][aria-selected="true"] {
  background: var(--accent) !important;
  border-color: var(--accent) !important;
  color: #ffffff !important;
}
/* Form footers */
.submit-row {
  margin-top: 1rem;
}
/* Tabs inside the charting section */
.chart-tabs {
  padding-top: 0.75rem;
}
/* Ledger strip */
.ledger-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
}
.ledger-stat {
  flex: 1 1 140px;
  min-width: 140px;
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 0.75rem 1rem;
  text-align: center;
}
.ledger-stat .label {
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--muted);
}
.ledger-stat .value {
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--text);
}
.ledger-stat.positive .value {
  color: var(--accent-weak);
}
.ledger-stat.negative .value {
  color: var(--danger);
}
/* Table theming overrides */
.stTable {
  --cell-padding: 0.5rem 0.75rem;
  color: var(--text) !important;
}
.stTable th {
  background: var(--bg);
  color: var(--muted);
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  border-bottom: 1px solid var(--border);
}
.stTable td {
  border-bottom: 1px solid var(--border);
  color: var(--text) !important;
}
.stTable tbody tr:hover {
  background: var(--panel) !important;
}
.stTextInput > div > input,
.stTextArea > div > textarea {
  background: var(--panel) !important;
  color: var(--text) !important;
  border: 1px solid var(--border) !important;
  border-radius: 6px !important;
}
.stTextInput > div > input:focus,
.stTextArea > div > textarea:focus {
  border-color: var(--accent) !important;
  box-shadow: 0 0 0 2px rgba(35, 134, 54, 0.25) !important;
}
.stButton > button {
  background: var(--accent) !important;
  color: #ffffff !important;
  border: 1px solid var(--accent) !important;
  border-radius: 6px !important;
  padding: 0.5rem 1rem !important;
  font-family: inherit !important;
}
.stButton > button:hover {
  background: var(--accent-weak) !important;
}
.stNumberInput > div > div > input {
  background: var(--panel) !important;
  color: var(--text) !important;
  border: 1px solid var(--border) !important;
  border-radius: 6px !important;
}
.stSelectbox > div > select,
.stMultiSelect > div > div > div > div > div {
  background: var(--panel) !important;
  color: var(--text) !important;
  border: 1px solid var(--border) !important;
  border-radius: 6px !important;
}
.auth-card {
  max-width: 380px;
  margin: 0 auto;
}
.form-error {
  color: var(--danger);
  font-size: 0.8rem;
  margin-top: 0.5rem;
}
"""

st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Shared data helpers
# ---------------------------------------------------------------------------


def _load_user() -> User | None:
    """Return the authenticated user or None."""
    return st.session_state.get("user")


def _active_user() -> User | None:
    user = _load_user()
    if user is None:
        st.switch_page([".", "auth"] if "auth" in st.page_config else ["./auth.py"])
    return user


def _selectbox_tickers() -> list[str]:
    return ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META", "BTC-USD", "ETH-USD", "SOL-USD", "EURUSD=X", "GBPUSD=X", "USDJPY=X"]


def _selectbox_intervals() -> list[str]:
    return ["1d", "5d", "1mo", "3mo", "1y"]


def _balance_row() -> None:
    user = _active_user()
    if user is None:
        return
    c1, c2 = st.columns([1, 1])
    with c1:
        st.metric(label="Cash Balance", value=f"${user.balance:,.2f}")
    with c2:
        st.metric(label="Account", value=f"#{user.id}")


def _total_portfolio_value(user: User) -> float:
    total = user.balance
    for p in user.portfolios:
        price = market_data.get_live_price(p.ticker) or 0.0
        total += price * p.shares
    return total


def _portfolio_holding_rows(user: User) -> list[dict]:
    rows: list[dict] = []
    for p in user.portfolios:
        price = market_data.get_live_price(p.ticker) or 0.0
        valuation = price * p.shares
        rows.append(
            {
                "Ticker": p.ticker,
                "Asset": p.asset_type,
                "Shares": f"{p.shares:,.4f}",
                "Avg Cost": f"${p.avg_cost:,.2f}",
                "Est. Price": f"${price:,.2f}",
                "Valuation": f"${valuation:,.2f}",
            }
        )
    return rows


def _render_holding_table(user: User) -> None:
    rows = _portfolio_holding_rows(user)
    if not rows:
        st.info("No positions yet. Place your first order in the Trading section.")
        return
    st.dataframe(
        rows,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Ticker": st.column_config.TextColumn("Ticker", width="medium"),
            "Asset": st.column_config.TextColumn("Asset", width="small"),
            "Shares": st.column_config.TextColumn("Shares", width="small"),
            "Avg Cost": st.column_config.TextColumn("Avg Cost", width="small"),
            "Est. Price": st.column_config.TextColumn("Est. Price", width="small"),
            "Valuation": st.column_config.TextColumn("Valuation", width="small"),
        },
    )


def _render_ledger(user: User, limit: int = 30) -> None:
    transactions = (
        Transaction.query.filter_by(user_id=user.id)
        .order_by(Transaction.timestamp.desc())
        .limit(limit)
        .all()
    )
    if not transactions:
        st.info("No transactions yet.")
        return
    rows = []
    for t in transactions:
        rows.append(
            {
                "Time": t.timestamp.astimezone().strftime("%Y-%m-%d %H:%M:%S UTC"),
                "Ticker": t.ticker,
                "Action": t.action,
                "Shares": f"{t.shares:,.4f}",
                "Price": f"${t.price:,.2f}",
                "Total": f"${t.shares * t.price:,.2f}",
            }
        )
    st.dataframe(
        rows,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Time": st.column_config.TextColumn("Time", width="small"),
            "Ticker": st.column_config.TextColumn("Ticker", width="small"),
            "Action": st.column_config.TextColumn("Action", width="small"),
            "Shares": st.column_config.TextColumn("Shares", width="small"),
            "Price": st.column_config.TextColumn("Price", width="small"),
            "Total": st.column_config.TextColumn("Total", width="small"),
        },
    )


# ---------------------------------------------------------------------------
# Auth (Login / Register) view
# ---------------------------------------------------------------------------


def auth_view() -> None:
    st.markdown('<div class="pane auth-card">', unsafe_allow_html=True)
    st.markdown('<div class="pane" style="padding:1rem;">', unsafe_allow_html=True)
    st.markdown(
        '<div style="text-align:center; margin-bottom:1rem;">'
        '<div style="font-size:2rem; font-weight:700; color:var(--accent);">'
        "▤ Paper Trading Terminal</div>"
        "<div style=\"font-size:0.85rem; color:var(--muted); margin-top:0.25rem;\">"
        "Multi-Asset Paper Trading Platform</div>"
        "</div>",
        unsafe_allow_html=True,
    )

    tab_log, tab_reg = st.tabs(["Login", "Register"])

    with tab_log:
        st.subheader("Sign in")
        username = st.text_input("Username", key="login_user")
        password = st.text_input("Password", type="password", key="login_pass")
        if st.button("Sign in", type="primary", use_container_width=True):
            user = authenticate_user(username, password)
            if user is None:
                st.error("Invalid username or password.")
            else:
                st.session_state["user"] = user
                st.success(f"Welcome back, {user.username}.")
                st.rerun()
        if st.button("Continue to dashboard", disabled=True, use_container_width=True):
            pass

    with tab_reg:
        st.subheader("Create an account")
        reg_user = st.text_input("Username", key="reg_user")
        reg_pass = st.text_input("Password", type="password", key="reg_pass")
        reg_pass2 = st.text_input("Confirm password", type="password", key="reg_pass2")
        if st.button("Register", type="primary", use_container_width=True):
            if not reg_user or not reg_pass or not reg_pass2:
                st.error("All fields are required.")
            elif reg_pass != reg_pass2:
                st.error("Passwords do not match.")
            elif len(reg_pass) < 6:
                st.error("Password must be at least 6 characters.")
            else:
                if register_user(reg_user, reg_pass):
                    st.success(f"Account created. Welcome, {reg_user}.")
                    st.rerun()
                else:
                    st.error("Registration failed. Username may already exist.")

    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Main dashboard
# ---------------------------------------------------------------------------


def main_view() -> None:
    user = _active_user()

    # --- Header / layout ---
    header = st.container()
    with header:
        st.markdown(
            '<div style="display:flex; justify-content:space-between; align-items:center;">'
            f'<div style="font-size:1.35rem; font-weight:700; color:var(--text);">'
            f'▤ Terminal — {user.username}</div>'
            f'<div style="font-size:0.8rem; color:var(--muted);">'
            f"Balance: ${user.balance:,.2f} | Portfolio: ${_total_portfolio_value(user):,.2f}</div>"
            "</div>",
            unsafe_allow_html=True,
        )

    # --- Metric grid ---
    col_a, col_b = st.columns([1, 1])
    with col_a:
        st.markdown('<div class="pane metric-card">', unsafe_allow_html=True)
        st.metric(label="Cash Balance", value=f"${user.balance:,.2f}")
        st.markdown('<div class="metric-sub">Available to invest</div>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    with col_b:
        st.markdown('<div class="pane metric-card">', unsafe_allow_html=True)
        st.metric(label="Total Portfolio Value", value=f"${_total_portfolio_value(user):,.2f}")
        st.markdown('<div class="metric-sub">Cash + live holdings</div>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # --- Live performance card ---
    st.markdown('<div class="pane">', unsafe_allow_html=True)
    st.markdown('<div class="metric-label">Performance</div>', unsafe_allow_html=True)
    total = _total_portfolio_value(user)
    starting = 100_000.0
    change = total - starting
    pct = (change / starting) * 100.0
    st.markdown(
        f'<div class="metric-value" style="color:{"var(--accent-weak)" if change >= 0 else "var(--danger)"};">'
        f"{change:+,.2f} ({pct:+.2f}%)</div>",
        unsafe_allow_html=True,
    )
    st.markdown('<div class="metric-sub">vs. initial $100,000.00</div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # --- Sidebar: Live balance + data toggle ---
    with st.sidebar:
        st.markdown("### Navigation")
        view_tabs = st.tabs(["Portfolio", "Chart", "Trading", "Ledger"])
        with view_tabs[0]:
            if st.button("View Holdings", use_container_width=True):
                st.session_state["active_view"] = "portfolio"
        with view_tabs[1]:
            if st.button("Chart Ticker", use_container_width=True):
                st.session_state["active_view"] = "chart"
        with view_tabs[2]:
            if st.button("Place Order", use_container_width=True):
                st.session_state["active_view"] = "trading"
        with view_tabs[3]:
            if st.button("Transaction Ledger", use_container_width=True):
                st.session_state["active_view"] = "ledger"

        st.markdown("### Controls")
        live_balance = st.checkbox("Live Balance Update", value=True, key="live_balance")
        st.radio(
            "Data Fetch Mode",
            ["Real-time", "Polling"],
            horizontal=True,
            key="data_mode",
        )
        data_mode = st.session_state.get("data_mode", "Real-time")
        if "data_mode" not in st.session_state:
            st.session_state["data_mode"] = "Real-time"
        polling_seconds = st.slider("Poll Interval (s)", min_value=5, max_value=60, value=30, key="poll_interval")

    # --- Sidebar live user balance indicator ---
    with st.sidebar:
        st.markdown('<div class="pane">', unsafe_allow_html=True)
        st.markdown('<div class="metric-label">Sidebar Balance</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="metric-value">${user.balance:,.2f}</div>',
            unsafe_allow_html=True,
        )
        st.markdown('<div class="metric-sub">'
                    f'Cached at: {st.session_state.get("balance_refresh", "")}</div>',
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

    # --- View controller ---
    active_view = st.session_state.get("active_view", "portfolio")
    if active_view == "portfolio":
        _portfolio_view(user, live_balance, polling_seconds, data_mode)
    elif active_view == "chart":
        _chart_view()
    elif active_view == "trading":
        _trading_view(user)
    elif active_view == "ledger":
        _ledger_view(user)

    # --- Footer ---
    st.markdown("---")
    st.markdown(
        '<div style="text-align:center; font-size:0.75rem; color:var(--muted);">'
        "▤ Multi-Asset Paper Trading Platform — Local demo. Live prices via yfinance.</div>",
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Portfolio view
# ---------------------------------------------------------------------------


def _portfolio_view(user: User, live_balance: bool, polling_seconds: int, data_mode: str) -> None:
    st.markdown('<div class="pane">', unsafe_allow_html=True)
    st.markdown('<div style="display:flex; justify-content:space-between; align-items:center;">'
                '<div style="font-size:1.1rem; font-weight:600; color:var(--text);">'
                "Holdings & Valuation</div>"
                '<div style="font-size:0.75rem; color:var(--muted);">'
                f"${_total_portfolio_value(user):,.2f} total</div>"
                "</div>", unsafe_allow_html=True)

    if live_balance:
        st.markdown('<div class="pane">', unsafe_allow_html=True)
        st.markdown('<div class="metric-label">Refresh Cash Balance</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="metric-value">${user.balance:,.2f}</div>',
            unsafe_allow_html=True,
        )
        st.markdown('<div class="metric-sub">Updates on cadence interval</div>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.markdown('<div class="pane">', unsafe_allow_html=True)
        st.markdown('<div class="metric-label">Cash Balance (static)</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="metric-value">${user.balance:,.2f}</div>', unsafe_allow_html=True)
        st.markdown('<div class="metric-sub">Refreshed on demand</div>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    if data_mode == "Polling":
        st.markdown('<div class="pane">', unsafe_allow_html=True)
        st.markdown('<div class="metric-label">Market Poll</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="metric-value">{polling_seconds}s</div>',
            unsafe_allow_html=True,
        )
        st.markdown('<div class="metric-sub">Live price refresh</div>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="pane">', unsafe_allow_html=True)
    st.markdown('<div class="metric-label">Positions</div>', unsafe_allow_html=True)
    _render_holding_table(user)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("---", unsafe_allow_html=True)
    _ledger_view(user)


# ---------------------------------------------------------------------------
# Chart view
# ---------------------------------------------------------------------------


def _chart_view() -> None:
    st.markdown('<div class="pane">', unsafe_allow_html=True)
    st.markdown(
        '<div style="display:flex; justify-content:space-between; align-items:center;">'
        '<div style="font-size:1.1rem; font-weight:600; color:var(--text);">'
        "Market Chart</div>"
        '<div style="font-size:0.75rem; color:var(--muted);">Interactive candlestick + volume</div>'
        "</div>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        ticker = st.selectbox("Ticker", _selectbox_tickers(), key="chart_ticker")
    with col2:
        interval = st.selectbox("Interval", _selectbox_intervals(), key="chart_interval")

    if st.button("Render Chart", type="primary", use_container_width=True, key="render_chart"):
        st.session_state["active_chart_ticker"] = ticker
        st.session_state["active_chart_interval"] = interval
        st.rerun()

    ticker = st.session_state.get("active_chart_ticker", ticker)
    interval = st.session_state.get("active_chart_interval", interval)
    if ticker and interval:
        st.markdown('<div class="chart-tabs">', unsafe_allow_html=True)
        chart_tabs = st.tabs(["Candlestick", "Volume", "Trades"])
        with chart_tabs[0]:
            _render_candlestick(ticker, interval)
        with chart_tabs[1]:
            _render_volume(ticker, interval)
        with chart_tabs[2]:
            _render_trades(ticker, interval)
        st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


def _fetch_ohlc(ticker: str, interval: str) -> pd.DataFrame:
    try:
        data = yf.download(ticker, period="5d", interval=interval, progress=False)
        if data.empty:
            return pd.DataFrame()
        df = data.reset_index()
        df.columns = [
            "Datetime",
            "Open",
            "High",
            "Low",
            "Close",
            "Adj Close",
            "Volume",
        ]
        return df
    except Exception:
        return pd.DataFrame()


def _render_candlestick(ticker: str, interval: str) -> None:
    df = _fetch_ohlc(ticker, interval)
    if df.empty:
        st.error("Could not fetch OHLC data for this ticker. Check the ticker symbol and try again.")
        return
    fig = go.Figure()
    fig.add_trace(
        go.Candlestick(
            x=df["Datetime"],
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            name="OHLC",
        )
    )
    fig.update_layout(
        title=f"{ticker} — {interval}",
        xaxis_title="Time",
        yaxis_title="Price",
        height=420,
        template="plotly_dark",
        margin=dict(l=20, r=20, t=50, b=30),
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_volume(ticker: str, interval: str) -> None:
    df = _fetch_ohlc(ticker, interval)
    if df.empty:
        st.error(_chart_view.__doc__ if False else "Could not fetch OHLC data for this ticker.")
        return
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=df["Datetime"],
            y=df["Volume"],
            name="Volume",
            marker_color="#238636",
        )
    )
    fig.update_layout(
        title=f"{ticker} — Volume",
        xaxis_title="Time",
        yaxis_title="Volume",
        height=420,
        template="plotly_dark",
        margin=dict(l=20, r=20, t=50, b=30),
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_trades(ticker: str, interval: str) -> None:
    df = _fetch_ohlc(ticker, interval)
    if df.empty:
        st.error("Could not fetch OHLC data for this ticker.")
        return
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df["Datetime"],
            y=df["Close"],
            mode="lines",
            line=dict(color="#238636", width=2),
            name="Close",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df["Datetime"],
            y=df["Open"],
            mode="lines",
            line=dict(color="#8b949e", width=1),
            name="Open",
        )
    )
    fig.update_layout(
        title=f"{ticker} — Lanes",
        xaxis_title="Time",
        yaxis_title="Price",
        height=420,
        template="plotly_dark",
        margin=dict(l=20, r=20, t=50, b=30),
    )
    st.plotly_chart(fig, use_container_width=True)


# ---------------------------------------------------------------------------
# Trading view
# ---------------------------------------------------------------------------


def _trading_view(user: User) -> None:
    st.markdown('<div class="pane">', unsafe_allow_html=True)
    st.markdown(
        '<div style="display:flex; justify-content:space-between; align-items:center;">'
        '<div style="font-size:1.1rem; font-weight:600; color:var(--text);">'
        "Place Order</div>"
        '<div style="font-size:0.75rem; color:var(--muted);">Fractional shares supported</div>'
        "</div>", unsafe_allow_html=True)

    col1, col2 = st.columns([1, 1])
    with col1:
        ticker = st.selectbox("Ticker", _selectbox_tickers(), key="trade_ticker")
        asset_type = st.selectbox(
            "Asset Class",
            ["Stock", "Crypto", "Forex"],
            key="trade_asset_type",
        )
    with col2:
        action = st.radio(
            "Action",
            ["BUY", "SELL"],
            horizontal=True,
            key="trade_action",
        )
        shares = st.number_input(
            "Shares (fractional)",
            min_value=0.0001,
            format="%.4f",
            key="trade_shares",
        )

    price = market_data.get_live_price(ticker)
    if price is None:
        st.warning("Live price unavailable. Could not fetch a quote for this ticker.")
        return

    cost = price * shares
    with st.expander("Breakdown", expanded=True):
        st.write(f"**Price:** ${price:,.4f}")
        st.write(f"**Shares:** {shares:,.4f}")
        st.write(f"**Total:** ${cost:,.2f}")
        st.write(f"**Available Cash:** ${user.balance:,.2f}")

    can_buy = action == "BUY" and user.balance >= cost
    if st.button("Execute Trade", type="primary", use_container_width=True, disabled=not can_buy):
        success = trading_engine.execute_trade(
            user_id=user.id,
            ticker=ticker,
            asset_type=asset_type,
            action=action,
            shares=shares,
            price=price,
        )
        if success:
            st.success(f"Trade executed: {action} {shares:,.4f} {ticker} @ ${price:,.4f}")
            st.rerun()
        else:
            st.error("Trade failed. Check your balance or available shares.")

    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Ledger view
# ---------------------------------------------------------------------------


def _ledger_view(user: User) -> None:
    st.markdown('<div class="pane">', unsafe_allow_html=True)
    st.markdown(
        '<div style="display:flex; justify-content:space-between; align-items:center;">'
        '<div style="font-size:1.1rem; font-weight:600; color:var(--text);">'
        "Transaction Ledger</div>"
        '<div style="font-size:0.75rem; color:var(--muted);">Immutable transaction log</div>'
        "</div>", unsafe_allow_html=True)

    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown('<div class="metric-label">Transaction Count</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="metric-value">{user.transactions.count()}</div>', unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="metric-label">Total Volume</div>', unsafe_allow_html=True)
        total = st.session_state.get("total_ledger_volume", 0.0)
        st.markdown(f'<div class="metric-value">${total:,.2f}</div>', unsafe_allow_html=True)

    _render_ledger(user, limit=50)

    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("---", unsafe_allow_html=True)

    # Live snapshot of ledger totals for the sidebar
    transactions = (
        Transaction.query.filter_by(user_id=user.id)
        .order_by(Transaction.timestamp.desc())
        .all()
    )
    if transactions:
        st.session_state["total_ledger_volume"] = sum(
            t.shares * t.price for t in transactions
        )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    init_db()
    st.session_state.setdefault("balance_refresh", "")
    if "active_view" not in st.session_state:
        st.session_state["active_view"] = "portfolio"
    if "active_chart_ticker" not in st.session_state:
        st.session_state["active_chart_ticker"] = "AAPL"
    if "active_chart_interval" not in st.session_state:
        st.session_state["active_chart_interval"] = "1d"

    if _load_user() is None:
        auth_view()
    else:
        main_view()


if __name__ == "__main__":
    main()
