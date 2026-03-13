"""
============================================================
  POLYMARKET BTC UP/DOWN 5-MIN — REAL TRADING BOT
  WARNING: REAL MONEY (USDC)
  VPS MODE — No budget limit — 24/7
  
  Rules:
    $2 per trade
    3 positions max
    Buy only > 80c
    Stop-loss sell at 40c
    Forced trade in last 45s
    Blitz zone last 7s (max 2 trades)
============================================================
SETUP:
  pip install requests py-clob-client python-dotenv
  Create .env:
    PRIVATE_KEY=0x...
    FUNDER_ADDRESS=0x...
    SIGNATURE_TYPE=1
    TELEGRAM_BOT_TOKEN=...   (optional, for alerts)
    TELEGRAM_CHAT_ID=...     (optional)
  python real_bot.py
"""

import os
import sys
import json
import time
import csv
import random
from datetime import datetime
from pathlib import Path

import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    from py_clob_client.client import ClobClient
    from py_clob_client.clob_types import MarketOrderArgs, OrderArgs, OrderType
    from py_clob_client.order_builder.constants import BUY, SELL
except ImportError:
    print("ERROR: pip install py-clob-client python-dotenv")
    sys.exit(1)

try:
    import telegram_alerts
except ImportError:
    telegram_alerts = None

# ============================================================
# CONFIG
# ============================================================
PRIVATE_KEY = os.getenv("PRIVATE_KEY", "")
FUNDER = os.getenv("FUNDER_ADDRESS", "")
SIG_TYPE = int(os.getenv("SIGNATURE_TYPE", "1"))

if not PRIVATE_KEY or not FUNDER:
    print("ERROR: Set PRIVATE_KEY and FUNDER_ADDRESS in .env")
    sys.exit(1)

HOST = "https://clob.polymarket.com"
CHAIN_ID = 137
GAMMA = "https://gamma-api.polymarket.com"
BINANCE = "https://api.binance.com/api/v3"

MAX_TRADE = 4.0
MAX_POS = 3
BUY_THRESH = 0.80
STOP_LOSS = 0.40
FORCED_SEC = 45
BLITZ_SEC = 7
BLITZ_MAX = 2

CSV_FILE = Path("real_trades.csv")

# ============================================================
# INIT
# ============================================================
print("=" * 60)
print("  POLYMARKET BTC BOT — REAL TRADING")
print("=" * 60)
print(f"  Funder:  {FUNDER[:10]}...{FUNDER[-6:]}")
print(f"  Trade:   ${MAX_TRADE}/order | 3 pos | SL 40c")
print(f"  Forced:  @{FORCED_SEC}s | Blitz: @{BLITZ_SEC}s (max {BLITZ_MAX})")
print(f"  Mode:    VPS 24/7 — no budget limit")
print()

print("[*] Connecting to Polymarket...")
try:
    client = ClobClient(HOST, key=PRIVATE_KEY, chain_id=CHAIN_ID, signature_type=SIG_TYPE, funder=FUNDER)
    client.set_api_creds(client.create_or_derive_api_creds())
    print("[OK] Connected")
except Exception as e:
    print(f"[FAIL] {e}")
    sys.exit(1)

def alert(msg):
    """Send Telegram alert if configured."""
    if telegram_alerts and telegram_alerts.enabled():
        telegram_alerts.send(msg)

alert("🤖 Polymarket BTC bot started — VPS 24/7")

# ============================================================
# CSV
# ============================================================
if not CSV_FILE.exists():
    with open(CSV_FILE, "w", newline="") as f:
        csv.writer(f).writerow(["time", "slug", "action", "side", "token", "amount_usd", "shares", "price", "order_id", "status", "pnl", "btc"])

def log_csv(row):
    with open(CSV_FILE, "a", newline="") as f:
        csv.writer(f).writerow(row)

# ============================================================
# HELPERS
# ============================================================
def get_window():
    n = int(time.time())
    s = n - (n % 300)
    return {"slug": f"btc-updown-5m-{s}", "end": s + 300, "left": s + 300 - n}

