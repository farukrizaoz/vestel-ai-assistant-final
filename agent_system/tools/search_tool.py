"""
Basit ve Etkili Ürün Arama Aracı
Agent karar versin, biz sadece ham veri sağlayalım
"""

import sqlite3
from crewai.tools import BaseTool
from agent_system.config import PRODUCTS_DATABASE_PATH


class VestelProductSearchTool(BaseTool):
    name: str = "Vestel Ürün Arama"
    description: str = """
    Vestel ürün veritabanında esnek arama yapar.
    Keywords ve description alanlarından ürün bilgilerini döndürür.
    Agent kendisi hangi ürünlerin uygun olduğuna karar verir.
    """

    def _run(self, query: str) -> str:
        """Basit ama kapsamlı ürün arama"""
        try:
            conn = sqlite3.connect(PRODUCTS_DATABASE_PATH)
            cursor = conn.cursor()
            
            # Geniş arama - hem keywords hem de desc alanlarında ara
            search_query = f"%{query.lower()}%"
            
            sql = """
            SELECT model_number, name, manual_keywords, manual_desc
            FROM products 
            WHERE LOWER(name) LIKE ? 
               OR LOWER(model_number) LIKE ?
               OR LOWER(manual_keywords) LIKE ?
               OR LOWER(manual_desc) LIKE ?
            LIMIT 20
            """
            
            cursor.execute(sql, (search_query, search_query, search_query, search_query))
            results = cursor.fetchall()
            
            conn.close()
            
            if not results:
                return f"'{query}' için hiç ürün bulunamadı."
            
            # Agent'ın karar verebilmesi için tüm bilgileri ver
            output = f"'{query}' arama sonuçları ({len(results)} ürün):\n\n"
            
            for i, (model, name, keywords, desc) in enumerate(results, 1):
                output += f"=== ÜRÜN {i} ===\n"
                output += f"Model: {model or 'Belirtilmemiş'}\n"
                output += f"İsim: {name or 'Belirtilmemiş'}\n"
                output += f"Özellikler: {keywords[:300] if keywords else 'Belirtilmemiş'}...\n"
                output += f"Açıklama: {desc or 'Açıklama yok'}\n\n"
            
            output += "Bu ürünler arasından kullanıcının isteğine en uygun olanları seç ve öner."
            
            return output
            
        except Exception as e:
            return f"Arama hatası: {str(e)}"


# Agent sistemine export et
ImprovedProductSearchTool = VestelProductSearchTool
