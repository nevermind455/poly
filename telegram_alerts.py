"""
Telegram alert helper for the Polymarket bot.
Add to .env: TELEGRAM_BOT_TOKEN=... and TELEGRAM_CHAT_ID=...
Get token from @BotFather, chat_id from @userinfobot or by messaging your bot and visiting:
  https://api.telegram.org/bot<TOKEN>/getUpdates
"""

import os
import threading

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()
TELEGRAM_API = "https://api.telegram.org/bot"


def send(text: str) -> bool:
    """Send a message to Telegram. Returns True if sent, False if skipped/failed. No blocking."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return False

    def _send():
        try:
            import requests
            r = requests.post(
                f"{TELEGRAM_API}{TELEGRAM_BOT_TOKEN}/sendMessage",
                json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "disable_web_page_preview": True},
                timeout=10,
            )
            return r.status_code == 200
        except Exception:
            return False

    t = threading.Thread(target=_send, daemon=True)
    t.start()
    return True


def enabled() -> bool:
    return bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)
