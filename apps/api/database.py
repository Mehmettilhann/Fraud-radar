import os
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker

#  Docker'daki postgres servisine bağlanıyoruz.
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@postgres:5432/fraud_db")

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class TransactionRecord(Base):
    __tablename__ = "transactions"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    amount = Column(Float)
    latitude = Column(Float)
    longitude = Column(Float)
    timestamp = Column(DateTime)
    is_fraud = Column(Boolean)
    fraud_reasons = Column(String)

# Sadece okuma yapacağımız için Base.metadata.create_all() kullanmıyoruz. 
# Tabloları zaten Worker oluşturdu!