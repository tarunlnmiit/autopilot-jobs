import urllib.parse
import requests


def send_whatsapp(phone: str, apikey: str, message: str) -> bool:
    encoded = urllib.parse.quote(message)
    url = f"https://api.textmebot.com/send.php?phone={phone}&text={encoded}&apikey={apikey}"
    try:
        resp = requests.get(url, timeout=15)
        if resp.status_code == 200:
            print("WhatsApp sent.")
            return True
        print(f"WhatsApp failed: HTTP {resp.status_code} — {resp.text[:200]}")
        return False
    except Exception as e:
        print(f"WhatsApp error: {e}")
        return False


def send_telegram(bot_token: str, chat_id: str, message: str) -> bool:
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "HTML"}
    try:
        resp = requests.post(url, json=payload, timeout=15)
        if resp.status_code == 200:
            print("Telegram sent.")
            return True
        print(f"Telegram failed: HTTP {resp.status_code} — {resp.text[:200]}")
        return False
    except Exception as e:
        print(f"Telegram error: {e}")
        return False
