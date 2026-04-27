import asyncio
import json
import urllib.request
import urllib.error
from typing import Optional

from mcp.server.fastmcp import FastMCP

# MCP Sunucusunu Başlatıyoruz
mcp = FastMCP("Kartaca Fraud Detection MCP")

# Ana API'mizin adresi (API servisimiz çalışır durumda olmalı)
API_BASE_URL = "http://api:8000"

def fetch_from_api(endpoint: str) -> dict:
    """Yardımcı Fonksiyon: Ana API'ye HTTP isteği atar."""
    url = f"{API_BASE_URL}{endpoint}"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode())
    except urllib.error.URLError as e:
        return {"error": f"API Bağlantı Hatası: {e.reason}"}

# ---------------------------------------------------------
# TOOL 1: KULLANICI DURUMUNU KONTROL ET
# ---------------------------------------------------------
@mcp.tool()
def check_user_status(user_id: int) -> str:
    """
    Belirli bir kullanıcının geçmiş işlemlerini ve fraud (dolandırıcılık) geçmişini kontrol eder.
    
    Args:
        user_id: Kontrol edilecek kullanıcının ID'si.
    """
    result = fetch_from_api(f"/transactions/{user_id}")
    
    if "error" in result:
        return f"Hata: Veri çekilemedi. ({result['error']})"
    if "message" in result:
        return f"Kullanıcı {user_id} için işlem bulunamadı."
        
    return (f"Kullanıcı {user_id} Raporu:\n"
            f"- Toplam İşlem: {result.get('total_transactions', 0)}\n"
            f"- Şüpheli (Fraud) İşlem: {result.get('total_frauds', 0)}\n"
            f"Tüm Detaylar: {json.dumps(result.get('history', []), indent=2, ensure_ascii=False)}")

# ---------------------------------------------------------
# TOOL 2: SON FRAUD İŞLEMLERİNİ GETİR
# ---------------------------------------------------------
@mcp.tool()
def get_recent_frauds(hours: int = 24) -> str:
    """
    Belirtilen zaman aralığındaki (saat bazında) şüpheli (fraud) işlemleri listeler.
    
    Args:
        hours: Geriye dönük kaç saatlik verinin getirileceği. (Varsayılan: 24)
    """
    result = fetch_from_api(f"/frauds?hours={hours}")
    
    if "error" in result:
        return f"Hata: Veri çekilemedi. ({result['error']})"
        
    frauds = result.get('frauds', [])
    if not frauds:
        return f"Son {hours} saat içinde hiç fraud (şüpheli) işlem bulunamadı. ✅"
        
    return (f"Son {hours} saatteki Şüpheli İşlem (Fraud) Raporu:\n"
            f"- Toplam Tespit Edilen Fraud: {result.get('total_frauds_found', 0)}\n"
            f"Detaylar: {json.dumps(frauds, indent=2, ensure_ascii=False)}")


if __name__ == "__main__":
    # stdio (Standart I/O) iletişiminde ekrana normal 'print' ile yazı YAZILAMAZ! 
    # Çünkü bu, veri iletişim borusunu tıkar ve JSON formatını bozar.
    mcp.run(transport="stdio")