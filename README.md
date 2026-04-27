# 🛡️ Fraud Radar: Gerçek Zamanlı E-Ticaret Anomali Tespit Platformu

## 1. Projenin Amacı ve Kapsamı
Bu proje, e-ticaret platformlarında gerçekleşen ödeme ve işlem (transaction) verilerini gerçek zamanlı toplayan, asenkron bir kural motorundan geçirerek şüpheli (fraud) işlemleri tespit eden ve sonuçları modern bir web arayüzünde görselleştiren dağıtık bir sistemdir. Ayrıca, entegre edilen Model Context Protocol (MCP) sayesinde yapay zeka ajanlarının sistemdeki anomali verilerini doğal dille sorgulayabilmesine olanak tanır. 

Temel amaç, yüksek trafik (load) altında ana sistemi bloklamadan fraud kontrolü yapabilen dayanıklı (resilient) ve ölçeklenebilir bir mimari kurmaktır.

---

## 2. Sistem Mimarisi ve Komponentlerin Açıklaması
Proje, bağımsız bileşenlerin birbirini engellemeden çalışabilmesi için **Mikroservis Mimarisi** standartlarında tasarlanmıştır:

* **API Service (FastAPI):** Dış dünyadan gelen verileri karşılar. Ana thread'i bloklamamak için işlemleri doğrudan RabbitMQ kuyruğuna yazar. Ayrıca Frontend'i anlık beslemek için WebSocket bağlantılarını yönetir.
* **Worker Service (Python):** Sistemin "Kural Motoru"dur. RabbitMQ'yu dinler. Gelen her işlemi Redis ve PostgreSQL üzerindeki geçmiş state'ler ile kıyaslayarak (Hız, Tutar, Konum kuralları) anomali tespiti yapar.
* **MCP Server:** Yapay zeka asistanlarının (Claude, Cursor vb.) fraud verilerine erişebilmesi için gerekli araçları (tools) dışa açan katmandır.
* **Frontend (React + Vite + Tailwind):** İşlem akışını ve risk analiz grafiklerini WebSocket üzerinden gecikmesiz olarak kullanıcıya sunar.

---

## 3. Teknoloji Seçimleri ve Gerekçeleri

* **Anomali Tespitinde Cache Yönetimi (Redis):** "Hız (Velocity) Kontrolü" kuralı gereği, bir kullanıcının son 1 dakika içindeki işlem sayısını saniyesinde bilmemiz gerekir. Bu soruyu her işlemde ilişkisel veritabanına (PostgreSQL) sormak, yüksek trafikte ciddi bir Disk I/O darboğazı (bottleneck) yaratır. Bu nedenle, hız takibi için okuma/yazma süresi mili-saniyeler seviyesinde olan In-Memory cache (Redis) tercih edilmiştir.
* **Asenkron İletişim (RabbitMQ):** E-ticaret sistemlerinde anlık trafik patlamaları yaşanabilir. Gelen istekleri doğrudan senkron işlemek sistemin çökmesine neden olur. RabbitMQ, bu yükü tamponlayarak (buffering) Worker'ların kendi kapasitelerine göre veriyi eritmesini sağlar.
* **Kalıcı Veri ve Durum (PostgreSQL):** İşlem logları finansal veri niteliği taşıdığı için ACID prensiplerine tam uyumlu bir ilişkisel veritabanı kullanılmıştır.

---

## 4. Kurulum Adımları (Detaylı)

Tüm sistem, bağımlılıkları (Postgres, Redis, RabbitMQ) ile birlikte Container mimarisine uygun tasarlanmıştır.

**Gereksinimler:** Sistemin çalışması için Docker ve Docker Compose kurulu olmalıdır.

1. Proje dizinine gidin:
   ```bash
   cd fraud-detection-platform
   ```
2. Tüm mimariyi tek komutla arka planda (detached mode) ayağa kaldırın:
   ```bash
   docker-compose up -d
   ```
3. Servislerin tam olarak hazır olması ve veritabanı bağlantılarının kurulması yaklaşık 10-15 saniye sürebilir. Servisler hazır olduğunda uygulamalara erişebilirsiniz.

---

## 5. Kullanım Rehberi

Sistem ayağa kalktıktan sonra aşağıdaki adreslerden komponentlere erişebilirsiniz:

