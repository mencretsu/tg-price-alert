import requests
from datetime import date, timedelta, datetime
import pytz
import os

BOT_TOKEN = os.environ['TELEGRAM_BOT_TOKEN']
CHANNEL_ID = os.environ['TELEGRAM_CHANNEL_ID']

VARIANTS = {
    "beras medium":  52,
    "beras premium": 51,
}

HEADERS = {"User-Agent": "Mozilla/5.0", "Referer": "https://sp2kp.kemendag.go.id/"}
BASE = "https://api-sp2kp.kemendag.go.id/report/api"

def get_harga(variant_id, tanggal):
    r = requests.get(
        f"{BASE}/average-price/hnt-disparity",
        params={"variant_id": variant_id, "tanggal": tanggal},
        headers=HEADERS, timeout=15,
    )
    data = r.json().get("data")
    if not data:
        return None
    return data["hnt"]

def get_last_two_dates():
    today = date.today()
    r = requests.get(
        f"{BASE}/hnt/history-series",
        params={
            "tanggal_start": (today - timedelta(days=14)).strftime("%Y-%m-%d"),
            "tanggal_end": today.strftime("%Y-%m-%d"),
            "variant_id": 52,
        },
        headers=HEADERS, timeout=15,
    )
    data = r.json().get("data") or []
    if len(data) < 2:
        return None, None
    return data[-1]["tanggal_data"], data[-2]["tanggal_data"]

def fmt_harga(n):
    return f"Rp {int(n):,}".replace(",", ".")

def fmt_pct(p):
    sign = "+" if p >= 0 else ""
    return f"{sign}{p:.2f}%"

def send_telegram(msg):
    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={"chat_id": CHANNEL_ID, "text": msg, "parse_mode": "HTML"},
    )

wib = pytz.timezone("Asia/Jakarta")
now = datetime.now(wib)

tgl_today, tgl_prev = get_last_two_dates()
if not tgl_today:
    send_telegram("⚠️ gagal ambil data")
    exit()

lines = []
for nama, vid in VARIANTS.items():
    h_today = get_harga(vid, tgl_today)
    h_prev  = get_harga(vid, tgl_prev)
    if not h_today or not h_prev:
        lines.append(f"{nama:<15} data tidak tersedia")
        continue
    pct = (h_today - h_prev) / h_prev * 100
    lines.append(f"{nama:<15} {fmt_harga(h_today)}  {fmt_pct(pct)}")

is_today = tgl_today == now.strftime("%Y-%m-%d")
tgl_label = now.strftime("%-d %b %Y") if is_today else \
            f"data per {datetime.strptime(tgl_today, '%Y-%m-%d').strftime('%-d %b')}"

msg = "\n".join(lines) + f"\n\n{tgl_label} \n· Data by: sp2kp.kemendag.go.id"
# print(msg)
# print(f"TOKEN: {BOT_TOKEN[:10]}...")
# print(f"CHANNEL: {CHANNEL_ID}")
# r = requests.post(
#     f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
#     json={"chat_id": CHANNEL_ID, "text": msg, "parse_mode": "HTML"},
# )
# print(r.json())
send_telegram(msg)
