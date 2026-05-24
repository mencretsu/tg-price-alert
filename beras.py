import requests
from datetime import date, timedelta
from datetime import datetime
import pytz
import os

BOT_TOKEN = os.environ['TELEGRAM_BOT_TOKEN']
CHANNEL_ID = os.environ['TELEGRAM_CHANNEL_ID']

# Variant ID beras nasional di SP2KP Kemendag
# komoditas "Beras" (id=1), tipe Barang Kebutuhan Pokok
BERAS_VARIANTS = {
    27: "Beras Medium",
    28: "Beras Premium",
}

BASE_URL = "https://api-sp2kp.kemendag.go.id"
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://sp2kp.kemendag.go.id/",
}

def get_harga_beras():
    # Ambil window 14 hari buat jaga-jaga kalau hari ini belum ada data
    today = date.today()
    tanggal_end = today.strftime("%Y-%m-%d")
    tanggal_start = (today - timedelta(days=14)).strftime("%Y-%m-%d")

    hasil = {}
    for variant_id, nama in BERAS_VARIANTS.items():
        try:
            r = requests.get(
                f"{BASE_URL}/report/api/hnt/history-series",
                params={
                    "tanggal_start": tanggal_start,
                    "tanggal_end": tanggal_end,
                    "variant_id": variant_id,
                },
                headers=HEADERS,
                timeout=15,
            )
            r.raise_for_status()
            data = r.json()

            rows = data.get("data", [])
            if rows:
                latest = rows[-1]
                harga = latest.get("harga", 0)
                tgl = latest.get("tanggal_data", "")
                if harga and harga > 0:
                    hasil[nama] = {"harga": harga, "tanggal": tgl}
            print(f"  ✓ {nama}: {hasil.get(nama)}")
        except Exception as e:
            print(f"  ✗ {nama} (id={variant_id}): {e}")

    return hasil if hasil else None

def send_telegram(msg):
    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={"chat_id": CHANNEL_ID, "text": msg, "parse_mode": "HTML"},
    )

wib = pytz.timezone("Asia/Jakarta")
now = datetime.now(wib)

print("Fetching harga beras dari SP2KP Kemendag...")
harga = get_harga_beras()

if not harga:
    send_telegram(
        f"⚠️ <b>Harga kosong</b>\n\n"
        f"Sumber SP2KP Kemendag tidak tersedia.\n"
        f"📅 {now.strftime('%d %b %Y')} 🕐 {now.strftime('%H.%M')} WIB"
    )
else:
    lines = []
    tgl_data = ""
    for nama, info in harga.items():
        lines.append(f"• {nama}: <b>Rp {info['harga']:,}/kg</b>")
        tgl_data = info["tanggal"]

    # Info kalau data bukan hari ini (weekend/libur)
    catatan = ""
    if tgl_data and tgl_data != now.strftime("%Y-%m-%d"):
        catatan = f"\n⚠️ <i>Data terakhir tersedia: {tgl_data}</i>"

    msg = (
        f"🌾 <b>Harga Beras Hari Ini</b>\n\n"
        + "\n".join(lines)
        + catatan
        + f"\n\n📅 {now.strftime('%d %b %Y')} 🕐 {now.strftime('%H.%M')} WIB\n"
        f"📊 Sumber: Kemendag SP2KP"
    )
    send_telegram(msg)
