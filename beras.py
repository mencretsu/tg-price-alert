import requests
from datetime import date, timedelta, datetime
import pytz
import os

BOT_TOKEN = os.environ['TELEGRAM_BOT_TOKEN']
CHANNEL_ID = os.environ['TELEGRAM_CHANNEL_ID']
LAST_SENT_FILE = "last_sent_beras.txt"

VARIANTS = {
    "beras medium":  52,
    "beras premium": 51,
}

HEADERS = {"User-Agent": "Mozilla/5.0", "Referer": "https://sp2kp.kemendag.go.id/"}
BASE = "https://api-sp2kp.kemendag.go.id/report/api"

def already_sent_today():
    try:
        with open(LAST_SENT_FILE, "r") as f:
            return f.read().strip() == date.today().strftime("%Y-%m-%d")
    except:
        return False

def mark_sent():
    with open(LAST_SENT_FILE, "w") as f:
        f.write(date.today().strftime("%Y-%m-%d"))

wib = pytz.timezone("Asia/Jakarta")
now = datetime.now(wib)

def get_last_two_dates():
    today = datetime.now(wib).date()  # fix: pakai WIB
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
    print(f"tgl_today dari API : '{tgl_today}'")
    print(f"now WIB            : '{now.strftime('%Y-%m-%d')}'")
    if len(data) < 2:
        return None, None
    return data[-1]["tanggal_data"][:10], data[-2]["tanggal_data"][:10]  # fix: slice [:10]
    
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

if already_sent_today():
    print("Udah kirim hari ini, skip.")
    exit()

tgl_today, tgl_prev = get_last_two_dates()
if not tgl_today:
    print("Gagal ambil data.")
    exit()

# Kalau data belum update hari ini, skip dulu — nanti run berikutnya coba lagi
if tgl_today != now.strftime("%Y-%m-%d"):
    print(f"Data masih per {tgl_today}, belum update. Skip.")
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

tgl_label = now.strftime("%-d %b %Y")
msg = "\n".join(lines) + \
      f"\n\n<i>ℹ️ Data diambil berdasarkan harga nasional tertimbang (HNT) pasar tradisional</i>" \
      f"\n\n{tgl_label}"
print(msg)
send_telegram(msg)
mark_sent()
