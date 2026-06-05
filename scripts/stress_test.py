import argparse
import time
import random
import requests
from datetime import datetime, timezone

parser = argparse.ArgumentParser()
parser.add_argument("--duration", type=int, default=10, help="Çalışma süresi (saniye)")
parser.add_argument("--rate", type=float, default=2.0, help="Saniyedeki istek sayısı")
parser.add_argument("--anomaly-chance", type=int, default=20, help="Anomali olasılığı (%)")
args = parser.parse_args()

API_URL = "http://localhost:8000/process-transaction"
print(f"🚀 Otomatik Test Başlıyor: Süre={args.duration}s, Hız={args.rate} req/s, Anomali Olasılığı=%{args.anomaly_chance}\n")

start_time = time.time()
req_interval = 1.0 / args.rate
users = [1, 2, 3, 4, 5] # Test edilecek kullanıcı havuzu

while time.time() - start_time < args.duration:
    loop_start = time.time()

    user_id = random.choice(users)
    # Verilen yüzdeye göre bu işlemin fraud olup olmayacağına zar atıyoruz
    is_anomaly = random.randint(1, 100) <= args.anomaly_chance

    if is_anomaly:
        amount = round(random.uniform(25000, 60000), 2) # Kural 1 İhlali: Devasa Tutar
        lat, lon = random.uniform(-90, 90), random.uniform(-180, 180) # Kural 2 İhlali: Rastgele imkansız konum
        status = " ANOMALİ ÜRETİLDİ"
    else:
        amount = round(random.uniform(10, 500), 2) # Normal alışveriş
        lat, lon = 41.0, 28.9 # İstanbul (Sabit normal konum)
        status = " Normal İşlem  "

    tx_data = {
        "user_id": user_id,
        "amount": amount,
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "latitude": lat,
        "longitude": lon
    }

    try:
        requests.post(API_URL, json=tx_data, timeout=2)
        print(f"{status} -> User: {user_id} | Tutar: {amount} TL")
    except Exception as e:
        print(f" Hata: API'ye ulaşılamıyor.")

    # Saniyedeki istek sayısını (rate) tutturmak için beklet
    elapsed = time.time() - loop_start
    sleep_time = req_interval - elapsed
    if sleep_time > 0:
        time.sleep(sleep_time)

print("\n Test başarıyla tamamlandı! Dashboard'u kontrol ediniz.")
