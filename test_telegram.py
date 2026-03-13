#!/usr/bin/env python3
"""Run on VPS: venv/bin/python3 test_telegram.py — checks .env and sends a test message."""
import os
import sys

# load .env from same folder
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

token = (os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()
chat_id = (os.getenv("TELEGRAM_CHAT_ID") or "").strip()

print("TELEGRAM_BOT_TOKEN:", "set" if token else "MISSING")
print("TELEGRAM_CHAT_ID:", repr(chat_id) if chat_id else "MISSING")

if not token or not chat_id:
    print("\nAdd to ~/poly/.env :")
    print("  TELEGRAM_BOT_TOKEN=your_bot_token_from_BotFather")
    print("  TELEGRAM_CHAT_ID=your_chat_id")
    print("Get chat_id: message your bot, then open https://api.telegram.org/bot<TOKEN>/getUpdates")
    sys.exit(1)

import requests
url = f"https://api.telegram.org/bot{token}/sendMessage"
r = requests.post(url, json={"chat_id": chat_id, "text": "Poly bot test — Telegram works."}, timeout=10)
print("\nResponse:", r.status_code, r.text[:200])
if r.status_code != 200:
    print("Fix token/chat_id or start the bot with /start in Telegram.")
    sys.exit(1)
print("OK — check Telegram for the test message.")
