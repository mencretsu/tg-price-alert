import requests
from datetime import datetime, date
import pytz
import os
import time

BOT_TOKEN = os.environ['TELEGRAM_BOT_TOKEN']
CHANNEL_ID = os.environ['TELEGRAM_CHANNEL_ID']

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36",
    "Accept": "application/json, text/plain, */*",
}

# ── SOURCE 1: hargapangan.id (PIHPS) ─────────────────────────────────────────
# Endpoint ini dipake sama mobile app PIHPS (reverse-engineered dari APK)
def get_from_pihps():
    today = date.today().strftime("%Y-%m-%d")
    # Komoditas ID beras di PIHPS: 1=Bawah I, 2=Bawah II, 3=Medium I,
    #                               4=Medium II, 5=Super I, 6=Super II
    nama_map = {
        "1": "Beras Bawah I",
        "2": "Beras Bawah II",
        "3": "Beras Medium I",
        "4": "Beras Medium II",
        "5": "Beras Super I",
        "6": "Beras Super II",
    }
    hasil = {}
    for kid, nama in nama_map.items():
        try:
            url = "https://hargapangan.id/tabel-harga/pasar-tradisional/komoditas"
            params = {
                "id_komoditas": kid,
                "id_provinsi": "0",   # 0 = nasional
                "id_kabupaten": "0",
                "tipe_laporan": "1",
                "tanggal_awal": today,
                "tanggal_akhir": today,
            }
            r = requests.get(url, params=params, headers=HEADERS, timeout=10)
            data = r.json()
            # Ambil harga rata-rata nasional dari response
            rows = data.get("data", [])
            harga_list = [
                float(row["harga"]) for row in rows
                if row.get("harga") and float(row["harga"]) > 0
            ]
            if harga_list:
                hasil[nama] = int(sum(harga_list) / len(harga_list))
            time.sleep(0.3)
        except Exception as e:
            print(f"  PIHPS komoditas {kid} error: {e}")
    return hasil if hasil else None

# ── SOURCE 2: Bapanas dev endpoint ───────────────────────────────────────────
# dev-panelharga masih hidup waktu dicek tadi
def get_from_bapanas():
    today = date.today().strftime("%Y-%m-%d")
    beras_ids = {34: "Beras Medium", 35: "Beras Premium"}
    hasil = {}
    try:
        url = "https://dev-panelharga.badanpangan.go.id/api/v1/harga-nasional"
        params = {"tanggal": today, "jenis": "eceran"}
        r = requests.get(url, params=params, headers=HEADERS, timeout=10)
        data = r.json()
        for item in data.get("data", []):
            kid = item.get("id") or item.get("komoditas_id")
            if kid in beras_ids:
                harga = item.get("harga") or item.get("harga_rata")
                if harga and float(harga) > 0:
                    hasil[beras_ids[kid]] = int(float(harga))
    except Exception as e:
        print(f"  Bapanas error: {e}")
    return hasil if hasil else None

# ── SOURCE 3: Scrape tabel statis bi.go.id/hargapangan ───────────────────────
# BI punya endpoint data chart yang return JSON (bukan HTML)
def get_from_bi_chart():
    try:
        # Endpoint chart BI yang return JSON langsung
        url = "https://www.bi.go.id/hargapangan/DataPage/GetHargaKomoditasNasional"
        today = date.today().strftime("%m/%d/%Y")
        payload = {
            "komoditasId": "1",  # 1 = Beras
            "tanggalAwal": today,
            "tanggalAkhir": today,
        }
        r = requests.post(url, json=payload, headers={
            **HEADERS,
            "Content-Type": "application/json",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": "https://www.bi.go.id/hargapangan",
        }, timeout=10)
        data = r.json()
        hasil = {}
        for item in data:
            nama = item.get("NamaKomoditas", "")
            harga = item.get("Harga", 0)
            if "beras" in nama.lower() and harga > 0:
                hasil[nama] = int(harga)
        return hasil if hasil else None
    except Exception as e:
        print(f"  BI chart error: {e}")
        return None

# ── MAIN ──────────────────────────────────────────────────────────────────────
def get_harga_beras():
    sources = [
        ("BI Chart API", get_from_bi_chart),
        ("Bapanas", get_from_bapanas),
        ("PIHPS", get_from_pihps),
    ]
    for nama_source, fn in sources:
        print(f"Mencoba {nama_source}...")
        hasil = fn()
        if hasil:
            print(f"  ✓ Berhasil dari {nama_source}: {len(hasil)} komoditas")
            return hasil, nama_source
        print(f"  ✗ Gagal dari {nama_source}")
    return None, None

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={
        "chat_id": CHANNEL_ID,
        "text": msg,
        "parse_mode": "HTML",
    })

wib = pytz.timezone("Asia/Jakarta")
now = datetime.now(wib)
harga, source = get_harga_beras()

if not harga:
    send_telegram(
        f"⚠️ <b>Gagal ambil data harga beras</b>\n\n"
        f"Semua sumber tidak tersedia saat ini.\n"
        f"📅 {now.strftime('%d %b %Y')} 🕐 {now.strftime('%H.%M')} WIB"
    )
else:
    lines = "\n".join([f"• {k}: <b>Rp {v:,}/kg</b>" for k, v in harga.items()])
    msg = (
        f"🌾 <b>Harga Beras Hari Ini</b>\n\n"
        f"{lines}\n\n"
        f"📅 {now.strftime('%d %b %Y')} 🕐 {now.strftime('%H.%M')} WIB\n"
        f"📊 Sumber: {source}"
    )
    send_telegram(msg)
