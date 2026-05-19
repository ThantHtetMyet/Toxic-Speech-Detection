"""
Telegram alert sender.

Setup:
  1. Open Telegram → message @BotFather → /newbot → copy token
  2. Message YOUR new bot once
  3. Visit: https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates
  4. Copy the "id" number from "chat" → that is your CHAT_ID
  5. Edit config.py → paste TELEGRAM_TOKEN and TELEGRAM_CHAT_ID
"""

import requests
from datetime import datetime
from config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID


def send_alert(mic_name: str, transcript: str, scores: dict) -> bool:
    """Send bullying alert to Telegram. Returns True if successful."""

    if TELEGRAM_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("[Telegram] Token not configured — skipping alert.")
        print("[Telegram] Edit config.py to set TELEGRAM_TOKEN and TELEGRAM_CHAT_ID")
        return False

    # Format score summary
    score_lines = "\n".join(
        f"  • {k}: {v*100:.1f}%"
        for k, v in scores.items()
        if v > 0.1
    ) or "  (keyword detection)"

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    message = (
        f"🚨 *BULLYING DETECTED*\n\n"
        f"📍 *Mic:* {mic_name}\n"
        f"🕐 *Time:* {now}\n\n"
        f"📝 *What was said:*\n"
        f"_{transcript[:400]}_\n\n"
        f"📊 *Confidence Scores:*\n{score_lines}"
    )

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

    try:
        resp = requests.post(url, json={
            "chat_id":    TELEGRAM_CHAT_ID,
            "text":       message,
            "parse_mode": "Markdown",
        }, timeout=10)

        if resp.ok:
            print(f"[Telegram] ✅ Alert sent for '{mic_name}'")
            return True
        else:
            print(f"[Telegram] ❌ Failed: {resp.status_code} — {resp.text}")
            return False

    except Exception as e:
        print(f"[Telegram] ❌ Error: {e}")
        return False
