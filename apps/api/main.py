from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import pika
import json
import uuid
from datetime import datetime, timedelta 

# Veritabanı bağlantımızı içeri aktarıyoruz
from apps.api.database import SessionLocal, TransactionRecord

app = FastAPI(title="Fraud Detection API")

# CORS İzinleri (Frontend'in API ile konuşabilmesi için)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Geliştirme ortamında tümüne izin veriyoruz
    allow_credentials=True,
    allow_methods=["*"],  # GET, POST, PUT, DELETE vb. hepsine izin ver
    allow_headers=["*"],
)

# RabbitMQ'ya kullanıcı adı ve şifre ile bağlanıyoruz
RABBITMQ_URL = "amqp://admin:secretpassword@127.0.0.1:5672/"
QUEUE_NAME = "pending_transactions"

class TransactionRequest(BaseModel):
    user_id: int
    amount: float
    latitude: float
    longitude: float

@app.on_event("startup")
def startup_event():
    global rabbit_conn, rabbit_channel
    try:
        # ConnectionParameters yerine URLParameters kullanıyoruz ki şifreyi çözebilsin
        rabbit_conn = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
        rabbit_channel = rabbit_conn.channel()
        rabbit_channel.queue_declare(queue=QUEUE_NAME, durable=True)
        print("✅ RabbitMQ bağlantısı başarılı!")
    except Exception as e:
        print(f"❌ RabbitMQ Bağlantı Hatası: {e}")

@app.on_event("shutdown")
def shutdown_event():
    if rabbit_conn and rabbit_conn.is_open:
        rabbit_conn.close()

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "api"}

@app.post("/process-transaction")
def process_transaction(tx: TransactionRequest):
    transaction_id = str(uuid.uuid4())
    message = {
        "transaction_id": transaction_id,
        "user_id": tx.user_id,
        "amount": tx.amount,
        "latitude": tx.latitude,
        "longitude": tx.longitude,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

    try:
        # 🛡️ Docker ağı içindeki 'rabbitmq' servisine bağlanıyoruz.
        rabbitmq_url = os.getenv("RABBITMQ_URL", "amqp://admin:secretpassword@rabbitmq:5672/")
        connection = pika.BlockingConnection(pika.URLParameters(rabbitmq_url))
        channel = connection.channel()
        
        # Kuyruğun var olduğundan emin oluyoruz
        channel.queue_declare(queue="pending_transactions", durable=True)
        
        channel.basic_publish(
            exchange='',
            routing_key="pending_transactions",  
            body=json.dumps(message),
            properties=pika.BasicProperties(delivery_mode=2)
        )
        
        # İşlem bitince kanalı kapatıyoruz (Memory Leak olmasın)
        connection.close()
        
        return {"status": "accepted", "transaction_id": transaction_id, "message": "İşlem analize gönderildi."}
    except Exception as e:
        # Hata detayını terminalde ve test scriptinde görebilmek için string olarak basıyoruz
        print(f"❌ RabbitMQ Kritik Hata: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ---------------------------------------------------------
# ENDPOINT 1: KULLANICI GEÇMİŞİ VE FRAUD RAPORU
# ---------------------------------------------------------
@app.get("/transactions/{user_id}")
def get_user_transactions(user_id: int):
    """
    Belirli bir kullanıcının geçmiş işlemlerini ve fraud (anomali) analiz sonuçlarını getirir.
    """
    db = SessionLocal()
    try:
        # Kullanıcıya ait işlemleri tarihe göre (en yeniden en eskiye) sıralayarak çekiyoruz
        transactions = db.query(TransactionRecord).filter(
            TransactionRecord.user_id == user_id
        ).order_by(TransactionRecord.timestamp.desc()).all()
        
        if not transactions:
            return {"user_id": user_id, "message": "Bu kullanıcıya ait işlem bulunamadı."}

        # Sadece bu kullanıcının toplam kaç fraud işlemi olduğunu da hesaplayalım 
        fraud_count = sum(1 for tx in transactions if tx.is_fraud)

        return {
            "user_id": user_id,
            "total_transactions": len(transactions),
            "total_frauds": fraud_count,
            "history": transactions
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail="Veritabanı okuma hatası")
    finally:
        db.close() # Kaynak sızıntısını önlemek için bağlantıyı kesinlikle kapatıyoruz

# ---------------------------------------------------------
# YENİ EKLENEN ENDPOINT 2: ZAMAN ARALIKLI FRAUD RAPORU
# ---------------------------------------------------------
@app.get("/frauds")
def get_recent_frauds(hours: int = Query(24, description="Son kaç saatteki fraud işlemleri getirilsin?")):
    """
    Belirli bir zaman aralığında (varsayılan son 24 saat) tespit edilen şüpheli (fraud) işlemleri listeler.
    """
    db = SessionLocal()
    try:
        # Şu anki zamandan, istenen saat kadar geriye giderek bir sınır belirliyoruz
        time_threshold = datetime.utcnow() - timedelta(hours=hours)

        # Veritabanında is_fraud=True olan ve zamanı threshold'dan büyük olanları çekiyoruz
        fraud_transactions = db.query(TransactionRecord).filter(
            TransactionRecord.is_fraud == True,
            TransactionRecord.timestamp >= time_threshold
        ).order_by(TransactionRecord.timestamp.desc()).all()

        return {
            "time_window_hours": hours,
            "total_frauds_found": len(fraud_transactions),
            "frauds": fraud_transactions
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail="Veritabanı okuma hatası")
    finally:
        db.close()

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        # Tüm bağlı istemcilere mesaj gönder
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                print(f"WebSocket gönderme hatası: {e}")

manager = ConnectionManager()

# WEBSOCKET ENDPOINT'İ (Frontend buraya bağlanacak)
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Frontend'den bir mesaj gelirse (Ping vs.) burada karşıla
            data = await websocket.receive_text()
            # Şimdilik sadece dinliyoruz, biz esas veriyi Worker'dan basacağız
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# WORKER'DAN GELEN SİNYALİ WEBSOCKET İLE FRONTEND'E AKTARAN KÖPRÜ
@app.post("/broadcast")
async def broadcast_transaction(transaction: dict):
    # Worker'dan gelen JSON verisini al ve WebSocket üzerinden tüm Frontend'lere canlı yayınla!
    await manager.broadcast(transaction)
    return {"message": "Yayınlandı"}