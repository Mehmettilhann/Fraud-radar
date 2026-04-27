import math
import redis
import json
import os
from datetime import datetime, timedelta
from database import SessionLocal, TransactionRecord
from sqlalchemy import desc, func

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
r = redis.Redis(host=REDIS_HOST, port=6379, db=0, decode_responses=True)

def calculate_distance(lat1, lon1, lat2, lon2):
    """İki GPS koordinatı arasındaki kuş uçuşu mesafeyi (KM) hesaplar."""
    R = 6371  
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def evaluate_transaction(data):
    """Kartaca Brief: En az 2 kural ihlali FRAUD sayılır."""
    violation_count = 0
    reasons = []
    
    user_id = data.get("user_id")
    amount = float(data.get("amount", 0))
    current_lat = float(data.get("latitude", 0))
    current_lon = float(data.get("longitude", 0))
    # Zaman hesabında kullanmak üzere işlemin anlık zamanı
    current_time = datetime.utcnow()

    # =========================================================
    # KURAL 1: HIZ (VELOCITY) KONTROLÜ
    # Brief: Aynı kullanıcının son 1 dakika içerisinde 5’ten fazla işlem yapması
    # =========================================================
    velocity_key = f"user:{user_id}:velocity"
    tx_count = r.incr(velocity_key)
    if tx_count == 1:
        r.expire(velocity_key, 60) # 1 dakikalık pencere (TTL)
        
    if tx_count > 5:
        violation_count += 1
        reasons.append(f"Hız İhlali (1 dk içinde {tx_count} işlem)")

    db = SessionLocal()
    try:
        # =========================================================
        # KURAL 2: TUTAR (AMOUNT) KONTROLÜ
        # Brief: İşlem tutarının, son 24 saatteki ortalama tutarın 3 katından fazla olması
        # =========================================================
        yesterday = current_time - timedelta(days=1)
        avg_amount_result = db.query(func.avg(TransactionRecord.amount)).filter(
            TransactionRecord.user_id == user_id,
            TransactionRecord.timestamp >= yesterday
        ).scalar()
        
        avg_amount = float(avg_amount_result) if avg_amount_result else 0.0

        # Eğer ortalama 0 ise (ilk işlem), mantıken 3 katı hesaplanamaz. 
        # Ama sistemi kandırmamaları için basit bir alt limit koyuyoruz.
        if avg_amount > 0 and amount > (avg_amount * 3):
            violation_count += 1
            reasons.append(f"Anormal Tutar (Ort: {avg_amount:.0f} TL, Gelen: {amount} TL)")
        elif avg_amount == 0 and amount > 5000: # Sisteme ilk kez giren biri aniden devasa çekerse (Ekstra Güvenlik)
            violation_count += 1
            reasons.append(f"Şüpheli İlk İşlem Tutarı ({amount} TL)")

        # =========================================================
        # KURAL 3: KONUM (LOCATION) KONTROLÜ (Zaman + Mesafe)
        # Brief: İki işlem arası sürenin, o mesafeyi katetmek için imkansız olması
        # =========================================================
        last_location_key = f"user:{user_id}:last_location"
        cached_location = r.get(last_location_key)

        last_lat, last_lon, last_timestamp = None, None, None

        if cached_location:
            last_loc = json.loads(cached_location)
            last_lat, last_lon = last_loc["lat"], last_loc["lon"]
            last_timestamp = datetime.fromisoformat(last_loc["timestamp"])
        else:
            # Redis'te yoksa DB'den en son işleme bak
            last_tx = db.query(TransactionRecord).filter(TransactionRecord.user_id == user_id).order_by(desc(TransactionRecord.timestamp)).first()
            if last_tx:
                last_lat, last_lon = float(last_tx.latitude), float(last_tx.longitude)
                # Timestamp timezone offset'i atarak parse et (Z -> +00:00 vs.)
                last_timestamp = last_tx.timestamp.replace(tzinfo=None)

        if last_lat and last_lon and last_timestamp:
            distance_km = calculate_distance(current_lat, current_lon, last_lat, last_lon)
            time_diff_hours = (current_time - last_timestamp).total_seconds() / 3600.0

            if time_diff_hours > 0:
                speed_kmh = distance_km / time_diff_hours
                # Ticari bir uçak maksimum 900-1000 km/s hızla uçar.
                # Eğer saatteki hızı 1000 km'den fazlaysa, bu adam ışınlanmıştır!
                if speed_kmh > 1000:
                    violation_count += 1
                    reasons.append(f"İmkansız Konum (Işınlanma Hızı: {int(speed_kmh)} km/s)")
            elif distance_km > 50:
                # Saniye farkı yok ama 50 km uzakta (Aynı anda iki farklı yerde olma durumu)
                violation_count += 1
                reasons.append("İmkansız Konum (Aynı saniyede farklı lokasyon)")

        # Bir sonraki işlem için anlık konumu ve zamanı Redis'e yaz
        r.set(last_location_key, json.dumps({
            "lat": current_lat,
            "lon": current_lon,
            "timestamp": current_time.isoformat()
        }), ex=86400) # 24 saat önbellekte tut

    except Exception as e:
        print(f"Kural Motoru Hatası: {e}")
    finally:
        db.close()

    #En az ikisi ihlal edildiğinde işlem şüpheli sayılır!
    is_fraud = violation_count >= 2
    
    final_reasons = ", ".join(reasons) if is_fraud else None
    
    return is_fraud, final_reasons