import asyncio
import aio_pika
import json
import requests
import os
from datetime import datetime
from database import SessionLocal, TransactionRecord
from rules import evaluate_transaction

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://admin:secretpassword@rabbitmq:5672/")
QUEUE_NAME = "pending_transactions"

async def process_message(message: aio_pika.IncomingMessage):
    async with message.process():
        data = json.loads(message.body.decode())
        print(f"\n📥 Yeni işlem yakalandı: {data['transaction_id']}")

        is_fraud, reasons = evaluate_transaction(data)

        try:
            dt_timestamp = datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))
        except ValueError:
            dt_timestamp = datetime.utcnow()

        db = SessionLocal()
        try:
            # 1. VERİTABANINA KAYIT
            record = TransactionRecord(
                id=data["transaction_id"],
                user_id=data["user_id"],
                amount=data["amount"],
                latitude=data["latitude"],
                longitude=data["longitude"],
                timestamp=dt_timestamp,
                is_fraud=is_fraud,
                fraud_reasons=reasons
            )
            db.add(record)
            db.commit()
            
            status_icon = " FRAUD" if is_fraud else " ONAYLANDI"
            reason_text = reasons if reasons else "Temiz"
            print(f"💾 Karar: {status_icon} | Kullanıcı: {data['user_id']} | Tutar: {data['amount']} | Sebep: {reason_text}")
        
            # 2. WEBSOCKET İÇİN API'YE SİNYAL GÖNDERME
            try:
                tx_data = {
                    "user_id": data["user_id"],
                    "amount": data["amount"],
                    "is_fraud": is_fraud,
                    "fraud_reasons": reasons if is_fraud else None
                } 
                # Şimdilik bloklamayı önlemek için 1 saniyelik timeout koyuyoruz.
                # API servisinin Docker adını kullanıyoruz.
                API_URL = os.getenv("API_URL", "http://api:8000/broadcast")
                requests.post(API_URL, json=tx_data, timeout=1)
            except Exception as e:
                print(f" Canlı yayın sinyali API'ye ulaştırılamadı: {e}")

        except Exception as e:
            print(f" DB Kayıt Hatası: {e}")
            db.rollback()
        finally:
            db.close()

async def main():
    connection = await aio_pika.connect_robust(RABBITMQ_URL)
    channel = await connection.channel()
    queue = await channel.declare_queue(QUEUE_NAME, durable=True)
    
    print("🚀 Worker (Beyin) başarıyla başlatıldı. Kuyruk dinleniyor...")
    await queue.consume(process_message)
    
    try:
        await asyncio.Future()
    finally:
        await connection.close()

if __name__ == "__main__":
    asyncio.run(main())
