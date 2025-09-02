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
        """Gelişmiş esnek ürün arama"""
        try:
            conn = sqlite3.connect(PRODUCTS_DATABASE_PATH)
            cursor = conn.cursor()
            
            # Arama terimlerini kelimelere ayır ve temizle
            search_terms = [term.strip().lower() for term in query.lower().split() if len(term) > 1]
            
            if not search_terms:
                return f"'{query}' için geçerli arama terimi bulunamadı."
            
            # Her kelime için LIKE koşulu oluştur
            conditions = []
            params = []
            
            for term in search_terms:
                term_pattern = f"%{term}%"
                conditions.append("""
                    (LOWER(name) LIKE ? 
                     OR LOWER(model_number) LIKE ?
                     OR LOWER(manual_keywords) LIKE ?
                     OR LOWER(manual_desc) LIKE ?)
                """)
                params.extend([term_pattern, term_pattern, term_pattern, term_pattern])
            
            # Tüm kelimelerin bulunduğu ürünleri ara (AND mantığı)
            sql = f"""
            SELECT model_number, name, manual_keywords, manual_desc
            FROM products 
            WHERE {' AND '.join(conditions)}
            LIMIT 20
            """
            
            cursor.execute(sql, params)
            results = cursor.fetchall()
            
            # Eğer tüm kelimelerle bulamazsa, en az yarısını içeren ürünleri ara
            if not results and len(search_terms) > 1:
                half_conditions = conditions[:max(1, len(conditions)//2)]
                half_params = params[:len(half_conditions)*4]
                
                sql = f"""
                SELECT model_number, name, manual_keywords, manual_desc
                FROM products 
                WHERE {' AND '.join(half_conditions)}
                LIMIT 20
                """
                
                cursor.execute(sql, half_params)
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