def fetch_btc():
    try:
        return float(requests.get(f"{BINANCE}/ticker/price", params={"symbol": "BTCUSDT"}, timeout=5).json()["price"])
    except:
        return None

def fetch_candles():
    try:
        return [{"c": float(k[4]), "h": float(k[2]), "l": float(k[3]), "v": float(k[5])} for k in requests.get(f"{BINANCE}/klines", params={"symbol": "BTCUSDT", "interval": "1m", "limit": 50}, timeout=10).json()]
    except:
        return []

def fetch_market(slug):
    try:
        r = requests.get(f"{GAMMA}/events", params={"slug": slug}, timeout=10)
        if r.status_code == 200:
            d = r.json()
            if d and d[0].get("markets"):
                m = d[0]["markets"][0]
                toks = json.loads(m.get("clobTokenIds", "[]"))
                prs = json.loads(m.get("outcomePrices", "[0.5,0.5]"))
                return {
                    "found": True,
                    "q": m.get("question", slug),
                    "cid": m.get("conditionId", ""),
                    "up_token": toks[0] if toks else "",
                    "down_token": toks[1] if len(toks) > 1 else "",
                    "up_price": float(prs[0]),
                    "down_price": float(prs[1]),
                }
    except Exception as e:
        print(f"  [!] Market: {e}")
    return {"found": False}

def get_price(token_id):
    """Get live midpoint price from CLOB"""
    try:
        r = client.get_midpoint(token_id)
        if r and r.get("mid") is not None:
            return float(r["mid"])
    except:
        pass
    try:
        r = client.get_price(token_id, "BUY")
        if r and r.get("price") is not None:
            return float(r["price"])
    except:
        pass
    return None

# ============================================================
# PLACE ORDER — BUY
# ============================================================
def buy_shares(token_id, usd_amount):
    """Buy shares with FOK market order. Returns order response or None."""
    try:
        print(f"  [ORDER] BUY ${usd_amount} on {token_id[:25]}...")
        order_args = MarketOrderArgs(
            token_id=token_id,
            amount=round(usd_amount, 2),
            side=BUY,
        )
        signed = client.create_market_order(order_args)
        resp = client.post_order(signed, OrderType.FOK)

        if resp:
            oid = resp.get("orderID", "")
            if oid:
                print(f"  [OK] Order ID: {oid}")
            else:
                print(f"  [OK] Response: {resp}")
            return resp
        return None
    except Exception as e:
        print(f"  [ERROR] Buy failed: {e}")
        return None

# ============================================================
# PLACE ORDER — SELL (for stop-loss)
# ============================================================
def sell_shares(token_id, shares):
    """Sell shares. Try market sell, then limit sell."""
    try:
        print(f"  [ORDER] SELL {shares} shares on {token_id[:25]}...")

        # Get current price for limit order
        mid = get_price(token_id)
        if mid is None or mid < 0.01:
            print(f"  [!] No price — cannot sell, will settle at expiry")
            return None

        # Limit sell slightly below mid for fast fill
        sell_price = round(max(0.01, mid - 0.02), 2)
        sell_size = max(5.0, round(shares, 2))

        order_args = OrderArgs(
            token_id=token_id,
            price=sell_price,
            size=sell_size,
            side=SELL,
        )
        signed = client.create_order(order_args)
        resp = client.post_order(signed, OrderType.GTC)

        if resp:
            oid = resp.get("orderID", "")
            if oid:
                print(f"  [OK] Sell order ID: {oid}")
            else:
                print(f"  [OK] Sell response: {resp}")
            return resp
        return None
    except Exception as e:
        print(f"  [ERROR] Sell failed: {e}")
        return None

# ============================================================
# AI SIGNAL
# ============================================================
def calc_ema(data, period):
    if len(data) < period:
        return []
    k = 2 / (period + 1)
    r = [sum(data[:period]) / period]
    for i in range(period, len(data)):
        r.append(data[i] * k + r[-1] * (1 - k))
    return r

