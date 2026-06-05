import requests
import time
import random
from datetime import datetime, timezone

API_URL = "http://localhost:8000/process-transaction"

def send_transaction(user_id, amount, lat, lon):
    tx_data = {
        # Her işleme rastgele eşsiz bir ID atıyoruz
        "transaction_id": f"tx-{random.randint(100000, 999999)}",
        "user_id": user_id,
        "amount": amount,
        # TAM ŞU ANIN TARİHİ (Böylece 24 saat grafiğine kesin düşecek)
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "latitude": lat,
        "longitude": lon
    }
    try:
        response = requests.post(API_URL, json=tx_data)
        print(f" Gönderildi: User {user_id} | {amount} TL -> API Cevabı: {response.text}")
    except Exception as e:
        print(f" Hata: {e}")

print("🚀 Canlı Veri Akışı Testi Başlıyor (Ekrana Bakmayı Unutma!)...\n")

# Senaryolar: Karışık olarak Normal ve Fraud (Dolandırıcılık) işlemleri atıyoruz
test_cases = [
    (10, 150.0, 41.0, 28.9),   # Normal İşlem (Sıradan bir alışveriş)
    (11, 45.0, 41.1, 29.0),    # Normal İşlem
    (1, 8500.0, 41.0, 28.9),   #  FRAUD: Tutar çok yüksek!
    (12, 120.0, 41.0, 28.9),   # Normal İşlem
    (2, 300.0, 41.0, 28.9),    # Normal İşlem (Kullanıcı 2 İstanbul'da)
    (2, 350.0, -34.6, -58.3),  #  FRAUD: Kullanıcı 2 aniden Arjantin'de işlem yaptı! (İmkansız Konum)
    (13, 80.0, 41.0, 28.9),    # Normal İşlem
]

for user_id, amount, lat, lon in test_cases:
    send_transaction(user_id, amount, lat, lon)
    time.sleep(1.5) # Ekranda akışı film gibi izleyebilmen için 1.5 saniye mola

print("\n Test tamamlandı! Dashboard'u kontrol et.")
