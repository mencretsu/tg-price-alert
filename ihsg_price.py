import requests
from datetime import datetime
import pytz
import os

BOT_TOKEN = os.environ['TELEGRAM_BOT_TOKENIHSG']
CHANNEL_ID = os.environ['TELEGRAM_CHANNEL_IDIHSG']
LAST_PRICE_FILE = "last_price_ihsg.txt"
THRESHOLD = 50

def get_ihsg():
    r = requests.get(
        "https://query1.finance.yahoo.com/v8/finance/chart/%5EJKSE",
        params={"interval": "1m", "range": "1d"},
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=15,
    )
    data = r.json()
    price = data["chart"]["result"][0]["meta"]["regularMarketPrice"]
    return round(price, 2)

def read_last_price():
    try:
        with open(LAST_PRICE_FILE, "r") as f:
            return float(f.read().strip())
    except:
        return None

def write_last_price(price):
    with open(LAST_PRICE_FILE, "w") as f:
        f.write(str(price))

def send_telegram(msg):
    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={"chat_id": CHANNEL_ID, "text": msg, "parse_mode": "HTML"},
    )

wib = pytz.timezone("Asia/Jakarta")
now = datetime.now(wib)

current = get_ihsg()
last = read_last_price()

if last is None:
    write_last_price(current)
    print(f"First run, harga disimpen: {current}")
else:
    diff = current - last
    if abs(diff) >= THRESHOLD:
        pct = diff / last * 100
        emoji = "🟢" if diff >= 0 else "🔴"
        sign = "+" if diff >= 0 else ""
        msg = (
            f"{emoji}\n"
            f"{last:,.2f} → {current:,.2f}\n"
            f"{sign}{pct:.2f}%\n\n"
            f"[{now.strftime('%-d %b %Y %H.%M')} WIB]"
        )
        print(msg)
        send_telegram(msg)
        write_last_price(current)
    else:
        print(f"No alert. Last: {last}, Current: {current}, Diff: {diff:.2f}")