def calc_rsi(closes, period):
    if len(closes) < period + 1:
        return None
    g = l = 0
    for i in range(len(closes) - period, len(closes)):
        d = closes[i] - closes[i - 1]
        if d > 0: g += d
        else: l -= d
    ag, al = g / period, l / period
    return 100 if al == 0 else round(100 - 100 / (1 + ag / al), 1)

def ai_signal(candles, btc_price):
    if len(candles) < 15:
        return {"sig": "NEUTRAL", "score": 0, "conf": 0}
    closes = [c["c"] for c in candles]
    e9 = calc_ema(closes, 9)
    e21 = calc_ema(closes, 21)
    r7 = calc_rsi(closes, 7)
    score = 0
    if r7 is not None:
        if r7 < 30: score += 2
        elif r7 > 70: score -= 2
    if e9 and e21:
        if e9[-1] > e21[-1]: score += 1.5
        else: score -= 1.5
    score = max(-10, min(10, score))
    sig = "BULLISH" if score > 2 else "BEARISH" if score < -2 else "NEUTRAL"
    return {"sig": sig, "score": round(score, 1), "conf": min(100, abs(score) * 10)}

# ============================================================
# STATE
# ============================================================
positions = []    # [{side, token_id, entry_price, usd, shares, order_id}]
pnl_total = 0.0
daily_pnl = 0.0
trades_total = 0
daily_trades = 0
wins = 0
losses = 0
blitz_total = 0
window_blitz = 0
windows_done = 0
current_slug = ""
current_day = datetime.now().strftime("%Y-%m-%d")
start_time = datetime.now()
market = None
up_price = 0.5
down_price = 0.5

print()
print("[*] Running 24/7 — Ctrl+C to stop")
print()

