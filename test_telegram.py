#!/usr/bin/env python3
"""Run on VPS: venv/bin/python3 test_telegram.py — checks .env and sends a test message."""
import os
import sys
import requests

# load .env from same folder
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

token = (os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()
raw_chat = (os.getenv("TELEGRAM_CHAT_ID") or "").strip().strip("'\"")
chat_id = int(raw_chat) if raw_chat.lstrip("-").isdigit() else raw_chat

print("TELEGRAM_BOT_TOKEN:", "set" if token else "MISSING")
print("TELEGRAM_CHAT_ID in .env:", repr(chat_id))

if not token:
    print("\nAdd TELEGRAM_BOT_TOKEN=... to ~/poly/.env")
    sys.exit(1)

# Fetch getUpdates to find valid chat_id
print("\nFetching getUpdates (chats that messaged your bot)...")
up = requests.get(f"https://api.telegram.org/bot{token}/getUpdates", timeout=10).json()
if not up.get("ok"):
    print("getUpdates failed:", up)
    sys.exit(1)
results = up.get("result", [])
seen = set()
for u in results:
    msg = u.get("message") or u.get("edited_message") or {}
    ch = msg.get("chat", {})
    cid = ch.get("id")
    if cid is not None and cid not in seen:
        seen.add(cid)
        print("  -> chat_id from Telegram:", cid, " (type:", ch.get("type", "?"), ")")
if not seen:
    print("  No chats found. Open your bot in Telegram, tap START, send 'hi', then run this again.")
    print("  Then set TELEGRAM_CHAT_ID= to the number shown above after you get one.")
    if not raw_chat:
        sys.exit(1)
elif raw_chat and seen:
    try:
        if int(raw_chat) not in seen:
            print("\nYour .env chat_id not in getUpdates. Try: TELEGRAM_CHAT_ID=" + str(list(seen)[0]))
    except ValueError:
        pass

if not raw_chat:
    print("\nAdd TELEGRAM_CHAT_ID=<number from above> to ~/poly/.env")
    sys.exit(1)

url = f"https://api.telegram.org/bot{token}/sendMessage"
r = requests.post(url, json={"chat_id": chat_id, "text": "Poly bot test — Telegram works."}, timeout=10)
print("\nSend response:", r.status_code, r.text[:250])
if r.status_code != 200:
    print("\n'chat not found' = open the bot in Telegram, tap START, send one message, then run this again.")
    if seen:
        print("Use this in .env: TELEGRAM_CHAT_ID=" + str(list(seen)[0]))
    sys.exit(1)
print("OK — check Telegram for the test message.")