* **Frontend Dashboard:** http://localhost:5173
  * Sol panelde şüpheli işlemlerin zamana göre dağılım grafiğini ve derinlemesine kullanıcı analizini yapabilirsiniz.
  * Sağ panelde canlı veri akışını (WebSocket) ve anlık radar uyarılarını izleyebilirsiniz.
* **API Swagger Arayüzü:** http://localhost:8000/docs

---

## 6. API ve MCP Dokümantasyonu

### REST API Endpoints
* `GET /transactions/{user_id}`: Belirli bir kullanıcının geçmiş tüm işlem sabıka kaydını ve detaylarını getirir.
* `GET /frauds?hours={X}`: Son `X` saat içerisinde tespit edilen tüm şüpheli (fraud) işlemlerin detaylı listesini döner.

### MCP (Model Context Protocol) Araçları
Sistem, yapay zeka ajanları için aşağıdaki araçları (tools) sunar:
* `get_recent_frauds`: Zaman aralığı parametresi alarak son anomali olaylarını listeler.
* `check_user_status`: Bir kullanıcı kimliği alarak, kullanıcının risk profilini analiz eder.

---

## 7. Script'lerin Kullanımı ve Parametreleri

Kural motorunu test etmek ve sisteme dışarıdan veri basmak için ana dizindeki `.sh` scriptlerini kullanabilirsiniz.

**Otomatik Test Script'i (`auto-test.sh`):**
Belirtilen parametrelere göre sistemi rastgele işlemlerle bombardımana tutar ve kural ihlali (ışınlanma, anormal tutar, yüksek hız) senaryoları yaratır.
   ```bash
   ./auto-test.sh --duration=60 --rate=5 --anomaly-chance=30
   ```
* `--duration`: Scriptin saniye cinsinden çalışma süresi.
* `--rate`: Saniyede gönderilecek ortalama işlem sayısı.
* `--anomaly-chance`: Gelen bir işlemin fraud (kural dışı) olma ihtimali (yüzde olarak).

**Manuel Veri Girişi Script'i (`manual-input.sh`):**
Uç nokta (edge-case) testleri yapmak için belirli bir kullanıcıya tekil veri fırlatır.
   ```bash
   # Kullanım: ./manual-input.sh <user_id> <amount> <location_lat,location_lon>
   ./manual-input.sh 999 850000 90.0,135.0
   ```

---

## 8. MCP Test Yönteminin Belgelenmesi

MCP sunucusunun API ile doğru iletişim kurduğunu doğrulamak için, MCP konteynerinin içine girerek doğrudan yerel ağ (Docker network) üzerinden sorgu simüle edebilirsiniz:

   ```bash
   docker exec -it fraud-mcp python -c "import urllib.request; print(urllib.request.urlopen('http://api:8000/frauds?hours=24').read().decode())"
   ```
Bu komut, MCP Server'ın çalıştığı izole ortamdan API'ye ulaştığını ve JSON formatında fraud verilerini başarıyla çekebildiğini kanıtlar.

---

## 9. Sorun Giderme (Troubleshooting) Rehberi

**Sorun 1: Stres testini başlattım ancak Dashboard'daki "Canlı Akış" paneline veriler düşmüyor.**
* **Neden (Race Condition):** Mikroservislerin ilk başlatılma anında, RabbitMQ portlarını tam açmadan önce `Worker` servisi bağlanmaya çalışmış olabilir. Bağlantı reddedildiğinde (Connection Refused) Worker servisi kapanır. Gönderdiğiniz işlemler kaybolmaz, RabbitMQ kuyruğunda işlenmeyi bekler.
* **Çözüm:** İşçi servisini yeniden başlatarak kuyruktaki verilerin işlenmesini sağlayın:
   ```bash
   docker-compose restart worker
   ```

**Sorun 2: Frontend veya API kodunda değişiklik yaptım ancak localhost'ta güncel halini göremiyorum.**
* **Neden:** Docker, inşa (build) sürecini hızlandırmak için mevcut imajları önbellekte (cache) tutar. Kod değişiklikleri mevcut konteynere otomatik yansımaz.
* **Çözüm:** İlgili servisi yeniden build ederek ayağa kaldırın:
   ```bash
   docker-compose up -d --build frontend
   ```