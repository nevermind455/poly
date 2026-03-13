"""
Polymarket BTC Bot — Advanced Command Center Dashboard

Reads bot log: real_trades.csv
Displays live trading statistics in terminal.

Features
- Live BTC price
- Bot uptime
- Total trades
- Wins / Losses
- Win rate
- Total PnL
- Equity curve (PnL over time)
- Last 10 trades

Install:
    pip install rich pandas requests

Run:
    python polymarket_bot_dashboard.py
"""

import time
import pandas as pd
import requests
from pathlib import Path
from datetime import datetime
from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.console import Console

CSV_FILE = Path("real_trades.csv")
BINANCE = "https://api.binance.com/api/v3/ticker/price"
REFRESH = 2

console = Console()
start_time = datetime.now()


def get_btc_price():
    try:
        r = requests.get(BINANCE, params={"symbol": "BTCUSDT"}, timeout=5)
        return float(r.json()["price"])
    except:
        return None


def load_data():
    if not CSV_FILE.exists():
        return pd.DataFrame()

    try:
        return pd.read_csv(CSV_FILE)
    except:
        return pd.DataFrame()


def calculate_stats(df):

    if df.empty:
        return {
            "trades": 0,
            "wins": 0,
            "losses": 0,
            "pnl": 0,
            "winrate": 0
        }

    pnl_vals = pd.to_numeric(df["pnl"], errors="coerce")

    pnl = pnl_vals.sum(skipna=True)

    wins = (pnl_vals > 0).sum()
    losses = (pnl_vals < 0).sum()

    total = wins + losses

    winrate = (wins / total * 100) if total > 0 else 0

    trades = len(df[df["action"].isin(["BUY", "FORCED", "BLITZ"])])

    return {
        "trades": trades,
        "wins": int(wins),
        "losses": int(losses),
        "pnl": float(pnl),
        "winrate": round(winrate, 1)
    }


def build_stats_table(stats, btc, uptime):

    table = Table(title="Bot Stats")

    table.add_column("Metric")
    table.add_column("Value")

    table.add_row("Time", datetime.now().strftime("%H:%M:%S"))

    if btc:
        table.add_row("BTC Price", f"${btc:,.0f}")
    else:
        table.add_row("BTC Price", "-")

    table.add_row("Uptime", str(uptime).split(".")[0])

    table.add_row("Total Trades", str(stats["trades"]))

    table.add_row("Wins", str(stats["wins"]))

    table.add_row("Losses", str(stats["losses"]))

    table.add_row("Win Rate", f"{stats['winrate']}%")

    table.add_row("Total PnL", f"${stats['pnl']:.4f}")

    return table


def build_recent_trades(df):

    table = Table(title="Recent Trades")

    table.add_column("Time")
    table.add_column("Action")
    table.add_column("Side")
    table.add_column("Price")
    table.add_column("PnL")

    if not df.empty:

        recent = df.tail(10)

        for _, r in recent.iterrows():

            t = str(r.get("time", ""))[11:19]
            action = str(r.get("action", ""))
            side = str(r.get("side", ""))
            price = str(r.get("price", ""))
            pnl = str(r.get("pnl", ""))

            table.add_row(t, action, side, price, pnl)

    return table


def build_equity_curve(df):

    table = Table(title="Equity Curve (Recent)")

    table.add_column("Trade #")
    table.add_column("PnL")

    if df.empty:
        return table

    pnl_vals = pd.to_numeric(df["pnl"], errors="coerce").fillna(0)

    equity = pnl_vals.cumsum()

    last = equity.tail(10)

    for i, v in enumerate(last):
        table.add_row(str(len(equity) - len(last) + i + 1), f"${v:.4f}")

    return table


def build_dashboard():

    btc = get_btc_price()

    df = load_data()

    stats = calculate_stats(df)

    uptime = datetime.now() - start_time

    layout = Layout()

    layout.split_column(
        Layout(name="top", size=10),
        Layout(name="middle", size=12),
        Layout(name="bottom")
    )

    layout["top"].update(Panel(build_stats_table(stats, btc, uptime)))

    layout["middle"].update(Panel(build_recent_trades(df)))

    layout["bottom"].update(Panel(build_equity_curve(df)))

    return layout


def main():

    with Live(build_dashboard(), refresh_per_second=1, console=console) as live:

        while True:

            time.sleep(REFRESH)

            live.update(build_dashboard())


if __name__ == "__main__":

    main()