# ============================================================
# MAIN LOOP
# ============================================================
while True:
    try:
        ts = datetime.now().strftime("%H:%M:%S")
        win = get_window()
        tl = win["left"]

        # ---- DAILY RESET ----
        today = datetime.now().strftime("%Y-%m-%d")
        if today != current_day:
            print(f"\n  [{ts}] === NEW DAY {today} === Yesterday: {daily_trades} trades, P/L: ${daily_pnl:+.4f}")
            log_csv([datetime.now().isoformat(), "DAILY", "RESET", "", "", "", "", "", "", "", f"{daily_pnl:.4f}", ""])
            current_day = today
            daily_pnl = 0.0
            daily_trades = 0

        # ---- UPTIME ----
        hours = (datetime.now() - start_time).total_seconds() / 3600

        # ---- NEW WINDOW ----
        if win["slug"] != current_slug:
            # Close old positions (should be empty if auto-exit worked)
            if positions:
                print(f"\n  [{ts}] {len(positions)} positions missed auto-exit — tracking P/L")
                for p in positions:
                    mid = get_price(p["token_id"])
                    if mid is not None:
                        pl = (mid - p["entry_price"]) * p["shares"]
                        pnl_total += pl
                        daily_pnl += pl
                        if pl >= 0: wins += 1
                        else: losses += 1
                        print(f"  [{ts}] SETTLED {p['side']} {p['entry_price']*100:.1f}c -> {mid*100:.1f}c | P/L: ${pl:.4f}")
                        print(f"  [{ts}] NOTE: Go to polymarket.com to claim this position")
                        log_csv([datetime.now().isoformat(), current_slug, "SETTLE_UNCLAIMED", p["side"], p["token_id"][:25], p["usd"], p["shares"], mid, p["order_id"], "needs_claim", f"{pl:.4f}", ""])
                positions = []
            windows_done += 1
            window_blitz = 0  # reset blitz counter

            current_slug = win["slug"]
            print(f"\n{'='*60}")
            print(f"  [{ts}] WINDOW: {win['slug']} | {tl}s left")
            print(f"{'='*60}")

            # Fetch market
            market = fetch_market(win["slug"])
            if market["found"]:
                print(f"  [{ts}] LIVE: {market['q']}")
                print(f"  [{ts}] UP={market['up_price']*100:.1f}c  DOWN={market['down_price']*100:.1f}c")
                up_price = market["up_price"]
                down_price = market["down_price"]
            else:
                print(f"  [{ts}] No live market this window")
                market = None

        # ---- NO MARKET? SKIP ----
        if not market or not market.get("found"):
            time.sleep(3)
            continue

        # ---- LIVE PRICES ----
        mid_up = get_price(market["up_token"])
        if mid_up is not None:
            up_price = mid_up
            down_price = round(1 - mid_up, 4)

        # ---- BTC + AI ----
        btc = fetch_btc() or 0
        candles = fetch_candles()
        ai = ai_signal(candles, btc)

        # ---- RECALC TIME ----
        win = get_window()
        tl = win["left"]

        
        if tl <= 0:
            time.sleep(1)
            continue

        in_blitz = 0 < tl <= BLITZ_SEC
        in_forced = BLITZ_SEC < tl <= FORCED_SEC

        # ---- DECIDE SIDE ----
        side = "UP" if ai["sig"] == "BULLISH" else "DOWN" if ai["sig"] == "BEARISH" else ("UP" if up_price >= down_price else "DOWN")
        price = up_price if side == "UP" else down_price
        token = market["up_token"] if side == "UP" else market["down_token"]
        higher_side = "UP" if up_price >= down_price else "DOWN"
        higher_price = max(up_price, down_price)
        higher_token = market["up_token"] if higher_side == "UP" else market["down_token"]

        # ---- UPDATE POSITION PRICES ----
        for p in positions:
            mid = get_price(p["token_id"])
            if mid is not None:
                p["current_price"] = mid

        # ============================================
        # STOP-LOSS — REAL SELL
        # ============================================
        new_pos = []
        for p in positions:
            cp = p.get("current_price", p["entry_price"])
            if cp <= STOP_LOSS:
                print(f"  [{ts}] !! SL HIT !! {p['side']} entry={p['entry_price']*100:.1f}c now={cp*100:.1f}c")

                # SELL THE SHARES
                sell_resp = sell_shares(p["token_id"], p["shares"])

                pl = (cp - p["entry_price"]) * p["shares"]
                pnl_total += pl
                daily_pnl += pl
                losses += 1
                trades_total += 1
                daily_trades += 1

                log_csv([
                    datetime.now().isoformat(), current_slug, "SL_SELL", p["side"],
                    p["token_id"][:25], p["usd"], p["shares"], cp,
                    sell_resp.get("orderID", "") if sell_resp else "no_fill",
                    "sold" if sell_resp else "settle_wait",
                    f"{pl:.4f}", f"{btc:.2f}"
                ])
                alert(f"🛑 STOP-LOSS {p['side']} @ {cp*100:.1f}c | P/L: ${pl:.2f} | BTC ${btc:,.0f}")
            else:
                new_pos.append(p)
        positions = new_pos

        # ============================================
        # BLITZ — last 7s only, never buy under 80¢
        # ============================================
        if in_blitz and higher_price >= BUY_THRESH and window_blitz < BLITZ_MAX:
            print(f"  [{ts}] >>> BLITZ {higher_side} @ {higher_price*100:.1f}c ${MAX_TRADE} ({tl}s) [{window_blitz+1}/{BLITZ_MAX}]")
            resp = buy_shares(higher_token, MAX_TRADE)
            if resp:
                shares = MAX_TRADE / higher_price if higher_price > 0 else 0
                positions.append({
                    "side": higher_side, "token_id": higher_token,
                    "entry_price": higher_price, "usd": MAX_TRADE,
                    "shares": round(shares, 2), "order_id": resp.get("orderID", ""),
                    "current_price": higher_price,
                })
                trades_total += 1
                daily_trades += 1
                blitz_total += 1
                window_blitz += 1
                log_csv([datetime.now().isoformat(), current_slug, "BLITZ", higher_side, higher_token[:25], MAX_TRADE, round(shares, 2), higher_price, resp.get("orderID", ""), "placed", "", f"{btc:.2f}"])
                alert(f"⚡ BLITZ {higher_side} @ {higher_price*100:.1f}c ${MAX_TRADE} | {win['slug']} | BTC ${btc:,.0f}")

        # ============================================
        # FORCED — must trade (skip if last 7s and would buy under 80¢)
        # ============================================
        elif in_forced and len(positions) < MAX_POS and not (tl <= BLITZ_SEC and price < BUY_THRESH):
            print(f"  [{ts}] >> FORCED {side} @ {price*100:.1f}c ${MAX_TRADE} ({tl}s)")
            resp = buy_shares(token, MAX_TRADE)
            if resp:
                shares = MAX_TRADE / price if price > 0 else 0
                positions.append({
                    "side": side, "token_id": token,
                    "entry_price": price, "usd": MAX_TRADE,
                    "shares": round(shares, 2), "order_id": resp.get("orderID", ""),
                    "current_price": price,
                })
                trades_total += 1
                daily_trades += 1
                log_csv([datetime.now().isoformat(), current_slug, "FORCED", side, token[:25], MAX_TRADE, round(shares, 2), price, resp.get("orderID", ""), "placed", "", f"{btc:.2f}"])
                alert(f"📌 FORCED {side} @ {price*100:.1f}c ${MAX_TRADE} | {current_slug} | BTC ${btc:,.0f}")

        # ============================================
        # NORMAL BUY
        # ============================================
        elif len(positions) < MAX_POS and price >= BUY_THRESH and ai["conf"] >= 40:
            print(f"  [{ts}] > BUY {side} @ {price*100:.1f}c ${MAX_TRADE} AI:{ai['sig']}({ai['conf']}%)")
            resp = buy_shares(token, MAX_TRADE)
            if resp:
                shares = MAX_TRADE / price if price > 0 else 0
                positions.append({
                    "side": side, "token_id": token,
                    "entry_price": price, "usd": MAX_TRADE,
                    "shares": round(shares, 2), "order_id": resp.get("orderID", ""),
                    "current_price": price,
                })
                trades_total += 1
                daily_trades += 1
                log_csv([datetime.now().isoformat(), current_slug, "BUY", side, token[:25], MAX_TRADE, round(shares, 2), price, resp.get("orderID", ""), "placed", "", f"{btc:.2f}"])
                alert(f"✅ BUY {side} @ {price*100:.1f}c ${MAX_TRADE} AI:{ai['sig']} | {current_slug} | BTC ${btc:,.0f}")

        # ============================================
        # STATUS
        # ============================================
        zone = "BLITZ!" if in_blitz else "FORCED" if in_forced else "open"
        wr = round(wins / (wins + losses) * 100, 1) if (wins + losses) > 0 else 0
        open_pl = sum((p.get("current_price", p["entry_price"]) - p["entry_price"]) * p["shares"] for p in positions)
        print(f"  [{ts}] {tl:3d}s {zone:7s} | BTC ${btc:,.0f} | UP={up_price*100:.1f}c DN={down_price*100:.1f}c | AI:{ai['sig']:8s} | Pos:{len(positions)}/{MAX_POS} | PnL:${pnl_total:+.2f} Day:${daily_pnl:+.2f} Open:${open_pl:+.2f} | {wins}W/{losses}L {wr}% | {hours:.1f}h")

        time.sleep(3)

    except KeyboardInterrupt:
        uptime = datetime.now() - start_time
        alert(f"🛑 Bot stopped | P/L: ${pnl_total:+.2f} | Today: ${daily_pnl:+.2f} | Trades: {trades_total} ({wins}W/{losses}L)")
        print(f"\n{'='*60}")
        print(f"  BOT STOPPED")
        print(f"  Uptime:  {uptime}")
        print(f"  Windows: {windows_done}")
        print(f"  P/L:     ${pnl_total:+.4f}")
        print(f"  Today:   ${daily_pnl:+.4f}")
        print(f"  Trades:  {trades_total} ({wins}W/{losses}L)")
        print(f"  Blitz:   {blitz_total}")
        print(f"  Open:    {len(positions)} positions (auto-settle on-chain)")
        print(f"  CSV:     {CSV_FILE}")
        print(f"{'='*60}")
        break
    except Exception as e:
        print(f"  [{ts}] ERROR: {e}")
        alert(f"❌ Bot ERROR: {e}")
        time.sleep(5)
