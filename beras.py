import requests
from bs4 import BeautifulSoup
import os
from datetime import datetime
import pytz
import time

BOT_TOKEN = os.environ['TELEGRAM_BOT_TOKEN']
CHANNEL_ID = os.environ['TELEGRAM_CHANNEL_ID']

def get_harga_beras(retries=3, delay=5):
    url = "https://www.bi.go.id/hargapangan"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=headers, timeout=15)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, 'html.parser')

            hasil = {}
            rows = soup.select('table tr')
            for row in rows:
                cols = row.find_all('td')
                if not cols:
                    continue
                nama = cols[0].get_text(strip=True).lower()
                if 'beras' in nama:
                    try:
                        harga = cols[1].get_text(strip=True).replace('.', '').replace(',', '')
                        hasil[cols[0].get_text(strip=True)] = int(harga)
                    except:
                        continue

            if hasil:
                return hasil
                
        except Exception as e:
            print(f"Attempt {attempt+1} failed: {e}")
            if attempt < retries - 1:
                time.sleep(delay)
    
    return None  # semua attempt gagal

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={
        'chat_id': CHANNEL_ID,
        'text': msg,
        'parse_mode': 'HTML'
    })

wib = pytz.timezone('Asia/Jakarta')
now = datetime.now(wib)

harga = get_harga_beras()

if not harga:
    send_telegram(
        f"⚠️ <b>Gagal ambil data harga beras</b>\n\n"
        f"Sudah dicoba 3x tapi tetap gagal.\n"
        f"📅 {now.strftime('%d %b %Y')} 🕐 {now.strftime('%H.%M')} WIB"
    )
else:
    lines = "\n".join([f"• {k}: <b>Rp {v:,}/kg</b>" for k, v in harga.items()])
    msg = f"""🌾 <b>Harga Beras Hari Ini</b>

{lines}

📅 {now.strftime('%d %b %Y')} 🕐 {now.strftime('%H.%M')} WIB
📊 Sumber: Bank Indonesia"""

    send_telegram(msg)
