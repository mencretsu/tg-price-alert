import requests
from datetime import date, timedelta, datetime
import pytz
import os

BOT_TOKEN = os.environ['TELEGRAM_BOT_TOKEN']
CHANNEL_ID = os.environ['TELEGRAM_CHANNEL_ID']

VARIANTS = {
    "beras medium":   {"id": 27, "region": "A"},
    "beras premium":  {"id": 28, "region": "A"},
    "bulog sphp":     {"id": 29, "region": "A"},
}

HEADERS = {"User-Agent": "Mozilla/5.0", "Referer": "https://sp2kp.kemendag.go.id/"}

def get_harga(variant_id):
    today = date.today()
    r = requests.get(
        "https://api-sp2kp.kemendag.go.id/report/api/hnt/history-series",
        params={
            "tanggal_start": (today - timedelta(days=14)).strftime("%Y-%m-%d"),
            "tanggal_end": today.strftime("%Y-%m-%d"),
            "variant_id": variant_id,
        },
        headers=HEADERS,
        timeout=15,
    )
    data = r.json().get("data") or []
    if len(data) < 2:
        return None
    latest = data[-1]
    prev   = data[-2]
    harga  = latest["harga"]
    pct    = (harga - prev["harga"]) / prev["harga"] * 100
    tgl    = latest["tanggal_data"]
    return {"harga": harga, "pct": pct, "tanggal": tgl}

def fmt_harga(n):
    return f"Rp {n:,}".replace(",", ".")

def fmt_pct(p):
    sign = "+" if p >= 0 else ""
    return f"{sign}{p:.2f}%"

def send_telegram(msg):
    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={"chat_id": CHANNEL_ID, "text": msg, "parse_mode": "HTML"},
    )

wib  = pytz.timezone("Asia/Jakarta")
now  = datetime.now(wib)
today_str = now.strftime("%Y-%m-%d")

lines = []
tgl_data = None

for nama, cfg in VARIANTS.items():
    d = get_harga(cfg["id"])
    if not d:
        lines.append(f"{nama:<15} data tidak tersedia")
        continue
    tgl_data = d["tanggal"]
    lines.append(f"{nama:<15} {fmt_harga(d['harga'])}  {fmt_pct(d['pct'])}")

is_latest = tgl_data == today_str
tgl_label = now.strftime("%-d %b %Y") if is_latest else \
            f"data per {datetime.strptime(tgl_data, '%Y-%m-%d').strftime('%-d %b')}"

msg = "\n".join(lines) + f"\n\n{tgl_label} · <sp2kp.kemendag.go.id>"
print(msg)
send_telegram(msg)
