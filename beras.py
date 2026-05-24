import requests
from datetime import datetime, date
import pytz
import os

BOT_TOKEN = os.environ['TELEGRAM_BOT_TOKEN']
CHANNEL_ID = os.environ['TELEGRAM_CHANNEL_ID']

# Mapping ID komoditas beras di API Bapanas
BERAS_KOMODITAS = {
    1: "Beras Kualitas Bawah I",
    2: "Beras Kualitas Bawah II",
    3: "Beras Kualitas Medium I",
    4: "Beras Kualitas Medium II",
    5: "Beras Kualitas Super I",
    6: "Beras Kualitas Super II",
}

def get_harga_beras():
    today = date.today().strftime("%Y-%m-%d")
    url = "https://panelharga.badanpangan.go.id/data/chart-all-komoditas-by-date-range"
    
    params = {
        "tgl1": today,
        "tgl2": today,
        "level": 1,  # 1=eceran, 2=grosir, 3=produsen
    }

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://panelharga.badanpangan.go.id/",
    }

    try:
        r = requests.get(url, params=params, headers=headers, timeout=15)
        r.raise_for_status()
        data = r.json()

        hasil = {}
        for item in data.get("data", []):
            kid = item.get("komoditas_id")
            if kid in BERAS_KOMODITAS:
                harga = item.get("harga_nasional")
                if harga and harga > 0:
                    hasil[BERAS_KOMODITAS[kid]] = int(harga)

        return hasil if hasil else None

    except Exception as e:
        print(f"Error: {e}")
        return None

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={
        "chat_id": CHANNEL_ID,
        "text": msg,
        "parse_mode": "HTML",
    })

wib = pytz.timezone("Asia/Jakarta")
now = datetime.now(wib)
harga = get_harga_beras()

if not harga:
    send_telegram(
        f"⚠️ <b>Gagal ambil data harga beras</b>\n\n"
        f"Tidak ada data tersedia hari ini.\n"
        f"📅 {now.strftime('%d %b %Y')} 🕐 {now.strftime('%H.%M')} WIB"
    )
else:
    lines = "\n".join([f"• {k}: <b>Rp {v:,}/kg</b>" for k, v in harga.items()])
    msg = (
        f"🌾 <b>Harga Beras Hari Ini</b>\n\n"
        f"{lines}\n\n"
        f"📅 {now.strftime('%d %b %Y')} 🕐 {now.strftime('%H.%M')} WIB\n"
        f"📊 Sumber: Badan Pangan Nasional"
    )
    send_telegram(msg)
