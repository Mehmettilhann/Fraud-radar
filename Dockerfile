# Temel imaj olarak hafif bir Python sürümü seçiyoruz
FROM python:3.10-slim

# Çalışma dizinini belirliyoruz
WORKDIR /app

# Gerekli sistem paketlerini yüklüyoruz (Postgres bağlantısı vb. için gerekebilir)
RUN apt-get update && apt-get install -y gcc libpq-dev && rm -rf /var/lib/apt/lists/*

# Önce gereksinimleri kopyalayıp kuruyoruz (Docker cache avantajı için)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Tüm proje kodlarını kopyalıyoruz
COPY . .

# Konteynerin hangi portu dinleyeceğini belirtiyoruz (API için)
EXPOSE 8000